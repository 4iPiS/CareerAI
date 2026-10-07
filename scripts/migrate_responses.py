#!/usr/bin/env python3
"""Перенос данных из data/real/responses.csv в PostgreSQL (survey_sessions).

Односторонняя миграция старых CSV-ответов в новую схему платформы.

Запуск:
    python scripts/migrate_responses.py [путь_к_csv]
"""

import csv
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sqlalchemy import select

from app.database import SessionLocal
from app.models import Feedback, SurveySession
from config.model_config import EXPANDED_FEATURES

FIELD_SEP = '|'


def _parse_float(value: str) -> float | None:
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def migrate(csv_path: Path) -> int:
    if not csv_path.exists():
        print(f'Файл не найден: {csv_path}')
        return 0

    with csv_path.open(encoding='utf-8-sig', newline='') as f:
        rows = list(csv.DictReader(f))

    imported = 0
    skipped = 0
    with SessionLocal() as db:
        existing = {
            s.session_uuid
            for s in db.scalars(select(SurveySession)).all()
        }
        for row in rows:
            session_id = (row.get('session_id') or '').strip()
            if not session_id or session_id in existing:
                skipped += 1
                continue

            answers: dict[str, Any] = {}
            profile: dict[str, Any] = {}
            for feature in EXPANDED_FEATURES:
                value = row.get(feature, '')
                parsed = _parse_float(value)
                answers[feature] = parsed if parsed is not None else value
                profile[feature] = parsed if parsed is not None else value

            recommendations = []
            for i in range(1, 6):
                field = row.get(f'rec{i}_field', '')
                prob = row.get(f'rec{i}_probability', '')
                if field:
                    recommendations.append({
                        'rank': i,
                        'field': field,
                        'probability': _parse_float(prob),
                    })

            session = SurveySession(
                session_uuid=session_id,
                stage='done',
                status='completed',
                answers=answers,
                profile=profile,
                recommendations=recommendations,
                custom_data={},
                state={},
                questions_asked=int(row.get('questions_asked') or 0),
                source=(row.get('source') or 'legacy'),
            )
            db.add(session)
            db.flush()

            chosen = (row.get('chosen_fields') or '').strip()
            if chosen:
                chosen_list = [c.strip() for c in chosen.split(FIELD_SEP) if c.strip()]
                score_raw = row.get('feedback_score', '')
                db.add(Feedback(
                    session_id=session.id,
                    chosen_fields=chosen_list,
                    feedback_score=_parse_float(score_raw),
                    label_source=row.get('label_source') or 'self_report',
                ))
            imported += 1

        db.commit()
    print(f'Импортировано сессий: {imported}, пропущено (уже есть): {skipped}')
    return imported


def main() -> None:
    default_path = Path('data/real/responses.csv')
    path = Path(sys.argv[1]) if len(sys.argv) > 1 else default_path
    migrate(path)


if __name__ == '__main__':
    main()