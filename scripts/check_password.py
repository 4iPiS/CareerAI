"""Check admin password"""
from app.database import SessionLocal
from app.models import AdminUser
from app.services.security import verify_password

db = SessionLocal()
user = db.query(AdminUser).first()
print(f'User: {user.username}')
print(f'Password hash: {user.password_hash}')
print(f'Verify admin: {verify_password("admin", user.password_hash)}')
print(f'Verify password123: {verify_password("password123", user.password_hash)}')
print(f'Verify Admin123: {verify_password("Admin123", user.password_hash)}')
db.close()
