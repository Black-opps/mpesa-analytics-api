# list_users.py

from app.core.database import SessionLocal
from app.models import User

db = SessionLocal()

print("=" * 60)
print("📊 CURRENT USERS IN DATABASE")
print("=" * 60)

users = db.query(User).all()
for user in users:
    print(f"ID: {user.id}")
    print(f"Email: {user.email}")
    print(f"Role: {user.role}")
    print(f"Active: {user.is_active}")
    print(f"Created: {user.created_at}")
    print("-" * 40)

print(f"\n✅ Total users: {len(users)}")
db.close()