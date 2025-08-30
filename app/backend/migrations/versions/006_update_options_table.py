"""Update options table to use Tradier API symbol as ID and add price field.

Revision ID: 006
Revises: 005
Create Date: 2025-08-28 19:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '006'
down_revision = '005'
branch_labels = None
depends_on = None


def upgrade():
    """Update options table structure."""
    
    # First, create a temporary table with the new structure
    op.create_table('options_new',
        sa.Column('symbol', sa.String(), nullable=False),  # Tradier API symbol (e.g., VXX190517P00016000)
        sa.Column('underlying_symbol', sa.String(), nullable=False),  # The underlying stock symbol
        sa.Column('expiry', sa.DateTime(timezone=True), nullable=False),
        sa.Column('strike', sa.Float(), nullable=False),
        sa.Column('option_type', sa.String(), nullable=False),  # 'put' or 'call'
        sa.Column('bid', sa.Float(), nullable=True),
        sa.Column('ask', sa.Float(), nullable=True),
        sa.Column('last', sa.Float(), nullable=True),
        sa.Column('price', sa.Float(), nullable=True),  # Calculated price field
        sa.Column('delta', sa.Float(), nullable=True),
        sa.Column('gamma', sa.Float(), nullable=True),
        sa.Column('theta', sa.Float(), nullable=True),
        sa.Column('vega', sa.Float(), nullable=True),
        sa.Column('implied_volatility', sa.Float(), nullable=True),
        sa.Column('iv_rank', sa.Float(), nullable=True),
        sa.Column('dte', sa.Integer(), nullable=True),
        sa.Column('open_interest', sa.Integer(), nullable=True),
        sa.Column('volume', sa.Integer(), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint('symbol')
    )
    
    # Create indexes for the new table
    op.create_index('idx_options_underlying_symbol', 'options_new', ['underlying_symbol'])
    op.create_index('idx_options_expiry', 'options_new', ['expiry'])
    op.create_index('idx_options_strike', 'options_new', ['strike'])
    op.create_index('idx_options_type', 'options_new', ['option_type'])
    op.create_index('idx_options_dte', 'options_new', ['dte'])
    op.create_index('idx_options_delta', 'options_new', ['delta'])
    op.create_index('idx_options_price', 'options_new', ['price'])
    
    # Create a composite index for common queries
    op.create_index('idx_options_underlying_expiry_type', 'options_new', ['underlying_symbol', 'expiry', 'option_type'])
    
    # Update foreign key constraints in other tables
    # First, add the new column to recommendations table
    op.add_column('recommendations', sa.Column('option_symbol', sa.String(), nullable=True))
    
    # Create a temporary index for the migration
    op.create_index('idx_recommendations_option_symbol_temp', 'recommendations', ['option_symbol'])
    
    # Drop foreign key constraints first
    op.drop_constraint('recommendations_option_id_fkey', 'recommendations', type_='foreignkey')
    
    # Drop the old table and rename the new one
    op.drop_table('options')
    op.rename_table('options_new', 'options')
    
    # Recreate foreign key constraint with the new structure
    op.create_foreign_key('recommendations_option_symbol_fkey', 'recommendations', 'options', ['option_symbol'], ['symbol'])


def downgrade():
    """Revert options table changes."""
    
    # Drop foreign key constraints first
    op.drop_constraint('recommendations_option_symbol_fkey', 'recommendations', type_='foreignkey')
    
    # Drop the new column from recommendations table
    op.drop_index('idx_recommendations_option_symbol_temp', 'recommendations')
    op.drop_column('recommendations', 'option_symbol')
    
    # Recreate the old options table structure
    op.create_table('options_old',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('symbol', sa.String(), nullable=False),
        sa.Column('expiry', sa.DateTime(timezone=True), nullable=False),
        sa.Column('strike', sa.Float(), nullable=False),
        sa.Column('option_type', sa.String(), nullable=False),
        sa.Column('bid', sa.Float(), nullable=True),
        sa.Column('ask', sa.Float(), nullable=True),
        sa.Column('last', sa.Float(), nullable=True),
        sa.Column('delta', sa.Float(), nullable=True),
        sa.Column('gamma', sa.Float(), nullable=True),
        sa.Column('theta', sa.Float(), nullable=True),
        sa.Column('vega', sa.Float(), nullable=True),
        sa.Column('implied_volatility', sa.Float(), nullable=True),
        sa.Column('iv_rank', sa.Float(), nullable=True),
        sa.Column('dte', sa.Integer(), nullable=True),
        sa.Column('open_interest', sa.Integer(), nullable=True),
        sa.Column('volume', sa.Integer(), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Recreate old indexes
    op.create_index('ix_options_id', 'options_old', ['id'])
    op.create_index('idx_symbol_expiry_strike_type', 'options_old', ['symbol', 'expiry', 'strike', 'option_type'], unique=True)
    
    # Drop the new table and rename the old one back
    op.drop_table('options')
    op.rename_table('options_old', 'options')
    
    # Recreate the old foreign key constraint
    op.create_foreign_key('recommendations_option_id_fkey', 'recommendations', 'options', ['option_id'], ['id'])
