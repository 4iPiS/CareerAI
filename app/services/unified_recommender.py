"""Объединённый рекоммендер: выбирает между локальной моделью и API.

Используется публичным API для генерации рекомендаций.
"""
from __future__ import annotations

import logging
from typing import Optional

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Direction, RecommenderSettings
from app.services.api_recommender import ApiRecommender
from app.services.recommender import Recommender as LocalRecommender

logger = logging.getLogger(__name__)


def get_recommendations(
    db: Session,
    profile: dict,
    top_n: int = 5,
) -> list[dict]:
    """Получает рекомендации согласно настройкам."""
    import sys
    settings = _get_recommender_settings(db)
    engine = (settings.engine or '').strip().lower()
    sys.stdout.write(f'[ENGINE] engine={engine} url={settings.api_base_url} model={settings.api_model}\n')
    sys.stdout.flush()
    logger.info(f'Recommender engine: {engine}, api_key: {bool(settings.api_key)}, api_url: {settings.api_base_url}, api_model: {settings.api_model}')

    if engine == 'api':
        return _api_recommendations(db, profile, top_n, settings)
    else:
        logger.info('Using local Keras model')
        return _local_recommendations(db, profile, top_n)


def _get_recommender_settings(db: Session) -> RecommenderSettings:
    """Загружает настройки рекоммендера (или создаёт дефолтные)."""
    from app.services.api_recommender import SYSTEM_PROMPT
    settings = db.scalar(
        select(RecommenderSettings).order_by(RecommenderSettings.id).limit(1),
    )
    if settings is None:
        settings = RecommenderSettings(system_prompt=SYSTEM_PROMPT)
        db.add(settings)
        db.commit()
        db.refresh(settings)
    elif not settings.system_prompt:
        settings.system_prompt = SYSTEM_PROMPT
        db.commit()
        db.refresh(settings)
    return settings


def _local_recommendations(
    db: Session,
    profile: dict,
    top_n: int,
) -> list[dict]:
    """Локальная модель."""
    rec = LocalRecommender(db)
    return rec.get_recommendations(profile, top_n)


def _api_recommendations(
    db: Session,
    profile: dict,
    top_n: int,
    settings: RecommenderSettings,
) -> list[dict]:
    """Внешний API, при ошибке — локальная модель."""
    logger.info(f'Calling API: {settings.api_base_url}  model={settings.api_model}')

    # Загружаем направления и навыки
    all_directions = db.scalars(
        select(Direction).where(Direction.is_active),
    ).all()
    directions = [d.name for d in all_directions]
    skill_map = {d.name: [f.code for f in d.features] for d in all_directions}
    code_to_name = {}
    for d in all_directions:
        for f in d.features:
            code_to_name[f.code] = f.label

    # Маппинг: skill_code → список ЕГЭ-предметов, которые усиливают это направление
    EGE_FOR_SKILL = {
        'experimental_physics': ['ege_physics'],
        'nuclear_physics': ['ege_physics'],
        'math_modeling': ['ege_math'],
        'algorithms_theory': ['ege_math'],
        'computer_systems': ['ege_informatics'],
        'software_development': ['ege_informatics'],
        'ai_ml': ['ege_informatics', 'ege_math'],
        'cybersecurity': ['ege_informatics'],
        'chemical_analysis': ['ege_chemistry'],
        'biotech': ['ege_biology'],
        'ecology': ['ege_biology'],
        'geology': ['ege_geography'],
        'economic_analysis': ['ege_social'],
        'business_analytics': ['ege_social'],
        'legal_knowledge': ['ege_social'],
        'public_administration': ['ege_social'],
        'management': ['ege_social'],
        'linguistics_skill': ['ege_foreign', 'ege_russian'],
        'psychological_counseling': ['ege_social', 'ege_biology'],
        'design': ['ege_literature'],
        'aerospace_design': ['ege_physics', 'ege_math'],
        'power_engineering': ['ege_physics', 'ege_math'],
        'electronics': ['ege_physics', 'ege_math'],
        'automation_tech': ['ege_physics', 'ege_math'],
    }

    # Добавляем соответствующие ЕГЭ-предметы к skill_map каждого направления
    for dname, skills in skill_map.items():
        extra_ege = set()
        for skill in skills:
            ege_subjects = EGE_FOR_SKILL.get(skill, [])
            extra_ege.update(ege_subjects)
        if extra_ege:
            skill_map[dname] = skills + list(extra_ege)

    api_rec = ApiRecommender(
        api_key=settings.api_key or '',
        api_base_url=settings.api_base_url or '',
        model=settings.api_model or '',
        system_prompt=settings.system_prompt or '',
        directions=directions,
        skill_map=skill_map,
        code_to_name=code_to_name,
    )

    recommendations = api_rec.get_recommendations(profile, top_n)
    if recommendations is not None:
        logger.info(f'API returned {len(recommendations)} recommendations')
        return recommendations

    logger.warning('API returned None, falling back to local model')
    # API недоступен — fallback на локальную модель
    local = LocalRecommender(db)
    return local.get_recommendations(profile, top_n)
