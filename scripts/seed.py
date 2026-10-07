#!/usr/bin/env python3
"""Сид: первичное наполнение БД из текущих Python-конфигов CareerAI.

Переносит:
- признаки (27) из EXPANDED_FEATURES,
- направления (19) + ключевые навыки из DUBNA_* / DIRECTION_KEY_SKILLS,
- вопросы опросника из AdaptiveQuestionnaireV4 (screening/detailed/personal/salary),
- настройки вуза,
- стартовую учётную запись администратора.

Идемпотентен: повторный запуск не дублирует данные.

Запуск:
    python scripts/seed.py
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sqlalchemy import func, select

from app.config import get_settings
from app.database import SessionLocal, engine
from app.models import (
    AdminRole,
    AdminUser,
    Direction,
    Feature,
    FeatureType,
    Question,
    QuestionGroup,
    QuestionGroupCode,
    QuestionType,
    UniversitySettings,
)
from app.services.security import hash_password
from config.dubna_directions import FIELD_DATABASE
from config.questions import AdaptiveQuestionnaireV4
from config.model_config import (
    ABITUR_URL,
    DEFAULT_FEATURE_VALUES,
    DIRECTION_DESCRIPTIONS,
    DIRECTION_KEY_SKILLS,
    DIRECTION_KEY_SKILLS_TEXT,
    DUBNA_CODES,
    DUBNA_DIRECTION_KEYS,
    EXPANDED_FEATURES,
    FEATURE_LABELS,
    UNIVERSITY_NAME,
    UNIVERSITY_URL,
)

GROUP_TITLES = {
    QuestionGroupCode.screening: 'Определение интересов',
    QuestionGroupCode.detailed: 'Углублённые вопросы по навыкам',
    QuestionGroupCode.personal: 'Общие качества',
    QuestionGroupCode.salary: 'Карьерные ожидания',
    QuestionGroupCode.ege: 'Баллы ЕГЭ',
    QuestionGroupCode.custom: 'Анкета абитуриента',
}

COMMON_TRAITS = {
    'logical_thinking',
    'memory_ability',
    'problem_solving',
    'communication_skill',
    'teamwork_skill',
}

DEFAULT_CONSENT_TEXT = (
    'Я даю согласие на обработку персональных данных в соответствии '
    'с Федеральным законом от 27.07.2006 № 152-ФЗ «О персональных данных».'
)


def seed_features(db) -> dict[str, Feature]:
    existing = {f.code: f for f in db.scalars(select(Feature)).all()}
    created = 0
    for idx, code in enumerate(EXPANDED_FEATURES):
        if code in existing:
            continue
        data_type = FeatureType.salary if code == 'desired_salary' else FeatureType.rating_1_5
        feature = Feature(
            code=code,
            label=FEATURE_LABELS.get(code, code),
            data_type=data_type,
            default_value=str(DEFAULT_FEATURE_VALUES.get(code, 3.0)),
            is_common=code in COMMON_TRAITS,
            sort_order=idx,
            is_active=True,
        )
        db.add(feature)
        existing[code] = feature
        created += 1
    db.flush()
    print(f'  признаки: {len(existing)} ({created} добавлено)')
    return existing


def seed_directions(db, features: dict[str, Feature]) -> dict[str, Direction]:
    existing = {d.name: d for d in db.scalars(select(Direction)).all()}
    created = 0
    for idx, name in enumerate(DUBNA_DIRECTION_KEYS):
        direction = existing.get(name)
        if direction is None:
            card = FIELD_DATABASE.get(name, {})
            direction = Direction(
                name=name,
                fgos_code=DUBNA_CODES.get(name, ''),
                description=DIRECTION_DESCRIPTIONS.get(name, ''),
                key_skills_text=DIRECTION_KEY_SKILLS_TEXT.get(name, ''),
                category=card.get('category', ''),
                avg_salary=card.get('avg_salary', 0),
                employment_rate=card.get('employment_rate', 0),
                study_years=card.get('study_years', 4),
                ege_typical=card.get('ege_typical', ''),
                sort_order=idx,
                is_active=True,
            )
            db.add(direction)
            db.flush()
            existing[name] = direction
            created += 1

        # ключевые навыки (M:N) — добавляем только недостающие
        for skill_code in DIRECTION_KEY_SKILLS.get(name, []):
            feature = features.get(skill_code)
            if feature is not None and feature not in direction.features:
                direction.features.append(feature)
    db.flush()
    print(f'  направления: {len(existing)} ({created} добавлено)')
    return existing


def seed_question_groups(db) -> dict[QuestionGroupCode, QuestionGroup]:
    groups: dict[QuestionGroupCode, QuestionGroup] = {}
    for idx, code in enumerate(QuestionGroupCode):
        group = db.scalar(select(QuestionGroup).where(QuestionGroup.code == code))
        if group is None:
            group = QuestionGroup(
                code=code,
                title=GROUP_TITLES[code],
                description='',
                sort_order=idx,
                is_active=True,
            )
            db.add(group)
            db.flush()
        groups[code] = group
    return groups


def _activation_for(chain_key: str) -> dict:
    """Правила активации цепочек навыков (как в config/questions)."""
    if chain_key == 'it_infrastructure':
        return {'type': 'interest_ge', 'feature': 'computer_systems', 'value': 3}
    if chain_key == 'economic_analysis':
        return {
            'type': 'any_interest_ge',
            'features': ['business_analytics', 'management'],
            'value': 3,
        }
    return {'type': 'interest_ge', 'feature': chain_key, 'value': 3}


def seed_questions(db, groups: dict[QuestionGroupCode, QuestionGroup], features: dict[str, Feature]):
    existing_count = db.scalar(select(func.count()).select_from(Question)) or 0
    if existing_count:
        print(f'  вопросы: уже есть ({existing_count}), пропуск')
        return
    questionnaire = AdaptiveQuestionnaireV4()
    added = 0

    # --- screening: 19 вопросов об интересах ---
    for idx, (trait, text) in enumerate(questionnaire.SCREENING_QUESTIONS):
        db.add(Question(
            group_id=groups[QuestionGroupCode.screening].id,
            feature_id=features[trait].id,
            text=text,
            question_type=QuestionType.rating_1_5,
            threshold=None,
            level=0,
            activation_condition=None,
            sort_order=idx,
            is_active=True,
        ))
        added += 1

    # --- detailed: цепочки навыков с порогами ветвления ---
    for chain_key, info in questionnaire.SKILL_QUESTIONS.items():
        activation = _activation_for(chain_key)
        for idx, (q_text, _original_threshold) in enumerate(info['questions']):
            # Порог = условие перехода от предыдущего вопроса цепочки.
            # Первый вопрос всегда задаётся (порог 1.0).
            threshold = 1.0 if idx == 0 else info['questions'][idx - 1][1]
            db.add(Question(
                group_id=groups[QuestionGroupCode.detailed].id,
                feature_id=features[info['skill']].id,
                text=q_text,
                question_type=QuestionType.rating_1_5,
                threshold=threshold,
                level=idx,
                activation_condition=activation,
                sort_order=0,
                is_active=True,
            ))
            added += 1

    # --- personal: 5 общих качеств ---
    for idx, (trait, text) in enumerate(questionnaire.COMMON_TRAITS.items()):
        db.add(Question(
            group_id=groups[QuestionGroupCode.personal].id,
            feature_id=features[trait].id,
            text=text,
            question_type=QuestionType.rating_1_5,
            threshold=None,
            level=0,
            activation_condition=None,
            sort_order=idx,
            is_active=True,
        ))
        added += 1

    # --- salary: желаемая зарплата ---
    db.add(Question(
        group_id=groups[QuestionGroupCode.salary].id,
        feature_id=features['desired_salary'].id,
        text='Какую желаемую зарплату (в рублях) вы ожидаете?',
        question_type=QuestionType.salary,
        threshold=None,
        level=0,
        activation_condition=None,
        sort_order=0,
        is_active=True,
    ))
    added += 1

    db.flush()
    print(f'  вопросы: {added} добавлено')


DEFAULT_CUSTOM_FIELDS = [
    ('full_name', 'ФИО', 'text', True, 0),
    ('phone', 'Телефон', 'phone', True, 1),
    ('email', 'Email', 'email', True, 2),
]


def seed_custom_fields(db):
    """Стартовые поля анкеты вуза (если их ещё нет)."""
    from app.models import CustomFormField

    existing_count = db.scalar(
        select(func.count()).select_from(CustomFormField),
    ) or 0
    if existing_count:
        print(f'  анкета вуза: уже есть ({existing_count} полей), пропуск')
        return
    for code, label, field_type, required, order in DEFAULT_CUSTOM_FIELDS:
        db.add(CustomFormField(
            code=code,
            label=label,
            field_type=field_type,
            options=None,
            required=required,
            sort_order=order,
            is_active=True,
        ))
    db.flush()
    print('  анкета вуза: добавлено 3 стартовых поля')


def seed_university_settings(db):
    count = db.scalar(select(func.count()).select_from(UniversitySettings)) or 0
    if count:
        print('  настройки вуза: уже есть, пропуск')
        return
    db.add(UniversitySettings(
        university_name=UNIVERSITY_NAME,
        university_url=UNIVERSITY_URL,
        abitur_url=ABITUR_URL,
        tagline='Подберём направления подготовки Университета «Дубна» под ваши интересы',
        primary_color='#667eea',
        consent_text=DEFAULT_CONSENT_TEXT,
    ))
    db.flush()
    print('  настройки вуза: созданы')


def seed_admin(db):
    settings = get_settings()
    exists = db.scalar(
        select(AdminUser).where(AdminUser.username == settings.initial_admin_username),
    )
    if exists:
        print('  администратор: уже есть, пропуск')
        return
    db.add(AdminUser(
        username=settings.initial_admin_username,
        password_hash=hash_password(settings.initial_admin_password),
        role=AdminRole.admin,
        is_active=True,
    ))
    db.flush()
    print(f"  администратор: {settings.initial_admin_username} создан")


def main() -> None:
    print('=== Seed CareerAI Platform ===')
    # Fallback: если миграции ещё не применялись — создаём таблицы.
    from app.models.base import Base

    Base.metadata.create_all(bind=engine)

    with SessionLocal() as db:
        # enum 'ege' для PostgreSQL должен существовать до вставки группы
        from scripts.add_ege import _add_ege_enum

        _add_ege_enum(db)
        features = seed_features(db)
        seed_directions(db, features)
        groups = seed_question_groups(db)
        seed_questions(db, groups, features)
        seed_university_settings(db)
        seed_custom_fields(db)
        seed_admin(db)
        db.commit()

    # EGE-блок: признаки ege_*, группа, вопрос и ege_typical направлений
    from scripts.add_ege import main as add_ege_main

    add_ege_main()

    # Актуальный список направлений с официального сайта
    from scripts.sync_directions import main as sync_directions_main

    sync_directions_main()

    # Признаки и вопросы под новые программы (ИИ, кибербезопасность и др.)
    from scripts.add_program_features import main as add_program_features_main

    add_program_features_main()

    # Понятные формулировки вопросов
    from scripts.update_questions import main as update_questions_main

    update_questions_main()
    print('=== Готово ===')


if __name__ == '__main__':
    main()