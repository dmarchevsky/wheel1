"""split tickers table into interesting_tickers and ticker_quotes

Revision ID: 003
Revises: 002
Create Date: 2024-01-15 11:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '003'
down_revision = '002'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create interesting_tickers table
    op.create_table('interesting_tickers',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('symbol', sa.String(), nullable=False),
        sa.Column('name', sa.String(), nullable=True),
        sa.Column('sector', sa.String(), nullable=True),
        sa.Column('industry', sa.String(), nullable=True),
        sa.Column('market_cap', sa.Float(), nullable=True),
        sa.Column('beta', sa.Float(), nullable=True),
        sa.Column('pe_ratio', sa.Float(), nullable=True),
        sa.Column('dividend_yield', sa.Float(), nullable=True),
        sa.Column('next_earnings_date', sa.DateTime(), nullable=True),
        sa.Column('active', sa.Boolean(), default=True),
        sa.Column('universe_score', sa.Float(), nullable=True),
        sa.Column('last_analysis_date', sa.DateTime(), nullable=True),
        sa.Column('source', sa.String(), default='sp500'),
        sa.Column('added_at', sa.DateTime(), default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(), default=sa.func.now()),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_interesting_tickers_id', 'interesting_tickers', ['id'], unique=False)
    op.create_index('ix_interesting_tickers_symbol', 'interesting_tickers', ['symbol'], unique=True)
    
    # Create ticker_quotes table
    op.create_table('ticker_quotes',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('symbol', sa.String(), nullable=False),
        sa.Column('current_price', sa.Float(), nullable=True),
        sa.Column('volume_avg_20d', sa.Float(), nullable=True),
        sa.Column('volatility_30d', sa.Float(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), default=sa.func.now()),
        sa.ForeignKeyConstraint(['symbol'], ['interesting_tickers.symbol'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_ticker_quotes_id', 'ticker_quotes', ['id'], unique=False)
    op.create_index('idx_symbol_unique', 'ticker_quotes', ['symbol'], unique=True)
    
    # Migrate data from tickers table
    op.execute("""
        INSERT INTO interesting_tickers (
            symbol, name, sector, industry, market_cap, beta, pe_ratio, 
            dividend_yield, next_earnings_date, active, universe_score, 
            last_analysis_date, updated_at
        )
        SELECT 
            symbol, name, sector, industry, market_cap, beta, pe_ratio,
            dividend_yield, next_earnings_date, active, universe_score,
            last_analysis_date, updated_at
        FROM tickers
    """)
    
    op.execute("""
        INSERT INTO ticker_quotes (
            symbol, current_price, volume_avg_20d, volatility_30d, updated_at
        )
        SELECT 
            symbol, current_price, volume_avg_20d, volatility_30d, updated_at
        FROM tickers
        WHERE current_price IS NOT NULL OR volume_avg_20d IS NOT NULL OR volatility_30d IS NOT NULL
    """)
    
    # Drop foreign key constraints first
    op.drop_constraint('options_symbol_fkey', 'options', type_='foreignkey')
    op.drop_constraint('positions_symbol_fkey', 'positions', type_='foreignkey')
    op.drop_constraint('recommendations_symbol_fkey', 'recommendations', type_='foreignkey')
    
    # Drop old tickers table
    op.drop_table('tickers')
    
    # Add new foreign key constraints
    op.create_foreign_key('options_symbol_fkey', 'options', 'interesting_tickers', ['symbol'], ['symbol'])
    op.create_foreign_key('positions_symbol_fkey', 'positions', 'interesting_tickers', ['symbol'], ['symbol'])
    op.create_foreign_key('recommendations_symbol_fkey', 'recommendations', 'interesting_tickers', ['symbol'], ['symbol'])


def downgrade() -> None:
    # Recreate tickers table
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
        sa.Column('active', sa.Boolean(), default=True),
        sa.Column('universe_score', sa.Float(), nullable=True),
        sa.Column('last_analysis_date', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), default=sa.func.now()),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_tickers_id', 'tickers', ['id'], unique=False)
    op.create_index('ix_tickers_symbol', 'tickers', ['symbol'], unique=True)
    
    # Migrate data back
    op.execute("""
        INSERT INTO tickers (
            symbol, name, sector, industry, market_cap, current_price,
            volume_avg_20d, volatility_30d, beta, pe_ratio, dividend_yield,
            next_earnings_date, active, universe_score, last_analysis_date, updated_at
        )
        SELECT 
            it.symbol, it.name, it.sector, it.industry, it.market_cap,
            tq.current_price, tq.volume_avg_20d, tq.volatility_30d,
            it.beta, it.pe_ratio, it.dividend_yield, it.next_earnings_date,
            it.active, it.universe_score, it.last_analysis_date, it.updated_at
        FROM interesting_tickers it
        LEFT JOIN ticker_quotes tq ON it.symbol = tq.symbol
    """)
    
    # Drop foreign key constraints first
    op.drop_constraint('options_symbol_fkey', 'options', type_='foreignkey')
    op.drop_constraint('positions_symbol_fkey', 'positions', type_='foreignkey')
    op.drop_constraint('recommendations_symbol_fkey', 'recommendations', type_='foreignkey')
    
    # Drop new tables
    op.drop_table('ticker_quotes')
    op.drop_table('interesting_tickers')
    
    # Add back original foreign key constraints
    op.create_foreign_key('options_symbol_fkey', 'options', 'tickers', ['symbol'], ['symbol'])
    op.create_foreign_key('positions_symbol_fkey', 'positions', 'tickers', ['symbol'], ['symbol'])
    op.create_foreign_key('recommendations_symbol_fkey', 'recommendations', 'tickers', ['symbol'], ['symbol'])
