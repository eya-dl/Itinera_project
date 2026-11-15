"""Le dataset de notes contient-il un signal exploitable (goût par utilisateur, qualité par lieu) ?

Quatre tests, chacun comparé à une loi nulle obtenue en mélangeant les notes :
1) uniformité de la distribution des notes (khi-deux) ;
2) variance expliquée par l'utilisateur et par le lieu, contre permutations ;
3) fiabilité par moitiés : la note moyenne d'un lieu calculée sur deux moitiés aléatoires de ses notes est-elle corrélée ?
4) stabilité des goûts : la note moyenne qu'un utilisateur donne à une catégorie (train) prédit-elle celle du test ?
Usage : python scripts/diagnose_signal.py
"""
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import stats

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from app import config  # noqa: E402

rng = np.random.default_rng(0)
places = pd.read_csv(config.PLACES_CSV)
train = pd.read_csv(config.RATINGS_TRAIN_CSV)
test = pd.read_csv(ROOT / "data" / "ratings_test.csv")
al = pd.concat([train, test], ignore_index=True).merge(places[["place_id", "category", "rating", "city"]], on="place_id")
y = al["user_rating"].to_numpy(float)
L = ["# Diagnostic du signal dans les notes", "", f"{len(al)} notes, {al['user_id'].nunique()} utilisateurs, {al['place_id'].nunique()} lieux.", ""]

# 1) uniformité
bins = pd.cut(al["user_rating"], [0, 1.5, 2.5, 3.5, 4.5, 5.5], labels=[1, 2, 3, 4, 5])
obs = bins.value_counts().sort_index()
chi = stats.chisquare(obs)
L += ["## 1. Distribution des notes", "", "Part par note arrondie : " + ", ".join(f"{k} : {v / len(al):.1%}" for k, v in obs.items()),
      f"Khi-deux d'uniformité : p = {chi.pvalue:.3g}. La distribution est quasi plate (chaque note entre {obs.min() / len(al):.0%} et {obs.max() / len(al):.0%}) : "
      "l'uniformité exacte est rejetée (la note 1 est un peu sous-représentée), mais une distribution aussi plate ressemble à un tirage au sort ; "
      "des notes réelles de voyageurs sont en général concentrées sur 4-5.", ""]


# 2) variance expliquée
def r2(groups):
    m = pd.Series(y).groupby(groups).transform("mean").to_numpy()
    return 1 - ((y - m) ** 2).sum() / ((y - y.mean()) ** 2).sum()


res = {}
for name, g in [("utilisateur", al["user_id"].to_numpy()), ("lieu", al["place_id"].to_numpy()), ("utilisateur × catégorie", (al["user_id"].astype(str) + "_" + al["category"]).to_numpy())]:
    obs_r2 = r2(g)
    null = []
    for _ in range(200):
        ys = rng.permutation(y)
        m = pd.Series(ys).groupby(g).transform("mean").to_numpy()
        null.append(1 - ((ys - m) ** 2).sum() / ((ys - ys.mean()) ** 2).sum())
    null = np.array(null)
    res[name] = (obs_r2, null.mean(), (null >= obs_r2).mean())
L += ["## 2. Variance des notes expliquée (R²) contre notes mélangées (200 permutations)", "",
      "| Effet | R² observé | R² attendu si bruit pur | p (permutation) |", "|---|---|---|---|"]
L += [f"| {k} | {a:.4f} | {b:.4f} | {p:.3f} |" for k, (a, b, p) in res.items()]
L += ["", "Lecture : plus il y a de groupes, plus le R² est mécaniquement grand même sans signal, d'où la colonne « attendu ». L'effet utilisateur est faible mais significatif (certains utilisateurs notent plus généreusement) : "
      "il décale tous les lieux d'un même utilisateur de la même façon et ne change donc pas leur ordre. L'effet lieu n'est pas distinguable du bruit. "
      "L'effet utilisateur × catégorie contient l'effet utilisateur : le test 4 vérifie s'il y a un goût propre à la catégorie.", ""]

# 3) fiabilité par moitiés (lieux)
rs = []
for _ in range(200):
    h = rng.random(len(al)) < 0.5
    a = al[h].groupby("place_id")["user_rating"].mean()
    b = al[~h].groupby("place_id")["user_rating"].mean()
    j = a.index.intersection(b.index)
    rs.append(np.corrcoef(a[j], b[j])[0, 1])
rs = np.array(rs)
L += ["## 3. Fiabilité par moitiés — la qualité d'un lieu est-elle stable ?", "",
      f"Corrélation entre la note moyenne d'un lieu sur deux moitiés aléatoires de ses notes : r = {rs.mean():.3f} (écart-type {rs.std():.3f} sur 200 tirages). "
      "Un vrai effet « lieu » donnerait r nettement > 0 ; ici l'IC est centré sur 0." if abs(rs.mean()) < 2 * rs.std() else
      f"Corrélation entre moitiés : r = {rs.mean():.3f} (écart-type {rs.std():.3f}).", ""]
# corrélation avec la note du lieu fournie par le dataset
rr = stats.pearsonr(al["rating"], al["user_rating"])
L += [f"Corrélation entre la note d'un lieu dans `place_features.csv` et les notes des utilisateurs : r = {rr[0]:.3f} (p = {rr[1]:.2f}). "
      "C'est la base de la composante `quality` du moteur (poids 0,7 sur cette note).", ""]

# 4) stabilité des goûts par catégorie
tr = train.merge(places[["place_id", "category"]], on="place_id").groupby(["user_id", "category"])["user_rating"].agg(["mean", "count"])
te = test.merge(places[["place_id", "category"]], on="place_id").groupby(["user_id", "category"])["user_rating"].agg(["mean", "count"])
j = tr.join(te, lsuffix="_tr", rsuffix="_te", how="inner")
j = j[(j["count_tr"] >= 3) & (j["count_te"] >= 2)]
# centré par utilisateur pour retirer la générosité globale
um_tr = train.groupby("user_id")["user_rating"].mean()
um_te = test.groupby("user_id")["user_rating"].mean()
a = j["mean_tr"] - j.index.get_level_values(0).map(um_tr)
b = j["mean_te"] - j.index.get_level_values(0).map(um_te)
r_obs = np.corrcoef(a, b)[0, 1]
null = []
for _ in range(500):
    null.append(np.corrcoef(a, rng.permutation(b.to_numpy()))[0, 1])
L += ["## 4. Stabilité des goûts par catégorie (fondement du « contenu »)", "",
      f"{len(j)} couples (utilisateur, catégorie) avec ≥ 3 notes en entraînement et ≥ 2 en test. "
      f"Corrélation entre l'écart à sa moyenne que l'utilisateur donne à une catégorie en train et en test : r = {r_obs:.3f} "
      f"(loi nulle : moyenne {np.mean(null):+.3f}, écart-type {np.std(null):.3f}, p = {(np.array(null) >= r_obs).mean():.3f}). "
      "Si les utilisateurs avaient des goûts par catégorie, r serait nettement positif.", ""]

# 5) structure
cities = al.groupby("user_id")["city"].nunique()
L += ["## 5. Autres indices de données synthétiques", "",
      f"- Chaque utilisateur a noté des lieux dans {cities.min()} à {cities.max()} villes sur 5 (médiane {cities.median():.0f}) : "
      "un voyageur réel noterait surtout une ou deux villes.",
      f"- Nombre de notes par utilisateur : {al.groupby('user_id').size().min()} à {al.groupby('user_id').size().max()}, quasi constant ; "
      f"notes par lieu : {al.groupby('place_id').size().min()} à {al.groupby('place_id').size().max()}.", ""]
(ROOT / "reports").mkdir(exist_ok=True)
(ROOT / "reports" / "diagnostic_signal.md").write_text("\n".join(L), encoding="utf-8")
print("\n".join(L))
