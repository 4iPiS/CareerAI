"""Фабрика приложения CareerAI Platform.

Запуск: uvicorn app.main:app --host 0.0.0.0 --port 7777
"""

from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import HTMLResponse, Response
from fastapi.staticfiles import StaticFiles

from app.api.admin_auth import router as admin_auth_router
from app.api.admin_catalog import router as admin_catalog_router
from app.api.admin_custom import router as admin_custom_router
from app.api.admin_media import router as admin_media_router
from app.api.admin_questions import router as admin_questions_router
from app.api.admin_recommender import router as admin_recommender_router
from app.api.admin_settings import router as admin_settings_router
from app.api.admin_stats import router as admin_stats_router
from app.api.admin_train import router as admin_train_router
from app.api.admin_users import router as admin_users_router
from app.api.public import router as public_router
from app.config import get_settings


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(
        title=settings.app_name,
        version='2.0.0',
        debug=settings.debug,
    )

    # Public API
    app.include_router(public_router, prefix='/api/v1')

    # Admin API
    app.include_router(admin_auth_router, prefix='/api/admin')
    app.include_router(admin_catalog_router, prefix='/api/admin')
    app.include_router(admin_questions_router, prefix='/api/admin')
    app.include_router(admin_custom_router, prefix='/api/admin')
    app.include_router(admin_settings_router, prefix='/api/admin')
    app.include_router(admin_recommender_router, prefix='/api/admin')
    app.include_router(admin_media_router, prefix='/api/admin')
    app.include_router(admin_train_router, prefix='/api/admin')
    app.include_router(admin_stats_router, prefix='/api/admin')
    app.include_router(admin_users_router, prefix='/api/admin')

    # Кастомный StaticFiles без кэша
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

    # Медиафайлы вуза
    Path(settings.media_dir).mkdir(parents=True, exist_ok=True)
    Path(settings.models_dir).mkdir(parents=True, exist_ok=True)
    app.mount('/media', StaticFiles(directory=settings.media_dir), name='media')

    # React SPA — статика из /app/static
    static_dir = Path('/app/static')
    if static_dir.exists():
        app.mount('/static-react', NoCacheStaticFiles(directory=str(static_dir)), name='static-react')

        @app.get('/health')
        def health():
            return {'status': 'ok'}

        @app.get('/index.html', response_class=HTMLResponse)
        def index_html():
            html = (static_dir / 'index.html').read_text(encoding='utf-8')
            import time
            v = str(int(time.time()))
            html = html.replace('.js"', f'.js?v={v}"')
            html = html.replace('.css"', f'.css?v={v}"')
            return HTMLResponse(html)

        @app.get('/', response_class=HTMLResponse)
        def index():
            return index_html()

        @app.get('/{path:path}', response_class=HTMLResponse)
        def spa_fallback(path: str):
            """SPA fallback — отдаём index.html для любого роута."""
            if path.startswith('api/') or path.startswith('static-react/'):
                return HTMLResponse('<h1>Not found</h1>', status_code=404)
            return index_html()

    # Admin UI (vanilla JS SPA) — полный функционал
    admin_ui_dir = Path(__file__).parent / 'admin_ui'
    if admin_ui_dir.exists() and not static_dir.exists():
        app.mount('/admin-static', StaticFiles(directory=str(admin_ui_dir / 'static')), name='admin-static')

        @app.get('/admin', response_class=HTMLResponse)
        @app.get('/admin/{path:path}', response_class=HTMLResponse)
        def admin_spa(path: str = ''):
            return HTMLResponse((admin_ui_dir / 'templates' / 'admin.html').read_text(encoding='utf-8'))

    return app


app = create_app()
