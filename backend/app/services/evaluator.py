from typing import Dict, Any
from app.services.football_data import (
    get_head2head,
    get_recent_history,
    get_competition_standings,
)
from app.services.odds_api import fetch_odds
from app.services.scoring import score_match


def _count_draws_in_h2h(h2h_matches: list) -> int:
    draws = 0
    for m in h2h_matches:
        score = m.get("score", {})
        full = score.get("fullTime") or {}
        if full.get("home") is None or full.get("away") is None:
            continue
        if full.get("home") == full.get("away"):
            draws += 1
    return draws


def _goal_diff_one_count(matches: list) -> int:
    c = 0
    for m in matches:
        score = m.get("score", {})
        full = score.get("fullTime") or {}
        if full.get("home") is None or full.get("away") is None:
            continue
        if abs(full.get("home") - full.get("away")) == 1:
            c += 1
    return c


def evaluate_match(home_id: int, away_id: int, competition_id: int, draw_odds: float | None = None, under25_odds: float | None = None) -> Dict[str, Any]:
    """Evaluate a match using the user's criteria. Returns a dict with rule results and final decision.

    If odds are not provided we attempt to fetch them from the secondary odds provider; if unavailable the odds checks are marked as 'unknown'.
    """
    result = {
        "h2h": {},
        "odds": {},
        "under25": {},
        "score_margin": {},
        "incentive": {},
        "final": None,
    }

    # H2H
    status, h2h = get_head2head(home_id, away_id, limit=10)
    if status == 200:
        draws = _count_draws_in_h2h(h2h)
        result["h2h"] = {"draws_in_10": draws, "passes": draws >= 4}
        if draws >= 4:
            result["final"] = {"decision": True, "reason": "h2h_override"}
            return result
    else:
        result["h2h"] = {"error": h2h}

    # Recent history -> score margin rule
    s_status, s_home = get_recent_history(home_id, limit=5)
    s_status2, s_away = get_recent_history(away_id, limit=5)
    if s_status == 200 and s_status2 == 200:
        home_gd1 = _goal_diff_one_count(s_home)
        away_gd1 = _goal_diff_one_count(s_away)
        result["score_margin"] = {
            "home_gd1_in_5": home_gd1,
            "away_gd1_in_5": away_gd1,
            "passes": home_gd1 >= 3 and away_gd1 >= 3,
        }
    else:
        result["score_margin"] = {"error": (s_home if s_status != 200 else s_away)}

    # Standings / incentive / context (mid-table)
    st_status, standings = get_competition_standings(competition_id)
    if st_status == 200:
        # find table entries
        table = None
        if isinstance(standings, dict):
            # football-data returns 'standings' list with 'table' inside
            for s in standings.get("standings", []):
                if s.get("type") == "TOTAL":
                    table = s.get("table")
                    break
            if table is None:
                # fallback: take first standings table
                first = standings.get("standings")
                if first and isinstance(first, list):
                    table = first[0].get("table")
        if table:
            num_teams = len(table)
            def find_pos(team_id):
                for row in table:
                    t = row.get("team", {})
                    if t.get("id") == team_id:
                        return row.get("position"), row.get("points")
                return None, None

            home_pos, home_pts = find_pos(home_id)
            away_pos, away_pts = find_pos(away_id)
            mid_min = 5
            mid_max = max(5, num_teams - 4)
            home_mid = home_pos is not None and (mid_min <= home_pos <= mid_max)
            away_mid = away_pos is not None and (mid_min <= away_pos <= mid_max)
            incentive = home_mid and away_mid and abs((home_pos or 0) - (away_pos or 0)) <= 5
            result["incentive"] = {
                "home_pos": home_pos,
                "away_pos": away_pos,
                "num_teams": num_teams,
                "home_mid": home_mid,
                "away_mid": away_mid,
                "passes": incentive,
            }
        else:
            result["incentive"] = {"error": "standings_table_unavailable"}
    else:
        result["incentive"] = {"error": standings}

    # Odds checks
    odds_checks = {"draw": None, "under25": None}

    # If caller provided override odds, use them
    if draw_odds is not None:
        odds_checks["draw"] = {"value": draw_odds, "passes": draw_odds >= 3.0}
    if under25_odds is not None:
        odds_checks["under25"] = {"value": under25_odds, "passes": 1.5 <= under25_odds <= 1.7}

    # Attempt fetch from secondary odds provider if any are missing
    if odds_checks["draw"] is None or odds_checks["under25"] is None:
        # naive attempt: try fetching odds by searching provider root; path may vary by provider
        status, data = fetch_odds(path='odds', params={"home": home_id, "away": away_id})
        if status == 200 and isinstance(data, dict):
            # Attempt to locate markets
            # Look for keys that might contain odds; providers differ widely, so this is best-effort
            # Check for 'markets' or 'bookmakers'
            markets = []
            if "markets" in data and isinstance(data["markets"], list):
                markets = data["markets"]
            elif "bookmakers" in data and isinstance(data["bookmakers"], list):
                for bm in data["bookmakers"]:
                    markets.extend(bm.get("markets", []))

            # search markets for '1X2' or 'total' entries
            for m in markets:
                name = m.get("key") or m.get("name", '').lower()
                outcomes = m.get("outcomes") or m.get("selections") or []
                if "1x2" in name or "match" in name and (odds_checks["draw"] is None):
                    # find draw outcome
                    for o in outcomes:
                        lab = (o.get("label") or o.get("name") or "").lower()
                        if lab in ("draw", "x"):
                            try:
                                val = float(o.get("price") or o.get("odds") or o.get("decimal"))
                                odds_checks["draw"] = {"value": val, "passes": val >= 3.0}
                            except Exception:
                                pass
                if ("total" in name or "over/under" in name or "goals" in name) and (odds_checks["under25"] is None):
                    for o in outcomes:
                        lab = (o.get("label") or o.get("name") or "").lower()
                        if "under 2.5" in lab or "u2.5" in lab or "under 2.5" in name:
                            try:
                                val = float(o.get("price") or o.get("odds") or o.get("decimal"))
                                odds_checks["under25"] = {"value": val, "passes": 1.5 <= val <= 1.7}
                            except Exception:
                                pass

    result["odds"] = odds_checks

    # Final decision: require all checks (score_margin, incentive, draw odds, under25) to pass
    missing = []
    failed = []

    # score_margin
    sm = result.get("score_margin")
    if isinstance(sm, dict) and "passes" in sm:
        if not sm["passes"]:
            failed.append("score_margin")
    else:
        missing.append("score_margin")

    inc = result.get("incentive")
    if isinstance(inc, dict) and "passes" in inc:
        if not inc["passes"]:
            failed.append("incentive")
    else:
        missing.append("incentive")

    # draw odds
    d = odds_checks.get("draw")
    if d is None:
        missing.append("draw_odds")
    else:
        if not d.get("passes"):
            failed.append("draw_odds")

    # under25
    u = odds_checks.get("under25")
    if u is None:
        missing.append("under25_odds")
    else:
        if not u.get("passes"):
            failed.append("under25_odds")

    # Attach rule-based scoring summary (Phase 4 engine)
    try:
        scoring = score_match(home_id, away_id, competition_id, draw_odds=(d.get("value") if d else None), under25_odds=(u.get("value") if u else None))
    except Exception as e:
        scoring = {"error": str(e)}
    result["scoring"] = scoring

    # Use scoring decision as authoritative for final output when available
    if isinstance(scoring, dict) and "passes" in scoring:
        result["final"] = {"decision": bool(scoring.get("passes")), "score": scoring.get("score"), "reasons": scoring.get("reasons")}
    else:
        if failed:
            result["final"] = {"decision": False, "failed_rules": failed, "missing": missing}
        elif missing:
            result["final"] = {"decision": None, "reason": "missing_data", "missing": missing}
        else:
            result["final"] = {"decision": True, "reason": "all_checks_passed"}

    return result
