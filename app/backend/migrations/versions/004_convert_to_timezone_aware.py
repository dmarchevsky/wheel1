"""Convert all timestamp columns to timezone-aware timestamps.

Revision ID: 004
Revises: 003_split_tickers_table
Create Date: 2025-08-28 17:45:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '004'
down_revision = '003_split_tickers_table'
branch_labels = None
depends_on = None


def upgrade():
    """Convert all timestamp columns to timezone-aware timestamps."""
    
    # Convert users table
    op.execute("ALTER TABLE users ALTER COLUMN created_at TYPE TIMESTAMP WITH TIME ZONE")
    
    # Convert settings table
    op.execute("ALTER TABLE settings ALTER COLUMN updated_at TYPE TIMESTAMP WITH TIME ZONE")
    
    # Convert interesting_tickers table
    op.execute("ALTER TABLE interesting_tickers ALTER COLUMN next_earnings_date TYPE TIMESTAMP WITH TIME ZONE")
    op.execute("ALTER TABLE interesting_tickers ALTER COLUMN last_analysis_date TYPE TIMESTAMP WITH TIME ZONE")
    op.execute("ALTER TABLE interesting_tickers ALTER COLUMN added_at TYPE TIMESTAMP WITH TIME ZONE")
    op.execute("ALTER TABLE interesting_tickers ALTER COLUMN updated_at TYPE TIMESTAMP WITH TIME ZONE")
    
    # Convert ticker_quotes table
    op.execute("ALTER TABLE ticker_quotes ALTER COLUMN updated_at TYPE TIMESTAMP WITH TIME ZONE")
    
    # Convert options table
    op.execute("ALTER TABLE options ALTER COLUMN expiry TYPE TIMESTAMP WITH TIME ZONE")
    op.execute("ALTER TABLE options ALTER COLUMN updated_at TYPE TIMESTAMP WITH TIME ZONE")
    
    # Convert recommendations table
    op.execute("ALTER TABLE recommendations ALTER COLUMN created_at TYPE TIMESTAMP WITH TIME ZONE")
    
    # Convert positions table
    op.execute("ALTER TABLE positions ALTER COLUMN updated_at TYPE TIMESTAMP WITH TIME ZONE")
    
    # Convert option_positions table
    op.execute("ALTER TABLE option_positions ALTER COLUMN expiry TYPE TIMESTAMP WITH TIME ZONE")
    op.execute("ALTER TABLE option_positions ALTER COLUMN open_time TYPE TIMESTAMP WITH TIME ZONE")
    op.execute("ALTER TABLE option_positions ALTER COLUMN updated_at TYPE TIMESTAMP WITH TIME ZONE")
    
    # Convert trades table
    op.execute("ALTER TABLE trades ALTER COLUMN created_at TYPE TIMESTAMP WITH TIME ZONE")
    op.execute("ALTER TABLE trades ALTER COLUMN updated_at TYPE TIMESTAMP WITH TIME ZONE")
    
    # Convert notifications table
    op.execute("ALTER TABLE notifications ALTER COLUMN created_at TYPE TIMESTAMP WITH TIME ZONE")
    op.execute("ALTER TABLE notifications ALTER COLUMN sent_at TYPE TIMESTAMP WITH TIME ZONE")
    
    # Convert telemetry table
    op.execute("ALTER TABLE telemetry ALTER COLUMN created_at TYPE TIMESTAMP WITH TIME ZONE")
    
    # Convert alerts table
    op.execute("ALTER TABLE alerts ALTER COLUMN created_at TYPE TIMESTAMP WITH TIME ZONE")
    op.execute("ALTER TABLE alerts ALTER COLUMN processed_at TYPE TIMESTAMP WITH TIME ZONE")
    
    # Convert chatgpt_cache table
    op.execute("ALTER TABLE chatgpt_cache ALTER COLUMN created_at TYPE TIMESTAMP WITH TIME ZONE")
    op.execute("ALTER TABLE chatgpt_cache ALTER COLUMN ttl TYPE TIMESTAMP WITH TIME ZONE")


def downgrade():
    """Convert all timestamp columns back to timezone-naive timestamps."""
    
    # Convert users table
    op.execute("ALTER TABLE users ALTER COLUMN created_at TYPE TIMESTAMP WITHOUT TIME ZONE")
    
    # Convert settings table
    op.execute("ALTER TABLE settings ALTER COLUMN updated_at TYPE TIMESTAMP WITHOUT TIME ZONE")
    
    # Convert interesting_tickers table
    op.execute("ALTER TABLE interesting_tickers ALTER COLUMN next_earnings_date TYPE TIMESTAMP WITHOUT TIME ZONE")
    op.execute("ALTER TABLE interesting_tickers ALTER COLUMN last_analysis_date TYPE TIMESTAMP WITHOUT TIME ZONE")
    op.execute("ALTER TABLE interesting_tickers ALTER COLUMN added_at TYPE TIMESTAMP WITHOUT TIME ZONE")
    op.execute("ALTER TABLE interesting_tickers ALTER COLUMN updated_at TYPE TIMESTAMP WITHOUT TIME ZONE")
    
    # Convert ticker_quotes table
    op.execute("ALTER TABLE ticker_quotes ALTER COLUMN updated_at TYPE TIMESTAMP WITHOUT TIME ZONE")
    
    # Convert options table
    op.execute("ALTER TABLE options ALTER COLUMN expiry TYPE TIMESTAMP WITHOUT TIME ZONE")
    op.execute("ALTER TABLE options ALTER COLUMN updated_at TYPE TIMESTAMP WITHOUT TIME ZONE")
    
    # Convert recommendations table
    op.execute("ALTER TABLE recommendations ALTER COLUMN created_at TYPE TIMESTAMP WITHOUT TIME ZONE")
    
    # Convert positions table
    op.execute("ALTER TABLE positions ALTER COLUMN updated_at TYPE TIMESTAMP WITHOUT TIME ZONE")
    
    # Convert option_positions table
    op.execute("ALTER TABLE option_positions ALTER COLUMN expiry TYPE TIMESTAMP WITHOUT TIME ZONE")
    op.execute("ALTER TABLE option_positions ALTER COLUMN open_time TYPE TIMESTAMP WITHOUT TIME ZONE")
    op.execute("ALTER TABLE option_positions ALTER COLUMN updated_at TYPE TIMESTAMP WITHOUT TIME ZONE")
    
    # Convert trades table
    op.execute("ALTER TABLE trades ALTER COLUMN created_at TYPE TIMESTAMP WITHOUT TIME ZONE")
    op.execute("ALTER TABLE trades ALTER COLUMN updated_at TYPE TIMESTAMP WITHOUT TIME ZONE")
    
    # Convert notifications table
    op.execute("ALTER TABLE notifications ALTER COLUMN created_at TYPE TIMESTAMP WITHOUT TIME ZONE")
    op.execute("ALTER TABLE notifications ALTER COLUMN sent_at TYPE TIMESTAMP WITHOUT TIME ZONE")
    
    # Convert telemetry table
    op.execute("ALTER TABLE telemetry ALTER COLUMN created_at TYPE TIMESTAMP WITHOUT TIME ZONE")
    
    # Convert alerts table
    op.execute("ALTER TABLE alerts ALTER COLUMN created_at TYPE TIMESTAMP WITHOUT TIME ZONE")
    op.execute("ALTER TABLE alerts ALTER COLUMN processed_at TYPE TIMESTAMP WITHOUT TIME ZONE")
    
    # Convert chatgpt_cache table
    op.execute("ALTER TABLE chatgpt_cache ALTER COLUMN created_at TYPE TIMESTAMP WITHOUT TIME ZONE")
    op.execute("ALTER TABLE chatgpt_cache ALTER COLUMN ttl TYPE TIMESTAMP WITHOUT TIME ZONE")
