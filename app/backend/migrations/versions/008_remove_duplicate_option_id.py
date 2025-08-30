"""Remove duplicate option_id column from recommendations table.

Revision ID: 008
Revises: 007
Create Date: 2025-08-29 21:30:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '008'
down_revision = '007'
branch_labels = None
depends_on = None


def upgrade():
    """Remove duplicate option_id column from recommendations table."""
    
    # Drop the foreign key constraint for option_id
    op.drop_constraint('recommendations_option_id_fkey', 'recommendations', type_='foreignkey')
    
    # Drop the option_id column
    op.drop_column('recommendations', 'option_id')


def downgrade():
    """Recreate option_id column in recommendations table."""
    
    # Add the option_id column back
    op.add_column('recommendations', sa.Column('option_id', sa.String(), nullable=True))
    
    # Recreate the foreign key constraint
    op.create_foreign_key('recommendations_option_id_fkey', 'recommendations', 'options', ['option_id'], ['symbol'])
