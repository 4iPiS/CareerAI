"""Админ-API: статистика, экспорт ответов, список сессий."""

from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import Response
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.api.deps import get_current_admin
from app.config import get_settings
from app.database import get_db
from app.models import AdminUser, SurveySession
from app.services.responses import count_stats, export_responses_csv

router = APIRouter(tags=['admin-stats'])


@router.get('/stats')
def stats(
    db: Session = Depends(get_db),
    _: AdminUser = Depends(get_current_admin),
):
    return {'stats': count_stats(db)}


@router.get('/responses.csv')
def responses_csv(
    db: Session = Depends(get_db),
    _: AdminUser = Depends(get_current_admin),
):
    csv_text = export_responses_csv(db)
    return Response(
        content=csv_text,
        media_type='text/csv; charset=utf-8',
        headers={
            'Content-Disposition': 'attachment; filename="responses.csv"',
        },
    )


@router.get('/sessions')
def sessions_list(
    limit: int = 50,
    db: Session = Depends(get_db),
    _: AdminUser = Depends(get_current_admin),
):
    rows = db.scalars(
        select(SurveySession)
        .options(selectinload(SurveySession.feedback))
        .order_by(SurveySession.id.desc())
        .limit(min(max(limit, 1), 200)),
    ).all()
    return {
        'sessions': [
            {
                'id': s.id,
                'session_uuid': s.session_uuid,
                'status': s.status,
                'stage': s.stage,
                'questions_asked': s.questions_asked,
                'source': s.source,
                'created_at': s.created_at.isoformat() if s.created_at else None,
                'feedback_score': s.feedback.feedback_score if s.feedback else None,
                'chosen_fields': s.feedback.chosen_fields if s.feedback else [],
                'profile': s.profile,
                'custom_data': s.custom_data,
                'recommendations': s.recommendations,
            }
            for s in rows
        ],
    }


@router.post('/responses/export-to-disk')
def export_responses_to_disk(
    db: Session = Depends(get_db),
    _: AdminUser = Depends(get_current_admin),
):
    """Экспортирует все завершённые сессии в CSV на диск (UTF-8 с BOM)."""
    csv_text = export_responses_csv(db)
    if not csv_text:
        raise HTTPException(status_code=400, detail='Нет завершённых сессий для экспорта')

    settings = get_settings()
    dest_dir = Path(settings.data_dir) / 'real'
    dest_dir.mkdir(parents=True, exist_ok=True)
    dest = dest_dir / 'responses.csv'
    dest.write_text(csv_text, encoding='utf-8-sig')

    # Посчитаю строки
    with open(dest, 'r', encoding='utf-8-sig') as f:
        lines = f.readlines()
    row_count = len(lines) - 1  # минус заголовок

    # Сохраняем количество строк в meta.json для отображения в админке
    import json as _json
    from datetime import datetime
    
    meta_path = dest.with_suffix('.meta.json')
    meta = {}
    if meta_path.exists():
        try:
            meta = _json.loads(meta_path.read_text())
        except Exception:
            pass
    meta['real_rows'] = row_count
    meta['updated_at'] = datetime.now().isoformat()
    meta_path.write_text(_json.dumps(meta, ensure_ascii=False))

    return {
        'ok': True,
        'path': str(dest),
        'rows': row_count,
        'encoding': 'utf-8-sig',
    }