"""Update main.py in container"""
from pathlib import Path

content = '''"""Фабрика приложения CareerAI Platform.

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
from app.config import get_settings


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(
        title=settings.app_name,
        version='2.0.0',
        debug=settings.debug,
    )

    # Публичный API
    app.include_router(admin_auth_router, prefix='/api/admin')
    app.include_router(admin_catalog_router, prefix='/api/admin')
    app.include_router(admin_questions_router, prefix='/api/admin')
    app.include_router(admin_custom_router, prefix='/api/admin')
    app.include_router(admin_settings_router, prefix='/api/admin')
    app.include_router(admin_recommender_router, prefix='/api/admin')
    app.include_router(admin_media_router, prefix='/api/admin')
    app.include_router(admin_train_router, prefix='/api/admin')
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
        app.mount('/static', StaticFiles(directory=str(static_dir)), name='static')

        @app.get('/', response_class=HTMLResponse)
        def index():
            return HTMLResponse((static_dir / 'index.html').read_text(encoding='utf-8'))

        @app.get('/{path:path}', response_class=HTMLResponse)
        def spa_fallback(path: str):
            """SPA fallback — отдаём index.html для любого роута."""
            if path.startswith('api/') or path.startswith('static/'):
                return HTMLResponse('<h1>Not found</h1>', status_code=404)
            return HTMLResponse((static_dir / 'index.html').read_text(encoding='utf-8'))
    else:
        # Fallback на старый шаблон
        @app.get('/', response_class=HTMLResponse)
        def index():
            html_path = Path('templates/index.html')
            if html_path.exists():
                return HTMLResponse(html_path.read_text(encoding='utf-8'))
            return HTMLResponse('<h1>CareerAI Platform</h1>')

    @app.get('/health')
    def health():
        return {'status': 'ok'}

    return app


app = create_app()
'''

# Write to container via docker exec
import subprocess
result = subprocess.run(
    ['docker', 'exec', 'career-ai', 'python', '-c', 
     f'from pathlib import Path; Path("/app/app/main.py").write_text(r"""{content.replace(chr(34), chr(39))}""", encoding="utf-8")'],
    capture_output=True, text=True
)
print('STDOUT:', result.stdout)
print('STDERR:', result.stderr)
print('RETURN CODE:', result.returncode)
