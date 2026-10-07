"""Фабрика приложения CareerAI Platform.

Запуск: uvicorn app.main:app --host 0.0.0.0 --port 7777
"""

from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, Response
from fastapi.staticfiles import StaticFiles

from app.api.admin_auth import router as admin_auth_router
from app.api.admin_catalog import router as admin_catalog_router
from app.api.admin_custom import router as admin_custom_router
from app.api.admin_media import router as admin_media_router
from app.api.admin_questions import router as admin_questions_router
from app.api.admin_settings import router as admin_settings_router
from app.api.admin_stats import router as admin_stats_router
from app.api.admin_train import router as admin_train_router
from app.api.admin_users import router as admin_users_router
from app.admin_ui import router as admin_ui_router
from app.api.public import router as public_router
from app.config import get_settings


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(
        title=settings.app_name,
        version='2.0.0',
        debug=settings.debug,
    )

    # Админ-UI
    app.include_router(admin_ui_router)

    # Публичный API
    app.include_router(public_router, prefix='/api/v1')

    # Админ-API (JWT)
    app.include_router(admin_auth_router, prefix='/api/admin')
    app.include_router(admin_catalog_router, prefix='/api/admin')
    app.include_router(admin_questions_router, prefix='/api/admin')
    app.include_router(admin_custom_router, prefix='/api/admin')
    app.include_router(admin_settings_router, prefix='/api/admin')
    app.include_router(admin_media_router, prefix='/api/admin')
    app.include_router(admin_train_router, prefix='/api/admin')
    app.include_router(admin_stats_router, prefix='/api/admin')
    app.include_router(admin_users_router, prefix='/api/admin')

    # Кастомный StaticFiles без кэша для админки
    class NoCacheStaticFiles(StaticFiles):
        async def __call__(self, scope, receive, send):
            if scope['type'] == 'http':
                original_send = send
                async def custom_send(message):
                    if message['type'] == 'http.response.start':
                        headers = list(message['headers'])
                        headers.extend([
                            (b'cache-control', b'no-cache, no-store, must-revalidate'),
                            (b'pragma', b'no-cache'),
                            (b'expires', b'0'),
                        ])
                        message['headers'] = headers
                    await original_send(message)
                await super().__call__(scope, receive, custom_send)
            else:
                await super().__call__(scope, receive, send)

    # Медиафайлы вуза + статика админки + публичная статика
    Path(settings.media_dir).mkdir(parents=True, exist_ok=True)
    Path(settings.models_dir).mkdir(parents=True, exist_ok=True)
    admin_static_dir = Path(__file__).parent / 'admin_ui' / 'static'
    app.mount('/admin-static', NoCacheStaticFiles(directory=admin_static_dir), name='admin-static')
    app.mount('/media', StaticFiles(directory=settings.media_dir), name='media')
    # Публичная статика (логотипы, фоновые картинки и т.д.)
    public_static_dir = Path(__file__).parent.parent / 'static'
    if public_static_dir.exists():
        app.mount('/static', StaticFiles(directory=str(public_static_dir)), name='static')

    @app.get('/health')
    def health():
        return {'status': 'ok'}

    @app.get('/', response_class=HTMLResponse)
    def index():
        """Публичный веб-опросник (подключается к /api/v1)."""
        html_path = Path('templates/index.html')
        if html_path.exists():
            return HTMLResponse(html_path.read_text(encoding='utf-8'))
        return HTMLResponse('<h1>CareerAI Platform</h1>')

    return app


app = create_app()