"""Сервис сессий: финализация опроса, обратная связь, экспорт ответов."""

from datetime import datetime
from typing import Any, Optional

import pandas as pd
from sqlalchemy import String, cast, func, select
from sqlalchemy.orm import Session

from app.models import Feedback, SurveySession
from app.services.questionnaire import SurveyEngine
from app.services.recommender import Recommender


def get_session_by_uuid(db: Session, session_uuid: str) -> Optional[SurveySession]:
    return db.scalar(
        select(SurveySession).where(SurveySession.session_uuid == session_uuid),
    )


def finalize_session(
    db: Session,
    session: SurveySession,
    custom_data: Optional[dict] = None,
) -> dict:
    """Заполняет профиль, считает рекомендации, помечает сессию завершённой."""
    engine = SurveyEngine(db)
    state = session.state or {}
    profile = engine.build_profile(state)

    recommender = Recommender(db)
    recommendations = recommender.get_recommendations(profile)

    session.profile = profile
    session.recommendations = recommendations
    # Не затираем анкету, если она уже сохранена (форма в начале опроса),
    # и не перезаписываем пустотой, когда custom_data не передавался.
    if custom_data is not None:
        session.custom_data = custom_data
    session.questions_asked = int(state.get('questions_asked', 0) or 0)
    session.status = 'completed'
    session.stage = 'done'
    session.completed_at = datetime.now()
    db.add(session)
    db.commit()
    db.refresh(session)

    return {
        'recommendations': recommendations,
        'stats': {'questions_asked': state.get('questions_asked', 0)},
    }


def save_feedback(
    db: Session,
    session_uuid: str,
    chosen_fields: list[str],
    feedback_score: Optional[int],
) -> Feedback:
    session = get_session_by_uuid(db, session_uuid)
    if session is None:
        raise LookupError('Сессия не найдена')

    cleaned: list[str] = []
    for name in chosen_fields:
        name = str(name).strip()
        if name and name not in cleaned:
            cleaned.append(name)
    if not cleaned:
        raise ValueError('Выберите хотя бы одно направление из списка')

    fb = db.scalar(select(Feedback).where(Feedback.session_id == session.id))
    if fb is None:
        fb = Feedback(
            session_id=session.id,
            chosen_fields=cleaned,
            feedback_score=feedback_score,
            label_source='self_report',
        )
        db.add(fb)
    else:
        fb.chosen_fields = cleaned
        fb.feedback_score = feedback_score
        fb.label_source = 'self_report'
    db.commit()
    db.refresh(fb)
    return fb


def export_responses_csv(db: Session) -> str:
    """Возвращает CSV всех завершённых сессий (для админки).

    Колонки: сессия + все признаки профиля + анкета + топ-5 рекомендаций
    + метки самооценки.
    """
    import json

    from app.models import Feature

    features = [
        f.code
        for f in db.scalars(select(Feature).order_by(Feature.sort_order)).all()
    ]
    sessions = db.scalars(
        select(SurveySession)
        .where(SurveySession.status == 'completed')
        .order_by(SurveySession.id),
    ).all()

    rows = []
    for s in sessions:
        profile = s.profile or {}
        row: dict[str, Any] = {
            'session_id': s.session_uuid,
            'created_at': s.created_at.isoformat() if s.created_at else '',
            'source': s.source,
            'questions_asked': s.questions_asked,
        }
        for feature in features:
            row[feature] = profile.get(feature, '')
        row['custom_data'] = json.dumps(s.custom_data or {}, ensure_ascii=False)
        recs = s.recommendations or []
        for i in range(5):
            rec = recs[i] if i < len(recs) else {}
            row[f'rec{i + 1}_field'] = rec.get('field', '')
            row[f'rec{i + 1}_probability'] = rec.get('probability', '')
        if s.feedback is not None:
            row['chosen_fields'] = '|'.join(s.feedback.chosen_fields or [])
            row['feedback_score'] = s.feedback.feedback_score
        else:
            row['chosen_fields'] = ''
            row['feedback_score'] = ''
        rows.append(row)

    df = pd.DataFrame(rows)
    if df.empty:
        return ''
    return df.to_csv(index=False, encoding='utf-8-sig')


def count_stats(db: Session) -> dict:
    total = db.scalar(select(func.count()).select_from(SurveySession)) or 0
    completed = db.scalar(
        select(func.count())
        .select_from(SurveySession)
        .where(SurveySession.status == 'completed'),
    ) or 0
    in_progress = db.scalar(
        select(func.count())
        .select_from(SurveySession)
        .where(SurveySession.status == 'in_progress'),
    ) or 0
    labeled = db.scalar(select(func.count()).select_from(Feedback)) or 0
    with_profile = db.scalar(
        select(func.count())
        .select_from(SurveySession)
        .where(cast(SurveySession.profile, String) != '{}'),
    ) or 0
    return {
        'total': total,
        'completed': completed,
        'in_progress': in_progress,
        'labeled': labeled,
        'with_profile': with_profile,
    }