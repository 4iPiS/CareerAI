"""Check app routes"""
from app.main import app
print('=== All Routes ===')
for route in app.routes:
    if hasattr(route, 'path'):
        print(f'  {route.path}')
