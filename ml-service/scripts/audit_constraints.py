"""Audit automatique des contraintes dures, de la cohérence géographique et de la fidélité des explications.

Génère N profils aléatoires, construit l'itinéraire et la liste de recommandations, puis vérifie sans exception :
budget, temps par jour, absence de doublons, coordonnées suspectes exclues, distances recalculées, filtre « gratuit »,
exclusion des lieux aimés, et que chaque phrase de `reasons` correspond aux champs numériques du lieu.
Compare aussi la distance moyenne entre étapes à celle de lieux tirés au hasard dans la même ville.

Usage : python scripts/audit_constraints.py [N]   ->   reports/audit_contraintes.md  (code de sortie 1 s'il y a une violation)
"""
import re
import sys
from collections import Counter
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from app import config  # noqa: E402
from app.itinerary import build_itinerary, haversine_km  # noqa: E402
from app.recommender import Recommender  # noqa: E402
from app.schemas import ItineraryRequest, Profile  # noqa: E402


def check_reasons(item, liked_ids, interests, bad):
    price = f"{item['price_eur']:.2f}"
    for r in item["reasons"]:
        if r == "Entrée gratuite.":
            ok = item["is_free"]
        elif (m := re.fullmatch(r"Entrée d'environ ([\d.]+) € par personne\.", r)):
            ok = (not item["is_free"]) and m.group(1) == price
        elif (m := re.fullmatch(r"Visite d'environ (\d+) min( \(durée estimée\))?\.", r)):
            ok = int(m.group(1)) == int(item["visit_minutes"]) and bool(m.group(2)) == item["duration_estimated"]
        elif (m := re.fullmatch(r"Très bien noté \(([\d.]+)/5\)\.", r)):
            ok = item["rating"] >= 4.5 and m.group(1) == f"{item['rating']:.1f}"
        elif (m := re.fullmatch(r"Correspond à ton intérêt pour « (.+) » \((\d)/5\)\.", r)):
            ok = config.CATEGORY_LABELS_FR[item["category"]] == m.group(1) and interests.get(item["category"], 0) == int(m.group(2)) >= 3
        elif r == "Proche de lieux que tu as aimés.":
            ok = bool(liked_ids)
        else:
            ok = False
        if not ok:
            bad["explication infidèle"] += 1
    # complétude : un lieu gratuit/payant, une durée, doivent toujours être mentionnés
    if sum(r.startswith(("Entrée", "Visite")) for r in item["reasons"]) < 2:
        bad["explication incomplète"] += 1


def main(n=400):
    places = pd.read_csv(config.PLACES_CSV)
    rec = Recommender(places, pd.read_csv(config.RATINGS_TRAIN_CSV))
    rng = np.random.default_rng(123)
    cities = sorted(places["city"].unique())
    ok_places = places[~places["coords_suspect"]]
    bad, checks, n_stops, days_built = Counter(), Counter(), 0, 0
    ratio_it, ratio_rand = [], []

    for _ in range(n):
        city = str(rng.choice(cities))
        pool = places[places["city"] == city]["place_id"].to_numpy()
        liked = [int(x) for x in rng.choice(pool, int(rng.integers(0, 4)), replace=False)]
        interests = {str(c): int(rng.integers(1, 6)) for c in rng.choice(config.CATEGORIES, int(rng.integers(0, 4)), replace=False)}
        kw = dict(interests=interests, days=int(rng.integers(1, 8)), travelers=int(rng.integers(1, 5)),
                  free_only=bool(rng.random() < 0.1), liked_place_ids=liked)
        if rng.random() < 0.6:
            kw["budget_eur"] = float(rng.choice([1, 3, 5, 10, 20, 40]))
        req = ItineraryRequest(city=city, daily_minutes=int(rng.choice([240, 360, 480, 720])), start_hour=int(rng.integers(6, 13)), **kw)
        plan = build_itinerary(rec, req)
        recs = rec.recommend(Profile(city=city, **kw), top_k=10)

        # --- recommandations
        for it in recs:
            checks["recommandation"] += 1
            bad["lieu aimé recommandé"] += it["place_id"] in liked
            bad["ville incorrecte"] += it["city"] != city
            bad["budget (recommandation)"] += "budget_eur" in kw and it["price_eur"] > kw["budget_eur"] + 1e-9
            bad["lieu payant en mode gratuit"] += kw["free_only"] and not it["is_free"]
            check_reasons(it, liked, interests, bad)
        # --- itinéraire
        t = plan["totals"]
        checks["itinéraire"] += 1
        bad["budget dépassé"] += "budget_eur" in kw and t["cost_per_person_eur"] > kw["budget_eur"] + 1e-9
        bad["drapeau within_budget faux"] += t["within_budget"] != ("budget_eur" not in kw or t["cost_per_person_eur"] <= kw["budget_eur"] + 1e-9)
        bad["trop de jours"] += len(plan["days"]) > req.days
        ids = [s["place_id"] for d in plan["days"] for s in d["stops"]]
        bad["doublon"] += len(ids) != len(set(ids))
        bad["lieu aimé dans l'itinéraire"] += bool(set(ids) & set(liked))
        for d in plan["days"]:
            days_built += 1
            stops = d["stops"]
            visit = sum(s["visit_minutes"] for s in stops)
            travel = sum(s["travel_minutes"] for s in stops)
            bad["temps journalier dépassé"] += d["total_minutes"] > req.daily_minutes
            bad["temps incohérent"] += abs(d["total_minutes"] - (visit + travel)) > len(stops)  # arrondis des trajets
            times = [m for s in stops for m in (s["start_time"], s["end_time"])]
            bad["horaires non croissants"] += times != sorted(times)
            for a, b in zip(stops, stops[1:]):
                bad["distance recalculée fausse"] += abs(haversine_km(a["lat"], a["lon"], b["lat"], b["lon"]) - b["travel_km"]) > 0.06
            for s in stops:
                n_stops += 1
                bad["coordonnées suspectes"] += s["coords_suspect"]
                bad["payant en mode gratuit"] += kw["free_only"] and not s["is_free"]
                check_reasons(s, liked, interests, bad)
            if len(stops) >= 2:
                ratio_it.append(np.mean([s["travel_km"] for s in stops[1:]]))
                sample = ok_places[ok_places["city"] == city].sample(len(stops), random_state=int(rng.integers(1e9)))
                pts = sample[["lat", "lon"]].to_numpy()
                ratio_rand.append(np.mean([haversine_km(*pts[i], *pts[i + 1]) for i in range(len(pts) - 1)]))

    total = sum(bad.values())
    L = ["# Audit automatique des contraintes et des explications", "",
         f"{n} profils aléatoires (ville, 1 à 7 jours, budget optionnel, mode gratuit, temps par jour, intérêts, 0 à 3 lieux aimés) : "
         f"{checks['itinéraire']} itinéraires ({days_built} jours, {n_stops} étapes) et {checks['recommandation']} recommandations vérifiés.", "",
         "| Vérification | Violations |", "|---|---|"]
    names = ["budget dépassé", "drapeau within_budget faux", "budget (recommandation)", "temps journalier dépassé", "temps incohérent", "horaires non croissants",
             "doublon", "trop de jours", "coordonnées suspectes", "distance recalculée fausse", "payant en mode gratuit", "lieu payant en mode gratuit",
             "lieu aimé recommandé", "lieu aimé dans l'itinéraire", "ville incorrecte", "explication infidèle", "explication incomplète"]
    L += [f"| {k} | {bad[k]} |" for k in names]
    L += ["", f"**Total : {total} violation(s).**", "",
          f"Cohérence géographique : distance moyenne entre étapes consécutives = {np.mean(ratio_it):.1f} km dans les itinéraires, "
          f"contre {np.mean(ratio_rand):.1f} km pour le même nombre de lieux tirés au hasard dans la même ville "
          f"({np.mean(ratio_it) / np.mean(ratio_rand):.0%} de la distance aléatoire).", ""]
    (ROOT / "reports").mkdir(exist_ok=True)
    (ROOT / "reports" / "audit_contraintes.md").write_text("\n".join(L), encoding="utf-8")
    print("\n".join(L))
    sys.exit(1 if total else 0)


if __name__ == "__main__":
    main(int(sys.argv[1]) if len(sys.argv) > 1 else 400)
