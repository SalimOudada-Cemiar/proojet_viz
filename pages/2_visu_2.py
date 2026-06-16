import streamlit as st
import plotly.graph_objects as go
import pandas as pd
import numpy as np

st.set_page_config(page_title="Taux d'effort locatif", layout="wide")

st.markdown("""
<style>
    .main-header {
        font-size: 2.5rem;
        font-weight: 700;
        color: #1f2937;
        margin-bottom: 0.5rem;
        text-align: center;
    }
    .sub-header {
        font-size: 1.1rem;
        color: #6b7280;
        text-align: center;
        margin-bottom: 2rem;
    }
    .main .block-container {
        overflow: hidden;
        max-height: 100vh;
    }
    section.main {
        overflow: hidden;
    }
</style>
""", unsafe_allow_html=True)

st.markdown('<p class="main-header">Pression financière du logement</p>', unsafe_allow_html=True)
st.markdown('<p class="sub-header">Proportion du revenu médian consacrée au loyer dans les grandes villes canadiennes</p>', unsafe_allow_html=True)

RENT_FILES = {
    'loyer_montreal.csv': 'Montréal',
    'loyer_quebec.csv': 'Québec',
    'loyer_gatineau.csv': 'Gatineau',
    'loyer_ottawa.csv': 'Ottawa',
    'loyer_calgary.csv': 'Calgary',
    'loyer_edmonton.csv': 'Edmonton',
    'loyer_toronto.csv': 'Toronto',
    'loyer_vancouver.csv': 'Vancouver',
    'loyer_winnipeg.csv': 'Winnipeg'
}

HOUSING_MAP = {
    'Bachelor units': 'Studio',
    'One bedroom units': '1 chambre',
    'Two bedroom units': '2 chambres',
    'Three bedroom units': '3 chambres'
}

HOUSING_ORDER = ['Studio', '1 chambre', '2 chambres', '3 chambres']
CITY_ORDER = ['Vancouver', 'Toronto', 'Calgary', 'Ottawa', 'Gatineau', 'Montréal', 'Winnipeg', 'Edmonton', 'Québec']
TARGET_REGIONS = 'Montréal|Québec|Gatineau|Ottawa|Calgary|Edmonton|Toronto|Vancouver|Winnipeg'


@st.cache_data
def load_data():
    df_income = process_income_data('data/revenus.csv')
    df_rent = process_rent_data('data')
    df_merged = pd.merge(df_rent, df_income, on=['Year', 'City'])
    df_merged['Effort_Rate'] = (df_merged['Average_Rent'] * 12 / df_merged['Median_Income']) * 100
    df_merged = df_merged.dropna(subset=['Average_Rent', 'Median_Income', 'Effort_Rate'])
    return df_merged


def process_income_data(path):
    df_inc_raw = pd.read_csv(path, encoding='utf-8', low_memory=False)
    df_inc = df_inc_raw[
        (df_inc_raw['Income source'] == 'Total income') & 
        (df_inc_raw['Statistics'] == 'Median income (excluding zeros)') &
        (df_inc_raw['Age group'] == '15 years and over') & 
        (df_inc_raw['Gender'] == 'Total - Gender')
    ]
    df_inc = df_inc[df_inc['GEO'].str.contains(TARGET_REGIONS, na=False, case=False)]
    df_inc = df_inc[['REF_DATE', 'GEO', 'VALUE']]
    df_inc.columns = ['Year', 'City_Raw', 'Median_Income']
    df_inc['City'] = df_inc['City_Raw'].str.split(',').str[0].str.strip()
    df_inc.loc[df_inc['City_Raw'].str.contains('Ottawa', case=False, na=False), 'City'] = 'Ottawa'
    df_gatineau = df_inc[df_inc['City'] == 'Ottawa'].copy()
    df_gatineau['City'] = 'Gatineau'
    df_inc = pd.concat([df_inc, df_gatineau], ignore_index=True)
    df_inc['Year'] = df_inc['Year'].astype(int)
    df_inc['Median_Income'] = pd.to_numeric(df_inc['Median_Income'], errors='coerce')
    return df_inc[['Year', 'City', 'Median_Income']]


def process_rent_data(folder_path):
    all_rents = []
    for file_name, city_name in RENT_FILES.items():
        try:
            df_city_raw = pd.read_csv(f"{folder_path}/{file_name}", encoding='utf-8', low_memory=False)
            if city_name == 'Gatineau':
                df_city = df_city_raw[df_city_raw['GEO'] == 'Ottawa-Gatineau, Quebec part, Ontario/Quebec'].copy()
            elif city_name == 'Ottawa':
                df_city = df_city_raw[df_city_raw['GEO'] == 'Ottawa-Gatineau, Ontario part, Ontario/Quebec'].copy()
            else:
                df_city = df_city_raw[df_city_raw['GEO'].str.contains(city_name, na=False, case=False)].copy()
            df_city = df_city[df_city['Type of structure'] == 'Row and apartment structures of three units and over']
            df_city['Housing_Type'] = df_city['Type of unit'].map(HOUSING_MAP)
            df_city = df_city.dropna(subset=['Housing_Type'])
            df_city = df_city[['REF_DATE', 'Housing_Type', 'VALUE']]
            df_city.columns = ['Year', 'Housing_Type', 'Average_Rent']
            df_city['City'] = city_name
            df_city['Year'] = df_city['Year'].astype(int)
            df_city['Average_Rent'] = pd.to_numeric(df_city['Average_Rent'], errors='coerce')
            all_rents.append(df_city)
        except FileNotFoundError:
            continue
    if not all_rents:
        return pd.DataFrame(columns=['Year', 'City', 'Housing_Type', 'Average_Rent'])
    return pd.concat(all_rents, ignore_index=True)


def create_heatmap(df, selected_year):
    df_year = df[df['Year'] == selected_year].copy()
    
    pivot_effort = df_year.pivot_table(index='City', columns='Housing_Type', values='Effort_Rate', aggfunc='mean')
    pivot_effort = pivot_effort.reindex(columns=HOUSING_ORDER)
    cities_present = [c for c in CITY_ORDER if c in pivot_effort.index]
    pivot_effort = pivot_effort.reindex(cities_present)
    
    pivot_rent = df_year.pivot_table(index='City', columns='Housing_Type', values='Average_Rent', aggfunc='mean')
    pivot_rent = pivot_rent.reindex(columns=HOUSING_ORDER).reindex(cities_present)
    
    pivot_income = df_year.pivot_table(index='City', columns='Housing_Type', values='Median_Income', aggfunc='mean')
    pivot_income = pivot_income.reindex(columns=HOUSING_ORDER).reindex(cities_present)
    
    z_values = pivot_effort.values
    rent_values = pivot_rent.values
    income_values = pivot_income.values
    
    annotations_text = np.where(np.isnan(z_values), '', np.char.add(np.round(z_values, 0).astype(int).astype(str), '%'))
    
    hover_text = []
    for i, city in enumerate(cities_present):
        row = []
        for j, housing in enumerate(HOUSING_ORDER):
            if np.isnan(z_values[i, j]):
                row.append('')
            else:
                text = (f"<b>{city}</b><br>Année: {selected_year}<br>Type: {housing}<br>"
                        f"Loyer moyen: {rent_values[i, j]:,.0f} $/mois<br>"
                        f"Revenu médian: {income_values[i, j]:,.0f} $/an<br>"
                        f"<b>Taux d'effort: {z_values[i, j]:.1f}%</b>")
                row.append(text)
        hover_text.append(row)
    
    fig = go.Figure(data=go.Heatmap(
        z=z_values, x=HOUSING_ORDER, y=cities_present, colorscale='Reds',
        zmin=0, zmax=100, text=annotations_text, texttemplate='%{text}',
        textfont={'size': 16, 'color': 'black', 'family': 'Arial Black'},
        hovertext=hover_text, hovertemplate='%{hovertext}<extra></extra>',
        colorbar=dict(
            title=dict(text='Taux d\'effort', side='right', font=dict(size=14)),
            ticksuffix='%', tickvals=[0, 30, 50, 70, 100], ticktext=['0%', '30%', '50%', '70%', '100%'],
            len=0.85, thickness=20, outlinewidth=0, bgcolor='rgba(255,255,255,0.9)'
        ),
        xgap=3, ygap=3
    ))
    
    fig.update_layout(
        title=dict(text=f'<b>Année {selected_year}</b>', font=dict(size=24, color='#1f2937'), x=0.5, xanchor='center'),
        xaxis=dict(title=dict(text='Type de logement', font=dict(size=14, color='#4b5563')), tickfont=dict(size=13, color='#374151'), side='bottom'),
        yaxis=dict(title=dict(text='', font=dict(size=14)), tickfont=dict(size=13, color='#374151')),
        height=550, margin=dict(l=120, r=80, t=70, b=70),
        paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)',
        hoverlabel=dict(bgcolor='white', font_size=13, font_family='Arial')
    )
    return fig


df = load_data()
available_years = sorted(df['Year'].unique())
min_year = max(1992, min(available_years))
max_year = min(2024, max(available_years))

selected_year = st.slider("Année", min_value=min_year, max_value=max_year, value=2022, step=1)

if selected_year in available_years:
    fig = create_heatmap(df, selected_year)
    st.plotly_chart(fig, use_container_width=True)
else:
    st.warning(f"Données non disponibles pour l'année {selected_year}")
