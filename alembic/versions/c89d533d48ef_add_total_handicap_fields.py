"""add total/handicap fields to event

Revision ID: c89d533d48ef
Revises: f2f87c298d3f
Create Date: 2026-08-29 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'c89d533d48ef'
down_revision: Union[str, Sequence[str], None] = 'f2f87c298d3f'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('event', sa.Column('total_value', sa.Float(), nullable=True))
    op.add_column('event', sa.Column('odd_total_over', sa.Float(), nullable=True))
    op.add_column('event', sa.Column('odd_total_under', sa.Float(), nullable=True))
    op.add_column('event', sa.Column('handicap_value', sa.Float(), nullable=True))
    op.add_column('event', sa.Column('odd_handicap_home', sa.Float(), nullable=True))
    op.add_column('event', sa.Column('odd_handicap_away', sa.Float(), nullable=True))


def downgrade() -> None:
    op.drop_column('event', 'odd_handicap_away')
    op.drop_column('event', 'odd_handicap_home')
    op.drop_column('event', 'handicap_value')
    op.drop_column('event', 'odd_total_under')
    op.drop_column('event', 'odd_total_over')
    op.drop_column('event', 'total_value')
