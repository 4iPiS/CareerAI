"""Единая нормализация признаков для обучения и инференса.

Раньше шкалы ЕГЭ расходились: синтетика генерировала 1-5, реальные ответы
опроса — 0-100 баллов, а инференс конвертировал 0-100 → 1-5. Из-за этого
StandardScaler обучался на смеси шкал и вероятности модели были занижены
и «плыли» от обучения к обучению.

Теперь каноническое представление:
  - ЕГЭ хранится как баллы 0-100 (как в опросе);
  - перед подачей в модель (обучение и инференс) значения приводятся
    к шкале 1-5: 0 → 1, 100 → 5;
  - навыки (rating_1_5) — шкала 1-5 без преобразований.
"""
from __future__ import annotations

from typing import Any


def is_ege_feature(code: str) -> bool:
    return str(code).startswith('ege_')


def ege_to_scale(raw: float) -> float:
    """Баллы ЕГЭ 0-100 → шкала 1-5 (0 → 1, 100 → 5)."""
    val = (float(raw) / 100.0) * 4.0 + 1.0
    return max(1.0, min(5.0, val))


def is_salary_feature(code: str) -> bool:
    return 'salary' in str(code).lower()


def normalize_feature_value(code: str, value: Any) -> float:
    """Нормализует значение одного признака.

    - ЕГЭ: баллы 0-100 → шкала 1-5;
    - зарплата: сырое значение без преобразований (скейлер обучен на нём —
      кламп к 1-5 давал z-выброс и ломал предсказания);
    - навыки: шкала 1-5 без преобразований.
    """
    if is_salary_feature(code):
        if value is None:
            return 100000.0
        try:
            return float(value)
        except (TypeError, ValueError):
            return 100000.0
    if value is None:
        return 1.0 if is_ege_feature(code) else 0.0
    try:
        val = float(value)
    except (TypeError, ValueError):
        return 1.0 if is_ege_feature(code) else 0.0
    if is_ege_feature(code):
        return ege_to_scale(val)
    return max(0.0, min(5.0, val))


def normalize_profile_values(profile: dict, feature_codes: list[str]) -> list[float]:
    """Готовит вектор значений признаков для модели (обучение/инференс).

    Отсутствующие ЕГЭ считаются несданными (0 баллов → 1 по шкале),
    отсутствующие навыки — 0 (клампится при использовании).
    """
    return [
        normalize_feature_value(code, profile.get(code))
        for code in feature_codes
    ]


def normalize_dataframe_ege(df: 'object', feature_codes: list[str]) -> 'object':
    """Приводит ЕГЭ-колонки DataFrame (0-100) к шкале 1-5.

    NaN в ЕГЭ-колонках = несданный предмет = 1.0 по шкале.
    """
    import numpy as np

    ege_cols = [c for c in feature_codes if is_ege_feature(c) and c in df.columns]
    if not ege_cols:
        return df
    for col in ege_cols:
        raw = df[col].astype(float)
        converted = (raw / 100.0) * 4.0 + 1.0
        converted = converted.clip(1.0, 5.0)
        df[col] = converted.where(raw.notna(), 1.0).astype('float32')
    return df
