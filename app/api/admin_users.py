"""Админ-API: управление учётными записями."""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_current_admin
from app.database import get_db
from app.models import AdminUser
from app.schemas.admin import UserCreate, UserDelete, UserUpdate
from app.services.security import hash_password, verify_password

router = APIRouter(tags=['admin-users'])


def _user_out(u: AdminUser) -> dict:
    return {
        'id': u.id,
        'username': u.username,
        'role': u.role.value,
        'is_active': u.is_active,
        'created_at': u.created_at.isoformat() if u.created_at else None,
    }


@router.get('/users')
def list_users(
    db: Session = Depends(get_db),
    _: AdminUser = Depends(get_current_admin),
):
    rows = db.scalars(select(AdminUser).order_by(AdminUser.id)).all()
    return {'users': [_user_out(u) for u in rows]}


@router.post('/users')
def create_user(
    payload: UserCreate,
    db: Session = Depends(get_db),
    _: AdminUser = Depends(get_current_admin),
):
    if db.scalar(select(AdminUser).where(AdminUser.username == payload.username)):
        raise HTTPException(status_code=400, detail='Пользователь уже существует')
    user = AdminUser(
        username=payload.username,
        password_hash=hash_password(payload.password),
        is_active=True,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return _user_out(user)


@router.put('/users/{user_id}')
def update_user(
    user_id: int,
    payload: UserUpdate,
    db: Session = Depends(get_db),
    _: AdminUser = Depends(get_current_admin),
):
    user = db.get(AdminUser, user_id)
    if user is None:
        raise HTTPException(status_code=404, detail='Пользователь не найден')
    if payload.password:
        if not payload.current_password or not verify_password(
            payload.current_password,
            user.password_hash,
        ):
            raise HTTPException(
                status_code=400,
                detail='Для смены пароля укажите текущий пароль',
            )
        user.password_hash = hash_password(payload.password)
    if payload.is_active is not None:
        user.is_active = payload.is_active
    db.commit()
    db.refresh(user)
    return _user_out(user)


@router.delete('/users/{user_id}')
def delete_user(
    user_id: int,
    payload: UserDelete,
    db: Session = Depends(get_db),
    current: AdminUser = Depends(get_current_admin),
):
    user = db.get(AdminUser, user_id)
    if user is None:
        raise HTTPException(status_code=404, detail='Пользователь не найден')
    if user.id == current.id:
        raise HTTPException(status_code=400, detail='Нельзя удалить самого себя')
    # Проверка: не последний ли это админ
    all_admins = db.scalars(select(AdminUser)).all()
    if len(all_admins) <= 1:
        raise HTTPException(status_code=400, detail='Нельзя удалить последнего администратора')
    # Требовать пароль при удалении
    if not verify_password(payload.password, current.password_hash):
        raise HTTPException(status_code=400, detail='Неверный пароль')
    db.delete(user)
    db.commit()
    return {'ok': True}
