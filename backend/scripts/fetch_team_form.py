"""Compute and store team form snapshots into `team_form` table.

Usage: python fetch_team_form.py
"""
from datetime import date
from statistics import mean
from app import logging_config
import logging

logger = logging.getLogger(__name__)
from app.db import SessionLocal
from app.models import Team, Match, TeamForm


def compute_form_for_team(session, team: Team, snapshot_date: date) -> TeamForm:
    # fetch last 5 finished matches for this team ordered by date desc
    matches = (
        session.query(Match)
        .filter(
            ((Match.home_team_id == team.id) | (Match.away_team_id == team.id)),
            Match.home_goals != None,
            Match.away_goals != None,
        )
        .order_by(Match.date_utc.desc())
        .limit(5)
        .all()
    )

    last5_wins = 0
    last5_draws = 0
    last5_losses = 0
    goals_for = []
    goals_against = []

    for m in matches:
        if team.id == m.home_team_id:
            gf = m.home_goals if m.home_goals is not None else 0
            ga = m.away_goals if m.away_goals is not None else 0
        else:
            gf = m.away_goals if m.away_goals is not None else 0
            ga = m.home_goals if m.home_goals is not None else 0

        goals_for.append(gf)
        goals_against.append(ga)

        if gf > ga:
            last5_wins += 1
        elif gf == ga:
            last5_draws += 1
        else:
            last5_losses += 1

    goals_for_avg = round(mean(goals_for), 2) if goals_for else None
    goals_against_avg = round(mean(goals_against), 2) if goals_against else None

    # upsert team_form for snapshot_date
    tf = (
        session.query(TeamForm)
        .filter(TeamForm.team_id == team.id, TeamForm.date_snapshot == snapshot_date)
        .one_or_none()
    )
    if not tf:
        tf = TeamForm(
            team_id=team.id,
            date_snapshot=snapshot_date,
            last5_wins=last5_wins,
            last5_draws=last5_draws,
            last5_losses=last5_losses,
            goals_for_avg=goals_for_avg,
            goals_against_avg=goals_against_avg,
        )
        session.add(tf)
    else:
        tf.last5_wins = last5_wins
        tf.last5_draws = last5_draws
        tf.last5_losses = last5_losses
        tf.goals_for_avg = goals_for_avg
        tf.goals_against_avg = goals_against_avg

    return tf


def run(snapshot_date: date = date.today()):
    session = SessionLocal()
    try:
        teams = session.query(Team).all()
        created = 0
        updated = 0
        for t in teams:
            existing = (
                session.query(TeamForm)
                .filter(TeamForm.team_id == t.id, TeamForm.date_snapshot == snapshot_date)
                .one_or_none()
            )
            tf = compute_form_for_team(session, t, snapshot_date)
            if existing:
                updated += 1
            else:
                created += 1

        session.commit()
        logger.info('Created: %s, Updated: %s team_form rows for %s', created, updated, snapshot_date)
    except Exception as e:
        session.rollback()
        logger.exception('Error computing team form: %s', e)
    finally:
        session.close()


if __name__ == '__main__':
    run()
