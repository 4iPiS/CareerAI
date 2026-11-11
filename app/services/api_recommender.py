"""API-рекоммендер: вызывает внешний LLM API для генерации рекомендаций.

probability считается в Python, LLM генерирует explanation для каждого направления отдельно.
"""
from __future__ import annotations

import json
import logging
from typing import Optional

import httpx

from app.services.recommender import get_match_level

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = (
    'Ты — карьерный консультант. Напиши 3-4 предложения объяснения почему направление подходит или нет пользователю.\n\n'
    'ОТВЕЧАЙ ПРАВИЛАМИ:\n'
    '  - НАЧНИ с вердикта: "Вердикт: направление [название] [да/нет/отчасти] подходит."\n'
    '  - Если вероятность >= 20% → "да подходит"\n'
    '  - Если вероятность >= 10% → "отчасти подходит"\n'
    '  - Если вероятность < 10% → "нет не подходит"\n'
    '  - Нейросеть редко даёт >50%, это нормально — ориентируйся на относительные значения.\n'
    '  - Напиши 1-2 предложения почему подходит (сильные навыки) или почему не подходит (слабые навыки).\n'
    '  - Дай конкретный совет что развить.\n'
    '  - ЗАКЛЮЧИ: "[Название] — [лучший вариант / хороший вариант / вариант для рассмотрения / требует подготовки]."\n\n'
    'ОТВЕЧАЙ ТОЛЬКО ТЕКСТОМ (без JSON, без нумерации, на русском языке).\n'
    'Используй русские названия навыков (не коды на английском).\n'
    'Максимум 4-5 предложений.'
)

API_TEMPERATURE = 0.7


def _calculate_probabilities(profile: dict, directions: list[str], skill_map: dict, code_to_name: dict) -> list[dict]:
    """Рассчитывает probability для каждого направления.

    Все значения приводятся к шкале 1-5. ЕГЭ (0-100) делится на 20.
    Считается среднее по всем ключевым навыкам направления.
    """
    results = []
    for direction in directions:
        skills = skill_map.get(direction, [])
        if not skills:
            continue

        scores = []
        for skill in skills:
            val = profile.get(skill)
            if val is None:
                val = 1.0
            else:
                val = float(val)

            # Нормализуем ЕГЭ (0-100 баллов) → шкала 1-5, как в локальной модели
            if skill.startswith('ege_'):
                val = max(1.0, min(5.0, (val / 100.0) * 4.0 + 1.0))
            else:
                val = max(0.0, min(5.0, val))

            scores.append(val)

        if not scores:
            probability = 0
        else:
            avg_score = sum(scores) / len(scores)
            probability = round((avg_score / 5.0) * 100)
            probability = max(0, min(100, probability))

        results.append({
            'field': direction,
            'probability': probability,
            'key_skills': skills,
        })

    results.sort(key=lambda x: x['probability'], reverse=True)
    return results[:10]


class ApiRecommender:
    """Вызывает внешний LLM API для генерации рекомендаций."""

    def __init__(
        self,
        api_key: str = '',
        api_base_url: str = '',
        model: str = '',
        system_prompt: str = '',
        directions: Optional[list[str]] = None,
        skill_map: Optional[dict[str, list[str]]] = None,
        code_to_name: Optional[dict[str, str]] = None,
    ):
        self.api_key = api_key
        self.api_base_url = (api_base_url or '').rstrip('/')
        self.model = model or 'gpt-4o-mini'
        self.system_prompt = system_prompt or SYSTEM_PROMPT
        self.directions = directions or []
        self.skill_map = skill_map or {}
        self.code_to_name = code_to_name or {}

    def get_recommendations(
        self,
        profile: dict,
        top_n: int = 5,
    ) -> Optional[list[dict]]:
        """Генерирует рекомендации через внешний API."""
        if not self.api_base_url.startswith(('http://', 'https://')):
            logger.error(f'Invalid api_base_url: {self.api_base_url!r}')
            return None
        try:
            # 1. Считаем probability в Python
            probs = _calculate_probabilities(profile, self.directions, self.skill_map, self.code_to_name)
            top_probs = probs[:top_n]

            # 2. Генерируем explanation ПАРАЛЛЕЛЬНО для всех top-N —
            # последовательные LLM-вызовы выглядели как «зависший сайт».
            import concurrent.futures

            def _explain(rec: dict) -> None:
                rec['explanation'] = self._generate_explanation(
                    profile, rec['field'], rec['probability'], rec['key_skills']
                ) or 'Нет совпадений с навыками пользователя.'

            with concurrent.futures.ThreadPoolExecutor(
                max_workers=min(5, len(top_probs) or 1),
            ) as pool:
                list(pool.map(_explain, top_probs))

            return self._format_recommendations(top_probs)
        except Exception as exc:
            logger.error(f'API recommendation failed: {exc}')
            return None

    def _generate_explanation(
        self,
        profile: dict,
        field: str,
        probability: int,
        key_skills: list[str],
    ) -> str:
        """Генерирует explanation для одного направления."""
        url = f'{self.api_base_url}/chat/completions'
        headers = {'Content-Type': 'application/json'}
        if self.api_key:
            headers['Authorization'] = f'Bearer {self.api_key}'

        # Формируем отображение навыков на русском
        profile_display = {}
        for code, score in profile.items():
            name = self.code_to_name.get(code, code)
            profile_display[name] = score
        profile_str = json.dumps(profile_display, ensure_ascii=False, indent=2)

        skills_display = ', '.join(self.code_to_name.get(s, s) for s in key_skills)

        prompt = (
            f'Профиль пользователя:\n{profile_str}\n\n'
            f'Направление: {field}\n'
            f'Вероятность совпадения: {probability}%\n'
            f'Ключевые навыки направления: {skills_display}\n\n'
            f'Напиши 3-4 предложения объяснения почему это направление подходит или нет пользователю.\n'
            f'Нейросеть редко даёт >50% — это нормально, ориентируйся на относительные значения.'
        )

        payload = {
            'model': self.model,
            'messages': [
                {'role': 'system', 'content': self.system_prompt},
                {'role': 'user', 'content': prompt},
            ],
            'temperature': API_TEMPERATURE,
            'max_tokens': 500,
        }

        try:
            logger.info(f'Explanation POST to {url} model={self.model} field={field}')
            with httpx.Client(timeout=httpx.Timeout(timeout=90.0, connect=10.0)) as client:
                response = client.post(url, headers=headers, json=payload)
                response.raise_for_status()
                data = response.json()
                choices = data.get('choices', [])
                if choices:
                    text = choices[0]['message']['content'].strip()
                    logger.info(f'Explanation for {field}: {text[:100]!r}')
                    return text
        except Exception as e:
            logger.warning(f'Explanation generation failed for {field}: {e}')

        return None

    @staticmethod
    def _verdict_from_probability(probability: float) -> str:
        if probability >= 55:
            return 'ПОДХОДИТ'
        if probability >= 30:
            return 'ЧАСТИЧНО ПОДХОДИТ'
        return 'НЕ ПОДХОДИТ'

    def _format_recommendations(
        self,
        raw: list[dict],
    ) -> list[dict]:
        """Форматирует ответ API в единый формат (probability 0-100)."""
        recommendations = []
        for rank, item in enumerate(raw, start=1):
            field_name = item.get('field', 'Неизвестное направление')
            probability = int(item.get('probability', 0) or 0)
            probability = max(0, min(100, probability))
            key_skills = item.get('key_skills', [])
            explanation = item.get('explanation', '')

            recommendations.append({
                'rank': rank,
                'field': field_name,
                'code': '',
                'image': '',
                'description': '',
                'probability': probability,
                'raw_probability': round(probability / 100.0, 4),
                'match_level': get_match_level(probability),
                'verdict': self._verdict_from_probability(probability),
                'strengths': [],
                'weaknesses': [],
                'advice': '',
                'summary': explanation,
                'explanation': explanation,
                'key_skills': ', '.join(key_skills) if isinstance(key_skills, list) else key_skills,
            })

        return recommendations
