#!/usr/bin/env python3
"""Идемпотентное добавление блока ЕГЭ: признаки, группа вопросов, типовые предметы направлений.

- добавляет enum-значение 'ege' в questiongroupcode (PostgreSQL; SQLite пропускается);
- создаёт 11 признаков ege_* (тип number, значение по умолчанию 0);
- создаёт группу вопросов 'ege' и один вопрос «Баллы ЕГЭ»;
- заполняет Direction.ege_typical для всех активных направлений.

Запускается при старте контейнера после seed.py и вручную для существующих БД.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sqlalchemy import func, select, text  # noqa: E402
from sqlalchemy.dialects import postgresql  # noqa: E402

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

# код → (label, типовые предметы направлений)
EGE_FEATURES = [
    ('ege_math', 'Математика (профильная)'),
    ('ege_russian', 'Русский язык'),
    ('ege_informatics', 'Информатика и ИКТ'),
    ('ege_physics', 'Физика'),
    ('ege_chemistry', 'Химия'),
    ('ege_biology', 'Биология'),
    ('ege_social', 'Обществознание'),
    ('ege_history', 'История'),
    ('ege_foreign', 'Иностранный язык'),
    ('ege_literature', 'Литература'),
    ('ege_geography', 'География'),
]

# направление → типовые предметы ЕГЭ (для карточки и обучения)
DIRECTION_EGE_TYPICAL = {
    'Химия': 'русский язык, химия, математика/физика',
    'Химия, физика и механика материалов': 'русский язык, химия, физика/математика',
    'Экология и природопользование': 'русский язык, математика, география/биология',
    'Физика': 'русский язык, физика, математика',
    'Информатика и вычислительная техника': 'русский язык, математика, информатика/физика',
    'Информационные системы и технологии': 'русский язык, математика, информатика/физика',
    'Прикладная информатика': 'русский язык, математика, информатика/физика',
    'Программная инженерия': 'русский язык, математика, информатика/физика',
    'Конструирование и технология электронных средств': 'русский язык, физика, математика',
    'Электроэнергетика и электротехника': 'русский язык, физика, математика',
    'Ядерные физика и технологии': 'русский язык, физика, математика',
    'Автоматизация технологических процессов': 'русский язык, математика, физика/информатика',
    'Авиастроение': 'русский язык, физика, математика',
    'Психология': 'русский язык, биология/математика/обществознание',
    'Менеджмент': 'русский язык, математика, обществознание',
    'Государственное и муниципальное управление': 'русский язык, обществознание, история',
    'Социология': 'русский язык, обществознание, математика/история',
    'Юриспруденция': 'русский язык, обществознание, история',
    'Лингвистика': 'русский язык, иностранный язык, история/литература',
}


def _add_ege_enum(db) -> None:
    """PostgreSQL: ALTER TYPE ... ADD VALUE.

    Имя enum берём из каталога БД (information_schema), т.к. SQLAlchemy
    может создавать тип с разными именами. SQLite пропускаем (VALUES
    не хранятся в enum-типе).
    """
    try:
        row = db.execute(
            text(
                "SELECT udt_name FROM information_schema.columns "
                "WHERE table_name='question_groups' AND column_name='code'"
            ),
        ).first()
        if row is None:
            return
        type_name = row[0]
        db.execute(text(f'ALTER TYPE "{type_name}" ADD VALUE IF NOT EXISTS \'ege\''))
        db.commit()
        print(f'  enum {type_name}: значение ege добавлено/уже есть')
    except Exception as exc:  # noqa: BLE001 — SQLite или нет таблицы
        db.rollback()
        print(f'  предупреждение: не удалось расширить enum ({exc})')


def main() -> None:
    print('=== Add EGE block ===')
    with SessionLocal() as db:
        _add_ege_enum(db)

        existing = {f.code: f for f in db.scalars(select(Feature)).all()}
        added = 0
        next_sort = (db.scalar(select(func.max(Feature.sort_order))) or 0) + 1
        for idx, (code, label) in enumerate(EGE_FEATURES):
            if code in existing:
                continue
            feature = Feature(
                code=code,
                label=label,
                data_type=FeatureType.number,
                default_value='0',
                is_common=False,
                sort_order=next_sort + idx,
                is_active=True,
            )
            db.add(feature)
            existing[code] = feature
            added += 1
        db.flush()
        print(f'  признаки ЕГЭ: {len([c for c in existing if c.startswith("ege_")])} ({added} добавлено)')

        group = db.scalar(select(QuestionGroup).where(QuestionGroup.code == QuestionGroupCode.ege))
        if group is None:
            group = QuestionGroup(
                code=QuestionGroupCode.ege,
                title='Баллы ЕГЭ',
                description='Баллы ЕГЭ по предметам (0 — предмет не сдавался)',
                sort_order=90,
                is_active=True,
            )
            db.add(group)
            db.flush()
            print('  группа "ege": создана')

        ege_count = db.scalar(
            select(func.count())
            .select_from(Question)
            .join(QuestionGroup)
            .where(QuestionGroup.code == QuestionGroupCode.ege),
        ) or 0
        if ege_count == 0:
            first_ege = existing.get('ege_math')
            db.add(Question(
                group_id=group.id,
                feature_id=first_ege.id if first_ege else None,
                text=(
                    'Укажите ваши баллы ЕГЭ по предметам '
                    '(поставьте 0, если предмет не сдавали)'
                ),
                question_type=QuestionType.number_input,
                threshold=None,
                level=0,
                activation_condition=None,
                sort_order=0,
                is_active=True,
            ))
            print('  вопрос "Баллы ЕГЭ": создан')

        updated = 0
        for direction in db.scalars(select(Direction)).all():
            typical = DIRECTION_EGE_TYPICAL.get(direction.name)
            if typical and direction.ege_typical != typical:
                direction.ege_typical = typical
                updated += 1
        db.flush()
        print(f'  направлений с ege_typical: {updated} обновлено')

        db.commit()
    print('=== EGE block ready ===')


if __name__ == '__main__':
    main()