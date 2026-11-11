import os
from sqlalchemy import create_engine, text

url = os.environ.get('DATABASE_URL')
engine = create_engine(url)
try:
    with engine.connect() as conn:
        rows = conn.execute(text('SELECT username, is_active, role FROM admin_users')).fetchall()
        print('Admin users:')
        for r in rows:
            print('  username:', r.username, 'is_active:', r.is_active, 'role:', r.role)
        tables = conn.execute(text("SELECT table_name FROM information_schema.tables WHERE table_schema='public'")).fetchall()
        print('Tables:', [t.table_name for t in tables])
except Exception as e:
    print('Error:', e)
