"""Админ-API: поля анкеты вуза (сбор данных абитуриентов)."""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_current_admin
from app.database import get_db
from app.models import AdminUser, CustomFieldType, CustomFormField
from app.schemas.admin import CustomFieldPayload

router = APIRouter(tags=['admin-custom'])

VALID_TYPES = {t.value for t in CustomFieldType}


def _field_out(f: CustomFormField) -> dict:
    return {
        'id': f.id,
        'code': f.code,
        'label': f.label,
        'field_type': f.field_type.value,
        'options': f.options,
        'required': f.required,
        'sort_order': f.sort_order,
        'is_active': f.is_active,
        'description': f.description or '',
        'examples': f.examples or [],
    }


@router.get('/custom-fields')
def list_fields(
    db: Session = Depends(get_db),
    _: AdminUser = Depends(get_current_admin),
):
    rows = db.scalars(
        select(CustomFormField).order_by(CustomFormField.sort_order, CustomFormField.id),
    ).all()
    return {'fields': [_field_out(f) for f in rows]}


@router.post('/custom-fields')
def create_field(
    payload: CustomFieldPayload,
    db: Session = Depends(get_db),
    _: AdminUser = Depends(get_current_admin),
):
    if payload.field_type not in VALID_TYPES:
        raise HTTPException(status_code=400, detail='Недопустимый тип поля')
    if db.scalar(select(CustomFormField).where(CustomFormField.code == payload.code)):
        raise HTTPException(status_code=400, detail='Поле с таким кодом уже существует')
    field = CustomFormField(
        code=payload.code,
        label=payload.label,
        field_type=CustomFieldType(payload.field_type),
        options=payload.options,
        required=payload.required,
        sort_order=payload.sort_order,
        is_active=payload.is_active,
        description=payload.description or '',
        examples=payload.examples,
    )
    db.add(field)
    db.commit()
    db.refresh(field)
    return _field_out(field)


@router.put('/custom-fields/{field_id}')
def update_field(
    field_id: int,
    payload: CustomFieldPayload,
    db: Session = Depends(get_db),
    _: AdminUser = Depends(get_current_admin),
):
    field = db.get(CustomFormField, field_id)
    if field is None:
        raise HTTPException(status_code=404, detail='Поле не найдено')
    if payload.field_type not in VALID_TYPES:
        raise HTTPException(status_code=400, detail='Недопустимый тип поля')
    dup = db.scalar(
        select(CustomFormField).where(
            CustomFormField.code == payload.code,
            CustomFormField.id != field_id,
        ),
    )
    if dup:
        raise HTTPException(status_code=400, detail='Поле с таким кодом уже существует')
    field.code = payload.code
    field.label = payload.label
    field.field_type = CustomFieldType(payload.field_type)
    field.options = payload.options
    field.required = payload.required
    field.sort_order = payload.sort_order
    field.is_active = payload.is_active
    field.description = payload.description or ''
    field.examples = payload.examples
    db.commit()
    db.refresh(field)
    return _field_out(field)


@router.delete('/custom-fields/{field_id}')
def delete_field(
    field_id: int,
    db: Session = Depends(get_db),
    _: AdminUser = Depends(get_current_admin),
):
    field = db.get(CustomFormField, field_id)
    if field is None:
        raise HTTPException(status_code=404, detail='Поле не найдено')
    db.delete(field)
    db.commit()
    return {'ok': True}