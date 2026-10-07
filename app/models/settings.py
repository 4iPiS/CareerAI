"""Настройки вуза (название, медиа, текст согласия)."""

from sqlalchemy import String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin


class UniversitySettings(Base, TimestampMixin):
    __tablename__ = 'university_settings'

    id: Mapped[int] = mapped_column(primary_key=True)
    university_name: Mapped[str] = mapped_column(String(255), nullable=False)
    university_url: Mapped[str] = mapped_column(String(500), default='')
    abitur_url: Mapped[str] = mapped_column(String(500), default='')
    tagline: Mapped[str] = mapped_column(String(500), default='')
    logo_path: Mapped[str] = mapped_column(String(500), default='')
    hero_image_path: Mapped[str] = mapped_column(String(500), default='')
    presenter_video_path: Mapped[str] = mapped_column(String(500), default='')
    primary_color: Mapped[str] = mapped_column(String(20), default='#667eea')
    primary_alpha: Mapped[float] = mapped_column(default=1.0)
    consent_text: Mapped[str] = mapped_column(Text, default='')
    custom_form_position: Mapped[str] = mapped_column(
        String(16),
        default='start',
        comment='Позиция анкеты вуза: start (в начале опроса) или end (в конце)',
    )

    def __repr__(self) -> str:
        return f'<UniversitySettings {self.university_name}>'