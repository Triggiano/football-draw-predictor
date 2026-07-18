import pytest
from app.services.scoring import score_match


def test_score_match_passes_with_good_odds():
    # Provide draw and under odds so external fetch is not required
    res = score_match(home_id=1, away_id=2, competition_id=100, draw_odds=3.2, under25_odds=1.6)
    assert isinstance(res, dict)
    assert "score" in res
    assert res["score"] >= 65
    assert res["passes"] is True


def test_score_match_fails_with_bad_odds():
    res = score_match(home_id=1, away_id=2, competition_id=100, draw_odds=2.0, under25_odds=2.5)
    assert isinstance(res, dict)
    assert "score" in res
    assert res["passes"] is False
