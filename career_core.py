# -*- coding: utf-8 -*-
"""Общая логика загрузки модели, предсказаний и объяснений."""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import joblib
import numpy as np
import pandas as pd
import tensorflow as tf

from config.model_config import (
    DEFAULT_FEATURE_VALUES,
    DIRECTION_DESCRIPTIONS,
    DIRECTION_KEY_SKILLS_TEXT,
    DIRECTION_SKILLS_MAP,
    DUBNA_CODES,
    EXPANDED_FEATURES,
    MODEL_DIR,
    SKILL_NAMES,
    UNIVERSITY_NAME,
    UNIVERSITY_URL,
)


def get_match_level(probability: float) -> str:
    if probability >= 85:
        return 'IDEAL'
    if probability >= 70:
        return 'EXCELLENT'
    if probability >= 55:
        return 'GOOD'
    if probability >= 40:
        return 'AVERAGE'
    return 'LOW'


def generate_explanation(
    direction: str,
    probability: float,
    student_profile: Dict[str, Any],
) -> str:
    parts = []

    if probability >= 85:
        verdict = 'Отличное соответствие'
    elif probability >= 70:
        verdict = 'Хорошее соответствие'
    elif probability >= 55:
        verdict = 'Среднее соответствие'
    elif probability >= 40:
        verdict = 'Базовое соответствие'
    elif probability >= 25:
        verdict = 'Начальный уровень'
    else:
        verdict = 'Низкое соответствие'

    parts.append(f'[{verdict}]')

    strengths = []
    if direction in DIRECTION_SKILLS_MAP:
        for skill in DIRECTION_SKILLS_MAP[direction]:
            value = float(student_profile.get(skill) or 0)
            if value >= 4.5:
                strengths.append(f'отлично владеете {SKILL_NAMES.get(skill, skill)}')
            elif value >= 3.5:
                strengths.append(f'хорошо знаете {SKILL_NAMES.get(skill, skill)}')

    for trait, name in [
        ('logical_thinking', 'логическим мышлением'),
        ('memory_ability', 'хорошей памятью'),
        ('problem_solving', 'навыками решения задач'),
    ]:
        value = float(student_profile.get(trait) or 0)
        if value >= 4:
            strengths.append(name)

    if strengths:
        unique = []
        for item in strengths:
            if item not in unique:
                unique.append(item)
        parts.append('Ваши сильные стороны: ' + ', '.join(unique[:3]))

    if probability < 40 and direction in DIRECTION_SKILLS_MAP:
        weak = []
        for skill in DIRECTION_SKILLS_MAP[direction]:
            value = float(student_profile.get(skill) or 0)
            if value < 3:
                weak.append(SKILL_NAMES.get(skill, skill))
        if weak:
            parts.append(f'Требуется развитие: {", ".join(weak)}')

    return ' '.join(parts)


def profile_from_dataframe(student_df: pd.DataFrame) -> Dict[str, Any]:
    profile = {}
    for feature in EXPANDED_FEATURES:
        if feature in student_df.columns:
            profile[feature] = student_df[feature].iloc[0]
        else:
            profile[feature] = DEFAULT_FEATURE_VALUES.get(feature, 3.0)
    return profile


def prepare_feature_matrix(student_df: pd.DataFrame, scaler) -> np.ndarray:
    profile = profile_from_dataframe(student_df)
    processed_df = pd.DataFrame([profile])[EXPANDED_FEATURES]
    return scaler.transform(processed_df.values.astype('float32'))


class CareerAdvisor:
    def __init__(self, model_dir: str = MODEL_DIR):
        self.model_dir = Path(model_dir)
        self.model = None
        self.scaler = None
        self.mlb = None

    def load_model(self) -> None:
        if not self.model_dir.exists():
            raise FileNotFoundError(
                f'Модель не найдена в {self.model_dir}. Запустите: python train_model.py'
            )

        self.model = tf.keras.models.load_model(
            self.model_dir / 'career_model.keras',
            compile=False,
        )
        self.scaler = joblib.load(self.model_dir / 'scaler.pkl')
        self.mlb = joblib.load(self.model_dir / 'multilabel_binarizer.pkl')

    @property
    def is_loaded(self) -> bool:
        return self.model is not None and self.scaler is not None and self.mlb is not None

    def predict_proba(self, student_df: pd.DataFrame) -> np.ndarray:
        if not self.is_loaded:
            raise RuntimeError('Модель не загружена')
        features = prepare_feature_matrix(student_df, self.scaler)
        return self.model.predict(features, verbose=0)[0]

    def get_recommendations(
        self,
        student_df: pd.DataFrame,
        top_n: int = 5,
    ) -> Tuple[List[Dict[str, Any]], np.ndarray, Dict[str, Any]]:
        profile = profile_from_dataframe(student_df)
        predictions = self.predict_proba(student_df)
        probabilities = predictions * 100
        sorted_indices = np.argsort(probabilities)[::-1][:top_n]

        recommendations = []
        for rank, idx in enumerate(sorted_indices, start=1):
            direction = self.mlb.classes_[idx]
            prob = float(probabilities[idx])
            recommendations.append({
                'rank': rank,
                'field': direction,
                'code': DUBNA_CODES.get(direction, ''),
                'description': DIRECTION_DESCRIPTIONS.get(direction, ''),
                'probability': round(prob, 1),
                'match_level': get_match_level(prob),
                'explanation': generate_explanation(direction, prob, profile),
                'key_skills': DIRECTION_KEY_SKILLS_TEXT.get(direction, ''),
            })

        return recommendations, predictions, profile

    def save_results(
        self,
        recommendations: List[Dict[str, Any]],
        profile: Dict[str, Any],
        output_dir: str = 'output',
        detailed: bool = False,
        source_csv: Optional[str] = None,
    ) -> Dict[str, str]:
        out = Path(output_dir)
        out.mkdir(parents=True, exist_ok=True)
        stamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        paths = {}

        csv_path = out / f'recommendations_{stamp}.csv'
        pd.DataFrame(recommendations).to_csv(csv_path, index=False, encoding='utf-8-sig')
        paths['csv'] = str(csv_path)

        if detailed:
            report = {
                'generated_at': datetime.now().isoformat(),
                'university': UNIVERSITY_NAME,
                'university_url': UNIVERSITY_URL,
                'source_csv': source_csv,
                'profile': {k: profile.get(k) for k in EXPANDED_FEATURES},
                'recommendations': recommendations,
            }
            json_path = out / f'report_{stamp}.json'
            json_path.write_text(
                json.dumps(report, ensure_ascii=False, indent=2),
                encoding='utf-8',
            )
            paths['json'] = str(json_path)

        return paths


def to_python(obj: Any) -> Any:
    if isinstance(obj, np.ndarray):
        return obj.tolist()
    if isinstance(obj, (np.float32, np.float64)):
        return float(obj)
    if isinstance(obj, (np.int32, np.int64)):
        return int(obj)
    if isinstance(obj, dict):
        return {key: to_python(value) for key, value in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [to_python(item) for item in obj]
    return obj
