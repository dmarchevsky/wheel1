"""Add put_call_ratio to interesting_tickers table.

Revision ID: 009
Revises: 008
Create Date: 2025-01-03 12:00:00.000000

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '009'
down_revision = '008'
branch_labels = None
depends_on = None


def upgrade():
    """Add put_call_ratio column to interesting_tickers table."""
    op.add_column('interesting_tickers', sa.Column('put_call_ratio', sa.Float(), nullable=True))


def downgrade():
    """Remove put_call_ratio column from interesting_tickers table."""
    op.drop_column('interesting_tickers', 'put_call_ratio')
