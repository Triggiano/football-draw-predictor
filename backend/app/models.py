from sqlalchemy import (
    Column,
    Integer,
    String,
    DateTime,
    Date,
    Float,
    Boolean,
    ForeignKey,
    func,
)
from sqlalchemy.dialects.postgresql import JSON
from sqlalchemy.orm import declarative_base, relationship

Base = declarative_base()


class Team(Base):
    __tablename__ = 'teams'

    id = Column(Integer, primary_key=True)
    name = Column(String(255), nullable=False, unique=True)
    league = Column(String(255), nullable=True)
    country = Column(String(255), nullable=True)


class Match(Base):
    __tablename__ = 'matches'

    id = Column(Integer, primary_key=True)
    api_match_id = Column(String(255), nullable=True, index=True)
    date_utc = Column(DateTime(timezone=False), nullable=False)
    home_team_id = Column(Integer, ForeignKey('teams.id'), nullable=False)
    away_team_id = Column(Integer, ForeignKey('teams.id'), nullable=False)
    home_odds = Column(Float, nullable=True)
    draw_odds = Column(Float, nullable=True)
    away_odds = Column(Float, nullable=True)
    status = Column(String(50), nullable=False, default='scheduled')
    home_goals = Column(Integer, nullable=True)
    away_goals = Column(Integer, nullable=True)

    home_team = relationship('Team', foreign_keys=[home_team_id])
    away_team = relationship('Team', foreign_keys=[away_team_id])


class TeamForm(Base):
    __tablename__ = 'team_form'

    id = Column(Integer, primary_key=True)
    team_id = Column(Integer, ForeignKey('teams.id'), nullable=False, index=True)
    date_snapshot = Column(Date, nullable=False)
    last5_wins = Column(Integer, nullable=False, default=0)
    last5_draws = Column(Integer, nullable=False, default=0)
    last5_losses = Column(Integer, nullable=False, default=0)
    goals_for_avg = Column(Float, nullable=True)
    goals_against_avg = Column(Float, nullable=True)

    team = relationship('Team')


class DrawScore(Base):
    __tablename__ = 'draw_scores'

    id = Column(Integer, primary_key=True)
    match_id = Column(Integer, ForeignKey('matches.id'), nullable=False, index=True)
    score_total = Column(Integer, nullable=False)
    passed = Column(Boolean, nullable=False, default=False)
    reason_json = Column(JSON, nullable=True)
    created_at = Column(DateTime(timezone=False), server_default=func.now())

    match = relationship('Match')
