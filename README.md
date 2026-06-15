# proojet_viz

## Installation de uv

```powershell
winget install --id=astral-sh.uv -e
```

Fermer et rouvrir le terminal après l'installation.

## Lancer le projet

```powershell
uv sync
uv run streamlit run main.py
```

## Ajouter un package

Ne pas utiliser `pip install`. Utiliser à la place :

```powershell
uv add nom_du_package
```

## Modifier les visualisations

Les visualisations se trouvent dans `pages/` :

- `pages/1_visu_1.py`
- `pages/2_visu_2.py`
- `pages/3_visu_3.py`
- `pages/4_visu_4.py`
