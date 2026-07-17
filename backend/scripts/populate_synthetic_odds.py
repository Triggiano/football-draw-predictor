"""Populate `matches.draw_odds` with deterministic synthetic values.

This uses a hash of the `api_match_id` to produce repeatable odds in a reasonable range.

Usage: python populate_synthetic_odds.py
"""
from datetime import date, timedelta
import hashlib
from app import logging_config
import logging

logger = logging.getLogger(__name__)
from app.db import SessionLocal
from app.models import Match


def synthetic_draw_odds(api_id: str) -> float:
    # deterministic pseudo-random value based on api_id
    h = hashlib.sha1(api_id.encode('utf-8')).hexdigest()
    v = int(h, 16) % 300  # 0..299
    odds = 2.0 + (v / 100.0)  # 2.00 .. 4.99
    return round(odds, 2)


def run(days_before: int = 3, days_after: int = 3):
    today = date.today()
    start = today - timedelta(days=days_before)
    end = today + timedelta(days=days_after)

    session = SessionLocal()
    try:
        matches = session.query(Match).filter(Match.date_utc >= start, Match.date_utc <= end).all()
        updated = 0
        for m in matches:
            if m.draw_odds is not None:
                continue
            api_id = m.api_match_id or str(m.id)
            m.draw_odds = synthetic_draw_odds(api_id)
            session.add(m)
            updated += 1
        session.commit()
        logger.info('Populated draw_odds for %s matches', updated)
    except Exception as e:
        session.rollback()
        logger.exception('Error populating synthetic odds: %s', e)
    finally:
        session.close()


if __name__ == '__main__':
    run()
