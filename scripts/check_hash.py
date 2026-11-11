"""Check admin password hash"""
from app.database import SessionLocal
from app.models import AdminUser
from app.services.security import verify_password, hash_password

db = SessionLocal()
user = db.query(AdminUser).first()
print(f'User: {user.username}')
print(f'Password hash in DB: {user.password_hash}')
print(f'Expected hash for admin123: {hash_password("admin123")}')
print(f'Verify admin123: {verify_password("admin123", user.password_hash)}')
print(f'Verify admin: {verify_password("admin", user.password_hash)}')
print(f'Verify password123: {verify_password("password123", user.password_hash)}')
print(f'Verify CareerAI123: {verify_password("CareerAI123", user.password_hash)}')
db.close()
