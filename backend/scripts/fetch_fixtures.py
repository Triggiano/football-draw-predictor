"""Fetch fixtures from football-data API and save to DB.

Usage: python fetch_fixtures.py
"""
from datetime import date, timedelta, datetime
import os
from typing import Optional

from app import logging_config
import logging

logger = logging.getLogger(__name__)
from app.services.football_data import get_matches
from app.db import SessionLocal
from app.models import Team, Match


def parse_iso_datetime(s: str) -> datetime:
    # Handle trailing Z by replacing with +00:00
    if s.endswith('Z'):
        s = s[:-1] + '+00:00'
    return datetime.fromisoformat(s)


def get_or_create_team(session, name: str) -> Team:
    name = name.strip()
    team = session.query(Team).filter(Team.name == name).one_or_none()
    if team:
        return team
    team = Team(name=name)
    session.add(team)
    session.flush()  # assign id
    return team


def upsert_match(session, api_match_id: str, date_utc: datetime, home_team: Team, away_team: Team, status: str, home_goals: Optional[int], away_goals: Optional[int]):
    m = session.query(Match).filter(Match.api_match_id == api_match_id).one_or_none()
    if not m:
        m = Match(
            api_match_id=api_match_id,
            date_utc=date_utc,
            home_team_id=home_team.id,
            away_team_id=away_team.id,
            status=status.lower() if status else 'scheduled',
            home_goals=home_goals,
            away_goals=away_goals,
        )
        session.add(m)
    else:
        # update fields
        m.date_utc = date_utc
        m.home_team_id = home_team.id
        m.away_team_id = away_team.id
        m.status = status.lower() if status else m.status
        m.home_goals = home_goals
        m.away_goals = away_goals
    session.flush()
    return m


def fetch_and_store(date_from: str, date_to: str):
    status, data = get_matches(params={'dateFrom': date_from, 'dateTo': date_to})
    if status != 200:
        logger.error('Failed to fetch matches: %s %s', status, data)
        return

    matches = None
    if isinstance(data, list):
        matches = data
    elif isinstance(data, dict):
        # common keys
        for key in ("matches", "data", "events", "games", "response"):
            if key in data and isinstance(data[key], list):
                matches = data[key]
                break

    if matches is None:
        logger.error('No matches list found in response JSON')
        return

    session = SessionLocal()
    created = 0
    updated = 0
    try:
        for raw in matches:
            api_id = str(raw.get('id') or raw.get('matchId') or '')
            if not api_id:
                # skip if no id
                continue
            utc = raw.get('utcDate') or raw.get('date') or raw.get('match_date')
            if not utc:
                continue
            try:
                dt = parse_iso_datetime(utc)
            except Exception:
                # fallback: parse date portion
                dt = datetime.fromisoformat(utc.split('T')[0])

            # teams
            home = raw.get('homeTeam') or raw.get('home') or {}
            away = raw.get('awayTeam') or raw.get('away') or {}
            home_name = home.get('name') if isinstance(home, dict) else str(home)
            away_name = away.get('name') if isinstance(away, dict) else str(away)
            if not home_name or not away_name:
                continue

            home_team = get_or_create_team(session, home_name)
            away_team = get_or_create_team(session, away_name)

            status_text = raw.get('status') or raw.get('match_status') or 'SCHEDULED'
            score = raw.get('score') or {}
            full = score.get('fullTime') if isinstance(score, dict) else None
            home_goals = None
            away_goals = None
            if isinstance(full, dict):
                home_goals = full.get('homeTeam')
                away_goals = full.get('awayTeam')

            # insert/update match
            existing = session.query(Match).filter(Match.api_match_id == api_id).one_or_none()
            if existing:
                upsert_match(session, api_id, dt, home_team, away_team, status_text, home_goals, away_goals)
                updated += 1
            else:
                upsert_match(session, api_id, dt, home_team, away_team, status_text, home_goals, away_goals)
                created += 1

        session.commit()
    except Exception as e:
        session.rollback()
        logger.exception('Error storing matches: %s', e)
    finally:
        session.close()

    logger.info('Created: %s, Updated: %s', created, updated)


if __name__ == '__main__':
    today = date.today()
    df = (today - timedelta(days=3)).isoformat()
    dt = (today + timedelta(days=3)).isoformat()
    logger.info('Fetching %s -> %s', df, dt)
    fetch_and_store(df, dt)
