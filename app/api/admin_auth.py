"""Админ-аутентификация: вход, выход, текущий пользователь."""

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_current_admin
from app.config import get_settings
from app.database import get_db
from app.models import AdminUser
from app.schemas.admin import LoginRequest
from app.services.security import (
    check_rate_limit,
    create_access_token,
    verify_password,
)

router = APIRouter(prefix='/auth', tags=['admin-auth'])


@router.post('/login')
def login(
    req: LoginRequest,
    response: Response,
    request: Request,
    db: Session = Depends(get_db),
):
    settings = get_settings()
    ip = request.client.host if request.client else 'unknown'
    if check_rate_limit(f'login:{ip}', settings.rate_limit_login_per_minute):
        raise HTTPException(status_code=429, detail='Слишком много попыток входа')

    user = db.scalar(select(AdminUser).where(AdminUser.username == req.username))
    if user is None or not verify_password(req.password, user.password_hash):
        raise HTTPException(status_code=401, detail='Неверный логин или пароль')
    if not user.is_active:
        raise HTTPException(status_code=403, detail='Учётная запись отключена')

    token = create_access_token(user.username, user.role.value)
    response.set_cookie(
        key=settings.admin_session_cookie,
        value=token,
        httponly=True,
        samesite='lax',
        secure=settings.cookie_secure,
        max_age=settings.access_token_expire_minutes * 60,
    )
    return {'ok': True, 'username': user.username, 'role': user.role.value, 'token': token}


@router.post('/logout')
def logout(response: Response):
    settings = get_settings()
    response.delete_cookie(key=settings.admin_session_cookie)
    return {'ok': True}


@router.get('/me')
def me(user: AdminUser = Depends(get_current_admin)):
    return {'username': user.username, 'role': user.role.value}