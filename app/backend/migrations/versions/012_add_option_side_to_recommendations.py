"""Add option_side column to recommendations table.

Revision ID: 012
Revises: 011
Create Date: 2025-01-03 14:00:00.000000

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '012'
down_revision = '011'
branch_labels = None
depends_on = None


def upgrade():
    """Add option_side column to recommendations table."""
    
    # Add option_side column to recommendations table
    op.add_column('recommendations', sa.Column('option_side', sa.String(), nullable=True))
    
    # Populate option_side from the related option's option_type
    op.execute("""
        UPDATE recommendations 
        SET option_side = options.option_type
        FROM options 
        WHERE recommendations.option_symbol = options.symbol
        AND options.option_type IS NOT NULL
    """)
    
    # Create index for option_side column for better query performance
    op.create_index('idx_recommendations_option_side', 'recommendations', ['option_side'])


def downgrade():
    """Remove option_side column from recommendations table."""
    
    # Drop the index first
    op.drop_index('idx_recommendations_option_side', 'recommendations')
    
    # Remove option_side column
    op.drop_column('recommendations', 'option_side')
