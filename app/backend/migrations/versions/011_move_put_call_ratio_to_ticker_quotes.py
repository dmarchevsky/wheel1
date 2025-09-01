"""Move put_call_ratio column from interesting_tickers to ticker_quotes table.

Revision ID: 011
Revises: 010
Create Date: 2025-01-03 13:00:00.000000

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '011'
down_revision = '010'
branch_labels = None
depends_on = None


def upgrade():
    """Move put_call_ratio column from interesting_tickers to ticker_quotes table."""
    
    # Step 1: Add put_call_ratio column to ticker_quotes table
    op.add_column('ticker_quotes', sa.Column('put_call_ratio', sa.Float(), nullable=True))
    
    # Step 2: Copy data from interesting_tickers.put_call_ratio to ticker_quotes.put_call_ratio
    op.execute("""
        UPDATE ticker_quotes 
        SET put_call_ratio = interesting_tickers.put_call_ratio
        FROM interesting_tickers 
        WHERE ticker_quotes.symbol = interesting_tickers.symbol
        AND interesting_tickers.put_call_ratio IS NOT NULL
    """)
    
    # Step 3: Remove put_call_ratio column from interesting_tickers table
    op.drop_column('interesting_tickers', 'put_call_ratio')


def downgrade():
    """Move put_call_ratio column back from ticker_quotes to interesting_tickers table."""
    
    # Step 1: Add put_call_ratio column back to interesting_tickers table
    op.add_column('interesting_tickers', sa.Column('put_call_ratio', sa.Float(), nullable=True))
    
    # Step 2: Copy data back from ticker_quotes.put_call_ratio to interesting_tickers.put_call_ratio
    op.execute("""
        UPDATE interesting_tickers 
        SET put_call_ratio = ticker_quotes.put_call_ratio
        FROM ticker_quotes 
        WHERE interesting_tickers.symbol = ticker_quotes.symbol
        AND ticker_quotes.put_call_ratio IS NOT NULL
    """)
    
    # Step 3: Remove put_call_ratio column from ticker_quotes table
    op.drop_column('ticker_quotes', 'put_call_ratio')
