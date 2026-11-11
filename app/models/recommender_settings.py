"""Настройки рекомендательной системы."""

from sqlalchemy import JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin


class RecommenderSettings(Base, TimestampMixin):
    """Настройки рекомендательной системы."""
    __tablename__ = 'recommender_settings'

    id: Mapped[int] = mapped_column(primary_key=True)
    engine: Mapped[str] = mapped_column(
        String(10),
        default='local',
        nullable=False,
        comment='local или api',
    )
    # --- API настройки ---
    api_provider: Mapped[str] = mapped_column(String(50), default='openai', comment='Провайдер: openai, custom')
    api_key: Mapped[str] = mapped_column(String(500), default='', comment='API ключ')
    api_base_url: Mapped[str] = mapped_column(String(500), default='', comment='Базовый URL API')
    api_model: Mapped[str] = mapped_column(String(100), default='', comment='Модель LLM (gpt-4o-mini, llama-3 и т.д.)')
    system_prompt: Mapped[str] = mapped_column(Text, default='', comment='Системный промпт для LLM')

    def __repr__(self) -> str:
        return f'<RecommenderSettings engine={self.engine}>'
