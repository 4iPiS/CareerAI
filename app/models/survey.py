"""Опросник, анкета вуза и сессии опросов."""

import enum
from datetime import datetime
from typing import List, Optional

from sqlalchemy import (
    JSON,
    Boolean,
    DateTime,
    Enum,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin


class QuestionGroupCode(str, enum.Enum):
    screening = 'screening'
    detailed = 'detailed'
    personal = 'personal'
    salary = 'salary'
    ege = 'ege'
    custom = 'custom'


class QuestionType(str, enum.Enum):
    rating_1_5 = 'rating_1_5'
    salary = 'salary'
    choice_single = 'choice_single'
    choice_multi = 'choice_multi'
    text_input = 'text_input'
    number_input = 'number_input'


class CustomFieldType(str, enum.Enum):
    text = 'text'
    email = 'email'
    phone = 'phone'
    select = 'select'
    checkbox = 'checkbox'
    date = 'date'
    number = 'number'


class QuestionGroup(Base, TimestampMixin):
    """Группа вопросов (этап опросника)."""
    __tablename__ = 'question_groups'

    id: Mapped[int] = mapped_column(primary_key=True)
    code: Mapped[QuestionGroupCode] = mapped_column(
        Enum(QuestionGroupCode, name='question_group_code'),
        unique=True,
        nullable=False,
    )
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str] = mapped_column(Text, default='')
    sort_order: Mapped[int] = mapped_column(Integer, default=0)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    questions: Mapped[List['Question']] = relationship(
        back_populates='group',
        order_by='Question.sort_order',
    )


class Question(Base, TimestampMixin):
    """Вопрос опросника.

    - group = screening: вопрос об интересе, пишется в feature.
    - group = detailed: цепочка навыков. Ветвление: если ответ < threshold,
      цепочка заканчивается. level 0/1/2 — базовый/средний/продвинутый.
      Активация цепочки — через activation_condition.
    - group = personal: общие качества.
    - group = salary: желаемая зарплата.
    """
    __tablename__ = 'questions'

    id: Mapped[int] = mapped_column(primary_key=True)
    group_id: Mapped[int] = mapped_column(
        ForeignKey('question_groups.id', ondelete='CASCADE'),
        nullable=False,
    )
    feature_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey('features.id', ondelete='SET NULL'),
        nullable=True,
    )
    text: Mapped[str] = mapped_column(Text, nullable=False)
    image_url: Mapped[Optional[str]] = mapped_column(String(1000), nullable=True)
    question_type: Mapped[QuestionType] = mapped_column(
        Enum(QuestionType, name='question_type'),
        default=QuestionType.rating_1_5,
        nullable=False,
    )
    options: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    threshold: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    level: Mapped[int] = mapped_column(Integer, default=0)
    activation_condition: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    # Пример: {"type": "interest_ge", "feature": "computer_systems", "value": 3}
    #         {"type": "any_interest_ge", "features": ["business_analytics", "management"], "value": 3}
    sort_order: Mapped[int] = mapped_column(Integer, default=0)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    group: Mapped[QuestionGroup] = relationship(back_populates='questions')
    feature: Mapped[Optional['Feature']] = relationship()

    def __repr__(self) -> str:
        return f'<Question id={self.id} group={self.group_id} level={self.level}>'


class CustomFormField(Base, TimestampMixin):
    """Поле анкеты сбора данных вуза (ФИО, телефон, город, ЕГЭ и т.п.)."""
    __tablename__ = 'custom_form_fields'

    id: Mapped[int] = mapped_column(primary_key=True)
    code: Mapped[str] = mapped_column(String(64), unique=True, index=True, nullable=False)
    label: Mapped[str] = mapped_column(String(255), nullable=False)
    field_type: Mapped[CustomFieldType] = mapped_column(
        Enum(CustomFieldType, name='custom_field_type'),
        default=CustomFieldType.text,
        nullable=False,
    )
    options: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    required: Mapped[bool] = mapped_column(Boolean, default=False)
    sort_order: Mapped[int] = mapped_column(Integer, default=0)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    description: Mapped[str] = mapped_column(String(500), default='', nullable=False)
    examples: Mapped[Optional[list]] = mapped_column(JSON, nullable=True)


class SurveySession(Base, TimestampMixin):
    """Сессия опроса (заменяет строку в responses.csv)."""
    __tablename__ = 'survey_sessions'

    id: Mapped[int] = mapped_column(primary_key=True)
    session_uuid: Mapped[str] = mapped_column(String(64), unique=True, index=True, nullable=False)
    stage: Mapped[str] = mapped_column(String(32), default='screening')
    status: Mapped[str] = mapped_column(String(16), default='in_progress')
    answers: Mapped[dict] = mapped_column(JSON, default=dict)
    profile: Mapped[dict] = mapped_column(JSON, default=dict)
    recommendations: Mapped[List] = mapped_column(JSON, default=list)
    custom_data: Mapped[dict] = mapped_column(JSON, default=dict)
    state: Mapped[Optional[dict]] = mapped_column(JSON, default=dict)
    questions_asked: Mapped[int] = mapped_column(Integer, default=0)
    source: Mapped[str] = mapped_column(String(16), default='web')
    completed_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    feedback: Mapped[Optional['Feedback']] = relationship(
        back_populates='session',
        uselist=False,
    )


class Feedback(Base, TimestampMixin):
    """Метки самооценки пользователя (выбранные направления + оценка)."""
    __tablename__ = 'feedback'

    id: Mapped[int] = mapped_column(primary_key=True)
    session_id: Mapped[int] = mapped_column(
        ForeignKey('survey_sessions.id', ondelete='CASCADE'),
        unique=True,
        nullable=False,
    )
    chosen_fields: Mapped[List] = mapped_column(JSON, default=list)
    feedback_score: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    label_source: Mapped[str] = mapped_column(String(32), default='self_report')

    session: Mapped[SurveySession] = relationship(back_populates='feedback')