import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))

import evaluate_full as ev  # noqa: E402
from app import config  # noqa: E402


def test_rank_metrics_known_values():
    # pertinents = {1, 5} ; liste = [1, 2, 3, 4] ; K = 4
    m = ev.rank_metrics([1, 2, 3, 4], {1, 5}, 4)
    assert m["P"] == pytest.approx(0.25)
    assert m["R"] == pytest.approx(0.5)
    assert m["HR"] == 1.0
    # DCG = 1/log2(2) = 1 ; IDCG = 1 + 1/log2(3)
    assert m["NDCG"] == pytest.approx(1.0 / (1.0 + 1.0 / np.log2(3)))


def test_rank_metrics_no_hit_and_perfect():
    assert ev.rank_metrics([2, 3], {1}, 2) == {"P": 0.0, "R": 0.0, "HR": 0.0, "NDCG": 0.0}
    perfect = ev.rank_metrics([1, 5, 9], {1, 5}, 2)
    assert perfect["NDCG"] == pytest.approx(1.0) and perfect["R"] == 1.0


def test_gini_extremes():
    assert ev.gini([1, 1, 1, 1]) == pytest.approx(0.0)
    assert ev.gini([0, 0, 0, 10]) == pytest.approx(0.75)


def test_paired_p_detects_real_difference_and_not_noise():
    rng = np.random.default_rng(0)
    a = rng.normal(0.5, 0.2, 300)
    assert ev.paired_p(a, a - 0.2)[3] < 0.01
    assert ev.paired_p(a, a + rng.normal(0, 0.2, 300))[3] > 0.01


@pytest.fixture(scope="module")
def ctx():
    places = pd.read_csv(config.PLACES_CSV)
    train = pd.read_csv(config.RATINGS_TRAIN_CSV)
    return ev.Ctx(places, train, places), train


def test_harness_hybrid_matches_engine(ctx):
    c, train = ctx
    for uid in (1, 17, 123):
        tr = train[train["user_id"] == uid].set_index("place_id")["user_rating"]
        assert ev.check_fidelity(c, tr)


def test_rankings_never_return_excluded_items(ctx):
    c, train = ctx
    tr = train[train["user_id"] == 5].set_index("place_id")["user_rating"]
    allowed = np.ones(c.n, dtype=bool)
    for i in tr.index:
        allowed[c.rec.pos[i]] = False
    for name, o in ev.rankings(c, tr, allowed, np.random.default_rng(0)).items():
        assert allowed[o].all(), name
        assert len(set(o)) == len(o) == ev.KMAX, name
