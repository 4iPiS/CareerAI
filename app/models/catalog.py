"""Каталог: признаки, направления и их связь (ключевые навыки)."""

import enum

from sqlalchemy import Boolean, Enum, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin


class FeatureType(str, enum.Enum):
    rating_1_5 = 'rating_1_5'
    salary = 'salary'
    number = 'number'
    text = 'text'


class Feature(Base, TimestampMixin):
    """Признак профиля (например, software_development, desired_salary)."""
    __tablename__ = 'features'

    id: Mapped[int] = mapped_column(primary_key=True)
    code: Mapped[str] = mapped_column(String(64), unique=True, index=True, nullable=False)
    label: Mapped[str] = mapped_column(String(255), nullable=False)
    data_type: Mapped[FeatureType] = mapped_column(
        Enum(FeatureType, name='feature_type'),
        default=FeatureType.rating_1_5,
        nullable=False,
    )
    default_value: Mapped[str] = mapped_column(String(32), default='3.0')
    is_common: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        comment='Общее качество (логика, память, коммуникация и т.п.)',
    )
    sort_order: Mapped[int] = mapped_column(Integer, default=0)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    directions: Mapped[list['Direction']] = relationship(
        secondary='direction_skills',
        back_populates='features',
    )

    def __repr__(self) -> str:
        return f'<Feature {self.code}>'


class Direction(Base, TimestampMixin):
    """Направление подготовки бакалавриата."""
    __tablename__ = 'directions'

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    fgos_code: Mapped[str] = mapped_column(String(32), default='')
    description: Mapped[str] = mapped_column(Text, default='')
    key_skills_text: Mapped[str] = mapped_column(Text, default='')
    category: Mapped[str] = mapped_column(String(255), default='')
    avg_salary: Mapped[int] = mapped_column(Integer, default=0)
    employment_rate: Mapped[int] = mapped_column(Integer, default=0)
    study_years: Mapped[int] = mapped_column(Integer, default=4)
    ege_typical: Mapped[str] = mapped_column(String(255), default='')
    image_path: Mapped[str] = mapped_column(String(500), default='')
    sort_order: Mapped[int] = mapped_column(Integer, default=0)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    features: Mapped[list['Feature']] = relationship(
        secondary='direction_skills',
        back_populates='directions',
    )

    def __repr__(self) -> str:
        return f'<Direction {self.name}>'


class DirectionSkill(Base):
    """M:N ключевые навыки направления (бывший DIRECTION_KEY_SKILLS)."""
    __tablename__ = 'direction_skills'

    direction_id: Mapped[int] = mapped_column(
        ForeignKey('directions.id', ondelete='CASCADE'),
        primary_key=True,
    )
    feature_id: Mapped[int] = mapped_column(
        ForeignKey('features.id', ondelete='CASCADE'),
        primary_key=True,
    )
    weight: Mapped[float] = mapped_column(Float, default=1.0)

    def __repr__(self) -> str:
        return f'<DirectionSkill d={self.direction_id} f={self.feature_id}>'