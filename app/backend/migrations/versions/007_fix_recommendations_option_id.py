"""Fix recommendations table option_id field to reference options.symbol.

Revision ID: 007
Revises: 006
Create Date: 2025-08-28 21:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '007'
down_revision = '006'
branch_labels = None
depends_on = None


def upgrade():
    """Fix recommendations table option_id field."""
    
    # Drop the old option_id column (it's an integer without foreign key constraint)
    op.drop_column('recommendations', 'option_id')
    
    # Add a new option_id column that references options.symbol
    op.add_column('recommendations', sa.Column('option_id', sa.String(), nullable=True))
    
    # Create foreign key constraint to options.symbol
    op.create_foreign_key('recommendations_option_id_fkey', 'recommendations', 'options', ['option_id'], ['symbol'])


def downgrade():
    """Revert recommendations table option_id field."""
    
    # Drop the new foreign key constraint
    op.drop_constraint('recommendations_option_id_fkey', 'recommendations', type_='foreignkey')
    
    # Drop the new option_id column
    op.drop_column('recommendations', 'option_id')
    
    # Recreate the old option_id column as integer
    op.add_column('recommendations', sa.Column('option_id', sa.Integer(), nullable=True))
    
    # Note: We can't recreate the old foreign key constraint since the options table structure has changed
