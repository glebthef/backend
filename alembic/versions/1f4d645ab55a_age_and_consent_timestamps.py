"""age and consent timestamps

Revision ID: 1f4d645ab55a
Revises: ec68ae159042
Create Date: 2026-10-13 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = '1f4d645ab55a'
down_revision: Union[str, Sequence[str], None] = 'ec68ae159042'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("user", sa.Column("age_confirmed_at", sa.DateTime(), nullable=True))
    op.add_column("user", sa.Column("consent_at", sa.DateTime(), nullable=True))


def downgrade() -> None:
    op.drop_column("user", "consent_at")
    op.drop_column("user", "age_confirmed_at")
