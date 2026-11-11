"""Админ-API: группы вопросов и вопросы опросника."""

from __future__ import annotations
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.api.deps import get_current_admin
from app.database import get_db
from app.models import (
    AdminUser,
    Feature,
    Question,
    QuestionGroup,
    QuestionGroupCode,
    QuestionType,
)
from app.schemas.admin import QuestionPayload

router = APIRouter(tags=['admin-questions'])

VALID_GROUPS = {g.value for g in QuestionGroupCode}
VALID_TYPES = {t.value for t in QuestionType}


def _question_out(q: Question) -> dict:
    return {
        'id': q.id,
        'group_code': q.group.code.value,
        'feature_code': q.feature.code if q.feature else None,
        'text': q.text,
        'image_url': q.image_url,
        'question_type': q.question_type.value,
        'options': q.options,
        'threshold': q.threshold,
        'level': q.level,
        'activation_condition': q.activation_condition,
        'sort_order': q.sort_order,
        'is_active': q.is_active,
    }


def _resolve_group(db: Session, group_code: str) -> QuestionGroup:
    if group_code not in VALID_GROUPS:
        raise HTTPException(status_code=400, detail=f'Недопустимая группа: {group_code}')
    group = db.scalar(
        select(QuestionGroup).where(QuestionGroup.code == QuestionGroupCode(group_code)),
    )
    if group is None:
        raise HTTPException(status_code=404, detail='Группа не найдена')
    return group


@router.get('/question-groups')
def list_groups(
    db: Session = Depends(get_db),
    _: AdminUser = Depends(get_current_admin),
):
    rows = db.scalars(select(QuestionGroup).order_by(QuestionGroup.sort_order)).all()
    return {
        'groups': [
            {
                'code': g.code.value,
                'title': g.title,
                'description': g.description,
                'sort_order': g.sort_order,
                'is_active': g.is_active,
            }
            for g in rows
        ],
    }


@router.get('/questions')
def list_questions(
    group: str | None = None,
    db: Session = Depends(get_db),
    _: AdminUser = Depends(get_current_admin),
):
    stmt = (
        select(Question)
        .options(selectinload(Question.group), selectinload(Question.feature))
        .order_by(Question.group_id, Question.sort_order, Question.level, Question.id)
    )
    if group:
        stmt = stmt.join(QuestionGroup).where(QuestionGroup.code == QuestionGroupCode(group))
    rows = db.scalars(stmt).all()
    return {'questions': [_question_out(q) for q in rows]}


@router.patch('/questions/{question_id}/toggle-active')
def toggle_question_active(
    question_id: int,
    payload: dict,
    db: Session = Depends(get_db),
    _: AdminUser = Depends(get_current_admin),
):
    question = db.get(Question, question_id)
    if question is None:
        raise HTTPException(status_code=404, detail='Вопрос не найден')
    question.is_active = bool(payload.get('is_active', False))
    db.commit()
    return _question_out(question)


@router.post('/questions')
def create_question(
    payload: QuestionPayload,
    db: Session = Depends(get_db),
    _: AdminUser = Depends(get_current_admin),
):
    if payload.question_type not in VALID_TYPES:
        raise HTTPException(status_code=400, detail='Недопустимый тип вопроса')
    group = _resolve_group(db, payload.group_code)

    feature = None
    if payload.feature_code:
        feature = db.scalar(select(Feature).where(Feature.code == payload.feature_code))
        if feature is None:
            raise HTTPException(status_code=400, detail='Признак не найден')

    question = Question(
        group_id=group.id,
        feature_id=feature.id if feature else None,
        text=payload.text,
        image_url=payload.image_url,
        question_type=QuestionType(payload.question_type),
        options=payload.options,
        threshold=payload.threshold,
        level=payload.level,
        activation_condition=payload.activation_condition,
        sort_order=payload.sort_order,
        is_active=payload.is_active,
    )
    db.add(question)
    db.commit()
    db.refresh(question)
    return _question_out(question)


@router.put('/questions/{question_id}')
def update_question(
    question_id: int,
    payload: QuestionPayload,
    db: Session = Depends(get_db),
    _: AdminUser = Depends(get_current_admin),
):
    question = db.get(Question, question_id)
    if question is None:
        raise HTTPException(status_code=404, detail='Вопрос не найден')
    if payload.question_type not in VALID_TYPES:
        raise HTTPException(status_code=400, detail='Недопустимый тип вопроса')
    group = _resolve_group(db, payload.group_code)

    feature = None
    if payload.feature_code:
        feature = db.scalar(select(Feature).where(Feature.code == payload.feature_code))
        if feature is None:
            raise HTTPException(status_code=400, detail='Признак не найден')

    question.group_id = group.id
    question.feature_id = feature.id if feature else None
    question.text = payload.text
    question.image_url = payload.image_url
    question.question_type = QuestionType(payload.question_type)
    question.options = payload.options
    question.threshold = payload.threshold
    question.level = payload.level
    question.activation_condition = payload.activation_condition
    question.sort_order = payload.sort_order
    question.is_active = payload.is_active
    db.commit()
    db.refresh(question)
    return _question_out(question)


@router.delete('/questions/{question_id}')
def delete_question(
    question_id: int,
    db: Session = Depends(get_db),
    _: AdminUser = Depends(get_current_admin),
):
    question = db.get(Question, question_id)
    if question is None:
        raise HTTPException(status_code=404, detail='Вопрос не найден')
    db.delete(question)
    db.commit()
    return {'ok': True}