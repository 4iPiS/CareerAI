"""Публичный API v1: опросник, рекомендации, анкета, обратная связь."""

import re
import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import CustomFormField, Direction, SurveySession, UniversitySettings
from app.schemas.public import (
    AnswerRequest,
    AnswerResponse,
    FeedbackRequest,
    QuestionPayload,
    StartResponse,
    SurveyDataRequest,
)
from app.services.questionnaire import SurveyEngine
from app.services.responses import finalize_session, get_session_by_uuid, save_feedback

router = APIRouter(tags=['public'])


def _get_session(db: Session, session_uuid: str) -> SurveySession:
    session = get_session_by_uuid(db, session_uuid)
    if session is None:
        raise HTTPException(status_code=404, detail='Сессия не найдена')
    return session


def _consent_text(db: Session) -> str:
    s = db.scalar(select(UniversitySettings).order_by(UniversitySettings.id).limit(1))
    return s.consent_text if s else ''


@router.post('/start', response_model=StartResponse)
def start(db: Session = Depends(get_db)):
    engine = SurveyEngine(db)
    state = engine.start_state()
    session_uuid = uuid.uuid4().hex[:32]
    session = SurveySession(
        session_uuid=session_uuid,
        stage='screening',
        status='in_progress',
        state=state,
        source='web',
    )
    db.add(session)
    db.commit()
    db.refresh(session)

    payload = engine.first_payload(state)
    session.state = state
    db.add(session)
    db.commit()

    if payload.get('is_custom'):
        payload['consent_text'] = _consent_text(db)

    return {'session_id': session_uuid, 'question': QuestionPayload(**payload)}


@router.post('/answer', response_model=AnswerResponse)
def answer(req: AnswerRequest, db: Session = Depends(get_db)):
    session = _get_session(db, req.session_id)
    if session.status == 'completed':
        raise HTTPException(status_code=400, detail='Опрос уже завершён')

    engine = SurveyEngine(db)
    state = dict(session.state or {})
    try:
        next_payload, new_state = engine.submit_answer(state, req.question_id, req.answer)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))

    session.state = new_state
    session.stage = new_state.get('stage', session.stage)
    session.questions_asked = int(new_state.get('questions_asked', 0) or 0)
    # Сохраняем промежуточный профиль — даже брошенные опросы не теряются
    session.profile = engine.build_profile(new_state)
    db.add(session)
    db.commit()

    if next_payload is None:
        result = finalize_session(db, session)
        result.update({'done': True, 'session_id': req.session_id})
        return AnswerResponse(**result)

    if next_payload.get('is_custom'):
        next_payload['consent_text'] = _consent_text(db)

    return AnswerResponse(
        done=False,
        session_id=req.session_id,
        question=QuestionPayload(**next_payload),
    )


def _validate_custom_data(db: Session, data: dict) -> None:
    """Проверяет обязательные поля анкеты и корректность email/телефона."""
    fields = db.scalars(
        select(CustomFormField)
        .where(CustomFormField.is_active.is_(True))
        .order_by(CustomFormField.sort_order),
    ).all()
    for f in fields:
        value = str(data.get(f.code, '') or '').strip()
        if f.required and not value:
            raise HTTPException(
                status_code=400,
                detail=f'Поле «{f.label}» обязательно для заполнения',
            )
        if not value:
            continue
        if f.field_type == 'email' and not re.match(
            r'^[^\s@]+@[^\s@]+\.[^\s@]{2,}$', value,
        ):
            raise HTTPException(
                status_code=400,
                detail=f'Укажите корректный email в поле «{f.label}»',
            )
        if f.field_type == 'phone':
            digits = re.sub(r'\D', '', value)
            if len(digits) < 10 or len(digits) > 15:
                raise HTTPException(
                    status_code=400,
                    detail=f'Укажите корректный телефон в поле «{f.label}» '
                           f'(например +7 900 000-00-00)',
                )


@router.post('/survey-data', response_model=AnswerResponse)
def survey_data(req: SurveyDataRequest, db: Session = Depends(get_db)):
    session = _get_session(db, req.session_id)
    if session.status == 'completed':
        raise HTTPException(status_code=400, detail='Опрос уже завершён')
    if not req.consent:
        raise HTTPException(
            status_code=400,
            detail='Необходимо согласие на обработку персональных данных',
        )

    _validate_custom_data(db, req.data)
    session.custom_data = req.data
    state = dict(session.state or {})
    engine = SurveyEngine(db)

    if state.get('stage') == 'custom':
        # Стартовая анкета вуза → продолжаем опрос
        next_payload = engine.after_custom_payload(state)
        session.state = state
        session.stage = state.get('stage', session.stage)
        db.add(session)
        db.commit()
        return AnswerResponse(
            done=False,
            session_id=req.session_id,
            question=QuestionPayload(**next_payload),
        )

    # Финальная анкета (позиция end) → завершаем и считаем рекомендации
    result = finalize_session(db, session, custom_data=req.data)
    result.update({'done': True, 'session_id': req.session_id})
    return AnswerResponse(**result)


@router.post('/feedback')
def feedback(req: FeedbackRequest, db: Session = Depends(get_db)):
    try:
        save_feedback(db, req.session_id, req.chosen_fields, req.feedback_score)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    return {
        'ok': True,
        'message': 'Спасибо! Ваши ответы сохранены для улучшения сервиса.',
    }


@router.get('/directions')
def directions(db: Session = Depends(get_db)):
    rows = db.scalars(
        select(Direction)
        .where(Direction.is_active)
        .order_by(Direction.sort_order),
    ).all()
    return {
        'directions': [
            {
                'name': d.name,
                'code': d.fgos_code,
                'description': d.description,
            }
            for d in rows
        ],
    }


@router.get('/settings')
def settings(db: Session = Depends(get_db)):
    s = db.scalar(select(UniversitySettings).order_by(UniversitySettings.id).limit(1))
    if s is None:
        return {'settings': {}}
    return {
        'settings': {
            'university_name': s.university_name,
            'tagline': s.tagline,
            'university_url': s.university_url,
            'abitur_url': s.abitur_url,
            'logo_path': s.logo_path,
            'hero_image_path': s.hero_image_path,
            'presenter_video_path': s.presenter_video_path,
            'primary_color': s.primary_color,
            'consent_text': s.consent_text,
            'custom_form_position': s.custom_form_position,
        },
    }