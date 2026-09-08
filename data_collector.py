# -*- coding: utf-8 -*-
"""
Сбор реальных данных в один CSV-файл.

data/real/responses.csv — профиль, рекомендации и метки (одна строка на опрос).
"""

from __future__ import annotations

import csv
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from config.model_config import DUBNA_DIRECTION_KEYS, EXPANDED_FEATURES

REAL_DATA_DIR = Path('data/real')
RESPONSES_CSV = REAL_DATA_DIR / 'responses.csv'

FIELD_SEP = '|'

RESPONSES_COLUMNS = [
    'session_id',
    'created_at',
    'source',
    'questions_asked',
    *EXPANDED_FEATURES,
    'rec1_field', 'rec1_probability',
    'rec2_field', 'rec2_probability',
    'rec3_field', 'rec3_probability',
    'rec4_field', 'rec4_probability',
    'rec5_field', 'rec5_probability',
    'chosen_fields',
    'feedback_score',
    'labeled_at',
    'label_source',
]


def _ensure_dir() -> None:
    REAL_DATA_DIR.mkdir(parents=True, exist_ok=True)


def _read_all_rows() -> List[Dict[str, str]]:
    if not RESPONSES_CSV.exists():
        return []
    with RESPONSES_CSV.open(encoding='utf-8-sig', newline='') as f:
        return list(csv.DictReader(f))


def _write_all_rows(rows: List[Dict[str, Any]]) -> None:
    _ensure_dir()
    with RESPONSES_CSV.open('w', newline='', encoding='utf-8-sig') as f:
        writer = csv.DictWriter(f, fieldnames=RESPONSES_COLUMNS, extrasaction='ignore')
        writer.writeheader()
        writer.writerows(rows)


def save_response(
    session_id: str,
    profile: Dict[str, Any],
    recommendations: List[Dict[str, Any]],
    *,
    source: str = 'web',
    questions_asked: int = 0,
) -> Path:
    """После опроса: одна строка с профилем и топ-5 (метки пока пустые)."""
    row: Dict[str, Any] = {
        'session_id': session_id,
        'created_at': datetime.now().isoformat(timespec='seconds'),
        'source': source,
        'questions_asked': questions_asked,
        'chosen_fields': '',
        'feedback_score': '',
        'labeled_at': '',
        'label_source': '',
    }

    for feature in EXPANDED_FEATURES:
        row[feature] = profile.get(feature, '')

    for i in range(5):
        prefix = f'rec{i + 1}'
        if i < len(recommendations):
            rec = recommendations[i]
            row[f'{prefix}_field'] = rec.get('field', '')
            row[f'{prefix}_probability'] = rec.get('probability', '')
        else:
            row[f'{prefix}_field'] = ''
            row[f'{prefix}_probability'] = ''

    rows = _read_all_rows()
    rows.append({col: str(row.get(col, '')) for col in RESPONSES_COLUMNS})
    _write_all_rows(rows)
    return RESPONSES_CSV


def update_labels(
    session_id: str,
    chosen_fields: List[str],
    *,
    feedback_score: Optional[int] = None,
    label_source: str = 'self_report',
) -> Path:
    """Дописывает метки в ту же строку по session_id."""
    valid = set(DUBNA_DIRECTION_KEYS)
    cleaned = []
    for name in chosen_fields:
        name = str(name).strip()
        if name and name in valid and name not in cleaned:
            cleaned.append(name)

    if not cleaned:
        raise ValueError('Выберите хотя бы одно направление из списка')

    if feedback_score is not None:
        feedback_score = max(1, min(5, int(feedback_score)))

    rows = _read_all_rows()
    updated = False
    for row in rows:
        if row.get('session_id') == session_id:
            row['chosen_fields'] = FIELD_SEP.join(cleaned)
            row['feedback_score'] = str(feedback_score) if feedback_score is not None else ''
            row['labeled_at'] = datetime.now().isoformat(timespec='seconds')
            row['label_source'] = label_source
            updated = True
            break

    if not updated:
        raise ValueError('Сессия не найдена в responses.csv')

    _write_all_rows(rows)
    return RESPONSES_CSV


def count_labeled_responses() -> int:
    return sum(1 for row in _read_all_rows() if row.get('chosen_fields', '').strip())
