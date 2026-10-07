"""ORM-модели платформы CareerAI.

Импорт всех моделей обязателен до конфигурации мапперов
и для alembic autogenerate.
"""

from app.models.admin import AdminRole, AdminUser
from app.models.base import Base
from app.models.catalog import Direction, DirectionSkill, Feature, FeatureType
from app.models.settings import UniversitySettings
from app.models.survey import (
    CustomFieldType,
    CustomFormField,
    Feedback,
    Question,
    QuestionGroup,
    QuestionGroupCode,
    QuestionType,
    SurveySession,
)
from app.models.training import ModelRun, ModelRunStatus

__all__ = [
    'AdminRole',
    'AdminUser',
    'Base',
    'CustomFieldType',
    'CustomFormField',
    'Direction',
    'DirectionSkill',
    'Feature',
    'FeatureType',
    'Feedback',
    'ModelRun',
    'ModelRunStatus',
    'Question',
    'QuestionGroup',
    'QuestionGroupCode',
    'QuestionType',
    'SurveySession',
    'UniversitySettings',
]
