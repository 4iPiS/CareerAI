"""Рекомендатель: предсказания модели + объяснения на конфигурации из БД.

Тяжёлые зависимости (tensorflow, joblib, numpy) импортируются лениво —
только когда есть обученная модель и нужен реальный расчёт.
"""

import json
from pathlib import Path
from typing import Any, Optional

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Direction, ModelRun, ModelRunStatus

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
            }]

        import numpy as np

        model, scaler, mlb, cfg = self._load(run)
        features = cfg.get('features', [])

        # Передаём -1 в модель (модель обучена на -1 для несданных ЕГЭ)
        row_values = []
        for f in features:
            val = profile.get(f)
            if val is None:
                val = -1.0 if f.startswith('ege_') else 0.0
            row_values.append(float(val))
        
        row = np.array([row_values], dtype='float32')
        x_scaled = scaler.transform(row)
        # Получаем probability из нейронки — она уже учитывает все признаки
        raw_probs = model.predict(x_scaled, verbose=0)[0]

        # Получаем все направления и их навыки
        all_directions = self.db.scalars(
            select(Direction).where(Direction.is_active)
        ).all()
        dir_map = {d.name: d for d in all_directions}
        class_names = mlb.classes_

        # Сортируем по probability нейронки
        dir_list = [n for n in class_names if n in dir_map]
        ranked = sorted(
            [(n, float(raw_probs[i])) for i, n in enumerate(class_names) if n in dir_map],
            key=lambda x: x[1],
            reverse=True,
        )

        # Вероятности из нейросети (0-1) → проценты (0-100)
        normalized = [(name, prob * 100) for name, prob in ranked]

        recommendations = []
        for rank, (name, prob) in enumerate(normalized[:top_n], start=1):
            direction = dir_map.get(name)
            key_skills = []
            if direction and direction.features:
                key_skills = [f.code for f in direction.features]

            recommendations.append({
                'rank': rank,
                'field': name,
                'code': direction.fgos_code if direction else '',
                'image': direction.image_path if direction else '',
                'description': direction.description if direction else '',
                'explanation': self._generate_explanation(
                    name, prob, profile, key_skills,
                    direction.description if direction else '',
                ),
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
    def _generate_explanation(
        direction_name: str,
        probability: float,
        profile: dict,
        key_skills: list[str],
        direction_description: str = '',
    ) -> str:
        """Генерирует персонализированное объяснение рекомендации."""
        parts = []

        # === 2. Почему это направление подходит (сильные стороны + обоснование) ===
        strengths_excellent = []  # >= 4.5
        strengths_good = []       # >= 3.5
        strengths_medium = []     # >= 2.5

        for skill in key_skills:
            value = float(profile.get(skill, 0) or 0)
            label = Recommender._skill_label(skill)
            if value >= 4.5:
                strengths_excellent.append((label, value))
            elif value >= 3.5:
                strengths_good.append((label, value))
            elif value >= 2.5:
                strengths_medium.append((label, value))

        # Общие черты
        for trait, phrase in Recommender.TRAIT_DESCRIPTIONS.items():
            value = float(profile.get(trait, 0) or 0)
            if value >= 4.5:
                strengths_excellent.append((phrase, value))
            elif value >= 3.5:
                strengths_good.append((phrase, value))
            elif value >= 2.5:
                strengths_medium.append((phrase, value))

        # Формируем секцию "Почему подходит"
        if strengths_excellent or strengths_good:
            reason_parts = []
            
            if strengths_excellent:
                skill_list = ', '.join([f'«{s[0]}» ({int(s[1])}/5)' for s in strengths_excellent[:3]])
                reason_parts.append(f'Вы отлично владеете: {skill_list}')
            
            if strengths_good:
                skill_list = ', '.join([f'«{s[0]}» ({int(s[1])}/5)' for s in strengths_good[:2]])
                reason_parts.append(f'Хорошо развиты: {skill_list}')
            
            # Обоснование связи с направлением
            matched_excellent = len([s for s in key_skills 
                                    if float(profile.get(s, 0) or 0) >= 4.0])
            if matched_excellent >= 2 and key_skills:
                reason_parts.append(
                    f'Ваши сильные навыки соответствуют ключевым требованиям этого направления'
                )
            
            parts.append('Почему подходит: ' + '. '.join(reason_parts))

        # === 3. Слабые стороны (что нужно развить) ===
        weak_skills = []
        for skill in key_skills:
            value = float(profile.get(skill, 0) or 0)
            if 0 < value < 3:  # Пропускаем 0 (неизвестно) и -1 (ЕГЭ не сдавал)
                weak_skills.append((Recommender._skill_label(skill), value))

        if weak_skills and probability < 85:
            weak_list = ', '.join([f'«{w[0]}» ({int(w[1])}/5)' for w in weak_skills[:3]])
            parts.append(f'Нужно развить: {weak_list}')

        # === 4. Рекомендации по развитию ===
        if probability >= 70 and weak_skills:
            top_weak = weak_skills[0]
            parts.append(
                f'Совет: перед поступлением обратите внимание на {top_weak[0]} — '
                f'это поможет успешно учиться на первых курсах'
            )
        elif probability < 40 and key_skills:
            # Для низких совпадений — более конкретные рекомендации
            key_skill = key_skills[0]
            parts.append(
                f'Для этого направления рекомендуется начать с изучения '
                f'{Recommender._skill_label(key_skill)} — это базовый навык, '
                f'который понадобится с первого курса'
            )

        # === 5. Итоговая рекомендация ===
        if probability >= 85:
            parts.append(
                f'Направление «{direction_name}» — оптимальный выбор. '
                f'С вашими сильными сторонами вы сможете успешно освоить программу'
            )
        elif probability >= 70:
            parts.append(
                f'«{direction_name}» — хороший вариант. '
                f'Рекомендуем обратить внимание на это направление'
            )
        elif probability >= 55:
            parts.append(
                f'«{direction_name}» — вариант для рассмотрения. '
                f'Часть необходимых навыков у вас есть, но потребуется подготовка'
            )
        elif probability >= 40:
            parts.append(
                f'«{direction_name}» — направление требует дополнительной подготовки. '
                f'Если интересно, начните изучать базовые навыки заранее'
            )
        else:
            parts.append(
                f'«{direction_name}» — пока низкое совпадение. '
                f'Попробуйте другие направления или сначала получите базовую подготовку'
            )

        return ' | '.join(parts)
