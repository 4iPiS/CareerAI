"""Fix database: add missing columns and stamp alembic version."""
from app.database import engine
from sqlalchemy import text

with engine.begin() as conn:
    conn.execute(text(
        "ALTER TABLE university_settings ADD COLUMN IF NOT EXISTS contact_email VARCHAR(255) NOT NULL DEFAULT ''"
    ))
    conn.execute(text(
        "ALTER TABLE university_settings ADD COLUMN IF NOT EXISTS support_phone VARCHAR(100) NOT NULL DEFAULT ''"
    ))
    conn.execute(text(
        "CREATE TABLE IF NOT EXISTS alembic_version "
        "(version_num VARCHAR(256) NOT NULL, "
        "CONSTRAINT alembic_version_pkc PRIMARY KEY (version_num))"
    ))
    conn.execute(text(
        "INSERT INTO alembic_version (version_num) VALUES ('005_add_university_contact_fields') "
        "ON CONFLICT (version_num) DO NOTHING"
    ))

print("Done: columns added and alembic stamped")

# Verify
from sqlalchemy import inspect
inspector = inspect(engine)
cols = [c['name'] for c in inspector.get_columns('university_settings')]
print('Columns:', cols)
print('has contact_email:', 'contact_email' in cols)
print('has support_phone:', 'support_phone' in cols)
