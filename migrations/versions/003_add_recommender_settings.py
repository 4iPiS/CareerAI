"""add recommender_settings table

Revision ID: 003_add_recommender_settings
Revises: 002_add_epoch_columns
Create Date: 2026-10-19

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '003_add_recommender_settings'
down_revision: Union[str, None] = '002_add_epoch_columns'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'recommender_settings',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('engine', sa.Enum('local', 'api', name='recommendation_engine', create_type=False), nullable=False, server_default='local'),
        sa.Column('api_provider', sa.String(50), nullable=False, server_default='openai'),
        sa.Column('api_key', sa.String(500), nullable=False, server_default=''),
        sa.Column('api_base_url', sa.String(500), nullable=False, server_default=''),
        sa.Column('api_model', sa.String(100), nullable=False, server_default='gpt-4o-mini'),
        sa.Column('api_temperature', sa.Float(), nullable=False, server_default='0.3'),
        sa.Column('prompt_template', sa.Text(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )


def downgrade() -> None:
    op.drop_table('recommender_settings')
    op.execute("DROP TYPE IF EXISTS recommendation_engine")
