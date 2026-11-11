"""Скрипт для добавления тестовых данных в базу."""
import os
os.environ['DATABASE_URL'] = 'postgresql+psycopg2://careerai:careerai@careerai-db:5432/careerai'

from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

DATABASE_URL = os.environ.get('DATABASE_URL', 'postgresql+psycopg2://careerai:careerai@careerai-db:5432/careerai')
engine = create_engine(DATABASE_URL)
Session = sessionmaker(bind=engine)
session = Session()

print("Adding test data...")

# Add directions
directions = [
    ('Информатика и вычислительные технологии', 'Высокий спрос на IT-специалистов'),
    ('Программная инженерия', 'Разработка программного обеспечения'),
    ('Прикладная математика и информатика', 'Математическое моделирование и IT'),
    ('Физика', 'Исследование физических процессов'),
    ('Математика', 'Чистая и прикладная математика'),
    ('Экономика', 'Управление экономическими системами'),
    ('Менеджмент', 'Управление организациями и проектами'),
    ('Бизнес-информатика', 'IT в бизнесе'),
    ('Электроника и наноинженерия', 'Радиоэлектроника и нанотехнологии'),
    ('Биотехнология', 'Биотехнологические исследования'),
]

for name, description in directions:
    result = session.execute(
        text("SELECT id FROM directions WHERE name = :name"),
        {'name': name}
    )
    if not result.fetchone():
        session.execute(
            text("INSERT INTO directions (name, description) VALUES (:name, :description)"),
            {'name': name, 'description': description}
        )

print(f"Added {len(directions)} directions")

# Add features
features = [
    ('Логическое мышление', 'ability', 'Логика и анализ'),
    ('Творческое мышление', 'ability', 'Креативность'),
    ('Аналитические способности', 'ability', 'Анализ данных'),
    ('Коммуникативность', 'soft', 'Общение'),
    ('Лидерство', 'soft', 'Управление людьми'),
    ('Внимательность к деталям', 'ability', 'Точность'),
    ('Работа с кодом', 'hard', 'Программирование'),
    ('Математические способности', 'ability', 'Математика'),
]

for label, feature_type, description in features:
    result = session.execute(
        text("SELECT id FROM features WHERE label = :label"),
        {'label': label}
    )
    if not result.fetchone():
        session.execute(
            text("INSERT INTO features (label, feature_type, description) VALUES (:label, :type, :desc)"),
            {'label': label, 'type': feature_type, 'desc': description}
        )

print(f"Added {len(features)} features")

# Add questions
questions = [
    ('Насколько вам интересно решать логические задачи?', 'screening', 1),
    ('Любите ли вы создавать что-то новое и творческое?', 'screening', 2),
    ('Вам нравится анализировать данные и находить закономерности?', 'screening', 3),
    ('Легко ли вы находите общий язык с новыми людьми?', 'screening', 4),
    ('Хотели бы вы управлять проектами и людьми?', 'screening', 5),
    ('Вам важно работать с точными данными и деталями?', 'screening', 6),
    ('Интересуется ли вы программированием?', 'detailed', 7),
    ('Насколько сильны ваши математические навыки?', 'detailed', 8),
]

for text, stage, sort_order in questions:
    result = session.execute(
        text("SELECT id FROM questions WHERE text = :text"),
        {'text': text}
    )
    if not result.fetchone():
        session.execute(
            text("""INSERT INTO questions (text, stage, sort_order, is_salary, is_ege, is_custom, is_ege_select)
                    VALUES (:text, :stage, :sort, false, false, false, false)"""),
            {'text': text, 'stage': stage, 'sort': sort_order}
        )

print(f"Added {len(questions)} questions")

session.commit()
print("Done! Database updated successfully.")
