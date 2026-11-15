"""Évaluation expérimentale complète du moteur de recommandation Itinera.

Compare l'hybride (app.recommender.Recommender.score + diversification) à chaque approche seule
(contenu, filtrage collaboratif item-item, qualité) et à deux références (popularité, aléatoire).

Métriques de précision : Precision@K, Recall@K, HR@K, NDCG@K (K = 5, 10, 20).
Métriques au-delà de la précision : couverture du catalogue, diversité intra-liste, nouveauté, Gini.
Cold-start : (1) nouveaux utilisateurs avec n notes connues, (2) nouveaux lieux sans aucune note.
Contrôle positif : mêmes expériences sur des notes synthétiques contenant un vrai signal, pour
vérifier que le banc d'essai sait détecter un gain quand il existe.

Usage : python scripts/evaluate_full.py [--seeds 3] [--quick]
Sorties : reports/evaluation_full.md, reports/eval_*.csv, reports/eval_*.png
"""
import argparse
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from app import config  # noqa: E402
from app.recommender import Recommender  # noqa: E402
from app.schemas import Profile  # noqa: E402

KS = (5, 10, 20)
KMAX = max(KS)
RELEVANT = 4.0
METHODS = ["Aléatoire", "Popularité", "Qualité seule", "Contenu seul", "Collaboratif seul",
           "Hybride sans similarité", "Hybride (complet)"]


# --------------------------------------------------------------------------- métriques
def rank_metrics(ranked, relevant, k):
    """ranked : positions ordonnées ; relevant : ensemble de positions pertinentes."""
    top = list(ranked[:k])
    hits = [1.0 if p in relevant else 0.0 for p in top]
    h = sum(hits)
    dcg = sum(g / np.log2(i + 2) for i, g in enumerate(hits))
    idcg = sum(1.0 / np.log2(i + 2) for i in range(min(len(relevant), k)))
    return {"P": h / k, "R": h / len(relevant), "HR": float(h > 0), "NDCG": dcg / idcg if idcg else 0.0}


def gini(counts):
    x = np.sort(np.asarray(counts, dtype=float))
    if x.sum() == 0:
        return 0.0
    n = len(x)
    return float((2 * np.arange(1, n + 1) - n - 1).dot(x) / (n * x.sum()))


def boot_ci(x, n=1000, seed=0):
    x = np.asarray(x, dtype=float)
    rng = np.random.default_rng(seed)
    means = x[rng.integers(0, len(x), (n, len(x)))].mean(axis=1)
    return float(x.mean()), float(np.percentile(means, 2.5)), float(np.percentile(means, 97.5))


def paired_p(a, b, n=2000, seed=1):
    """Bootstrap apparié sur les utilisateurs : p-valeur bilatérale de mean(a-b) = 0, et IC95 % de la différence."""
    d = np.asarray(a, dtype=float) - np.asarray(b, dtype=float)
    rng = np.random.default_rng(seed)
    means = d[rng.integers(0, len(d), (n, len(d)))].mean(axis=1)
    p = 2 * min((means <= 0).mean(), (means >= 0).mean())
    return float(d.mean()), float(np.percentile(means, 2.5)), float(np.percentile(means, 97.5)), float(min(1.0, p))


# --------------------------------------------------------------------------- contexte de modèle
class Ctx:
    """Un Recommender ajusté + tableaux alignés sur rec.ids, pour classer vite sans toucher au moteur."""

    def __init__(self, places, train, feat):
        self.rec = Recommender(places, train)
        r = self.rec
        self.n = len(r.ids)
        self.ids = np.array(r.ids)
        self.cat = r.places["category"].to_numpy()
        self.cat_code = pd.Categorical(self.cat, categories=config.CATEGORIES).codes
        self.quality = r.places["quality"].to_numpy()
        pop = train.groupby("place_id").size().reindex(r.ids).fillna(0)
        self.pop = pop.to_numpy()
        self.n_users = train["user_id"].nunique()
        f = feat.set_index("place_id").loc[r.ids]
        cols = [c for c in f.columns if c.startswith("cat_") or c.startswith("city_")] + ["price_norm"]
        m = f[cols].to_numpy(dtype=float)
        self.F = m / np.maximum(np.linalg.norm(m, axis=1, keepdims=True), 1e-9)

    def profile_of(self, tr):
        """Profil déduit des notes connues d'un utilisateur : poids par catégorie = note moyenne arrondie, lieux aimés = notes >= 4."""
        cat_of = dict(zip(self.ids, self.cat))
        by_cat = {}
        for pid, v in tr.items():
            by_cat.setdefault(cat_of[pid], []).append(v)
        w = {c: int(np.clip(round(np.mean(by_cat[c])), 0, 5)) if c in by_cat else 0 for c in config.CATEGORIES}
        liked = [int(i) for i, v in tr.items() if v >= RELEVANT]
        return w, liked


def order(score, allowed, rng, k=KMAX):
    s = np.where(allowed, np.asarray(score, dtype=float) + 1e-9 * rng.random(len(score)), -np.inf)
    return np.argsort(-s)[:k]


def diversify(score, cat_code, allowed, k=KMAX):
    """Même sélection gloutonne que Recommender.recommend (pénalité par lieu déjà pris de la même catégorie)."""
    counts = np.zeros(len(config.CATEGORIES))
    remaining = allowed & np.isfinite(score)
    picked = []
    for _ in range(min(k, int(remaining.sum()))):
        adj = np.where(remaining, score - config.DIVERSITY_PENALTY * counts[cat_code], -np.inf)
        j = int(np.argmax(adj))
        picked.append(j)
        remaining[j] = False
        counts[cat_code[j]] += 1
    return np.array(picked)


def hybrid_scores(ctx, w, liked, use_sim=True):
    p = Profile(interests=w, liked_place_ids=liked if use_sim else [])
    df = ctx.rec.score(p)
    s = np.full(ctx.n, -np.inf)
    if not df.empty:
        s[[ctx.rec.pos[i] for i in df.index]] = df["score"].to_numpy()
    return s


def rankings(ctx, tr, allowed, rng, which=METHODS):
    """Classements (positions) de chaque méthode pour un utilisateur dont les notes connues sont `tr`."""
    w, liked = ctx.profile_of(tr)
    out = {}
    if "Aléatoire" in which:
        out["Aléatoire"] = order(rng.random(ctx.n), allowed, rng)
    if "Popularité" in which:
        out["Popularité"] = order(ctx.pop, allowed, rng)
    if "Qualité seule" in which:
        out["Qualité seule"] = order(ctx.quality, allowed, rng)
    if "Contenu seul" in which:
        out["Contenu seul"] = order(np.array([w[c] / 5 for c in ctx.cat]), allowed, rng)
    if "Collaboratif seul" in which:
        idx = [ctx.rec.pos[i] for i in liked]
        out["Collaboratif seul"] = order(ctx.rec.sim[:, idx].mean(axis=1) if idx else np.zeros(ctx.n), allowed, rng)
    if "Hybride sans similarité" in which:
        out["Hybride sans similarité"] = diversify(hybrid_scores(ctx, w, liked, use_sim=False), ctx.cat_code, allowed)
    if "Hybride (complet)" in which:
        out["Hybride (complet)"] = diversify(hybrid_scores(ctx, w, liked, use_sim=True), ctx.cat_code, allowed)
    return out


def check_fidelity(ctx, tr, k=10):
    """Vérifie que le classement de l'hybride du banc d'essai = rec.recommend() quand seuls les lieux aimés sont exclus."""
    w, liked = ctx.profile_of(tr)
    ref = [r["place_id"] for r in ctx.rec.recommend(Profile(interests=w, liked_place_ids=liked), top_k=k)]
    allowed = np.ones(ctx.n, dtype=bool)
    for i in liked:
        allowed[ctx.rec.pos[i]] = False
    mine = [int(ctx.ids[j]) for j in diversify(hybrid_scores(ctx, w, liked), ctx.cat_code, allowed, k)]
    return ref == mine


# --------------------------------------------------------------------------- expérience principale
def run_main(places, feat, train, test, rng, label):
    ctx = Ctx(places, train, feat)
    tr_by_u = {u: g.set_index("place_id")["user_rating"] for u, g in train.groupby("user_id")}
    rows, lists, ranked_all = [], {m: [] for m in METHODS}, {}
    for u, g in test.groupby("user_id"):
        rel = {ctx.rec.pos[i] for i in g.loc[g["user_rating"] >= RELEVANT, "place_id"]}
        if not rel:
            continue
        tr = tr_by_u[u]
        allowed = np.ones(ctx.n, dtype=bool)
        for i in tr.index:
            allowed[ctx.rec.pos[i]] = False
        rk = rankings(ctx, tr, allowed, rng)
        ranked_all[u] = (rk, rel)
        for m, o in rk.items():
            lists[m].append(o[:10])
            for k in KS:
                rows.append({"user": u, "method": m, "K": k, **rank_metrics(o, rel, k)})
        ideal = {"user": u, "method": "Idéal (borne)", "K": 10}
        ideal.update({"P": min(len(rel), 10) / 10, "R": min(len(rel), 10) / len(rel), "HR": 1.0, "NDCG": 1.0})
        rows.append(ideal)
    df = pd.DataFrame(rows)

    # au-delà de la précision (liste de 10)
    beyond = []
    for m, ls in lists.items():
        flat = np.concatenate(ls)
        cov = len(set(flat)) / ctx.n
        ild = np.mean([(1 - (ctx.F[l] @ ctx.F[l].T)[np.triu_indices(len(l), 1)]).mean() for l in ls])
        p = (ctx.pop[flat] + 1) / (ctx.n_users + 1)
        nov = float(np.mean(-np.log2(p)))
        g = gini(np.bincount(flat, minlength=ctx.n))
        cats = np.mean([len(set(ctx.cat[l])) for l in ls])
        beyond.append({"method": m, "coverage@10": cov, "ILD@10": float(ild), "novelty@10": nov, "gini@10": g, "cat_distinctes@10": float(cats)})
    return ctx, df, pd.DataFrame(beyond), ranked_all


# --------------------------------------------------------------------------- cold-start utilisateurs
def run_cold_users(places, feat, train, test, seed, ns=(0, 1, 3, 5, 10, 25)):
    rng = np.random.default_rng(seed)
    users = np.array(sorted(train["user_id"].unique()))
    cold = set(rng.choice(users, size=len(users) // 5, replace=False))
    ctx = Ctx(places, train[~train["user_id"].isin(cold)], feat)  # le modèle n'a jamais vu ces utilisateurs
    rows = []
    for u in sorted(cold):
        g = test[test["user_id"] == u]
        rel = {ctx.rec.pos[i] for i in g.loc[g["user_rating"] >= RELEVANT, "place_id"]}
        if not rel:
            continue
        full = train[train["user_id"] == u].sample(frac=1, random_state=int(rng.integers(1e9))).set_index("place_id")["user_rating"]
        allowed = np.ones(ctx.n, dtype=bool)
        for i in full.index:
            allowed[ctx.rec.pos[i]] = False
        for n in ns:
            rk = rankings(ctx, full.iloc[:n], allowed, rng)
            for m, o in rk.items():
                rows.append({"seed": seed, "user": u, "n": n, "method": m, **rank_metrics(o, rel, 10)})
    return pd.DataFrame(rows)


# --------------------------------------------------------------------------- cold-start lieux
def run_cold_items(places, feat, train, test, seed, frac=0.15):
    rng = np.random.default_rng(seed)
    ids = places["place_id"].to_numpy()
    cold_ids = set(rng.choice(ids, size=int(len(ids) * frac), replace=False))
    ctx = Ctx(places, train[~train["place_id"].isin(cold_ids)], feat)  # aucun lieu froid n'a de note à l'entraînement
    cold_pos = np.array([ctx.rec.pos[i] for i in cold_ids])
    is_cold = np.zeros(ctx.n, dtype=bool)
    is_cold[cold_pos] = True
    tr_by_u = {u: g[~g["place_id"].isin(cold_ids)].set_index("place_id")["user_rating"] for u, g in train.groupby("user_id")}
    methods = [m for m in METHODS]
    rows = []
    for u, g in test.groupby("user_id"):
        rel = {ctx.rec.pos[i] for i in g.loc[(g["user_rating"] >= RELEVANT) & g["place_id"].isin(cold_ids), "place_id"]}
        if not rel:
            continue
        tr = tr_by_u[u]
        seen = set(train.loc[train["user_id"] == u, "place_id"])  # y compris ses notes sur lieux froids (exclues du pool)
        base = np.ones(ctx.n, dtype=bool)
        for i in seen:
            base[ctx.rec.pos[i]] = False
        # (a) catalogue complet : un lieu froid peut-il entrer dans le top-10 ?
        rk = rankings(ctx, tr, base, rng, methods)
        for m, o in rk.items():
            rows.append({"seed": seed, "user": u, "protocol": "catalogue complet", "method": m,
                         "cold_share@10": float(is_cold[o[:10]].mean()), **rank_metrics(o, rel, 10)})
        # (b) lieux froids seuls : le contenu sait-il les ordonner ?
        rk = rankings(ctx, tr, base & is_cold, rng, methods)
        for m, o in rk.items():
            rows.append({"seed": seed, "user": u, "protocol": "lieux froids seuls", "method": m, "cold_share@10": 1.0, **rank_metrics(o, rel, 10)})
    return pd.DataFrame(rows), float(frac)


# --------------------------------------------------------------------------- notes synthétiques (contrôle positif)
def synthetic_ratings(places, train, test, seed=7):
    rng = np.random.default_rng(seed)
    allr = pd.concat([train.assign(split="train"), test.assign(split="test")], ignore_index=True)
    users = allr["user_id"].unique()
    aff = {u: rng.normal(0, 1.0, len(config.CATEGORIES)) for u in users}
    p = places.set_index("place_id")
    z = (p["rating"] - p["rating"].mean()) / p["rating"].std()
    code = {c: i for i, c in enumerate(config.CATEGORIES)}
    a = np.array([aff[u][code[p.at[i, "category"]]] for u, i in zip(allr["user_id"], allr["place_id"])])
    raw = 3 + a + 0.7 * allr["place_id"].map(z).to_numpy() + rng.normal(0, 0.8, len(allr))
    allr["user_rating"] = np.clip(np.round(raw), 1, 5)
    return allr[allr["split"] == "train"].drop(columns="split"), allr[allr["split"] == "test"].drop(columns="split")


# --------------------------------------------------------------------------- mise en forme
def fmt_ci(x):
    m, lo, hi = boot_ci(x)
    return f"{m:.3f} [{lo:.3f}; {hi:.3f}]"


def table_main(df, k=10):
    sub = df[df["K"] == k]
    out = ["| Méthode | Precision@%d | Recall@%d | HR@%d | NDCG@%d |" % (k, k, k, k), "|---|---|---|---|---|"]
    for m in METHODS + ["Idéal (borne)"]:
        s = sub[sub["method"] == m]
        if s.empty:
            continue
        out.append(f"| {m} | {s['P'].mean():.3f} | {s['R'].mean():.3f} | {fmt_ci(s['HR'])} | {fmt_ci(s['NDCG'])} |")
    return out


def table_tests(df, k=10):
    sub = df[df["K"] == k].pivot(index="user", columns="method", values="NDCG")
    sub_hr = df[df["K"] == k].pivot(index="user", columns="method", values="HR")
    out = [f"| Comparaison (Hybride complet moins …) | Δ NDCG@{k} [IC95 %] | p | Δ HR@{k} [IC95 %] | p |", "|---|---|---|---|---|"]
    for m in ["Aléatoire", "Popularité", "Qualité seule", "Contenu seul", "Collaboratif seul"]:
        d, lo, hi, p = paired_p(sub["Hybride (complet)"], sub[m])
        d2, lo2, hi2, p2 = paired_p(sub_hr["Hybride (complet)"], sub_hr[m])
        out.append(f"| {m} | {d:+.4f} [{lo:+.4f}; {hi:+.4f}] | {p:.3f} | {d2:+.3f} [{lo2:+.3f}; {hi2:+.3f}] | {p2:.3f} |")
    return out


def table_beyond(b):
    out = ["| Méthode | Couverture@10 | Diversité intra-liste | Nouveauté (bits) | Gini | Catégories distinctes / 10 |", "|---|---|---|---|---|---|"]
    for _, r in b.iterrows():
        out.append(f"| {r['method']} | {r['coverage@10']:.3f} | {r['ILD@10']:.3f} | {r['novelty@10']:.2f} | {r['gini@10']:.3f} | {r['cat_distinctes@10']:.2f} |")
    return out


def seed_table(df, group_cols, value_cols):
    per_seed = df.groupby(["seed"] + group_cols)[value_cols].mean().reset_index()
    agg = per_seed.groupby(group_cols)[value_cols].agg(["mean", "std"])
    return agg


def figures(df_real, df_syn, cold_u, cold_i, out_dir):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    fig, axes = plt.subplots(1, 2, figsize=(12, 4.2), sharey=False)
    for ax, df, title in zip(axes, [df_real, df_syn], ["Notes réelles (dataset Kaggle)", "Notes synthétiques (signal planté)"]):
        sub = df[(df["K"] == 10) & (df["method"].isin(METHODS))]
        means, errs = [], []
        for m in METHODS:
            mm, lo, hi = boot_ci(sub[sub["method"] == m]["NDCG"])
            means.append(mm); errs.append([mm - lo, hi - mm])
        ax.barh(METHODS, means, xerr=np.array(errs).T, color=["#9aa5a8"] * 2 + ["#5fa8b0"] * 3 + ["#2a8a94", "#0a3440"], capsize=3)
        ax.invert_yaxis(); ax.set_title(title); ax.set_xlabel("NDCG@10 (IC95 % bootstrap)")
    fig.tight_layout(); fig.savefig(out_dir / "eval_main.png", dpi=140); plt.close(fig)

    fig, axes = plt.subplots(1, 2, figsize=(12, 4.2))
    for ax, d, title in zip(axes, cold_u, ["Cold-start utilisateurs — notes réelles", "Cold-start utilisateurs — notes synthétiques"]):
        g = d.groupby(["seed", "n", "method"])["HR"].mean().reset_index().groupby(["n", "method"])["HR"].mean().unstack()
        for m in ["Aléatoire", "Popularité", "Contenu seul", "Collaboratif seul", "Hybride (complet)"]:
            ax.plot(g.index, g[m], marker="o", label=m)
        ax.set_xlabel("nombre de notes connues du nouvel utilisateur"); ax.set_ylabel("HR@10"); ax.set_title(title); ax.legend(fontsize=7)
    fig.tight_layout(); fig.savefig(out_dir / "eval_cold_users.png", dpi=140); plt.close(fig)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--seeds", type=int, default=3)
    ap.add_argument("--quick", action="store_true", help="1 graine, utilisateurs/lieux froids réduits (test rapide)")
    args = ap.parse_args()
    seeds = 1 if args.quick else args.seeds
    t0 = time.time()

    places = pd.read_csv(config.PLACES_CSV)
    feat = places  # place_features.csv contient déjà toutes les colonnes (config.PLACES_CSV)
    train = pd.read_csv(config.RATINGS_TRAIN_CSV)
    test = pd.read_csv(ROOT / "data" / "ratings_test.csv")
    s_train, s_test = synthetic_ratings(places, train, test)
    rng = np.random.default_rng(42)
    log = lambda s: print(f"[{time.time() - t0:6.0f}s] {s}", flush=True)

    ctx, df_real, beyond_real, _ = run_main(places, feat, train, test, rng, "réel")
    log("principal (réel) terminé")
    ok = check_fidelity(ctx, train[train["user_id"] == 1].set_index("place_id")["user_rating"])
    log(f"fidélité hybride banc d'essai = rec.recommend() : {ok}")
    _, df_syn, beyond_syn, _ = run_main(places, feat, s_train, s_test, rng, "synthétique")
    log("principal (synthétique) terminé")

    cu_real = pd.concat([run_cold_users(places, feat, train, test, s) for s in range(seeds)])
    log("cold-start utilisateurs (réel) terminé")
    cu_syn = pd.concat([run_cold_users(places, feat, s_train, s_test, s) for s in range(seeds)])
    log("cold-start utilisateurs (synthétique) terminé")
    ci_real = pd.concat([run_cold_items(places, feat, train, test, s)[0] for s in range(seeds)])
    log("cold-start lieux (réel) terminé")
    ci_syn = pd.concat([run_cold_items(places, feat, s_train, s_test, s)[0] for s in range(seeds)])
    log("cold-start lieux (synthétique) terminé")

    # latence
    w, liked = {"sea": 5, "culture": 3}, [5, 15, 20, 30]
    t = time.time()
    for _ in range(10):
        ctx.rec.recommend(Profile(interests=w, liked_place_ids=liked), top_k=10)
    lat = (time.time() - t) / 10

    rep = ROOT / "reports"
    rep.mkdir(exist_ok=True)
    df_real.to_csv(rep / "eval_main_real_users.csv", index=False)
    df_syn.to_csv(rep / "eval_main_synthetic_users.csv", index=False)
    cu_real.to_csv(rep / "eval_cold_users_real.csv", index=False)
    cu_syn.to_csv(rep / "eval_cold_users_synthetic.csv", index=False)
    ci_real.to_csv(rep / "eval_cold_items_real.csv", index=False)
    ci_syn.to_csv(rep / "eval_cold_items_synthetic.csv", index=False)
    figures(df_real, df_syn, [cu_real, cu_syn], None, rep)

    rel_rate = float((test["user_rating"] >= RELEVANT).mean())
    L = []
    L += ["# Évaluation expérimentale — hybride vs approches seules vs popularité", "",
          f"Données : {train['user_id'].nunique()} utilisateurs, {len(places)} lieux, {len(train)} notes d'entraînement, {len(test)} notes de test "
          f"(20 % de chaque utilisateur). Pertinent = note >= {RELEVANT:g} ({rel_rate:.0%} des notes de test). "
          f"Les lieux déjà notés à l'entraînement sont exclus des classements. Utilisateurs évalués : {df_real['user'].nunique()}.", "",
          "Profil de chaque utilisateur déduit de ses notes d'entraînement : poids d'intérêt par catégorie = note moyenne arrondie, "
          "lieux aimés = notes >= 4 (même protocole que `evaluate.py`). Toutes les méthodes sont départagées aléatoirement en cas d'égalité.", "",
          "Approches : **Popularité** = nombre de notes ; **Qualité seule** = composante `quality` du moteur ; **Contenu seul** = composante `interests` ; "
          "**Collaboratif seul** = similarité item-item moyenne avec les lieux aimés ; **Hybride** = `Recommender.score` complet (intérêts + qualité + similarité) "
          "suivi de la diversification de `recommend`. `Hybride sans similarité` est l'ablation. Le budget n'est pas évalué ici : c'est une contrainte, pas un signal de préférence.", "",
          f"Fidélité du banc d'essai : le classement de l'hybride reproduit `Recommender.recommend()` ({'oui' if ok else 'NON, voir code'}).", ""]
    L += ["## 1. Résultats sur les notes réelles (K = 10)", ""] + table_main(df_real) + [""]
    L += ["Tests appariés (bootstrap sur les utilisateurs) :", ""] + table_tests(df_real) + [""]
    L += ["### Autres K (NDCG, HR)", "", "| Méthode | " + " | ".join(f"NDCG@{k} | HR@{k}" for k in KS) + " |", "|---|" + "---|---|" * len(KS)]
    for m in METHODS:
        cells = []
        for k in KS:
            s = df_real[(df_real["method"] == m) & (df_real["K"] == k)]
            cells += [f"{s['NDCG'].mean():.3f}", f"{s['HR'].mean():.3f}"]
        L.append(f"| {m} | " + " | ".join(cells) + " |")
    L += ["", "## 2. Au-delà de la précision (listes de 10, notes réelles)", ""] + table_beyond(beyond_real) + [""]
    L += ["## 3. Contrôle positif : notes synthétiques avec un vrai signal (K = 10)", "",
          "Mêmes paires utilisateur-lieu, même découpage, mais la note = 3 + affinité de l'utilisateur pour la catégorie + effet de la note du lieu + bruit. "
          "Si le banc d'essai fonctionne, les approches personnalisées doivent battre la popularité ici.", ""] + table_main(df_syn) + [""]
    L += ["Tests appariés :", ""] + table_tests(df_syn) + [""] + ["Au-delà de la précision :", ""] + table_beyond(beyond_syn) + [""]

    L += ["## 4. Cold-start — nouveaux utilisateurs", "",
          f"20 % des utilisateurs sont retirés de l'entraînement (modèle refitté sans eux), {seeds} graine(s). On révèle n de leurs notes d'entraînement pour fabriquer leur profil ; "
          "le test est inchangé. n = 0 : aucun profil (le moteur n'a que la qualité). Moyenne sur les graines ; HR@10 / NDCG@10.", ""]
    for name, d in [("Notes réelles", cu_real), ("Notes synthétiques", cu_syn)]:
        g = d.groupby(["seed", "n", "method"])[["HR", "NDCG"]].mean().reset_index().groupby(["n", "method"])[["HR", "NDCG"]].mean()
        ns = sorted(d["n"].unique())
        L += [f"**{name}** : HR@10 par nombre de notes connues", "", "| Méthode | " + " | ".join(f"n={n}" for n in ns) + " |", "|---|" + "---|" * len(ns)]
        for m in METHODS:
            L.append(f"| {m} | " + " | ".join(f"{g.loc[(n, m), 'HR']:.3f}" for n in ns) + " |")
        L.append("")
    L += ["![cold-start utilisateurs](eval_cold_users.png)", ""]

    L += ["## 5. Cold-start — nouveaux lieux", "",
          f"15 % des lieux sont retirés des notes d'entraînement (aucune note, donc popularité = 0 et similarité collaborative = 0), {seeds} graine(s). "
          "Pertinent = lieu froid noté >= 4 dans le test. Protocole (a) : classement sur tout le catalogue, "
          "on mesure aussi la part de lieux froids dans le top-10 (15 % = proportion dans le catalogue). Protocole (b) : classement parmi les seuls lieux froids.", ""]
    for name, d in [("Notes réelles", ci_real), ("Notes synthétiques", ci_syn)]:
        for proto in ["catalogue complet", "lieux froids seuls"]:
            s = d[d["protocol"] == proto]
            g = s.groupby(["seed", "method"])[["HR", "R", "NDCG", "cold_share@10"]].mean().reset_index().groupby("method")[["HR", "R", "NDCG", "cold_share@10"]].mean()
            L += [f"**{name} — {proto}**", "", "| Méthode | HR@10 | Recall@10 | NDCG@10 | Part de lieux froids dans le top-10 |", "|---|---|---|---|---|"]
            for m in METHODS:
                r = g.loc[m]
                L.append(f"| {m} | {r['HR']:.3f} | {r['R']:.3f} | {r['NDCG']:.3f} | {r['cold_share@10']:.2f} |")
            L.append("")
    L += [f"Latence : `recommend()` avec lieux aimés = {lat * 1000:.0f} ms par requête (boucles `iterrows` dans la similarité de contenu).", "",
          f"Durée totale de l'évaluation : {time.time() - t0:.0f} s.", ""]
    (rep / "evaluation_full.md").write_text("\n".join(L), encoding="utf-8")
    log("rapport écrit : reports/evaluation_full.md")


if __name__ == "__main__":
    main()
