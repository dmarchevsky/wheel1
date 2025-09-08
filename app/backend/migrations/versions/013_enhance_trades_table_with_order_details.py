"""Enhance trades table with comprehensive order details.

Revision ID: 013
Revises: 012
Create Date: 2025-01-09 12:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '013'
down_revision = '012'
branch_labels = None
depends_on = None


def upgrade():
    """Add comprehensive order tracking columns to trades table."""
    
    # Add extended order details
    op.add_column('trades', sa.Column('order_type', sa.String(), nullable=True))
    op.add_column('trades', sa.Column('duration', sa.String(), nullable=True))
    op.add_column('trades', sa.Column('class_type', sa.String(), nullable=True))
    op.add_column('trades', sa.Column('filled_quantity', sa.Integer(), nullable=True, default=0))
    op.add_column('trades', sa.Column('avg_fill_price', sa.Float(), nullable=True))
    op.add_column('trades', sa.Column('remaining_quantity', sa.Integer(), nullable=True))
    
    # Add trading environment tracking
    op.add_column('trades', sa.Column('environment', sa.String(), nullable=True))
    
    # Add complete Tradier data storage
    op.add_column('trades', sa.Column('tradier_data', postgresql.JSONB(astext_type=sa.Text()), nullable=True))
    
    # Add denormalized option details for easier querying
    op.add_column('trades', sa.Column('strike', sa.Float(), nullable=True))
    op.add_column('trades', sa.Column('expiry', sa.DateTime(timezone=True), nullable=True))
    op.add_column('trades', sa.Column('option_type', sa.String(), nullable=True))
    
    # Add additional timestamps
    op.add_column('trades', sa.Column('filled_at', sa.DateTime(timezone=True), nullable=True))
    
    # Create new indexes for better query performance
    op.create_index('idx_trades_order_id', 'trades', ['order_id'])
    op.create_index('idx_trades_environment', 'trades', ['environment'])
    op.create_index('idx_trades_expiry', 'trades', ['expiry'])
    
    # Update existing comment to clarify price field usage
    op.execute("COMMENT ON COLUMN trades.price IS 'Limit price or 0 for market orders'")


def downgrade():
    """Remove order tracking enhancements from trades table."""
    
    # Drop the new indexes first
    op.drop_index('idx_trades_expiry', 'trades')
    op.drop_index('idx_trades_environment', 'trades')
    op.drop_index('idx_trades_order_id', 'trades')
    
    # Remove all the added columns
    op.drop_column('trades', 'filled_at')
    op.drop_column('trades', 'option_type')
    op.drop_column('trades', 'expiry')
    op.drop_column('trades', 'strike')
    op.drop_column('trades', 'tradier_data')
    op.drop_column('trades', 'environment')
    op.drop_column('trades', 'remaining_quantity')
    op.drop_column('trades', 'avg_fill_price')
    op.drop_column('trades', 'filled_quantity')
    op.drop_column('trades', 'class_type')
    op.drop_column('trades', 'duration')
    op.drop_column('trades', 'order_type')