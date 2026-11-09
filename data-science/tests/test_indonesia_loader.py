import pytest

from voyage.indonesia import prepare_all


@pytest.fixture(scope="module")
def data():
    return prepare_all()


def test_places_clean(data):
    p = data["places"]
    assert p["place_id"].is_unique
    assert not any(c.startswith("Unnamed") for c in p.columns)
    assert p["visit_minutes"].notna().all() and (p["visit_minutes"] > 0).all()
    assert (p["price_eur"] >= 0).all()
    assert set(p["price_tier"]) <= {"free", "low", "medium", "high"}
    assert p["coords_ok"].all()


def test_free_places_have_free_tier(data):
    p = data["places"]
    assert (p.loc[p["is_free"], "price_tier"] == "free").all()
    assert (p.loc[~p["is_free"], "price_tier"] != "free").all()


def test_ratings_deduplicated_and_valid(data):
    r, p = data["ratings"], data["places"]
    assert not r.duplicated(["user_id", "place_id"]).any()
    assert r["place_id"].isin(p["place_id"]).all()
    assert r["user_rating"].between(1, 5).all()


def test_users_origin_split(data):
    u = data["users"]
    assert u["origin_city"].notna().all()


def test_packages_long_format(data):
    k = data["packages"]
    assert k["position"].between(1, 5).all()
    assert k["place_id"].notna().mean() > 0.9  # la quasi-totalité des noms se rapproche


def test_suspect_coordinates_are_flagged_not_dropped(data):
    p = data["places"]
    assert len(p) == 437
    assert 1 <= p["coords_suspect"].sum() <= 5
    assert "Pelabuhan Marina" in set(p.loc[p["coords_suspect"], "name"])
