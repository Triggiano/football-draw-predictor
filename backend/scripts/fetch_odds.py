"""Fetch draw odds for matches in DB and update `matches.draw_odds`.

Usage: python fetch_odds.py
"""
from datetime import date, timedelta
import os
from typing import Any

from app import logging_config
import logging

logger = logging.getLogger(__name__)
from app.services.odds_api import fetch_odds
from app.db import SessionLocal
from app.models import Match


def find_draw_odds(data: Any) -> float | None:
    """Attempt to locate a draw price in the provider response.

    Heuristics supported:
    - Look for 'bookmakers' -> markets -> outcomes with name 'Draw'/'X'
    - Look for 'markets' -> outcomes
    - Look for top-level 'draw' key or 'prices' dict
    """
    if data is None:
        return None

    if isinstance(data, dict):
        # common structure: bookmakers -> list -> markets -> list -> outcomes
        if 'bookmakers' in data and isinstance(data['bookmakers'], list):
            for bm in data['bookmakers']:
                odds = find_draw_odds(bm)
                if odds:
                    return odds

        if 'markets' in data and isinstance(data['markets'], list):
            for m in data['markets']:
                if isinstance(m, dict) and 'outcomes' in m:
                    for o in m['outcomes']:
                        name = (o.get('name') or o.get('label') or '').lower()
                        price = o.get('price') or o.get('odds') or o.get('price_decimal')
                        if name in ('draw', 'x', 'tie') or name.startswith('draw'):
                            try:
                                return float(price)
                            except Exception:
                                continue

        # direct keys
        for key in ('draw', 'X', 'x', 'tie'):
            if key in data:
                try:
                    return float(data[key])
                except Exception:
                    pass

        # nested search
        for v in data.values():
            odds = find_draw_odds(v)
            if odds:
                return odds

    elif isinstance(data, list):
        for item in data:
            odds = find_draw_odds(item)
            if odds:
                return odds

    return None


def run_for_range(days_before: int = 3, days_after: int = 3):
    today = date.today()
    start = today - timedelta(days=days_before)
    end = today + timedelta(days=days_after)

    session = SessionLocal()
    try:
        matches = session.query(Match).filter(Match.date_utc >= start, Match.date_utc <= end).all()
        logger.info('Found %s matches in date range', len(matches))
        updated = 0
        for m in matches:
            # skip if already has draw_odds
            if m.draw_odds is not None:
                continue

            home = m.home_team.name if m.home_team else None
            away = m.away_team.name if m.away_team else None

            # try a few candidate endpoints/params
            tried = []
            candidates = [('', {'home': home, 'away': away}), ('odds', {'home': home, 'away': away}), ('v1/odds', {'home': home, 'away': away})]
            draw = None
            for path, params in candidates:
                status, data = fetch_odds(path=path, params={k: v for k, v in params.items() if v})
                tried.append((path, status))
                if status != 200:
                    continue
                draw = find_draw_odds(data)
                if draw is not None:
                    break

            if draw is not None:
                try:
                    m.draw_odds = float(draw)
                    session.add(m)
                    session.commit()
                    updated += 1
                    logger.info('Updated match %s draw_odds=%s', m.id, m.draw_odds)
                except Exception as e:
                    session.rollback()
                    logger.exception('Failed to update match %s: %s', m.id, e)
            else:
                logger.debug('No draw odds for match %s (api_id=%s), tried: %s', m.id, m.api_match_id, tried)
        logger.info('Total updated: %s', updated)
    finally:
        session.close()


if __name__ == '__main__':
    run_for_range()
