"""Évaluation sur les circuits touristiques réels de packages.csv (leave-one-out) + balayage de la pénalité de diversité.

Les notes du dataset n'ont pas de signal (reports/diagnostic_signal.md) ; les circuits, eux, en ont :
dans un circuit, 67 % des paires de lieux ont la même catégorie (28 % pour des lieux tirés au hasard dans la même ville)
et les lieux sont plus proches (11,6 km contre 17,2 km).

Protocole : pour chaque circuit (3 à 5 lieux) et chaque lieu du circuit, on le cache, on donne les autres comme
`liked_place_ids` avec la ville du circuit, et on regarde à quel rang le moteur retrouve le lieu caché
(HR@5, HR@10, MRR, NDCG@10). 405 cas. Le classement est celui de Recommender.recommend().

Usage : python scripts/evaluate_circuits.py   ->   reports/evaluation_circuits.md
"""
import sys
from contextlib import contextmanager
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))

from app import config  # noqa: E402
from app.recommender import Recommender  # noqa: E402
from app.schemas import Profile  # noqa: E402
from evaluate_full import boot_ci, paired_p  # noqa: E402

PACKAGES = ROOT.parent / "data-science" / "data" / "processed" / "packages.csv"
ORIG = dict(weights={"interests": 0.45, "quality": 0.25, "budget": 0.15, "similarity": 0.15}, penalty=0.04, qshare=0.7, mix={"content": 0.5, "cf": 0.5})
CONFIGS = {
    "Moteur d'origine": ORIG,
    "Proposition de l'autre agent (sim 0,05 ; pénalité 0,12 ; qualité 0,9/0,1)": dict(
        weights={"interests": 0.50, "quality": 0.30, "budget": 0.15, "similarity": 0.05}, penalty=0.12, qshare=0.9, mix={"content": 0.5, "cf": 0.5}),
    "Origine + seulement sim 0,05": {**ORIG, "weights": {"interests": 0.45, "quality": 0.25, "budget": 0.15, "similarity": 0.05}},
    "Origine sans filtrage collaboratif (contenu seul)": {**ORIG, "mix": {"content": 1.0, "cf": 0.0}},
    "Contenu seul + sim 0,25 (poids non renormalisés)": {**ORIG, "mix": {"content": 1.0, "cf": 0.0}, "weights": {"interests": 0.45, "quality": 0.25, "budget": 0.15, "similarity": 0.25}},
    "NOUVEAU RÉGLAGE ADOPTÉ (contenu seul ; 0,40 / 0,20 / 0,15 / 0,25)": {**ORIG, "mix": {"content": 1.0, "cf": 0.0}, "weights": {"interests": 0.40, "quality": 0.20, "budget": 0.15, "similarity": 0.25}},
    "Contenu seul + sim 0,35": {**ORIG, "mix": {"content": 1.0, "cf": 0.0}, "weights": {"interests": 0.45, "quality": 0.25, "budget": 0.15, "similarity": 0.35}},
    "Contenu seul + pénalité 0,12": {**ORIG, "mix": {"content": 1.0, "cf": 0.0}, "penalty": 0.12},
}


@contextmanager
def configured(c):
    saved = (dict(config.SCORE_WEIGHTS), config.DIVERSITY_PENALTY, config.QUALITY_RATING_SHARE, dict(config.SIMILARITY_MIX))
    config.SCORE_WEIGHTS.update(c["weights"])
    config.DIVERSITY_PENALTY, config.QUALITY_RATING_SHARE = c["penalty"], c["qshare"]
    config.SIMILARITY_MIX.clear(); config.SIMILARITY_MIX.update(c["mix"])
    try:
        yield
    finally:
        config.SCORE_WEIGHTS.update(saved[0]); config.DIVERSITY_PENALTY, config.QUALITY_RATING_SHARE = saved[1], saved[2]
        config.SIMILARITY_MIX.clear(); config.SIMILARITY_MIX.update(saved[3])


def loo_ranks(rec, cases):
    ranks = []
    for liked, target, city in cases:
        out = rec.recommend(Profile(city=city, liked_place_ids=liked), top_k=1000)
        ids = [r["place_id"] for r in out]
        ranks.append(ids.index(target) + 1 if target in ids else 10_000)
    return np.array(ranks)


def metrics(ranks):
    return {"HR@5": (ranks <= 5).astype(float), "HR@10": (ranks <= 10).astype(float), "MRR": 1.0 / ranks,
            "NDCG@10": np.where(ranks <= 10, 1.0 / np.log2(ranks + 1), 0.0)}


def diversity_sweep(places, train):
    rows = []
    cats = config.CATEGORIES
    for pen in (0.04, 0.08, 0.12, 0.15):
        with configured({**ORIG, "penalty": pen, "mix": {"content": 1.0, "cf": 0.0}}):
            rec = Recommender(places, train)
            distinct, fit, first_switch = [], [], []
            for c in cats:  # profil mono-intérêt : « je veux surtout cette catégorie »
                for city in sorted(places["city"].unique()):
                    out = rec.recommend(Profile(city=city, interests={c: 5}), top_k=10)
                    cl = [r["category"] for r in out]
                    distinct.append(len(set(cl)))
                    fit.append(np.mean([x == c for x in cl]))
                    first_switch.append(next((i for i, x in enumerate(cl) if x != c), 10))
            rows.append({"pénalité": pen, "catégories distinctes / 10": np.mean(distinct), "part dans la catégorie voulue": np.mean(fit), "rang du 1er lieu d'une autre catégorie": np.mean(first_switch) + 1})
    return pd.DataFrame(rows)


def main():
    places = pd.read_csv(config.PLACES_CSV)
    train = pd.read_csv(config.RATINGS_TRAIN_CSV)
    pk = pd.read_csv(PACKAGES)
    cases, pkg_of = [], []
    for pid, g in pk.groupby("package_id"):
        pl = g["place_id"].tolist()
        for t in pl:
            cases.append(([i for i in pl if i != t], t, g["city"].iloc[0]))
            pkg_of.append(pid)
    results = {}
    for name, c in CONFIGS.items():
        with configured(c):
            rec = Recommender(places, train)
            results[name] = metrics(loo_ranks(rec, cases))
    # références
    rng = np.random.default_rng(0)
    by_city = places.groupby("city")["place_id"].apply(list).to_dict()
    pop = train.groupby("place_id").size()
    rnd, popr = [], []
    for liked, t, city in cases:
        pool = [i for i in by_city[city] if i not in liked]
        rnd.append(1 + (rng.random(len(pool)) > rng.random()).sum() * 0)  # placeholder, remplacé ci-dessous
        order = rng.permutation(pool)
        rnd[-1] = int(np.where(order == t)[0][0]) + 1
        p_sorted = sorted(pool, key=lambda i: (-pop.get(i, 0), rng.random()))
        popr.append(p_sorted.index(t) + 1)
    results = {"Aléatoire (même ville)": metrics(np.array(rnd)), "Popularité (nb de notes, même ville)": metrics(np.array(popr)), **results}

    L = ["# Évaluation sur les circuits réels (leave-one-out)", "",
         f"{len(pk['package_id'].unique())} circuits, {len(cases)} cas (un lieu caché, les autres donnés comme lieux aimés, ville du circuit). "
         "Intervalle de confiance à 95 % par bootstrap sur les cas ; p-valeur = bootstrap apparié contre le moteur d'origine. "
         "Les cas d'un même circuit ne sont pas indépendants : les p-valeurs sont indicatives.", "",
         "| Méthode | HR@5 | HR@10 | MRR | NDCG@10 | Δ NDCG@10 vs origine (p) |", "|---|---|---|---|---|---|"]
    base = results["Moteur d'origine"]["NDCG@10"]
    for name, m in results.items():
        mm, lo, hi = boot_ci(m["NDCG@10"])
        d, _, _, p = paired_p(m["NDCG@10"], base)
        delta = "" if name == "Moteur d'origine" else f"{d:+.3f} (p = {p:.3f})"
        L.append(f"| {name} | {m['HR@5'].mean():.3f} | {m['HR@10'].mean():.3f} | {m['MRR'].mean():.3f} | {mm:.3f} [{lo:.3f}; {hi:.3f}] | {delta} |")
    L += ["", "## Balayage de la pénalité de diversité (profil mono-intérêt, note 5, par ville et catégorie)", ""]
    sw = diversity_sweep(places, train)
    L += ["| " + " | ".join(sw.columns) + " |", "|" + "---|" * len(sw.columns)]
    for _, r in sw.iterrows():
        L.append("| " + " | ".join(f"{v:.2f}" for v in r.to_numpy()) + " |")
    (ROOT / "reports").mkdir(exist_ok=True)
    (ROOT / "reports" / "evaluation_circuits.md").write_text("\n".join(L) + "\n", encoding="utf-8")
    print("\n".join(L))


if __name__ == "__main__":
    main()
