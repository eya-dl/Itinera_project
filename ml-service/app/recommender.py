"""Moteur de recommandation de lieux : hybride contenu + qualité + budget + similarité.

Le score d'un lieu combine :
- interests  : adéquation entre la catégorie du lieu et les intérêts déclarés (0-5)
- quality    : note du lieu et moyenne bayésienne des notes utilisateurs
- budget     : prix d'entrée comparé à la part de budget par visite
- similarity : proximité avec des lieux déjà aimés (filtrage item-item + contenu)
Les composantes inactives (pas d'intérêts, pas de budget, pas de lieux aimés) sont écartées
et les poids renormalisés. Les explications sont générées à partir de ces composantes.
"""
import numpy as np
import pandas as pd

from . import config
from .schemas import Profile

BAYES_PRIOR = 20  # nombre de notes "fictives" pour lisser la moyenne des notes utilisateurs


class UnknownCityError(ValueError):
    pass


class Recommender:
    def __init__(self, places: pd.DataFrame, ratings_train: pd.DataFrame):
        self.places = places.set_index("place_id", drop=False).copy()
        self.cities = sorted(self.places["city"].unique())
        self.ids = list(self.places.index)
        self.pos = {pid: i for i, pid in enumerate(self.ids)}

        gm = ratings_train["user_rating"].mean()
        st = ratings_train.groupby("place_id")["user_rating"].agg(["count", "mean"])
        bayes = (st["count"] * st["mean"] + BAYES_PRIOR * gm) / (st["count"] + BAYES_PRIOR)
        user_q = (bayes.reindex(self.places.index).fillna(gm) - 1) / 4
        r = self.places["rating"]
        rating_q = (r - r.min()) / (r.max() - r.min())
        self.places["quality"] = 0.7 * rating_q + 0.3 * user_q

        # Similarité item-item (cosinus sur notes centrées par utilisateur).
        m = ratings_train.pivot(index="user_id", columns="place_id", values="user_rating")
        centered = m.sub(m.mean(axis=1), axis=0).fillna(0).reindex(columns=self.places.index, fill_value=0)
        x = centered.to_numpy()
        norms = np.linalg.norm(x, axis=0)
        norms[norms == 0] = 1.0
        self.sim = (x.T @ x) / np.outer(norms, norms)
        np.fill_diagonal(self.sim, 0.0)

    # ------------------------------------------------------------------ utilitaires
    def get_place(self, place_id: int) -> dict:
        if place_id not in self.pos:
            raise KeyError(place_id)
        return self._to_dict(self.places.loc[place_id])

    @staticmethod
    def _short(text: str, n: int = 240) -> str:
        text = " ".join(str(text).split())
        return text if len(text) <= n else text[: n - 1].rsplit(" ", 1)[0] + "…"

    def _to_dict(self, row) -> dict:
        return {
            "place_id": int(row["place_id"]),
            "name": row["name"],
            "city": row["city"],
            "category": row["category"],
            "category_label": config.CATEGORY_LABELS_FR.get(row["category"], row["category"]),
            "description": self._short(row["description"]),
            "price_idr": int(row["price_idr"]),
            "price_eur": float(row["price_eur"]),
            "is_free": bool(row["is_free"]),
            "visit_minutes": int(row["visit_minutes"]),
            "duration_estimated": bool(row["visit_minutes_imputed"]),
            "rating": float(row["rating"]),
            "lat": float(row["lat"]),
            "lon": float(row["lon"]),
            "coords_suspect": bool(row["coords_suspect"]),
        }

    def _content_similarity(self, row, liked: pd.DataFrame) -> float:
        score = (
            0.6 * (liked["category"] == row["category"]).mean()
            + 0.2 * (liked["city"] == row["city"]).mean()
            + 0.2 * (liked["price_tier"] == row["price_tier"]).mean()
        )
        return float(score)

    def _similarity_scores(self, df: pd.DataFrame, liked_ids: list) -> pd.Series:
        liked_ids = [i for i in liked_ids if i in self.pos]
        liked = self.places.loc[liked_ids]
        cols = [self.pos[i] for i in liked_ids]
        cf = pd.Series([self.sim[self.pos[pid], cols].mean() for pid in df.index], index=df.index)
        cf_rank = cf.rank(pct=True)  # robuste à l'échelle des similarités
        content = pd.Series([self._content_similarity(r, liked) for _, r in df.iterrows()], index=df.index)
        return 0.5 * cf_rank + 0.5 * content

    # ------------------------------------------------------------------ recommandation
    def candidates(self, p: Profile) -> pd.DataFrame:
        df = self.places
        if p.city:
            if p.city not in self.cities:
                raise UnknownCityError(f"Ville inconnue : {p.city!r}. Villes disponibles : {self.cities}")
            df = df[df["city"] == p.city]
        if p.free_only:
            df = df[df["is_free"]]
        if p.budget_eur is not None:
            df = df[df["price_eur"] <= p.budget_eur]
        return df[~df.index.isin(p.liked_place_ids)].copy()

    def score(self, p: Profile) -> pd.DataFrame:
        df = self.candidates(p)
        if df.empty:
            return df
        comps = {}
        weights = {}

        if sum(p.interests.values()) > 0:
            comps["interests"] = df["category"].map(lambda c: p.interests.get(c, 0) / 5)
            weights["interests"] = config.SCORE_WEIGHTS["interests"]
        comps["quality"] = df["quality"]
        weights["quality"] = config.SCORE_WEIGHTS["quality"]
        if p.budget_eur is not None:
            share = p.budget_eur / (p.days * config.PAID_VISITS_PER_DAY)
            comps["budget"] = df["price_eur"].map(lambda x: 1.0 if x == 0 else max(0.0, 1 - x / share))
            weights["budget"] = config.SCORE_WEIGHTS["budget"]
        if p.liked_place_ids and any(i in self.pos for i in p.liked_place_ids):
            comps["similarity"] = self._similarity_scores(df, p.liked_place_ids)
            weights["similarity"] = config.SCORE_WEIGHTS["similarity"]

        total = sum(weights.values())
        df["score"] = sum(comps[k] * weights[k] / total for k in comps)
        for k, s in comps.items():
            df[f"c_{k}"] = s
        df.attrs["weights"] = {k: round(w / total, 3) for k, w in weights.items()}
        return df

    def _reasons(self, row, p: Profile) -> list:
        reasons = []
        label = config.CATEGORY_LABELS_FR.get(row["category"], row["category"])
        w = p.interests.get(row["category"], 0)
        if w >= 3:
            reasons.append(f"Correspond à ton intérêt pour « {label} » ({w}/5).")
        reasons.append("Entrée gratuite." if row["is_free"] else f"Entrée d'environ {row['price_eur']:.2f} € par personne.")
        suffix = " (durée estimée)" if row["visit_minutes_imputed"] else ""
        reasons.append(f"Visite d'environ {int(row['visit_minutes'])} min{suffix}.")
        if row["rating"] >= 4.5:
            reasons.append(f"Très bien noté ({row['rating']:.1f}/5).")
        if row.get("c_similarity", 0) >= 0.6:
            reasons.append("Proche de lieux que tu as aimés.")
        return reasons

    def recommend(self, p: Profile, top_k: int = 10) -> list:
        df = self.score(p)
        if df.empty:
            return []
        picked, counts = [], {}
        remaining = df.sort_values("score", ascending=False)
        while len(picked) < top_k and not remaining.empty:
            adj = remaining["score"] - config.DIVERSITY_PENALTY * remaining["category"].map(lambda c: counts.get(c, 0))
            best_id = adj.idxmax()
            row = remaining.loc[best_id]
            picked.append(row)
            counts[row["category"]] = counts.get(row["category"], 0) + 1
            remaining = remaining.drop(best_id)

        out = []
        for row in picked:
            item = self._to_dict(row)
            item["score"] = round(float(row["score"]), 3)
            item["breakdown"] = {k[2:]: round(float(row[k]), 3) for k in row.index if k.startswith("c_")}
            item["reasons"] = self._reasons(row, p)
            out.append(item)
        return out

    def similar_places(self, place_id: int, n: int = 5) -> list:
        if place_id not in self.pos:
            raise KeyError(place_id)
        base = self.places.loc[place_id]
        liked = self.places.loc[[place_id]]
        df = self.places.drop(place_id)
        cf = pd.Series(self.sim[self.pos[place_id], [self.pos[i] for i in df.index]], index=df.index)
        content = pd.Series([self._content_similarity(r, liked) for _, r in df.iterrows()], index=df.index)
        s = (0.5 * cf.rank(pct=True) + 0.5 * content).sort_values(ascending=False).head(n)
        return [{**self._to_dict(df.loc[i]), "similarity": round(float(v), 3)} for i, v in s.items()]
