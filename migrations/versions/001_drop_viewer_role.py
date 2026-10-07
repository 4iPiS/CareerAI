"""удалить роль viewer из admin_users

Revision ID: 001_drop_viewer_role
Revises: 
Create Date: 2026-09-23
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.exc import ProgrammingError

revision = '001_drop_viewer_role'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    conn = op.get_bind()
    try:
        conn.execute(sa.text("UPDATE admin_users SET role = 'admin' WHERE role = 'viewer'"))
    except ProgrammingError:
        # role 'viewer' больше не существует в enum — пропускаем
        pass


def downgrade() -> None:
    pass
