"""enum types for statuses

Revision ID: ec68ae159042
Revises: bb0aa3039911
Create Date: 2026-10-12 20:07:27.529136

"""
from typing import Sequence, Union

from alembic import op


revision: str = 'ec68ae159042'
down_revision: Union[str, Sequence[str], None] = 'bb0aa3039911'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


ENUMS = {
    "bet_type": ("single", "express"),
    "bet_status": ("pending", "won", "lost", "refund", "cancelled"),
    "bet_outcome": ("p1", "x", "p2", "total_over", "total_under", "handicap_home", "handicap_away"),
    "event_status": ("upcoming", "finished"),
    "payment_status": ("pending", "succeeded", "canceled"),
    "chat_sender": ("user", "support"),
}

COLUMNS = [
    ("bet", "type", "bet_type"),
    ("bet", "status", "bet_status"),
    ("bet_leg", "status", "bet_status"),
    ("bet_leg", "outcome", "bet_outcome"),
    ("event", "status", "event_status"),
    ("payment", "status", "payment_status"),
    ("chat_message", "sender", "chat_sender"),
]


def upgrade() -> None:
    for name, values in ENUMS.items():
        items = ", ".join(f"'{v}'" for v in values)
        op.execute(f"CREATE TYPE {name} AS ENUM ({items})")
    for table, column, enum_name in COLUMNS:
        op.execute(
            f'ALTER TABLE "{table}" ALTER COLUMN {column} '
            f"TYPE {enum_name} USING {column}::{enum_name}"
        )


def downgrade() -> None:
    for table, column, _ in COLUMNS:
        op.execute(
            f'ALTER TABLE "{table}" ALTER COLUMN {column} '
            f"TYPE VARCHAR USING {column}::text"
        )
    for name in ENUMS:
        op.execute(f"DROP TYPE {name}")
