"""Initial schema creation

Revision ID: 001_initial_schema
Revises: 
Create Date: 2025-08-27 03:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '001_initial_schema'
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    # Create settings table
    op.create_table('settings',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('key', sa.String(), nullable=False),
        sa.Column('value', sa.Text(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_settings_key'), 'settings', ['key'], unique=True)
    
    # Create tickers table
    op.create_table('tickers',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('symbol', sa.String(), nullable=False),
        sa.Column('name', sa.String(), nullable=True),
        sa.Column('sector', sa.String(), nullable=True),
        sa.Column('industry', sa.String(), nullable=True),
        sa.Column('market_cap', sa.Float(), nullable=True),
        sa.Column('current_price', sa.Float(), nullable=True),
        sa.Column('volume_avg_20d', sa.Float(), nullable=True),
        sa.Column('volatility_30d', sa.Float(), nullable=True),
        sa.Column('beta', sa.Float(), nullable=True),
        sa.Column('pe_ratio', sa.Float(), nullable=True),
        sa.Column('dividend_yield', sa.Float(), nullable=True),
        sa.Column('next_earnings_date', sa.DateTime(), nullable=True),
        sa.Column('active', sa.Boolean(), nullable=True),
        sa.Column('universe_score', sa.Float(), nullable=True),
        sa.Column('last_analysis_date', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_tickers_id'), 'tickers', ['id'], unique=False)
    op.create_index(op.f('ix_tickers_symbol'), 'tickers', ['symbol'], unique=True)
    
    # Create options table
    op.create_table('options',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('symbol', sa.String(), nullable=False),
        sa.Column('expiry', sa.DateTime(), nullable=False),
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
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['symbol'], ['tickers.symbol'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_options_id'), 'options', ['id'], unique=False)
    op.create_index('idx_symbol_expiry_strike_type', 'options', ['symbol', 'expiry', 'strike', 'option_type'], unique=True)
    
    # Create recommendations table
    op.create_table('recommendations',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('symbol', sa.String(), nullable=False),
        sa.Column('option_id', sa.Integer(), nullable=True),
        sa.Column('rationale_json', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('score', sa.Float(), nullable=False),
        sa.Column('status', sa.String(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['option_id'], ['options.id'], ),
        sa.ForeignKeyConstraint(['symbol'], ['tickers.symbol'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_recommendations_id'), 'recommendations', ['id'], unique=False)
    
    # Create positions table
    op.create_table('positions',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('symbol', sa.String(), nullable=False),
        sa.Column('shares', sa.Integer(), nullable=False),
        sa.Column('avg_price', sa.Float(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['symbol'], ['tickers.symbol'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_positions_id'), 'positions', ['id'], unique=False)
    
    # Create option_positions table
    op.create_table('option_positions',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('symbol', sa.String(), nullable=False),
        sa.Column('option_id', sa.Integer(), nullable=False),
        sa.Column('quantity', sa.Integer(), nullable=False),
        sa.Column('avg_price', sa.Float(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['option_id'], ['options.id'], ),
        sa.ForeignKeyConstraint(['symbol'], ['tickers.symbol'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_option_positions_id'), 'option_positions', ['id'], unique=False)
    
    # Create trades table
    op.create_table('trades',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('recommendation_id', sa.Integer(), nullable=True),
        sa.Column('symbol', sa.String(), nullable=False),
        sa.Column('option_id', sa.Integer(), nullable=True),
        sa.Column('trade_type', sa.String(), nullable=False),
        sa.Column('quantity', sa.Integer(), nullable=False),
        sa.Column('price', sa.Float(), nullable=False),
        sa.Column('executed_at', sa.DateTime(), nullable=True),
        sa.Column('status', sa.String(), nullable=True),
        sa.ForeignKeyConstraint(['option_id'], ['options.id'], ),
        sa.ForeignKeyConstraint(['recommendation_id'], ['recommendations.id'], ),
        sa.ForeignKeyConstraint(['symbol'], ['tickers.symbol'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_trades_id'), 'trades', ['id'], unique=False)
    
    # Create earnings_calendar table
    op.create_table('earnings_calendar',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('symbol', sa.String(), nullable=False),
        sa.Column('earnings_date', sa.DateTime(), nullable=False),
        sa.Column('source', sa.String(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['symbol'], ['tickers.symbol'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_earnings_calendar_id'), 'earnings_calendar', ['id'], unique=False)
    op.create_index(op.f('ix_earnings_calendar_symbol'), 'earnings_calendar', ['symbol'], unique=False)


def downgrade():
    op.drop_index(op.f('ix_earnings_calendar_symbol'), table_name='earnings_calendar')
    op.drop_index(op.f('ix_earnings_calendar_id'), table_name='earnings_calendar')
    op.drop_table('earnings_calendar')
    op.drop_index(op.f('ix_trades_id'), table_name='trades')
    op.drop_table('trades')
    op.drop_index(op.f('ix_option_positions_id'), table_name='option_positions')
    op.drop_table('option_positions')
    op.drop_index(op.f('ix_positions_id'), table_name='positions')
    op.drop_table('positions')
    op.drop_index(op.f('ix_recommendations_id'), table_name='recommendations')
    op.drop_table('recommendations')
    op.drop_index('idx_symbol_expiry_strike_type', table_name='options')
    op.drop_index(op.f('ix_options_id'), table_name='options')
    op.drop_table('options')
    op.drop_index(op.f('ix_tickers_symbol'), table_name='tickers')
    op.drop_index(op.f('ix_tickers_id'), table_name='tickers')
    op.drop_table('tickers')
    op.drop_index(op.f('ix_settings_key'), table_name='settings')
    op.drop_table('settings')



