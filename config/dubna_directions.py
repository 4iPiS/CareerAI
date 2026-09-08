# -*- coding: utf-8 -*-
"""
Расширенные карточки направлений (ЕГЭ, зарплата, описания).
Канонический список направлений и признаков модели — в config.model_config.
"""

from config.model_config import (
    ABITUR_URL,
    DIRECTIONS_SOURCE,
    DUBNA_CODES,
    DUBNA_DIRECTION_KEYS,
    UNIVERSITY_NAME,
    UNIVERSITY_URL,
)

# Обратная совместимость: FIELD_DATABASE содержит подробности по части направлений.
# Для направлений вне словаря используйте DIRECTION_DESCRIPTIONS из model_config.

FIELD_DATABASE = {
    'Физика': {
        'code': '03.03.02',
        'category': 'Физика и астрономия',
        'avg_salary': 120000,
        'employment_rate': 92,
        'study_years': 4,
        'human_description': (
            'Готовит теоретических и экспериментальных физиков. '
            'В Дубне — сильная школа ядерной и фундаментальной физики.'
        ),
        'ege_typical': 'Математика, Физика, Русский язык',
        'universities': [UNIVERSITY_NAME],
    },
    'Химия': {
        'code': '04.03.01',
        'category': 'Химия',
        'avg_salary': 100000,
        'employment_rate': 88,
        'study_years': 4,
        'human_description': 'Квалифицированные химики для промышленности, НИИ и образования.',
        'ege_typical': 'Химия, Математика, Русский язык',
        'universities': [UNIVERSITY_NAME],
    },
    'Программная инженерия': {
        'code': '09.03.04',
        'category': 'Информатика и вычислительная техника',
        'avg_salary': 160000,
        'employment_rate': 97,
        'study_years': 4,
        'human_description': 'Разработка и сопровождение программных систем.',
        'ege_typical': 'Математика, Информатика, Русский язык',
        'universities': [UNIVERSITY_NAME],
    },
}


def get_direction_card(direction_name: str) -> dict:
    """Подробная карточка направления или минимальные данные из model_config."""
    from config.model_config import DIRECTION_DESCRIPTIONS

    if direction_name in FIELD_DATABASE:
        return FIELD_DATABASE[direction_name]
    return {
        'code': DUBNA_CODES.get(direction_name, ''),
        'human_description': DIRECTION_DESCRIPTIONS.get(direction_name, ''),
        'universities': [UNIVERSITY_NAME],
    }
