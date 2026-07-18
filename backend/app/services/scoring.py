from typing import Dict, Any, List, Optional, Tuple
from app.services.football_data import (
    get_head2head,
    get_recent_history,
    get_competition_standings,
)
from app.services.odds_api import fetch_odds


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


def _fetch_markets(home_id: int, away_id: int) -> Tuple[Optional[float], Optional[float], Optional[float], Dict[str, Any]]:
    """Try to fetch draw odds, under2.5 odds, and best winner odds (min of home/away) from provider.

    Returns: (draw_odds, under25_odds, min_winner_odds, raw_data)
    """
    try:
        status, data = fetch_odds(path="odds", params={"home": home_id, "away": away_id})
    except Exception:
        return None, None, None, {}

    if status != 200 or not isinstance(data, dict):
        return None, None, None, data

    markets = []
    if "markets" in data and isinstance(data["markets"], list):
        markets = data["markets"]
    elif "bookmakers" in data and isinstance(data["bookmakers"], list):
        for bm in data["bookmakers"]:
            markets.extend(bm.get("markets", []))

    draw_odds = None
    under25_odds = None
    winner_odds: List[float] = []

    for m in markets:
        name = (m.get("key") or m.get("name") or "").lower()
        outcomes = m.get("outcomes") or m.get("selections") or []

        # draw
        if "1x2" in name or "match" in name or "1 x 2" in name:
            for o in outcomes:
                lab = (o.get("label") or o.get("name") or "").lower()
                try:
                    val = float(o.get("price") or o.get("odds") or o.get("decimal"))
                except Exception:
                    continue
                if lab in ("draw", "x"):
                    draw_odds = val
                if lab in ("home", "1", "home win", "home victory"):
                    winner_odds.append(val)
                if lab in ("away", "2", "away win", "away victory"):
                    winner_odds.append(val)

        # under 2.5
        if "total" in name or "over/under" in name or "goals" in name or "under" in name:
            for o in outcomes:
                lab = (o.get("label") or o.get("name") or "").lower()
                if "under 2.5" in lab or "u2.5" in lab or "under 2.5" in name:
                    try:
                        under25_odds = float(o.get("price") or o.get("odds") or o.get("decimal"))
                    except Exception:
                        pass

    min_winner = min(winner_odds) if winner_odds else None
    return draw_odds, under25_odds, min_winner, data


def score_match(home_id: int, away_id: int, competition_id: int, draw_odds: float | None = None, under25_odds: float | None = None) -> Dict[str, Any]:
    """Score a match for 'draw' potential. Returns score 0-100 with per-criterion reasons.

    Criteria (example weighting):
    - draw odds in 3.1-3.6: 25
    - team balance (standings): 15
    - recent draw rate: 15
    - under2.5 odds 1.50-1.70: 10
    - low goal diff trend: 10
    - H2H draws: 15
    - no huge favorite: 10
    """
    reasons: Dict[str, Any] = {}
    total = 0

    # H2H
    try:
        st, h2h = get_head2head(home_id, away_id, limit=6)
    except Exception:
        st, h2h = None, None

    h2h_draws = None
    if st == 200 and isinstance(h2h, list):
        h2h_draws = _count_draws_in_h2h(h2h)
        if h2h_draws >= 2:
            h2h_points = 15
        elif h2h_draws == 1:
            h2h_points = 7
        else:
            h2h_points = 0
        reasons["h2h_draws"] = h2h_draws
        reasons["h2h_draw_points"] = h2h_points
        total += h2h_points
    else:
        reasons["h2h_error"] = True
        reasons["h2h_draw_points"] = 0

    # Recent history -> draw rate and goal-diff trend
    try:
        s1_status, s_home = get_recent_history(home_id, limit=6)
        s2_status, s_away = get_recent_history(away_id, limit=6)
    except Exception:
        s1_status, s_home, s2_status, s_away = None, None, None, None

    # draw rate
    draw_rate_points = 0
    if s1_status == 200 and s2_status == 200 and isinstance(s_home, list) and isinstance(s_away, list):
        def draw_rate(matches: List[dict]) -> float:
            c = 0
            t = 0
            for m in matches:
                score = m.get("score", {})
                full = score.get("fullTime") or {}
                if full.get("home") is None or full.get("away") is None:
                    continue
                t += 1
                if full.get("home") == full.get("away"):
                    c += 1
            return c / t if t else 0.0

        r1 = draw_rate(s_home)
        r2 = draw_rate(s_away)
        avg_draw_rate = (r1 + r2) / 2
        reasons["recent_draw_rate"] = round(avg_draw_rate, 3)
        if avg_draw_rate >= 0.4:
            draw_rate_points = 15
        elif avg_draw_rate >= 0.25:
            draw_rate_points = 7
        total += draw_rate_points
        reasons["recent_draw_points"] = draw_rate_points
    else:
        reasons["recent_draw_error"] = True
        reasons["recent_draw_points"] = 0

    # low goal diff trend
    gd_points = 0
    if s1_status == 200 and s2_status == 200 and isinstance(s_home, list) and isinstance(s_away, list):
        hd = _goal_diff_one_count(s_home)
        ad = _goal_diff_one_count(s_away)
        reasons["home_gd1_in_6"] = hd
        reasons["away_gd1_in_6"] = ad
        if hd >= 3 and ad >= 3:
            gd_points = 10
        total += gd_points
        reasons["goal_diff_points"] = gd_points
    else:
        reasons["goal_diff_error"] = True
        reasons["goal_diff_points"] = 0

    # Standings / balance
    try:
        st_status, standings = get_competition_standings(competition_id)
    except Exception:
        st_status, standings = None, None

    balance_points = 0
    if st_status == 200 and isinstance(standings, dict):
        table = None
        for s in standings.get("standings", []):
            if s.get("type") == "TOTAL":
                table = s.get("table")
                break
        if table is None:
            first = standings.get("standings")
            if first and isinstance(first, list):
                table = first[0].get("table")

        if table:
            def find_pos(team_id):
                for row in table:
                    t = row.get("team", {})
                    if t.get("id") == team_id:
                        return row.get("position")
                return None

            hp = find_pos(home_id)
            ap = find_pos(away_id)
            reasons["home_pos"] = hp
            reasons["away_pos"] = ap
            if hp is not None and ap is not None:
                diff = abs(hp - ap)
                if diff <= 2:
                    balance_points = 15
                elif diff <= 5:
                    balance_points = 8
        total += balance_points
        reasons["team_balance_points"] = balance_points
    else:
        reasons["standings_error"] = True
        reasons["team_balance_points"] = 0

    # Odds: draw odds and under2.5 and favorite
    draw_market_val = draw_odds
    under25_market_val = under25_odds
    min_winner = None
    try:
        # Only fetch markets if we are missing draw or under2.5 values.
        if draw_market_val is None or under25_market_val is None:
            dval, uval, minw, raw = _fetch_markets(home_id, away_id)
            if draw_market_val is None:
                draw_market_val = dval
            if under25_market_val is None:
                under25_market_val = uval
            min_winner = minw
            reasons["odds_raw"] = bool(raw)
    except Exception:
        reasons["odds_error"] = True

    # draw odds criterion (25 points)
    draw_points = 0
    if draw_market_val is not None:
        reasons["draw_odds_value"] = draw_market_val
        if 3.1 <= draw_market_val <= 3.6:
            draw_points = 25
        elif 3.0 <= draw_market_val < 3.1 or 3.6 < draw_market_val <= 3.9:
            draw_points = 10
    else:
        reasons["draw_odds_missing"] = True
    total += draw_points
    reasons["draw_odds_points"] = draw_points

    # under2.5 criterion (10 points)
    under_points = 0
    if under25_market_val is not None:
        reasons["under25_value"] = under25_market_val
        if 1.5 <= under25_market_val <= 1.7:
            under_points = 10
    else:
        reasons["under25_missing"] = True
    total += under_points
    reasons["under25_points"] = under_points

    # no huge favorite (10 points)
    fav_points = 0
    if min_winner is not None:
        reasons["min_winner_odds"] = min_winner
        if min_winner >= 1.4:
            fav_points = 10
    else:
        reasons["min_winner_unknown"] = True
    total += fav_points
    reasons["no_huge_fav_points"] = fav_points

    score = int(max(0, min(100, total)))

    return {
        "score": score,
        "passes": score >= 65,
        "reasons": reasons,
        "raw_points_total": total,
    }


def select_day_outputs(scored_matches: List[Dict[str, Any]], min_per_day: int = 3, max_per_day: int = 10) -> Dict[str, Any]:
    """Selects per-day outputs from a list of scored matches.

    - Keep top `max_per_day` by score if more than max.
    - If fewer than `min_per_day`, return what's available and add `low_confidence` badge.
    """
    sorted_matches = sorted(scored_matches, key=lambda s: s.get("score", 0), reverse=True)
    selected = sorted_matches[:max_per_day]
    low_confidence = len(selected) < min_per_day
    return {
        "selected": selected,
        "low_confidence": low_confidence,
        "count": len(selected),
    }
