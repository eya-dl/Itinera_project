# data-science — Partie 1 : données Indonesia Tourism

- `data/raw/indonesia/` : CSV d'origine (dataset Kaggle *Indonesia Tourism Destination*)
- `notebooks/01_nettoyage_preprocessing.ipynb` : nettoyage + preprocessing, étape par étape
- `scripts/01_prepare_indonesia.py` et `voyage/indonesia/loader.py` : même pipeline en script
- `data/processed/` : tables propres, variables, train/test des notes
- `reports/` : rapport qualité et figures

```bash
pip install -r requirements.txt
jupyter notebook notebooks/01_nettoyage_preprocessing.ipynb
python -m pytest
```
Les fichiers utiles au service de recommandation sont copiés dans `../ml-service/data/`
(`place_features.csv`, `ratings_train.csv`, `ratings_test.csv`) : à recopier après une nouvelle exécution du notebook.
