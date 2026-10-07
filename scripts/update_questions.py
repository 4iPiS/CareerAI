#!/usr/bin/env python3
"""Переписывает вопросы опросника на понятные формулировки.

Обновляет ТЕКСТ существующих вопросов в БД (по группам и признакам), ничего
не добавляя и не удаляя. Повторный запуск безопасен (идемпотентен).

Важно: вопросы «Интересы» теперь звучат как вопрос с оценкой интереса,
а не как ярлык темы.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sqlalchemy import select  # noqa: E402

from app.database import SessionLocal  # noqa: E402
from app.models import Question, QuestionGroupCode  # noqa: E402

SCREENING_BY_FEATURE = {
    'chemical_analysis': 'Насколько вам интересна химия, изучение веществ и работа в лаборатории?',
    'experimental_physics': 'Насколько вам интересна физика, эксперименты и устройство окружающего мира?',
    'ecology': 'Насколько вам интересна экология, охрана природы и окружающая среда?',
    'computer_systems': 'Насколько вам интересны компьютеры, сети и IT-инфраструктура?',
    'software_development': 'Насколько вам интересно программирование и создание сайтов и приложений?',
    'business_analytics': 'Насколько вам интересен анализ данных и применение IT в бизнесе?',
    'electronics': 'Насколько вам интересна электроника и конструирование устройств?',
    'power_engineering': 'Насколько вам интересна энергетика и работа с электричеством?',
    'nuclear_physics': 'Насколько вам интересна ядерная физика и атомная энергетика?',
    'automation_tech': 'Насколько вам интересны роботы, автоматизация и современное производство?',
    'aerospace_design': 'Насколько вам интересна авиация, ракеты и космос?',
    'psychological_counseling': 'Насколько вам интересна психология и помощь другим людям?',
    'management': 'Насколько вам интересно управление компаниями и ведение бизнеса?',
    'public_administration': 'Насколько вам интересна работа в государственных органах и управление регионом?',
    'social_research': 'Насколько вам интересно изучение общества, опросы и социологические исследования?',
    'legal_knowledge': 'Насколько вам интересно право, законы и юридическая работа?',
    'linguistics_skill': 'Насколько вам интересны иностранные языки, перевод и лингвистика?',
    'math_modeling': 'Насколько вам интересна математика и математическое моделирование?',
    'algorithms_theory': 'Насколько вам интересны алгоритмы и решение задач по программированию?',
}

PERSONAL_BY_FEATURE = {
    'logical_thinking': 'Насколько легко вам решать нестандартные логические задачи?',
    'memory_ability': 'Оцените свою память и умение запоминать большие объёмы информации',
    'problem_solving': 'Насколько вам нравится искать решения сложных задач?',
    'communication_skill': 'Насколько легко вам общаться и договариваться с людьми?',
    'teamwork_skill': 'Насколько комфортно вам работать в команде?',
}

SALARY_TEXT = 'Какую желаемую зарплату (руб. в месяц) вы ожидаете после окончания вуза?'


def main() -> None:
    print('=== Update questions ===')
    changed = 0
    with SessionLocal() as db:
        questions = db.scalars(select(Question)).all()
        for q in questions:
            gcode = q.group.code.value if q.group else None
            fcode = q.feature.code if q.feature else None
            new_text = None
            if gcode == QuestionGroupCode.screening.value and fcode in SCREENING_BY_FEATURE:
                new_text = SCREENING_BY_FEATURE[fcode]
            elif gcode == QuestionGroupCode.personal.value and fcode in PERSONAL_BY_FEATURE:
                new_text = PERSONAL_BY_FEATURE[fcode]
            elif gcode == QuestionGroupCode.salary.value:
                new_text = SALARY_TEXT
            if new_text and q.text != new_text:
                q.text = new_text
                changed += 1
        db.commit()
        print(f'  обновлено текстов: {changed}')
    print('=== Done ===')


if __name__ == '__main__':
    main()