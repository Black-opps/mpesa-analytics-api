from src.core.database import SessionLocal
from src.models import Transaction, User
from datetime import datetime, timedelta
import random

db = SessionLocal()

# Get the admin user
admin = db.query(User).filter(User.email == "admin@example.com").first()
if not admin:
    print("Admin user not found!")
    exit()

# Add sample transactions
transactions = [
    Transaction(
        transaction_id=f"TXN{random.randint(100000, 999999)}",
        amount=1500.00,
        transaction_type="send_money",
        counterparty="254712345678",
        timestamp=datetime.now() - timedelta(days=5),
        user_id=admin.id
    ),
    Transaction(
        transaction_id=f"TXN{random.randint(100000, 999999)}",
        amount=3200.50,
        transaction_type="pay_bill",
        counterparty="123456",
        timestamp=datetime.now() - timedelta(days=3),
        user_id=admin.id
    ),
    Transaction(
        transaction_id=f"TXN{random.randint(100000, 999999)}",
        amount=750.25,
        transaction_type="buy_goods",
        counterparty="789012",
        timestamp=datetime.now() - timedelta(days=1),
        user_id=admin.id
    ),
    Transaction(
        transaction_id=f"TXN{random.randint(100000, 999999)}",
        amount=5000.00,
        transaction_type="send_money",
        counterparty="254798765432",
        timestamp=datetime.now(),
        user_id=admin.id
    ),
]

for tx in transactions:
    db.add(tx)

db.commit()
print(f"✅ Added {len(transactions)} test transactions for user {admin.email}")

# Verify
count = db.query(Transaction).filter(Transaction.user_id == admin.id).count()
print(f"Total transactions for user: {count}")

db.close()
