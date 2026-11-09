import pandas as pd
import pytest
from fastapi.testclient import TestClient

from app import config
from app.main import app
from app.recommender import Recommender
from app.schemas import ItineraryRequest, Profile


@pytest.fixture(scope="module")
def rec():
    return Recommender(pd.read_csv(config.PLACES_CSV), pd.read_csv(config.RATINGS_TRAIN_CSV))


@pytest.fixture(scope="module")
def client():
    with TestClient(app) as c:
        yield c


def test_results_sorted_and_in_city(rec):
    out = rec.recommend(Profile(city="Yogyakarta", interests={"culture": 5}), top_k=10)
    assert len(out) == 10
    assert all(i["city"] == "Yogyakarta" for i in out)
    assert all(0 <= i["score"] <= 1 for i in out)


def test_interest_drives_category(rec):
    out = rec.recommend(Profile(city="Bandung", interests={"nature": 5}), top_k=5)
    assert sum(i["category"] == "nature" for i in out) >= 3


def test_budget_and_free_filters(rec):
    out = rec.recommend(Profile(budget_eur=2.0), top_k=50)
    assert out and all(i["price_eur"] <= 2.0 for i in out)
    free = rec.recommend(Profile(free_only=True), top_k=50)
    assert free and all(i["is_free"] for i in free)


def test_liked_places_excluded_and_similarity_used(rec):
    out = rec.recommend(Profile(city="Jakarta", liked_place_ids=[1]), top_k=10)
    assert all(i["place_id"] != 1 for i in out)
    assert all("similarity" in i["breakdown"] for i in out)


def test_every_item_has_explanations(rec):
    out = rec.recommend(Profile(interests={"sea": 5}), top_k=5)
    assert all(len(i["reasons"]) >= 2 for i in out)


def test_itinerary_respects_constraints(rec):
    from app.itinerary import build_itinerary

    req = ItineraryRequest(city="Yogyakarta", days=3, interests={"culture": 5, "nature": 3}, budget_eur=10, daily_minutes=480)
    plan = build_itinerary(rec, req)
    assert 1 <= len(plan["days"]) <= 3
    ids = [s["place_id"] for d in plan["days"] for s in d["stops"]]
    assert len(ids) == len(set(ids))  # aucun lieu en double
    assert all(d["total_minutes"] <= 480 for d in plan["days"])
    assert plan["totals"]["cost_per_person_eur"] <= 10 and plan["totals"]["within_budget"]


def test_api_endpoints(client):
    assert client.get("/health").json()["status"] == "ok"
    meta = client.get("/meta").json()
    assert "Jakarta" in meta["cities"] and len(meta["categories"]) == 6
    r = client.post("/recommend", json={"city": "Bandung", "interests": {"nature": 4}, "top_k": 3})
    assert r.status_code == 200 and r.json()["count"] == 3
    r = client.post("/itinerary", json={"city": "Jakarta", "days": 2})
    assert r.status_code == 200 and r.json()["days"]
    assert client.get("/places/1").json()["similar"]


def test_api_validation_errors(client):
    assert client.post("/recommend", json={"city": "Paris"}).status_code == 422
    assert client.post("/recommend", json={"interests": {"foo": 3}}).status_code == 422
    assert client.post("/itinerary", json={"days": 2}).status_code == 422  # ville obligatoire
    assert client.get("/places/99999").status_code == 404


def test_itinerary_excludes_suspect_coordinates(rec):
    from app.itinerary import build_itinerary

    for city in ("Jakarta", "Bandung"):
        plan = build_itinerary(rec, ItineraryRequest(city=city, days=14, daily_minutes=720))
        stops = [s for d in plan["days"] for s in d["stops"]]
        assert stops and not any(s["coords_suspect"] for s in stops)
        assert max(s["travel_km"] for s in stops) < 100
