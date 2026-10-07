#!/usr/bin/env python3
"""Признаки и вопросы под новые программы (31 профиль с сайта вуза).

Добавляет 5 признаков (ИИ/ML, кибербезопасность, биотехнологии, геология,
дизайн) + скрининговые вопросы к ним, и привязывает их к подходящим программам.
Идемпотентен.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sqlalchemy import func, select  # noqa: E402

from app.database import SessionLocal  # noqa: E402
from app.models import (  # noqa: E402
    Direction,
    Feature,
    FeatureType,
    Question,
    QuestionGroup,
    QuestionGroupCode,
    QuestionType,
)

# код → (label, текст вопроса)
NEW_FEATURES = [
    ('ai_ml', 'ИИ и машинное обучение',
     'Насколько вам интересны искусственный интеллект и машинное обучение?'),
    ('cybersecurity', 'Кибербезопасность',
     'Насколько вам интересна защита данных и кибербезопасность?'),
    ('biotech', 'Биология и биотехнологии',
     'Насколько вам интересны биология и биотехнологии?'),
    ('geology', 'Геология и недра Земли',
     'Насколько вам интересна геология и изучение земных недр?'),
    ('design', 'Дизайн и визуальное творчество',
     'Насколько вам интересен дизайн и визуальное творчество?'),
]

# программа → новые признаки
PROGRAM_NEW_SKILLS = {
    'Инженерия систем искусственного интеллекта': ['ai_ml'],
    'Системы обработки данных и машинное обучение': ['ai_ml'],
    'Интеллектуальные системы управления роботизированными технологическими процессами': ['ai_ml'],
    'Безопасность информационных систем': ['cybersecurity'],
    'Ядерно-физические технологии в биологии и медицине': ['biotech'],
    'Геофизические методы поиска и разведки месторождений полезных ископаемых': ['geology'],
    'Прикладная информатика в компьютерном дизайне': ['design'],
    'Проектирование беспилотных летательных аппаратов': ['design'],
}


def main() -> None:
    print('=== Add program features ===')
    with SessionLocal() as db:
        existing = {f.code: f for f in db.scalars(select(Feature)).all()}
        next_sort = (db.scalar(select(func.max(Feature.sort_order))) or 0) + 1
        added = 0
        for idx, (code, label, _q) in enumerate(NEW_FEATURES):
            if code in existing:
                continue
            feature = Feature(
                code=code,
                label=label,
                data_type=FeatureType.rating_1_5,
                default_value='3.0',
                is_common=False,
                sort_order=next_sort + idx,
                is_active=True,
            )
            db.add(feature)
            existing[code] = feature
            added += 1
        db.flush()
        print(f'  признаков добавлено: {added}')

        # скрининговые вопросы для новых признаков
        groups = {g.code.value: g for g in db.scalars(select(QuestionGroup)).all()}
        screening = groups.get(QuestionGroupCode.screening.value)
        added_q = 0
        for code, _label, text in NEW_FEATURES:
            feature = existing.get(code)
            if feature is None or screening is None:
                continue
            exists = db.scalar(
                select(func.count())
                .select_from(Question)
                .where(Question.feature_id == feature.id),
            ) or 0
            if exists:
                continue
            max_order = db.scalar(
                select(func.max(Question.sort_order)).select_from(Question),
            ) or 0
            db.add(Question(
                group_id=screening.id,
                feature_id=feature.id,
                text=text,
                question_type=QuestionType.rating_1_5,
                threshold=None,
                level=0,
                activation_condition=None,
                sort_order=max_order + 1,
                is_active=True,
            ))
            added_q += 1
        print(f'  вопросов добавлено: {added_q}')

        # привязка к программам
        for direction in db.scalars(select(Direction).where(Direction.is_active.is_(True))).all():
            for skill_code in PROGRAM_NEW_SKILLS.get(direction.name, []):
                feature = existing.get(skill_code)
                if feature is not None and feature not in direction.features:
                    direction.features.append(feature)

        db.commit()
    print('=== Done ===')


if __name__ == '__main__':
    main()