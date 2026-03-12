# add_transactions_for_new_users.py

from app.core.database import SessionLocal
from app.models import User, Transaction
from datetime import datetime, timedelta
import random

db = SessionLocal()

# Get the new users
john = db.query(User).filter(User.email == "john@example.com").first()
jane = db.query(User).filter(User.email == "jane@example.com").first()

# Transaction types and counterparties
transaction_types = ["send_money", "pay_bill", "buy_goods", "withdraw"]
counterparties = [
    "254712345678", "254723456789", "254734567890", 
    "254745678901", "254756789012"
]

def add_transactions_for_user(user, num_transactions=15):
    print(f"Adding transactions for {user.email}...")
    for i in range(num_transactions):
        days_ago = random.randint(0, 30)
        tx = Transaction(
            transaction_id=f"TXN{user.id}{1000 + i}",
            amount=random.randint(100, 10000),
            transaction_type=random.choice(transaction_types),
            counterparty=random.choice(counterparties),
            timestamp=datetime.now() - timedelta(days=days_ago),
            user_id=user.id
        )
        db.add(tx)
    print(f"  ✅ Added {num_transactions} transactions")

# Add transactions for John and Jane
if john:
    add_transactions_for_user(john, 12)
if jane:
    add_transactions_for_user(jane, 18)

db.commit()
db.close()

print("\n🎉 Transactions added successfully!")
print("Now John and Jane will see data in their dashboards!")