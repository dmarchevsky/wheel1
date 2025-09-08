"""Add position snapshots and option events tables with expiration tracking

Revision ID: 014
Revises: 013
Create Date: 2025-09-05 13:45:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '014'
down_revision = '013'
branch_labels = None
depends_on = None


def upgrade():
    # Create position_snapshots table
    op.create_table('position_snapshots',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('symbol', sa.String(), nullable=False),
    sa.Column('contract_symbol', sa.String(), nullable=True),
    sa.Column('environment', sa.String(), nullable=False),
    sa.Column('quantity', sa.Float(), nullable=False),
    sa.Column('cost_basis', sa.Float(), nullable=True),
    sa.Column('current_price', sa.Float(), nullable=True),
    sa.Column('market_value', sa.Float(), nullable=True),
    sa.Column('pnl', sa.Float(), nullable=True),
    sa.Column('pnl_percent', sa.Float(), nullable=True),
    sa.Column('snapshot_date', sa.DateTime(timezone=True), nullable=False),
    sa.Column('tradier_data', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), nullable=True),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index('idx_position_snapshots_symbol_date', 'position_snapshots', ['symbol', 'snapshot_date'])
    op.create_index('idx_position_snapshots_env_date', 'position_snapshots', ['environment', 'snapshot_date'])
    op.create_index('idx_position_snapshots_contract', 'position_snapshots', ['contract_symbol'])
    op.create_index(op.f('ix_position_snapshots_id'), 'position_snapshots', ['id'], unique=False)

    # Create option_events table
    op.create_table('option_events',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('trade_id', sa.Integer(), nullable=True),
    sa.Column('symbol', sa.String(), nullable=False),
    sa.Column('contract_symbol', sa.String(), nullable=False),
    sa.Column('event_type', sa.String(), nullable=False),
    sa.Column('event_date', sa.DateTime(timezone=True), nullable=False),
    sa.Column('final_price', sa.Float(), nullable=True),
    sa.Column('final_pnl', sa.Float(), nullable=True),
    sa.Column('environment', sa.String(), nullable=False),
    sa.Column('tradier_data', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), nullable=True),
    sa.ForeignKeyConstraint(['trade_id'], ['trades.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index('idx_option_events_trade_id', 'option_events', ['trade_id'])
    op.create_index('idx_option_events_event_date', 'option_events', ['event_date'])
    op.create_index('idx_option_events_symbol_type', 'option_events', ['symbol', 'event_type'])
    op.create_index('idx_option_events_contract', 'option_events', ['contract_symbol'])
    op.create_index(op.f('ix_option_events_id'), 'option_events', ['id'], unique=False)

    # Add new columns to trades table
    op.add_column('trades', sa.Column('expiration_outcome', sa.String(), nullable=True))
    op.add_column('trades', sa.Column('final_pnl', sa.Float(), nullable=True))
    op.add_column('trades', sa.Column('closed_at', sa.DateTime(timezone=True), nullable=True))


def downgrade():
    # Remove columns from trades table
    op.drop_column('trades', 'closed_at')
    op.drop_column('trades', 'final_pnl')
    op.drop_column('trades', 'expiration_outcome')
    
    # Drop option_events table
    op.drop_index(op.f('ix_option_events_id'), table_name='option_events')
    op.drop_index('idx_option_events_contract', table_name='option_events')
    op.drop_index('idx_option_events_symbol_type', table_name='option_events')
    op.drop_index('idx_option_events_event_date', table_name='option_events')
    op.drop_index('idx_option_events_trade_id', table_name='option_events')
    op.drop_table('option_events')
    
    # Drop position_snapshots table
    op.drop_index(op.f('ix_position_snapshots_id'), table_name='position_snapshots')
    op.drop_index('idx_position_snapshots_contract', table_name='position_snapshots')
    op.drop_index('idx_position_snapshots_env_date', table_name='position_snapshots')
    op.drop_index('idx_position_snapshots_symbol_date', table_name='position_snapshots')
    op.drop_table('position_snapshots')