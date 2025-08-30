"""Expand recommendations rationale_json into separate columns.

Revision ID: 005
Revises: 004_convert_to_timezone_aware
Create Date: 2025-08-28 18:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '005'
down_revision = '004'
branch_labels = None
depends_on = None


def upgrade():
    """Expand rationale_json into separate columns."""
    
    # Add new columns to recommendations table
    op.add_column('recommendations', sa.Column('annualized_yield', sa.Float(), nullable=True))
    op.add_column('recommendations', sa.Column('proximity_score', sa.Float(), nullable=True))
    op.add_column('recommendations', sa.Column('liquidity_score', sa.Float(), nullable=True))
    op.add_column('recommendations', sa.Column('risk_adjustment', sa.Float(), nullable=True))
    op.add_column('recommendations', sa.Column('qualitative_score', sa.Float(), nullable=True))
    op.add_column('recommendations', sa.Column('dte', sa.Integer(), nullable=True))
    op.add_column('recommendations', sa.Column('spread_pct', sa.Float(), nullable=True))
    op.add_column('recommendations', sa.Column('mid_price', sa.Float(), nullable=True))
    op.add_column('recommendations', sa.Column('delta', sa.Float(), nullable=True))
    op.add_column('recommendations', sa.Column('iv_rank', sa.Float(), nullable=True))
    op.add_column('recommendations', sa.Column('open_interest', sa.Integer(), nullable=True))
    op.add_column('recommendations', sa.Column('volume', sa.Integer(), nullable=True))
    
    # Migrate existing data from rationale_json to new columns
    op.execute("""
        UPDATE recommendations 
        SET 
            annualized_yield = (rationale_json->>'annualized_yield')::float,
            proximity_score = (rationale_json->>'proximity_score')::float,
            liquidity_score = (rationale_json->>'liquidity_score')::float,
            risk_adjustment = (rationale_json->>'risk_adjustment')::float,
            qualitative_score = (rationale_json->>'qualitative_score')::float,
            dte = (rationale_json->>'dte')::integer,
            spread_pct = (rationale_json->>'spread_pct')::float,
            mid_price = (rationale_json->>'mid_price')::float,
            delta = (rationale_json->>'delta')::float,
            iv_rank = (rationale_json->>'iv_rank')::float,
            open_interest = (rationale_json->>'open_interest')::integer,
            volume = (rationale_json->>'volume')::integer
        WHERE rationale_json IS NOT NULL
    """)
    
    # Create indexes for commonly queried fields
    op.create_index('idx_recommendations_annualized_yield', 'recommendations', ['annualized_yield'])
    op.create_index('idx_recommendations_proximity_score', 'recommendations', ['proximity_score'])
    op.create_index('idx_recommendations_liquidity_score', 'recommendations', ['liquidity_score'])
    op.create_index('idx_recommendations_dte', 'recommendations', ['dte'])
    op.create_index('idx_recommendations_delta', 'recommendations', ['delta'])
    op.create_index('idx_recommendations_iv_rank', 'recommendations', ['iv_rank'])


def downgrade():
    """Revert rationale_json expansion."""
    
    # Drop indexes
    op.drop_index('idx_recommendations_annualized_yield', 'recommendations')
    op.drop_index('idx_recommendations_proximity_score', 'recommendations')
    op.drop_index('idx_recommendations_liquidity_score', 'recommendations')
    op.drop_index('idx_recommendations_dte', 'recommendations')
    op.drop_index('idx_recommendations_delta', 'recommendations')
    op.drop_index('idx_recommendations_iv_rank', 'recommendations')
    
    # Drop new columns
    op.drop_column('recommendations', 'annualized_yield')
    op.drop_column('recommendations', 'proximity_score')
    op.drop_column('recommendations', 'liquidity_score')
    op.drop_column('recommendations', 'risk_adjustment')
    op.drop_column('recommendations', 'qualitative_score')
    op.drop_column('recommendations', 'dte')
    op.drop_column('recommendations', 'spread_pct')
    op.drop_column('recommendations', 'mid_price')
    op.drop_column('recommendations', 'delta')
    op.drop_column('recommendations', 'iv_rank')
    op.drop_column('recommendations', 'open_interest')
    op.drop_column('recommendations', 'volume')
