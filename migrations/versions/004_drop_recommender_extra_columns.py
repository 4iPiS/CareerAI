"""drop api_model, api_temperature, prompt_template columns

Revision ID: 004_drop_recommender_extra_columns
Revises: 003_add_recommender_settings
Create Date: 2026-10-19

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '004_drop_recommender_extra_columns'
down_revision: Union[str, None] = '003_add_recommender_settings'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.drop_column('recommender_settings', 'api_model')
    op.drop_column('recommender_settings', 'api_temperature')
    op.drop_column('recommender_settings', 'prompt_template')


def downgrade() -> None:
    op.add_column('recommender_settings', sa.Column('api_model', sa.String(100), nullable=False, server_default='gpt-4o-mini'))
    op.add_column('recommender_settings', sa.Column('api_temperature', sa.Float(), nullable=False, server_default='0.3'))
    op.add_column('recommender_settings', sa.Column('prompt_template', sa.Text(), nullable=False, server_default=''))
