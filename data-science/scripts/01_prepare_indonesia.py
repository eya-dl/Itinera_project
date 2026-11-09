"""Partie 1 : nettoyage + exploration du dataset Indonesia Tourism.

Usage : python scripts/01_prepare_indonesia.py
Sorties : data/processed/*.csv, reports/*.png, reports/indonesia_data_report.md
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt

from voyage.indonesia import PROCESSED_DIR, load_raw, prepare_all

REPORTS = Path(__file__).resolve().parents[1] / "reports"


def save(fig, name):
    fig.tight_layout()
    fig.savefig(REPORTS / name, dpi=120)
    plt.close(fig)


def make_figures(d):
    places, ratings = d["places"], d["ratings"]

    ct = places.groupby(["city", "category"]).size().unstack(fill_value=0)
    ax = ct.plot(kind="bar", stacked=True, figsize=(8, 5))
    ax.set_title("Lieux par ville et par catégorie")
    ax.set_xlabel("")
    ax.set_ylabel("Nombre de lieux")
    plt.setp(ax.get_xticklabels(), rotation=0)
    save(ax.figure, "places_par_ville_categorie.png")

    fig, ax = plt.subplots(figsize=(7, 4))
    paid = places.loc[~places["is_free"], "price_idr"]
    ax.hist(paid, bins=30, log=True)
    ax.set_title(f"Prix d'entrée des lieux payants (en IDR, échelle log) — {len(paid)} lieux")
    ax.set_xlabel("Prix (IDR)")
    save(fig, "distribution_prix.png")

    fig, ax = plt.subplots(figsize=(7, 4))
    obs = places.loc[~places["visit_minutes_imputed"], "visit_minutes"]
    imp = places.loc[places["visit_minutes_imputed"], "visit_minutes"]
    ax.hist([obs, imp], bins=15, stacked=True, label=["observée", "imputée"])
    ax.set_title("Durée de visite (minutes)")
    ax.legend()
    save(fig, "distribution_duree.png")

    fig, axes = plt.subplots(1, 2, figsize=(10, 4))
    ratings["user_rating"].round().value_counts().sort_index().plot(kind="bar", ax=axes[0])
    axes[0].set_title("Répartition des notes utilisateurs")
    axes[0].set_xlabel("Note")
    ratings.groupby("user_id").size().plot(kind="hist", bins=20, ax=axes[1])
    axes[1].set_title("Nombre de notes par utilisateur")
    save(fig, "notes_utilisateurs.png")

    fig, ax = plt.subplots(figsize=(8, 5))
    for city, g in places.groupby("city"):
        ax.scatter(g["lon"], g["lat"], s=14, label=city)
    ax.set_title("Carte des lieux (longitude / latitude)")
    ax.set_xlabel("Longitude")
    ax.set_ylabel("Latitude")
    ax.legend()
    save(fig, "carte_lieux.png")


def write_report(raw, d):
    places, ratings, users, packages = d["places"], d["ratings"], d["users"], d["packages"]
    raw_ratings = len(raw["ratings"])
    unmatched = packages["place_id"].isna().sum()
    sparse = ratings.groupby("place_id").size()
    lines = [
        "# Rapport qualité des données — Indonesia Tourism",
        "",
        f"- Lieux : **{len(places)}** dans {places['city'].nunique()} villes, {places['category'].nunique()} catégories",
        f"- Durée de visite imputée : **{places['visit_minutes_imputed'].sum()}** lieux ({places['visit_minutes_imputed'].mean():.0%})",
        f"- Entrée gratuite (prix = 0) : **{places['is_free'].sum()}** lieux ({places['is_free'].mean():.0%})",
        f"- Coordonnées hors Indonésie : **{(~places['coords_ok']).sum()}**",
        f"- Notes utilisateurs : {raw_ratings} brutes -> **{len(ratings)}** après dédoublonnage",
        f"- Utilisateurs : {len(users)} ; lieux notés au moins une fois : {ratings['place_id'].nunique()}/{len(places)}",
        f"- Notes par lieu : médiane {sparse.median():.0f}, min {sparse.min()}, max {sparse.max()}",
        f"- Circuits : {packages['package_id'].nunique()} ; lieux non rapprochés d'un place_id : **{unmatched}**/{len(packages)}",
        "",
        "## Lieux par ville et catégorie",
        "",
        places.groupby(["city", "category"]).size().unstack(fill_value=0).to_markdown(),
        "",
        "## Prix (IDR) par catégorie",
        "",
        places.groupby("category")["price_idr"].describe()[["count", "50%", "max"]].round(0).to_markdown(),
        "",
        "Figures : `reports/*.png`",
    ]
    (REPORTS / "indonesia_data_report.md").write_text("\n".join(lines), encoding="utf-8")
    print("\n".join(lines[:12]))


def main():
    REPORTS.mkdir(exist_ok=True)
    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
    raw = load_raw()
    d = prepare_all()
    for name, df in d.items():
        df.to_csv(PROCESSED_DIR / f"{name}.csv", index=False)
    make_figures(d)
    write_report(raw, d)


if __name__ == "__main__":
    main()
