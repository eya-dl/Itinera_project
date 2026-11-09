"""Évaluation hors ligne sur ratings_test.csv (20 % des notes de chaque utilisateur).

1) Prédiction de notes : RMSE / MAE de plusieurs références et d'un item-kNN.
2) Classement : Precision@10 et Recall@10 pour retrouver les lieux notés >= 4 dans le test.
Usage : python scripts/evaluate.py
"""
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from app import config  # noqa: E402
from app.recommender import Recommender  # noqa: E402
from app.schemas import Profile  # noqa: E402

K = 10
RELEVANT = 4.0
rng = np.random.default_rng(42)

places = pd.read_csv(config.PLACES_CSV)
train = pd.read_csv(config.RATINGS_TRAIN_CSV)
test = pd.read_csv(ROOT / "data" / "ratings_test.csv")
rec = Recommender(places, train)

gm = train["user_rating"].mean()
user_mean = train.groupby("user_id")["user_rating"].mean()
place_stats = train.groupby("place_id")["user_rating"].agg(["count", "mean"])
place_mean = ((place_stats["count"] * place_stats["mean"] + 20 * gm) / (place_stats["count"] + 20))
place_bias = place_mean - gm
user_bias = user_mean - gm
train_by_user = {u: g.set_index("place_id")["user_rating"] for u, g in train.groupby("user_id")}


def rmse(a, b): return float(np.sqrt(np.mean((np.asarray(a) - np.asarray(b)) ** 2)))
def mae(a, b): return float(np.mean(np.abs(np.asarray(a) - np.asarray(b))))


def predict_knn(u, pid, k=20):
    rated = train_by_user[u]
    mu = user_mean[u]
    sims = pd.Series(rec.sim[rec.pos[pid], [rec.pos[i] for i in rated.index]], index=rated.index)
    top = sims.abs().sort_values(ascending=False).head(k).index
    num = (sims[top] * (rated[top] - mu)).sum()
    den = sims[top].abs().sum()
    return float(np.clip(mu + (num / den if den else 0), 1, 5))


y = test["user_rating"].to_numpy()
preds = {
    "Moyenne globale": np.full(len(test), gm),
    "Moyenne utilisateur": test["user_id"].map(user_mean).fillna(gm).to_numpy(),
    "Moyenne lieu (lissée)": test["place_id"].map(place_mean).fillna(gm).to_numpy(),
    "Biais utilisateur + lieu": np.clip(gm + test["user_id"].map(user_bias).fillna(0) + test["place_id"].map(place_bias).fillna(0), 1, 5).to_numpy(),
    "Item-kNN (k=20)": np.array([predict_knn(u, p) for u, p in zip(test["user_id"], test["place_id"])]),
}
rows_rating = [(n, rmse(y, p), mae(y, p)) for n, p in preds.items()]

# ---- classement
cat_of = places.set_index("place_id")["category"]
popularity = train.groupby("place_id").size()
all_ids = np.array(rec.ids)
methods = {k: [] for k in ["Aléatoire", "Popularité", "Qualité (note + moyenne lissée)", "Contenu (intérêts déduits des notes)", "Item-CF (lieux aimés)"]}
for u, g in test.groupby("user_id"):
    relevant = set(g.loc[g["user_rating"] >= RELEVANT, "place_id"])
    if not relevant:
        continue
    seen = set(train_by_user[u].index)
    cand = [i for i in all_ids if i not in seen]

    def metrics(order):
        top = order[:K]
        hit = len(set(top) & relevant)
        return hit / K, hit / len(relevant)

    methods["Aléatoire"].append(metrics(list(rng.permutation(cand))))
    methods["Popularité"].append(metrics(sorted(cand, key=lambda i: -popularity.get(i, 0))))
    methods["Qualité (note + moyenne lissée)"].append(metrics(sorted(cand, key=lambda i: -rec.places.at[i, "quality"])))

    tr = train_by_user[u]
    weights = {c: int(np.clip(round(tr[[i for i in tr.index if cat_of[i] == c]].mean()), 0, 5)) if any(cat_of[i] == c for i in tr.index) else 0 for c in config.CATEGORIES}
    scored = rec.score(Profile(interests=weights))
    scored = scored[~scored.index.isin(seen)].sort_values("score", ascending=False)
    methods["Contenu (intérêts déduits des notes)"].append(metrics(list(scored.index)))

    liked = [i for i in tr.index if tr[i] >= RELEVANT]
    if liked:
        s = rec.sim[:, [rec.pos[i] for i in liked]].mean(axis=1)
        order = [rec.ids[j] for j in np.argsort(-s) if rec.ids[j] not in seen]
    else:
        order = cand
    methods["Item-CF (lieux aimés)"].append(metrics(order))

rows_rank = [(n, np.mean([m[0] for m in v]), np.mean([m[1] for m in v])) for n, v in methods.items()]

lines = ["# Évaluation hors ligne", "",
         f"Test : {len(test)} notes, {test['user_id'].nunique()} utilisateurs. Pertinent = note >= {RELEVANT:g}.", "",
         "## Prédiction des notes", "", "| Méthode | RMSE | MAE |", "|---|---|---|"]
lines += [f"| {n} | {a:.3f} | {b:.3f} |" for n, a, b in rows_rating]
lines += ["", f"## Classement (top {K})", "", f"| Méthode | Precision@{K} | Recall@{K} |", "|---|---|---|"]
lines += [f"| {n} | {a:.3f} | {b:.3f} |" for n, a, b in rows_rank]
lines += ["", "Lecture : aucune méthode ne bat nettement la moyenne globale (RMSE) ni l'aléatoire (Precision@10). "
          "Les notes de ce dataset ne contiennent pas de signal individuel exploitable : la personnalisation du moteur "
          "repose donc sur le profil déclaré (intérêts, budget, durée), pas sur l'historique de notes. "
          "Il faut évaluer ce moteur par ses contraintes (budget, temps, ville) et par un test auprès de vrais utilisateurs."]
out = ROOT / "reports" / "evaluation.md"
out.write_text("\n".join(lines), encoding="utf-8")
print("\n".join(lines))
