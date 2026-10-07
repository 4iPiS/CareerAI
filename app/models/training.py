"""История запусков обучения модели."""

import enum
from datetime import datetime
from typing import Optional

from sqlalchemy import JSON, DateTime, Enum, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin


class ModelRunStatus(str, enum.Enum):
    pending = 'pending'
    running = 'running'
    completed = 'completed'
    failed = 'failed'


class ModelRun(Base, TimestampMixin):
    """Один запуск обучения: конфигурация-снапшот, метрики, артефакты."""
    __tablename__ = 'model_runs'

    id: Mapped[int] = mapped_column(primary_key=True)
    status: Mapped[ModelRunStatus] = mapped_column(
        Enum(ModelRunStatus, name='model_run_status'),
        default=ModelRunStatus.pending,
        nullable=False,
    )
    config_snapshot: Mapped[dict] = mapped_column(JSON, default=dict)
    metrics: Mapped[dict] = mapped_column(JSON, default=dict)
    artifact_dir: Mapped[str] = mapped_column(String(500), default='')
    error_message: Mapped[str] = mapped_column(Text, default='')
    triggered_by: Mapped[Optional[int]] = mapped_column(
        ForeignKey('admin_users.id', ondelete='SET NULL'),
        nullable=True,
    )
    current_epoch: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    total_epochs: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    finished_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    def __repr__(self) -> str:
        return f'<ModelRun id={self.id} status={self.status.value}>'