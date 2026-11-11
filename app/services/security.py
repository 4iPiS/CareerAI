"""Безопасность: хеширование паролей, JWT-токены, rate-limiting."""
from __future__ import annotations

import threading
import time
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

import bcrypt
import jwt

from app.config import get_settings

_RATE_LIMIT_HITS: Dict[str, List[float]] = {}
_RATE_LIMIT_LOCK = threading.Lock()


def hash_password(password: str) -> str:
    """Хеш пароля (bcrypt)."""
    return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')


def verify_password(password: str, password_hash: str) -> bool:
    """Проверка пароля против хеша."""
    try:
        return bcrypt.checkpw(password.encode('utf-8'), password_hash.encode('utf-8'))
    except ValueError:
        return False


def check_rate_limit(key: str, limit: int, window_seconds: int = 60) -> bool:
    """Простой in-memory rate limiter. Возвращает True, если лимит превышен."""
    now = time.monotonic()
    with _RATE_LIMIT_LOCK:
        hits = [t for t in _RATE_LIMIT_HITS.get(key, []) if now - t < window_seconds]
        hits.append(now)
        _RATE_LIMIT_HITS[key] = hits
        return len(hits) > limit


def create_access_token(
    subject: str,
    role: str,
    expires_minutes: Optional[int] = None,
    extra: Optional[Dict[str, Any]] = None,
) -> str:
    """Создание JWT (HS256)."""
    settings = get_settings()
    expire = datetime.now(timezone.utc) + timedelta(
        minutes=expires_minutes or settings.access_token_expire_minutes,
    )
    payload: dict[str, Any] = {'sub': subject, 'role': role, 'exp': expire}
    if extra:
        payload.update(extra)
    return jwt.encode(payload, settings.secret_key, algorithm=settings.jwt_algorithm)


def decode_access_token(token: str) -> dict[str, Any]:
    """Декодирование JWT; при невалидном токене бросает jwt.PyJWTError."""
    settings = get_settings()
    return jwt.decode(token, settings.secret_key, algorithms=[settings.jwt_algorithm])