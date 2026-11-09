"""Construction d'itinéraire : un jour = un groupe de lieux proches, sous contrainte de temps et de budget."""
import math

from . import config
from .recommender import Recommender
from .schemas import ItineraryRequest


def haversine_km(lat1, lon1, lat2, lon2) -> float:
    r = 6371.0
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dphi, dl = p2 - p1, math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * r * math.asin(math.sqrt(a))


def _hhmm(minutes: float) -> str:
    m = int(round(minutes))
    return f"{m // 60:02d}:{m % 60:02d}"


def build_itinerary(rec: Recommender, req: ItineraryRequest) -> dict:
    # Les lieux aux coordonnées suspectes sont exclus : ils fausseraient distances et temps de trajet.
    pool = [p for p in rec.recommend(req, top_k=min(80, req.days * 10) + 5) if not p["coords_suspect"]]
    warnings = []
    if not pool:
        return {"city": req.city, "days": [], "totals": _totals([], req), "warnings": ["Aucun lieu ne correspond aux critères."]}

    spent = 0.0  # coût d'entrée par personne déjà engagé

    def affordable(p) -> bool:
        return req.budget_eur is None or spent + p["price_eur"] <= req.budget_eur + 1e-9

    days = []
    for d in range(1, req.days + 1):
        seed = next((p for p in pool if affordable(p)), None)
        if seed is None:
            break
        pool.remove(seed)
        stops = [{**seed, "travel_minutes": 0, "travel_km": 0.0}]
        spent += seed["price_eur"]
        used = seed["visit_minutes"]

        while True:
            last = stops[-1]
            best, best_key, best_t, best_km = None, None, 0, 0.0
            for p in pool:
                if not affordable(p):
                    continue
                km = haversine_km(last["lat"], last["lon"], p["lat"], p["lon"])
                t = km / config.TRAVEL_SPEED_KMH * 60 + config.HOP_OVERHEAD_MIN
                if used + t + p["visit_minutes"] > req.daily_minutes:
                    continue
                key = km - 8 * p["score"]  # proche et bien classé
                if best_key is None or key < best_key:
                    best, best_key, best_t, best_km = p, key, t, km
            if best is None:
                break
            pool.remove(best)
            spent += best["price_eur"]
            used += best_t + best["visit_minutes"]
            stops.append({**best, "travel_minutes": int(round(best_t)), "travel_km": round(best_km, 1)})

        clock = req.start_hour * 60
        for s in stops:
            clock += s["travel_minutes"]
            s["start_time"] = _hhmm(clock)
            clock += s["visit_minutes"]
            s["end_time"] = _hhmm(clock)

        days.append({
            "day": d,
            "stops": stops,
            "total_minutes": int(round(used)),
            "distance_km": round(sum(s["travel_km"] for s in stops), 1),
            "cost_eur": round(sum(s["price_eur"] for s in stops), 2),
            "summary": f"{len(stops)} lieu(x), environ {used / 60:.1f} h, de {stops[0]['start_time']} à {stops[-1]['end_time']}.",
        })

    if len(days) < req.days:
        warnings.append(f"Seulement {len(days)} jour(s) planifié(s) sur {req.days} : pas assez de lieux compatibles avec le budget ou la ville.")
    return {"city": req.city, "days": days, "totals": _totals(days, req), "warnings": warnings}


def _totals(days: list, req: ItineraryRequest) -> dict:
    per_person = round(sum(d["cost_eur"] for d in days), 2)
    return {
        "places": sum(len(d["stops"]) for d in days),
        "cost_per_person_eur": per_person,
        "cost_group_eur": round(per_person * req.travelers, 2),
        "budget_eur": req.budget_eur,
        "within_budget": req.budget_eur is None or per_person <= req.budget_eur + 1e-9,
        "distance_km": round(sum(d["distance_km"] for d in days), 1),
    }
