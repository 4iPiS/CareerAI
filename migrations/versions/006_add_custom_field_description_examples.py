"""add description and examples to custom_form_fields

Revision ID: 006_add_custom_field_description_examples
Revises: 005_add_university_contact_fields
Create Date: 2026-11-02

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '006_add_custom_field_description_examples'
down_revision: Union[str, None] = '005_add_university_contact_fields'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('custom_form_fields', sa.Column('description', sa.String(500), nullable=False, server_default=''))
    op.add_column('custom_form_fields', sa.Column('examples', sa.JSON(), nullable=True))


def downgrade() -> None:
    op.drop_column('custom_form_fields', 'examples')
    op.drop_column('custom_form_fields', 'description')
