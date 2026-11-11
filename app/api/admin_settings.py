from __future__ import annotations

"""Админ-API: настройки вуза."""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_current_admin
from app.database import get_db
from app.models import AdminUser, UniversitySettings
from app.schemas.admin import SettingsPayload

router = APIRouter(tags=['admin-settings'])

MEDIA_FIELDS = (
    'logo_path',
    'hero_image_path',
    'presenter_video_path',
)


def _normalize_media_path(value: str | None) -> str:
    """Приводит путь медиа к виду image/xxx.jpg или ''.

    Отклоняет локальные пути (C:\\...) и внешние ссылки.
    """
    v = (value or '').strip()
    if not v:
        return ''
    if '\\' in v or '://' in v or v.startswith('http'):
        raise HTTPException(
            status_code=400,
            detail='Путь должен быть из Медиатеки, например image/xxxx.jpg',
        )
    if v.startswith('/media/'):
        v = v[len('/media/'):]
    return v.lstrip('/')


def _settings_out(s: UniversitySettings) -> dict:
    return {
        'id': s.id,
        'university_name': s.university_name,
        'university_url': s.university_url,
        'abitur_url': s.abitur_url,
        'tagline': s.tagline,
        'logo_path': s.logo_path,
        'hero_image_path': s.hero_image_path,
        'presenter_video_path': s.presenter_video_path,
        'primary_color': s.primary_color,
        'primary_alpha': s.primary_alpha,
        'consent_text': s.consent_text,
        'custom_form_position': s.custom_form_position,
        'contact_email': s.contact_email,
        'support_phone': s.support_phone,
    }


def _get_or_create(db: Session) -> UniversitySettings:
    settings = db.scalar(select(UniversitySettings).order_by(UniversitySettings.id).limit(1))
    if settings is None:
        settings = UniversitySettings(university_name='Мой университет')
        db.add(settings)
        db.flush()
    return settings


@router.get('/settings')
def get_settings(
    db: Session = Depends(get_db),
    _: AdminUser = Depends(get_current_admin),
):
    return {'settings': _settings_out(_get_or_create(db))}


@router.put('/settings')
def update_settings(
    payload: SettingsPayload,
    db: Session = Depends(get_db),
    _: AdminUser = Depends(get_current_admin),
):
    settings = _get_or_create(db)
    data = payload.model_dump(exclude_none=True)
    for field in MEDIA_FIELDS:
        if field in data:
            data[field] = _normalize_media_path(data[field])
    for field, value in data.items():
        setattr(settings, field, value)
    db.commit()
    db.refresh(settings)
    return {'settings': _settings_out(settings)}