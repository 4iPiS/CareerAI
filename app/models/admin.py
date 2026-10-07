"""Учётные записи администраторов."""

import enum

from sqlalchemy import Boolean, Enum, String
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin


class AdminRole(str, enum.Enum):
    admin = 'admin'


class AdminUser(Base, TimestampMixin):
    __tablename__ = 'admin_users'

    id: Mapped[int] = mapped_column(primary_key=True)
    username: Mapped[str] = mapped_column(String(64), unique=True, index=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[AdminRole] = mapped_column(
        Enum(AdminRole, name='admin_role'),
        default=AdminRole.admin,
        nullable=False,
    )
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    def __repr__(self) -> str:
        return f'<AdminUser {self.username} ({self.role.value})>'