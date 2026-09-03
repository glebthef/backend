"""restructure bets into bet + bet_leg (single/express support)

Revision ID: 784ecee5c3af
Revises: c89d533d48ef
Create Date: 2026-09-03 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = '784ecee5c3af'
down_revision: Union[str, Sequence[str], None] = 'c89d533d48ef'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'bet_leg',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('bet_id', sa.Integer(), nullable=False),
        sa.Column('event_id', sa.Integer(), nullable=False),
        sa.Column('outcome', sa.String(), nullable=False),
        sa.Column('odd', sa.Float(), nullable=False),
        sa.Column('line_value', sa.Float(), nullable=True),
        sa.Column('status', sa.String(), nullable=False),
        sa.ForeignKeyConstraint(['bet_id'], ['bet.id'], ),
        sa.ForeignKeyConstraint(['event_id'], ['event.id'], ),
        sa.PrimaryKeyConstraint('id'),
    )

    op.add_column('bet', sa.Column('bet_type', sa.String(), nullable=True))
    op.add_column('bet', sa.Column('combined_odd', sa.Float(), nullable=True))

    # migrate existing single bets (event_id/outcome/odd live directly on bet) into bet_leg rows
    op.execute("""
        INSERT INTO bet_leg (bet_id, event_id, outcome, odd, line_value, status)
        SELECT id, event_id, outcome, odd, NULL, status FROM bet
    """)
    op.execute("UPDATE bet SET bet_type = 'single', combined_odd = odd")

    op.alter_column('bet', 'bet_type', nullable=False)
    op.alter_column('bet', 'combined_odd', nullable=False)

    op.drop_constraint('bet_event_id_fkey', 'bet', type_='foreignkey')
    op.drop_column('bet', 'event_id')
    op.drop_column('bet', 'outcome')
    op.drop_column('bet', 'odd')


def downgrade() -> None:
    op.add_column('bet', sa.Column('odd', sa.Float(), nullable=True))
    op.add_column('bet', sa.Column('outcome', sa.String(), nullable=True))
    op.add_column('bet', sa.Column('event_id', sa.Integer(), nullable=True))

    op.execute("""
        UPDATE bet b SET
            event_id = bl.event_id,
            outcome = bl.outcome,
            odd = bl.odd
        FROM (
            SELECT DISTINCT ON (bet_id) bet_id, event_id, outcome, odd
            FROM bet_leg ORDER BY bet_id, id
        ) bl
        WHERE b.id = bl.bet_id
    """)

    op.alter_column('bet', 'event_id', nullable=False)
    op.alter_column('bet', 'outcome', nullable=False)
    op.alter_column('bet', 'odd', nullable=False)
    op.create_foreign_key('bet_event_id_fkey', 'bet', 'event', ['event_id'], ['id'])

    op.drop_column('bet', 'combined_odd')
    op.drop_column('bet', 'bet_type')

    op.drop_table('bet_leg')
