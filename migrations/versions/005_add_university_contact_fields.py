"""add contact_email and support_phone to university_settings

Revision ID: 005_add_university_contact_fields
Revises: 004_drop_recommender_extra_columns
Create Date: 2026-10-28

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '005_add_university_contact_fields'
down_revision: Union[str, None] = '004_drop_recommender_extra_columns'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('university_settings', sa.Column('contact_email', sa.String(255), nullable=False, server_default=''))
    op.add_column('university_settings', sa.Column('support_phone', sa.String(100), nullable=False, server_default=''))


def downgrade() -> None:
    op.drop_column('university_settings', 'support_phone')
    op.drop_column('university_settings', 'contact_email')