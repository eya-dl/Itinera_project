"""Partie 1 : chargement et nettoyage du dataset Indonesia Tourism.

Chaque fonction clean_* prend un DataFrame brut et renvoie un DataFrame propre
(noms de colonnes en snake_case, types corrects, aucune ligne supprimée sans raison).
"""
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
RAW_DIR = ROOT / "data" / "raw" / "indonesia"
PROCESSED_DIR = ROOT / "data" / "processed"

# Taux de conversion approximatif, à mettre à jour avant d'afficher des prix à l'utilisateur.
IDR_PER_EUR = 18_500

# Rectangle englobant l'Indonésie, pour détecter des coordonnées aberrantes.
INDONESIA_BBOX = {"lat": (-11.5, 6.5), "lon": (94.5, 141.5)}

# Noms de lieux des circuits qui diffèrent légèrement de ceux de la table des lieux.
# Les deux derniers sont des rapprochements plausibles mais à valider à la main.
PLACE_ALIASES = {
    "Monas": "Monumen Nasional",
    "Taman Pelangi Jogja": "Taman Pelangi Yogyakarta",
    "Wisata Kalibiru": "Wisata Alam Kalibiru",
    "Gunung Tangkuban Perahu": "GunungTangkuban perahu",
    "Ade Irma Suryani Nasution Traffic Park": "Taman Lalu Lintas Ade Irma Suryani Nasution",
    "Stone Garden Geopark": "Stone Garden Citatah",
    "Semarang Gallery": "Semarang Contemporary Art Gallery",
}

CATEGORY_EN = {
    "Bahari": "sea",
    "Budaya": "culture",
    "Cagar Alam": "nature",
    "Pusat Perbelanjaan": "shopping",
    "Taman Hiburan": "amusement",
    "Tempat Ibadah": "religious",
}


def _haversine_km(lat1, lon1, lat2, lon2):
    """Distance en km (vectorisée) entre deux points en degrés."""
    p1, p2 = np.radians(lat1), np.radians(lat2)
    a = np.sin((p2 - p1) / 2) ** 2 + np.cos(p1) * np.cos(p2) * np.sin(np.radians(lon2 - lon1) / 2) ** 2
    return 2 * 6371.0 * np.arcsin(np.sqrt(a))


# Au-delà de ce seuil par rapport au centre médian de la ville, la coordonnée est jugée suspecte.
SUSPECT_KM = 100


def load_raw(raw_dir: Path = RAW_DIR) -> dict:
    """Lit les 4 CSV bruts. Clés : places, ratings, users, packages."""
    raw_dir = Path(raw_dir)
    return {
        "places": pd.read_csv(raw_dir / "tourism_with_id.csv"),
        "ratings": pd.read_csv(raw_dir / "tourism_rating.csv"),
        "users": pd.read_csv(raw_dir / "user.csv"),
        "packages": pd.read_csv(raw_dir / "package_tourism.csv"),
    }


def clean_places(df: pd.DataFrame, idr_per_eur: float = IDR_PER_EUR) -> pd.DataFrame:
    out = df.drop(
        columns=[c for c in df.columns if c.startswith("Unnamed") or c == "Coordinate"]
    ).rename(
        columns={
            "Place_Id": "place_id",
            "Place_Name": "name",
            "Description": "description",
            "Category": "category_raw",
            "City": "city",
            "Price": "price_idr",
            "Rating": "rating",
            "Time_Minutes": "visit_minutes",
            "Lat": "lat",
            "Long": "lon",
        }
    )
    for col in ("name", "description", "category_raw", "city"):
        out[col] = out[col].astype("string").str.strip()

    out["category"] = out["category_raw"].map(CATEGORY_EN).fillna(out["category_raw"].str.lower())

    # Durée de visite : 53 % de valeurs manquantes -> médiane de la catégorie,
    # sinon médiane globale (aucune valeur observée pour "religious").
    out["visit_minutes_imputed"] = out["visit_minutes"].isna()
    category_median = out.groupby("category")["visit_minutes"].transform("median")
    out["visit_minutes"] = (
        out["visit_minutes"].fillna(category_median).fillna(out["visit_minutes"].median())
    ).astype(int)

    # Prix : conversion en euros, indicateur de gratuité et tranche de prix.
    out["is_free"] = out["price_idr"] == 0
    out["price_eur"] = (out["price_idr"] / idr_per_eur).round(2)
    out["price_tier"] = "free"
    paid = out.loc[~out["is_free"], "price_idr"]
    out.loc[~out["is_free"], "price_tier"] = pd.qcut(
        paid.rank(method="first"), 3, labels=["low", "medium", "high"]
    ).astype(str)

    # Coordonnées : on signale les valeurs aberrantes sans supprimer la ligne.
    out["coords_ok"] = out["lat"].between(*INDONESIA_BBOX["lat"]) & out["lon"].between(
        *INDONESIA_BBOX["lon"]
    )

    # Cohérence géographique : distance au centre médian de la ville (erreurs de saisie probables au-delà de 100 km).
    med = out.groupby("city")[["lat", "lon"]].transform("median")
    out["dist_to_city_median_km"] = _haversine_km(out["lat"], out["lon"], med["lat"], med["lon"]).round(1)
    out["coords_suspect"] = out["dist_to_city_median_km"] > SUSPECT_KM
    return out


def clean_ratings(df: pd.DataFrame, places: pd.DataFrame) -> pd.DataFrame:
    out = df.rename(
        columns={"User_Id": "user_id", "Place_Id": "place_id", "Place_Ratings": "user_rating"}
    )
    out = out[out["place_id"].isin(places["place_id"])]
    # Un utilisateur peut avoir noté deux fois le même lieu : on moyenne.
    out = out.groupby(["user_id", "place_id"], as_index=False)["user_rating"].mean()
    return out


def clean_users(df: pd.DataFrame) -> pd.DataFrame:
    out = df.rename(columns={"User_Id": "user_id", "Location": "location", "Age": "age"}).copy()
    parts = out["location"].str.split(",", n=1, expand=True)
    out["origin_city"] = parts[0].str.strip()
    out["origin_province"] = parts[1].str.strip() if parts.shape[1] > 1 else pd.NA
    return out


def clean_packages(df: pd.DataFrame, places: pd.DataFrame) -> pd.DataFrame:
    """Circuits au format long : un lieu par ligne, avec son rang dans le circuit."""
    long = df.rename(columns={"Package": "package_id", "City": "city"}).melt(
        id_vars=["package_id", "city"],
        value_vars=[c for c in df.columns if c.startswith("Place_Tourism")],
        var_name="position",
        value_name="place_name",
    )
    long["position"] = long["position"].str.extract(r"(\d+)").astype(int)
    long = long.dropna(subset=["place_name"]).copy()
    # Nettoyage des noms : espaces et "| " parasites en début de chaîne, puis alias connus.
    long["place_name"] = (
        long["place_name"].str.strip().str.replace(r"^\|\s*", "", regex=True).str.strip()
    )
    long["place_name"] = long["place_name"].replace(PLACE_ALIASES)

    key = places[["place_id", "name", "city"]].rename(columns={"name": "place_name"})
    long = long.merge(key, on=["place_name", "city"], how="left")
    long["place_id"] = long["place_id"].astype("Int64")
    return long.sort_values(["package_id", "position"]).reset_index(drop=True)


def prepare_all(raw_dir: Path = RAW_DIR, idr_per_eur: float = IDR_PER_EUR) -> dict:
    raw = load_raw(raw_dir)
    places = clean_places(raw["places"], idr_per_eur)
    return {
        "places": places,
        "ratings": clean_ratings(raw["ratings"], places),
        "users": clean_users(raw["users"]),
        "packages": clean_packages(raw["packages"], places),
    }
