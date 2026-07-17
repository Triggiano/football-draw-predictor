"""create initial tables

Revision ID: 0001_create_initial_tables
Revises: 
Create Date: 2026-07-17 00:00:00.000000
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '0001_create_initial_tables'
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'teams',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('name', sa.String(length=255), nullable=False, unique=True),
        sa.Column('league', sa.String(length=255), nullable=True),
        sa.Column('country', sa.String(length=255), nullable=True),
    )

    op.create_table(
        'matches',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('api_match_id', sa.String(length=255), nullable=True, index=True),
        sa.Column('date_utc', sa.DateTime(), nullable=False),
        sa.Column('home_team_id', sa.Integer(), sa.ForeignKey('teams.id'), nullable=False),
        sa.Column('away_team_id', sa.Integer(), sa.ForeignKey('teams.id'), nullable=False),
        sa.Column('home_odds', sa.Float(), nullable=True),
        sa.Column('draw_odds', sa.Float(), nullable=True),
        sa.Column('away_odds', sa.Float(), nullable=True),
        sa.Column('status', sa.String(length=50), nullable=False, server_default='scheduled'),
        sa.Column('home_goals', sa.Integer(), nullable=True),
        sa.Column('away_goals', sa.Integer(), nullable=True),
    )

    op.create_table(
        'team_form',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('team_id', sa.Integer(), sa.ForeignKey('teams.id'), nullable=False, index=True),
        sa.Column('date_snapshot', sa.Date(), nullable=False),
        sa.Column('last5_wins', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('last5_draws', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('last5_losses', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('goals_for_avg', sa.Float(), nullable=True),
        sa.Column('goals_against_avg', sa.Float(), nullable=True),
    )

    op.create_table(
        'draw_scores',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('match_id', sa.Integer(), sa.ForeignKey('matches.id'), nullable=False, index=True),
        sa.Column('score_total', sa.Integer(), nullable=False),
        sa.Column('passed', sa.Boolean(), nullable=False, server_default=sa.text('false')),
        sa.Column('reason_json', postgresql.JSON(), nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now()),
    )


def downgrade():
    op.drop_table('draw_scores')
    op.drop_table('team_form')
    op.drop_table('matches')
    op.drop_table('teams')
