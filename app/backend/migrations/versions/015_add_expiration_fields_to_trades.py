"""Add expiration fields to trades table

Revision ID: 015
Revises: 014
Create Date: 2025-09-05 13:50:00.000000

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '015'
down_revision = '014'
branch_labels = None
depends_on = None


def upgrade():
    # Add new columns to trades table for expiration tracking
    op.add_column('trades', sa.Column('expiration_outcome', sa.String(), nullable=True))
    op.add_column('trades', sa.Column('final_pnl', sa.Float(), nullable=True))
    op.add_column('trades', sa.Column('closed_at', sa.DateTime(timezone=True), nullable=True))


def downgrade():
    # Remove columns from trades table
    op.drop_column('trades', 'closed_at')
    op.drop_column('trades', 'final_pnl')
    op.drop_column('trades', 'expiration_outcome')