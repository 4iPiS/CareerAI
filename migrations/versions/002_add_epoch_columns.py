"""add current_epoch and total_epochs to model_runs

Revision ID: 002_add_epoch_columns
Revises: 001_drop_viewer_role
Create Date: 2026-09-27

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '002_add_epoch_columns'
down_revision: Union[str, None] = '001_drop_viewer_role'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('model_runs', sa.Column('current_epoch', sa.Integer(), nullable=True))
    op.add_column('model_runs', sa.Column('total_epochs', sa.Integer(), nullable=True))


def downgrade() -> None:
    op.drop_column('model_runs', 'total_epochs')
    op.drop_column('model_runs', 'current_epoch')
