"""Add probability of profit fields

Revision ID: 010
Revises: 009
Create Date: 2024-12-19 10:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '010'
down_revision = '009'
branch_labels = None
depends_on = None


def upgrade():
    """Add probability of profit fields to recommendations table."""
    # Add probability_of_profit_black_scholes column
    op.add_column('recommendations', sa.Column('probability_of_profit_black_scholes', sa.Float(), nullable=True))
    
    # Add probability_of_profit_monte_carlo column
    op.add_column('recommendations', sa.Column('probability_of_profit_monte_carlo', sa.Float(), nullable=True))


def downgrade():
    """Remove probability of profit fields from recommendations table."""
    # Drop probability_of_profit_monte_carlo column
    op.drop_column('recommendations', 'probability_of_profit_monte_carlo')
    
    # Drop probability_of_profit_black_scholes column
    op.drop_column('recommendations', 'probability_of_profit_black_scholes')
