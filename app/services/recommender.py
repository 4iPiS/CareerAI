"""Рекомендатель: предсказания модели + объяснения на конфигурации из БД.

Тяжёлые зависимости (tensorflow, joblib, numpy) импортируются лениво —
только когда есть обученная модель и нужен реальный расчёт.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Optional

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Direction, ModelRun, ModelRunStatus
from app.services.feature_normalization import normalize_profile_values

MATCH_THRESHOLDS = [
    (85, 'IDEAL'),
    (70, 'EXCELLENT'),
    (55, 'GOOD'),
    (40, 'AVERAGE'),
]


def get_match_level(probability: float) -> str:
    for threshold, level in MATCH_THRESHOLDS:
        if probability >= threshold:
            return level
    return 'LOW'


class Recommender:
    """Загружает артефакты последней успешной модели и строит топ-рекомендации."""

    def __init__(self, db: Session):
        self.db = db
        self._cache: dict[int, tuple] = {}

    # --- артефакты модели ---

    def latest_run(self) -> Optional[ModelRun]:
        return self.db.scalar(
            select(ModelRun)
            .where(ModelRun.status == ModelRunStatus.completed)
            .order_by(ModelRun.id.desc())
            .limit(1)
        )

    def _load(self, run: ModelRun) -> tuple:
        if run.id in self._cache:
            return self._cache[run.id]
        import joblib
        import tensorflow as tf

        artifact_dir = Path(run.artifact_dir)
        model = tf.keras.models.load_model(artifact_dir / 'model.keras', compile=False)
        scaler = joblib.load(artifact_dir / 'scaler.pkl')
        mlb = joblib.load(artifact_dir / 'mlb.pkl')
        with (artifact_dir / 'config.json').open(encoding='utf-8') as f:
            cfg = json.load(f)
        self._cache[run.id] = (model, scaler, mlb, cfg)
        return self._cache[run.id]

    # --- рекомендации ---

    def get_recommendations(self, profile: dict, top_n: int = 5) -> list[dict]:
        run = self.latest_run()
        if run is None:
            return [{
                'rank': 1,
                'field': 'Модель не обучена',
                'code': '',
                'description': 'Обучите модель в админ-панели.',
                'explanation': 'Модель отсутствует: запустите обучение.',
                'key_skills': '',
                'probability': 0,
                'match_level': 'LOW',
            }]

        import numpy as np

        model, scaler, mlb, cfg = self._load(run)
        features = cfg.get('features', [])

        # Получаем все активные направления и их навыки
        all_directions = self.db.scalars(
            select(Direction).where(Direction.is_active)
        ).all()
        dir_map = {d.name: d for d in all_directions}
        class_names = mlb.classes_

        # === Нормализация: ЕГЭ 0-100 → 1-5, навыки 1-5 как есть ===
        # Единая нормализация — та же, что использовалась при обучении.
        row_values = normalize_profile_values(profile, features)

        row = np.array([row_values], dtype='float32')
        x_scaled = scaler.transform(row)
        # Получаем probability из модели — она уже учитывает все признаки
        raw_probs = np.asarray(model.predict(x_scaled, verbose=0)[0], dtype='float64')

        # === Temperature scaling (калибровка, подобранная при обучении) ===
        # Усиливаем/смягчаем контраст вероятностей той же функцией, что
        # и на этапе калибровки: p^(1/T). Без нормализации на сумму —
        # шкала 0-1 сохраняется, порядок не меняется.
        temperature = float(cfg.get('temperature', 1.0) or 1.0)
        cal_probs = raw_probs
        if temperature > 0 and abs(temperature - 1.0) > 1e-6:
            cal_probs = np.power(np.clip(raw_probs, 1e-9, 1.0), 1.0 / temperature)

        # Сортируем по calibrated probability (для ранжирования)
        ranked = sorted(
            [(n, float(cal_probs[i])) for i, n in enumerate(class_names) if n in dir_map],
            key=lambda x: x[1],
            reverse=True,
        )

        # === Отображаемый процент: якорная нормализация ===
        # Абсолютные sigmoid-вероятности занижены (multi-label: даже идеальный
        # профиль даёт топ-1 ~15-40%) и зависят от числа направлений.
        # Топ-1 привязывается к шкале 55 + 40*anchor, где anchor — сырая
        # вероятность лучшего направления (0.15 → ~61%, 0.5 → ~75%,
        # 0.9 → ~91%). Остальные — пропорционально. Проценты интерпретируемы
        # и стабильны от обучения к обучению.
        top = ranked[:top_n]
        anchor = top[0][1] if top else 0.0

        recommendations = []
        for rank, (name, cal_prob) in enumerate(top, start=1):
            direction = dir_map.get(name)
            key_skills = []
            if direction and direction.features:
                key_skills = [f.code for f in direction.features]

            if anchor > 0:
                prob_pct = round(cal_prob / anchor * (55.0 + 40.0 * anchor))
            else:
                prob_pct = 1
            prob_pct = max(1, min(100, prob_pct))

            # Вердикт на основе отображаемого процента
            if prob_pct >= 55:
                verdict = 'ПОДХОДИТ'
            elif prob_pct >= 30:
                verdict = 'ЧАСТИЧНО ПОДХОДИТ'
            else:
                verdict = 'НЕ ПОДХОДИТ'

            exp = self._build_explanation(name, verdict, profile, key_skills)

            recommendations.append({
                'rank': rank,
                'field': name,
                'code': direction.fgos_code if direction else '',
                'image': direction.image_path if direction else '',
                'description': direction.description if direction else '',
                'probability': prob_pct,
                'raw_probability': round(cal_prob, 4),
                'match_level': get_match_level(prob_pct),
                'verdict': verdict,
                'strengths': exp['strengths'],
                'weaknesses': exp['weaknesses'],
                'advice': exp['advice'],
                'summary': exp['summary'],
                'explanation': exp['text'],
                'key_skills': direction.key_skills_text if direction else '',
            })
        return recommendations

    # --- объяснения ---

    # Карта навыков → понятные описания на русском
    SKILL_DESCRIPTIONS = {
        'math_modeling': 'математическое моделирование',
        'algorithms_theory': 'теория алгоритмов',
        'computer_systems': 'устройство компьютерных систем',
        'software_development': 'разработка программного обеспечения',
        'business_analytics': 'бизнес-аналитика',
        'it_infrastructure': 'информационная инфраструктура',
        'power_engineering': 'энергетика',
        'automation_tech': 'автоматизация технологий',
        'electronics': 'электроника',
        'economic_analysis': 'экономический анализ',
        'ai_ml': 'искусственный интеллект и ML',
        'cybersecurity': 'кибербезопасность',
        'communication_skill': 'коммуникация',
        'legal_knowledge': 'правовые знания',
        'social_research': 'социальные исследования',
        'psychological_counseling': 'психологическое консультирование',
        'linguistics_skill': 'лингвистика',
        'management': 'управление',
        'public_administration': 'государственное управление',
        'design': 'дизайн',
        'experimental_physics': 'экспериментальная физика',
        'nuclear_physics': 'ядерная физика',
        'aerospace_design': 'аэрокосмическое проектирование',
        'chemical_analysis': 'химический анализ',
        'geology': 'геология',
        'biotech': 'биотехнологии',
        'ecology': 'экология',
        # ЕГЭ предметы
        'ege_math': 'ЕГЭ по математике',
        'ege_russian': 'ЕГЭ по русскому языку',
        'ege_informatics': 'ЕГЭ по информатике',
        'ege_physics': 'ЕГЭ по физике',
        'ege_chemistry': 'ЕГЭ по химии',
        'ege_biology': 'ЕГЭ по биологии',
        'ege_social': 'ЕГЭ по обществознанию',
        'ege_history': 'ЕГЭ по истории',
        'ege_foreign': 'ЕГЭ по иностранному языку',
        'ege_literature': 'ЕГЭ по литературе',
        'ege_geography': 'ЕГЭ по географии',
    }

    # Карта общих признаков → понятные описания
    TRAIT_DESCRIPTIONS = {
        'logical_thinking': 'логическое мышление',
        'memory_ability': 'память',
        'problem_solving': 'решение сложных задач',
        'creativity': 'креативность',
        'attention_to_detail': 'внимательность к деталям',
    }

    @staticmethod
    def _skill_label(skill_code: str) -> str:
        """Возвращает понятное название навыка."""
        return Recommender.SKILL_DESCRIPTIONS.get(skill_code, skill_code)

    @staticmethod
    def _build_explanation(
        direction_name: str,
        verdict: str,
        profile: dict,
        key_skills: list[str],
    ) -> dict:
        """Строит структурированное объяснение рекомендации.

        Возвращает dict с полями:
          - verdict: 'ПОДХОДИТ' / 'ЧАСТИЧНО ПОДХОДИТ' / 'НЕ ПОДХОДИТ'
          - strengths: список сильных сторон (готовые фразы)
          - weaknesses: список пробелов
          - advice: конкретный совет
          - summary: итоговое предложение
          - text: все блоки, склеенные ' | ' (обратная совместимость)
        """
        # === Ключевые навыки направления с оценками пользователя ===
        items: list[tuple[str, str, float]] = []
        for skill in key_skills:
            val = profile.get(skill)
            if val is None:
                continue
            try:
                v = float(val)
            except (TypeError, ValueError):
                continue
            if skill.startswith('ege_'):
                # В профиле ЕГЭ хранится в баллах 0-100 → шкала 1-5
                v = (v / 100.0) * 4.0 + 1.0
            items.append((skill, Recommender._skill_label(skill), min(v, 5.0)))

        items.sort(key=lambda x: x[2], reverse=True)

        strong_skills = [(s, l, v) for s, l, v in items if v >= 4.0]
        medium_skills = [(s, l, v) for s, l, v in items if 3.0 <= v < 4.0]
        weak_skills = [(s, l, v) for s, l, v in items if v < 3.0]

        def _fmt(item: tuple[str, str, float]) -> str:
            return f'«{item[1]}» ({int(round(item[2]))}/5)'

        strengths: list[str] = []
        weaknesses: list[str] = []

        if strong_skills:
            names = ', '.join(_fmt(s) for s in strong_skills[:3])
            strengths.append(f'Хорошо развиты: {names}')
        if medium_skills:
            names = ', '.join(_fmt(m) for m in medium_skills[:2])
            strengths.append(f'Базовый уровень: {names}')

        # Общие качества как сильная сторона
        strong_traits = [
            phrase
            for trait, phrase in Recommender.TRAIT_DESCRIPTIONS.items()
            if float(profile.get(trait, 0) or 0) >= 4.0
        ]
        if strong_traits:
            strengths.append(f'Сильные качества: {", ".join(strong_traits[:2])}')

        if weak_skills:
            names = ', '.join(_fmt(w) for w in weak_skills[:3])
            weaknesses.append(f'Требуют внимания: {names}')

        # === Совет ===
        if verdict == 'ПОДХОДИТ':
            if weak_skills:
                advice = f'Совет: подтяните {_fmt(weak_skills[0])} — это усилит профиль.'
            else:
                advice = 'Совет: продолжайте развиваться в этом направлении — у вас уверенная база.'
        elif verdict == 'ЧАСТИЧНО ПОДХОДИТ':
            if weak_skills:
                advice = f'Совет: начните с {_fmt(weak_skills[0])} — это заметно повысит соответствие.'
            else:
                advice = 'Совет: углубите ключевые навыки направления до уверенного уровня.'
        else:
            if strong_skills:
                advice = 'Совет: сильные стороны есть, но они относятся к другим направлениям — рассмотрите варианты выше.'
            else:
                advice = 'Совет: начните с основ — вводных курсов по ключевым навыкам направления.'

        # === Итог ===
        if verdict == 'ПОДХОДИТ':
            summary = (
                f'«{direction_name}» — лучший вариант из подобранных: '
                f'ваш профиль совпадает с ключевыми навыками направления.'
            )
        elif verdict == 'ЧАСТИЧНО ПОДХОДИТ':
            summary = (
                f'«{direction_name}» — вариант для рассмотрения: '
                f'часть навыков уже развита, остальное достижимо при подготовке.'
            )
        else:
            summary = (
                f'«{direction_name}» пока слабо совпадает с вашим профилем — '
                f'обратите внимание на направления выше.'
            )

        verdict_reason = {
            'ПОДХОДИТ': 'да',
            'ЧАСТИЧНО ПОДХОДИТ': 'отчасти',
            'НЕ ПОДХОДИТ': 'нет',
        }.get(verdict, 'нет')
        parts = [
            f'Вердикт: направление «{direction_name}» {verdict_reason} подходит.',
        ]
        parts.extend(strengths)
        parts.extend(weaknesses)
        parts.append(advice)
        parts.append(summary)

        return {
            'verdict': verdict,
            'strengths': strengths,
            'weaknesses': weaknesses,
            'advice': advice,
            'summary': summary,
            'text': ' | '.join(parts),
        }
