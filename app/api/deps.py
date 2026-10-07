"""Dependencies админки: текущий администратор."""

from typing import Optional

import jwt as pyjwt
from fastapi import Depends, HTTPException, Request
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import get_settings
from app.database import get_db
from app.models import AdminUser
from app.services.security import decode_access_token


def _extract_token(request: Request) -> Optional[str]:
    auth = request.headers.get('Authorization')
    if auth and auth.lower().startswith('bearer '):
        return auth[7:]
    return request.cookies.get(get_settings().admin_session_cookie)


def get_current_admin(
    request: Request,
    db: Session = Depends(get_db),
) -> AdminUser:
    """Возвращает текущего администратора из cookie или Bearer-токена."""
    token = _extract_token(request)
    if not token:
        raise HTTPException(status_code=401, detail='Требуется авторизация')
    try:
        payload = decode_access_token(token)
    except pyjwt.PyJWTError:
        raise HTTPException(status_code=401, detail='Недействительный токен')

    username = payload.get('sub')
    if not username:
        raise HTTPException(status_code=401, detail='Недействительный токен')

    user = db.scalar(select(AdminUser).where(AdminUser.username == username))
    if user is None or not user.is_active:
        raise HTTPException(status_code=401, detail='Пользователь не найден')
    return user