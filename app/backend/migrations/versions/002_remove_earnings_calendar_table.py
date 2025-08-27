"""remove earnings calendar table

Revision ID: 002
Revises: 001_initial_schema
Create Date: 2024-01-15 10:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '002'
down_revision = '001_initial_schema'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Drop earnings_calendar table and its indexes
    op.drop_index('idx_symbol_earnings_date', table_name='earnings_calendar')
    op.drop_index('ix_earnings_calendar_id', table_name='earnings_calendar')
    op.drop_table('earnings_calendar')


def downgrade() -> None:
    # Recreate earnings_calendar table (if needed for rollback)
    op.create_table('earnings_calendar',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('symbol', sa.String(), nullable=False),
        sa.Column('earnings_date', sa.DateTime(), nullable=False),
        sa.Column('source', sa.String(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['symbol'], ['tickers.symbol'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_earnings_calendar_id', 'earnings_calendar', ['id'], unique=False)
    op.create_index('idx_symbol_earnings_date', 'earnings_calendar', ['symbol', 'earnings_date'], unique=False)
