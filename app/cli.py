#!/usr/bin/env python3
"""CLI платформы CareerAI: рекомендации по CSV и консольный опросник.

Работает на конфигурации из БД (как и веб-версия).

Примеры:
    python -m app.cli recommend examples/student_it_profile.csv
    python -m app.cli ask
"""
from __future__ import annotations

import argparse
import csv
import sys
import uuid
from pathlib import Path

from sqlalchemy import select

from app.database import SessionLocal
from app.models import Feature, SurveySession
from app.services.questionnaire import SurveyEngine
from app.services.recommender import Recommender

INDICATORS = {
    'IDEAL': '🟢',
    'EXCELLENT': '🔵',
    'GOOD': '🟡',
    'AVERAGE': '⚪',
    'LOW': '⚪',
    'ERROR': '⛔',
}


def _print_recommendations(recommendations: list[dict]) -> None:
    print('\n' + '=' * 70)
    print('ВАШИ РЕКОМЕНДАЦИИ')
    print('=' * 70)
    for rec in recommendations:
        indicator = INDICATORS.get(rec['match_level'], '⚪')
        print(f"\n{indicator} {rec['rank']}. {rec['field']}")
        if rec.get('code'):
            print(f"   Код ФГОС: {rec['code']}")
        print(f"   Вероятность: {rec['probability']}% ({rec['match_level']})")
        if rec.get('description'):
            print(f"   {rec['description']}")
        if rec.get('explanation'):
            print(f"   {rec['explanation']}")
        if rec.get('key_skills'):
            print(f"   Ключевые навыки: {rec['key_skills']}")
        print('-' * 50)
    print('=' * 70)


def cmd_recommend(args: argparse.Namespace) -> None:
    csv_path = Path(args.csv_file)
    if not csv_path.exists():
        print(f'ERROR: файл не найден: {csv_path}')
        sys.exit(1)

    with csv_path.open(encoding='utf-8-sig', newline='') as f:
        rows = list(csv.DictReader(f))
    if not rows:
        print('ERROR: CSV пуст')
        sys.exit(1)
    profile_row = rows[0]

    with SessionLocal() as db:
        features = {f.code: f for f in db.scalars(select(Feature)).all()}
        profile = {}
        for code, feat in features.items():
            raw = profile_row.get(code, '').strip()
            if raw == '':
                value = feat.default_value
            else:
                value = raw
            try:
                profile[code] = float(value)
            except ValueError:
                profile[code] = value

        recommender = Recommender(db)
        recommendations = recommender.get_recommendations(
            profile,
            top_n=args.top_n,
        )

    _print_recommendations(recommendations)


def _ask_rating(text: str) -> int:
    print(f"\n   {text}")
    print("   1 - совсем не интересую / очень низкий")
    print("   2 - слабый интерес / ниже среднего")
    print("   3 - средний интерес / средний уровень")
    print("   4 - интересно / выше среднего")
    print("   5 - очень интересно / высокий уровень")
    while True:
        try:
            value = int(input("   Ваша оценка (1-5): "))
            if 1 <= value <= 5:
                return value
            print("   Введите число от 1 до 5")
        except ValueError:
            print("   Введите число от 1 до 5")


def _ask_salary() -> int:
    print("\n   Какую желаемую зарплату (в рублях) вы ожидаете?")
    while True:
        try:
            value = max(30000, min(300000, int(input("   -> "))))
            return round(value, -3)
        except ValueError:
            print("   Введите число")


def cmd_ask(args: argparse.Namespace) -> None:
    print("\n" + "=" * 70)
    print("ПРОФОРИЕНТАЦИОННЫЙ ОПРОСНИК (платформа CareerAI)")
    print("=" * 70)

    session_uuid = uuid.uuid4().hex[:32]
    with SessionLocal() as db:
        engine = SurveyEngine(db)
        state = engine.start_state()
        session = SurveySession(
            session_uuid=session_uuid,
            stage='screening',
            status='in_progress',
            state=state,
            source='cli',
        )
        db.add(session)
        db.commit()

        payload = engine.first_payload(state)
        while payload is not None:
            print(f"\n--- [{payload.get('progress', {}).get('title', '')}] ---")
            if payload.get('is_salary'):
                answer = _ask_salary()
            elif payload.get('type') in ('choice_single', 'choice_multi'):
                answer = input(f"   {payload['text']} -> ")
            elif payload.get('type') in ('text_input', 'number_input'):
                answer = input(f"   {payload['text']} -> ")
            else:
                print(f"   {payload['text']}")
                if payload.get('context'):
                    print(f"   ({payload['context']})")
                answer = _ask_rating(payload['text'])

            next_payload, state = engine.submit_answer(state, payload['id'], answer)
            session.state = state
            session.stage = state.get('stage', session.stage)
            db.add(session)
            db.commit()
            payload = next_payload

        # финализация: профиль + рекомендации
        profile = engine.build_profile(state)
        recommender = Recommender(db)
        recommendations = recommender.get_recommendations(profile)
        session.profile = profile
        session.recommendations = recommendations
        session.status = 'completed'
        session.stage = 'done'
        db.add(session)
        db.commit()

    _print_recommendations(recommendations)


def main() -> None:
    parser = argparse.ArgumentParser(
        prog='careerai',
        description='CareerAI Platform — CLI',
    )
    sub = parser.add_subparsers(dest='command', required=True)

    p_rec = sub.add_parser('recommend', help='Рекомендации по CSV-профилю')
    p_rec.add_argument('csv_file', help='CSV с профилем (колонки-признаки)')
    p_rec.add_argument('--top-n', type=int, default=5)
    p_rec.set_defaults(func=cmd_recommend)

    p_ask = sub.add_parser('ask', help='Консольный опросник')
    p_ask.set_defaults(func=cmd_ask)

    args = parser.parse_args()
    args.func(args)


if __name__ == '__main__':
    main()