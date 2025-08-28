"""Convert all timestamps to Pacific timezone

Revision ID: 002_convert_timestamps_to_pacific
Revises: 001_initial_schema
Create Date: 2025-08-28 23:45:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
import pytz
from datetime import datetime

# revision identifiers, used by Alembic.
revision = '002_convert_timestamps_to_pacific'
down_revision = '001_initial_schema'
branch_labels = None
depends_on = None


def upgrade():
    """Convert all UTC timestamps to Pacific timezone."""
    # Get database connection
    connection = op.get_bind()
    
    # Pacific timezone
    pacific_tz = pytz.timezone("America/Los_Angeles")
    
    # Tables with timestamp columns to update
    tables_and_columns = [
        ("users", ["created_at"]),
        ("settings", ["updated_at"]),
        ("interesting_tickers", ["added_at", "updated_at"]),
        ("ticker_quotes", ["updated_at"]),
        ("options", ["updated_at"]),
        ("recommendations", ["created_at"]),
        ("positions", ["updated_at"]),
        ("option_positions", ["updated_at"]),
        ("trades", ["created_at", "updated_at"]),
        ("notifications", ["created_at", "sent_at"]),
        ("telemetry", ["created_at"]),
        ("alerts", ["created_at", "processed_at"]),
        ("chatgpt_cache", ["created_at", "ttl"]),
    ]
    
    for table_name, columns in tables_and_columns:
        for column_name in columns:
            # Check if table and column exist
            inspector = sa.inspect(connection)
            if table_name in inspector.get_table_names():
                table_columns = [col['name'] for col in inspector.get_columns(table_name)]
                if column_name in table_columns:
                    # Convert UTC timestamps to Pacific timezone
                    # This assumes existing timestamps are in UTC
                    connection.execute(
                        sa.text(f"""
                        UPDATE {table_name} 
                        SET {column_name} = {column_name} AT TIME ZONE 'UTC' AT TIME ZONE 'America/Los_Angeles'
                        WHERE {column_name} IS NOT NULL
                        """
                        )
                    )
                    print(f"Updated {table_name}.{column_name} to Pacific timezone")


def downgrade():
    """Convert Pacific timestamps back to UTC (if needed)."""
    # Get database connection
    connection = op.get_bind()
    
    # Tables with timestamp columns to update
    tables_and_columns = [
        ("users", ["created_at"]),
        ("settings", ["updated_at"]),
        ("interesting_tickers", ["added_at", "updated_at"]),
        ("ticker_quotes", ["updated_at"]),
        ("options", ["updated_at"]),
        ("recommendations", ["created_at"]),
        ("positions", ["updated_at"]),
        ("option_positions", ["updated_at"]),
        ("trades", ["created_at", "updated_at"]),
        ("notifications", ["created_at", "sent_at"]),
        ("telemetry", ["created_at"]),
        ("alerts", ["created_at", "processed_at"]),
        ("chatgpt_cache", ["created_at", "ttl"]),
    ]
    
    for table_name, columns in tables_and_columns:
        for column_name in columns:
            # Check if table and column exist
            inspector = sa.inspect(connection)
            if table_name in inspector.get_table_names():
                table_columns = [col['name'] for col in inspector.get_columns(table_name)]
                if column_name in table_columns:
                    # Convert Pacific timestamps back to UTC
                    connection.execute(
                        sa.text(f"""
                        UPDATE {table_name} 
                        SET {column_name} = {column_name} AT TIME ZONE 'America/Los_Angeles' AT TIME ZONE 'UTC'
                        WHERE {column_name} IS NOT NULL
                        """
                        )
                    )
                    print(f"Reverted {table_name}.{column_name} to UTC")
