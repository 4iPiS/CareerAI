"""Админ-API: CRUD направлений и признаков."""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.api.deps import get_current_admin
from app.database import get_db
from app.models import AdminUser, Direction, Feature, FeatureType
from app.schemas.admin import DirectionPayload, FeaturePayload

router = APIRouter(tags=['admin-catalog'])


def _direction_out(d: Direction) -> dict:
    return {
        'id': d.id,
        'name': d.name,
        'fgos_code': d.fgos_code,
        'description': d.description,
        'key_skills_text': d.key_skills_text,
        'category': d.category,
        'avg_salary': d.avg_salary,
        'employment_rate': d.employment_rate,
        'study_years': d.study_years,
        'ege_typical': d.ege_typical,
        'image_path': d.image_path,
        'sort_order': d.sort_order,
        'is_active': d.is_active,
        'skill_codes': sorted(f.code for f in d.features),
    }


def _feature_out(f: Feature) -> dict:
    return {
        'id': f.id,
        'code': f.code,
        'label': f.label,
        'data_type': f.data_type.value,
        'default_value': f.default_value,
        'is_common': f.is_common,
        'sort_order': f.sort_order,
        'is_active': f.is_active,
    }


def _set_direction_skills(db: Session, direction: Direction, skill_codes: list[str]) -> None:
    if not skill_codes:
        direction.features = []
        return
    features = db.scalars(
        select(Feature).where(Feature.code.in_(skill_codes)),
    ).all()
    by_code = {f.code: f for f in features}
    missing = [c for c in skill_codes if c not in by_code]
    if missing:
        raise HTTPException(status_code=400, detail=f'Нет признаков: {", ".join(missing)}')
    direction.features = list(by_code.values())


# ==== Направления ====

@router.get('/directions')
def list_directions(
    db: Session = Depends(get_db),
    _: AdminUser = Depends(get_current_admin),
):
    rows = db.scalars(
        select(Direction)
        .options(selectinload(Direction.features))
        .order_by(Direction.sort_order, Direction.id),
    ).all()
    return {'directions': [_direction_out(d) for d in rows]}


@router.post('/directions')
def create_direction(
    payload: DirectionPayload,
    db: Session = Depends(get_db),
    _: AdminUser = Depends(get_current_admin),
):
    if db.scalar(select(Direction).where(Direction.name == payload.name)):
        raise HTTPException(status_code=400, detail='Направление с таким названием уже существует')
    direction = Direction(**payload.model_dump(exclude={'skill_codes'}))
    db.add(direction)
    db.flush()
    _set_direction_skills(db, direction, payload.skill_codes)
    db.commit()
    db.refresh(direction)
    return _direction_out(direction)


@router.put('/directions/{direction_id}')
def update_direction(
    direction_id: int,
    payload: DirectionPayload,
    db: Session = Depends(get_db),
    _: AdminUser = Depends(get_current_admin),
):
    direction = db.get(Direction, direction_id)
    if direction is None:
        raise HTTPException(status_code=404, detail='Направление не найдено')
    dup = db.scalar(
        select(Direction).where(
            Direction.name == payload.name,
            Direction.id != direction_id,
        ),
    )
    if dup:
        raise HTTPException(status_code=400, detail='Направление с таким названием уже существует')
    for field, value in payload.model_dump(exclude={'skill_codes'}).items():
        setattr(direction, field, value)
    _set_direction_skills(db, direction, payload.skill_codes)
    db.commit()
    db.refresh(direction)
    return _direction_out(direction)


@router.delete('/directions/{direction_id}')
def delete_direction(
    direction_id: int,
    db: Session = Depends(get_db),
    _: AdminUser = Depends(get_current_admin),
):
    direction = db.get(Direction, direction_id)
    if direction is None:
        raise HTTPException(status_code=404, detail='Направление не найдено')
    db.delete(direction)
    db.commit()
    return {'ok': True}


# ==== Признаки ====

@router.get('/features')
def list_features(
    db: Session = Depends(get_db),
    _: AdminUser = Depends(get_current_admin),
):
    rows = db.scalars(select(Feature).order_by(Feature.sort_order, Feature.id)).all()
    return {'features': [_feature_out(f) for f in rows]}


@router.post('/features')
def create_feature(
    payload: FeaturePayload,
    db: Session = Depends(get_db),
    _: AdminUser = Depends(get_current_admin),
):
    if db.scalar(select(Feature).where(Feature.code == payload.code)):
        raise HTTPException(status_code=400, detail='Признак с таким кодом уже существует')
    try:
        data_type = FeatureType(payload.data_type)
    except ValueError:
        raise HTTPException(status_code=400, detail='Недопустимый тип признака')
    feature = Feature(**payload.model_dump(exclude={'data_type'}), data_type=data_type)
    db.add(feature)
    db.commit()
    db.refresh(feature)
    return _feature_out(feature)


@router.put('/features/{feature_id}')
def update_feature(
    feature_id: int,
    payload: FeaturePayload,
    db: Session = Depends(get_db),
    _: AdminUser = Depends(get_current_admin),
):
    feature = db.get(Feature, feature_id)
    if feature is None:
        raise HTTPException(status_code=404, detail='Признак не найден')
    dup = db.scalar(
        select(Feature).where(Feature.code == payload.code, Feature.id != feature_id),
    )
    if dup:
        raise HTTPException(status_code=400, detail='Признак с таким кодом уже существует')
    try:
        data_type = FeatureType(payload.data_type)
    except ValueError:
        raise HTTPException(status_code=400, detail='Недопустимый тип признака')
    for field, value in payload.model_dump(exclude={'data_type'}).items():
        setattr(feature, field, value)
    feature.data_type = data_type
    db.commit()
    db.refresh(feature)
    return _feature_out(feature)


@router.delete('/features/{feature_id}')
def delete_feature(
    feature_id: int,
    db: Session = Depends(get_db),
    _: AdminUser = Depends(get_current_admin),
):
    feature = db.get(Feature, feature_id)
    if feature is None:
        raise HTTPException(status_code=404, detail='Признак не найден')
    db.delete(feature)
    db.commit()
    return {'ok': True}