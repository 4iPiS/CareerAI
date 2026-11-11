"""Debug app creation"""
from app.main import create_app
app = create_app()
print('=== App Routes ===')
for route in app.routes:
    if hasattr(route, 'path'):
        print(f'  {route.path}')
