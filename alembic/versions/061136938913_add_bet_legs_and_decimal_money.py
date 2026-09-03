"""restructure bets into bet + bet_leg (single/express support) and switch
money/odds columns from float to numeric for exact decimal arithmetic

Revision ID: 061136938913
Revises: c89d533d48ef
Create Date: 2026-09-03 17:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = '061136938913'
down_revision: Union[str, Sequence[str], None] = 'c89d533d48ef'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # --- float -> numeric, so the app can use Decimal without silent float drift ---
    op.alter_column('user', 'balance', type_=sa.Numeric(12, 2),
                     postgresql_using='balance::numeric(12,2)')

    for col in ('odd_p1', 'odd_x', 'odd_p2', 'total_value',
                'odd_total_over', 'odd_total_under',
                'handicap_value', 'odd_handicap_home', 'odd_handicap_away'):
        op.alter_column('event', col, type_=sa.Numeric(6, 2),
                         postgresql_using=f'{col}::numeric(6,2)')

    # --- bet + bet_leg restructuring (single bet -> bet with 1 leg; express -> bet with N legs) ---
    op.create_table(
        'bet_leg',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('bet_id', sa.Integer(), nullable=False),
        sa.Column('event_id', sa.Integer(), nullable=False),
        sa.Column('outcome', sa.String(), nullable=False),
        sa.Column('odd', sa.Numeric(6, 2), nullable=False),
        sa.Column('line_value', sa.Numeric(6, 2), nullable=True),
        sa.Column('status', sa.String(), nullable=False),
        sa.ForeignKeyConstraint(['bet_id'], ['bet.id'], ),
        sa.ForeignKeyConstraint(['event_id'], ['event.id'], ),
        sa.PrimaryKeyConstraint('id'),
    )

    op.add_column('bet', sa.Column('type', sa.String(), nullable=True))
    op.add_column('bet', sa.Column('combined_odd', sa.Numeric(10, 4), nullable=True))
    op.add_column('bet', sa.Column('potential_payout', sa.Numeric(12, 2), nullable=True))

    # migrate existing single bets (event_id/outcome/odd live directly on bet) into bet_leg rows
    op.execute("""
        INSERT INTO bet_leg (bet_id, event_id, outcome, odd, line_value, status)
        SELECT id, event_id, outcome, odd::numeric(6,2), NULL, status FROM bet
    """)
    op.execute("""
        UPDATE bet SET
            type = 'single',
            combined_odd = odd::numeric(10,4),
            potential_payout = round((amount * odd)::numeric, 2)
    """)

    op.alter_column('bet', 'amount', type_=sa.Numeric(12, 2),
                     postgresql_using='amount::numeric(12,2)')
    op.alter_column('bet', 'type', nullable=False)
    op.alter_column('bet', 'combined_odd', nullable=False)
    op.alter_column('bet', 'potential_payout', nullable=False)

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

    op.alter_column('bet', 'amount', type_=sa.Float(), postgresql_using='amount::float')
    op.drop_column('bet', 'potential_payout')
    op.drop_column('bet', 'combined_odd')
    op.drop_column('bet', 'type')

    op.drop_table('bet_leg')

    for col in ('odd_p1', 'odd_x', 'odd_p2', 'total_value',
                'odd_total_over', 'odd_total_under',
                'handicap_value', 'odd_handicap_home', 'odd_handicap_away'):
        op.alter_column('event', col, type_=sa.Float(), postgresql_using=f'{col}::float')

    op.alter_column('user', 'balance', type_=sa.Float(), postgresql_using='balance::float')
