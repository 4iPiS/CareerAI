"""Конфигурация приложения через переменные окружения (pydantic-settings)."""

from functools import lru_cache

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file='.env',
        env_file_encoding='utf-8',
        extra='ignore',
    )

    # --- App ---
    app_name: str = 'CareerAI Platform'
    environment: str = 'development'  # development | production
    debug: bool = False
    host: str = '0.0.0.0'
    port: int = 7777

    # --- Database ---
    database_url: str = (
        'postgresql+psycopg2://careerai:careerai@localhost:5432/careerai'
    )

    # --- Security ---
    secret_key: str = 'change-me-in-production-0123456789'
    jwt_algorithm: str = 'HS256'
    access_token_expire_minutes: int = 480  # 8 часов
    admin_session_cookie: str = 'careerai_admin'
    cookie_secure: bool = False  # True при HTTPS
    rate_limit_login_per_minute: int = 10

    # --- Domain (для HTTPS/nginx) ---
    domain: str = 'localhost'

    # --- Storage ---
    data_dir: str = 'data'
    media_dir: str = 'media'
    models_dir: str = 'models'

    # --- Initial admin (создаётся при первом сиде) ---
    initial_admin_username: str = 'admin'
    initial_admin_password: str = 'admin123'

    @field_validator('debug', mode='before')
    @classmethod
    def _parse_debug(cls, value):
        """Терпим к строковым значениям env DEBUG (например, 'release')."""
        if isinstance(value, str):
            return value.strip().lower() in ('1', 'true', 'yes', 'on', 'debug')
        return value


@lru_cache
def get_settings() -> Settings:
    return Settings()