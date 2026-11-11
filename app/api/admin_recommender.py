"""Админ-API: настройки рекомендательной системы."""

import json

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_current_admin
from app.database import get_db
from app.models import AdminUser, Direction, RecommenderSettings
from app.schemas.admin import RecommenderSettingsPayload

router = APIRouter(tags=['admin-recommender'])


def _settings_out(s: RecommenderSettings) -> dict:
    return {
        'id': s.id,
        'engine': s.engine,
        'api_provider': s.api_provider,
        'api_key': s.api_key[:8] + '...' if s.api_key else '',
        'api_base_url': s.api_base_url,
        'api_model': s.api_model,
        'system_prompt': s.system_prompt,
    }


def _get_or_create(db: Session) -> RecommenderSettings:
    settings = db.scalar(
        select(RecommenderSettings).order_by(RecommenderSettings.id).limit(1),
    )
    if settings is None:
        settings = RecommenderSettings()
        db.add(settings)
        db.flush()
    return settings


@router.get('/recommender-settings')
def get_recommender_settings(
    db: Session = Depends(get_db),
    _: AdminUser = Depends(get_current_admin),
):
    """Получить настройки рекомендательной системы."""
    from app.services.api_recommender import SYSTEM_PROMPT
    settings = _get_or_create(db)
    if not settings.system_prompt:
        settings.system_prompt = SYSTEM_PROMPT
        db.commit()
        db.refresh(settings)
    return {'settings': _settings_out(settings)}


@router.post('/recommender-preview-prompt')
def preview_prompt(
    profile: dict,
    db: Session = Depends(get_db),
    _: AdminUser = Depends(get_current_admin),
):
    """Предпросмотр системного промпта — показывает что отправляется в LM."""
    from app.services.api_recommender import SYSTEM_PROMPT
    from app.services.unified_recommender import _get_recommender_settings
    settings = _get_recommender_settings(db)
    system_prompt = settings.system_prompt or SYSTEM_PROMPT

    # Формируем пример user-prompt с реальными данными
    all_directions = db.scalars(
        select(Direction).where(Direction.is_active),
    ).all()
    directions = [d.name for d in all_directions]
    skill_map = {d.name: [f.code for f in d.features] for d in all_directions}

    # Показываем первые 3 направления как пример
    sample_directions = directions[:3]
    sample_skills = '\n'.join(
        f'- {d}: {", ".join(skill_map[d][:3])}'
        for d in sample_directions
        if skill_map.get(d)
    )
    profile_str = json.dumps(profile, ensure_ascii=False, indent=2)

    user_prompt = (
        f'Профиль пользователя:\n{profile_str}\n\n'
        f'Направления для анализа ({len(directions)} шт, показаны первые 3):\n{sample_skills}\n\n'
        f'Напиши explanation (2-3 предложения) для КАЖДОГО направления.'
    )

    full_prompt = f'{system_prompt}\n\n---\n\n{user_prompt}'
    return {
        'system_prompt': system_prompt,
        'user_prompt': user_prompt,
        'full_prompt': full_prompt,
    }


@router.put('/recommender-settings')
def update_recommender_settings(
    payload: RecommenderSettingsPayload,
    db: Session = Depends(get_db),
    _: AdminUser = Depends(get_current_admin),
):
    """Обновить настройки рекомендательной системы."""
    settings = _get_or_create(db)
    data = payload.model_dump(exclude_none=True)

    # Всегда сохраняем system_prompt если он в payload
    if payload.system_prompt is not None:
        data['system_prompt'] = payload.system_prompt

    # Валидация engine
    if 'engine' in data and data['engine'] not in ('local', 'api'):
        raise HTTPException(
            status_code=400,
            detail='engine должен быть "local" или "api"',
        )

    # Валидация api_base_url
    if 'api_base_url' in data:
        url = data['api_base_url'].strip()
        if url and not url.startswith('http'):
            raise HTTPException(
                status_code=400,
                detail='api_base_url должен начинаться с http:// или https://',
            )
        data['api_base_url'] = url

    for field, value in data.items():
        setattr(settings, field, value)

    db.commit()
    db.refresh(settings)
    return {'settings': _settings_out(settings)}
