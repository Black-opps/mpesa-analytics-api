# add_admin_transactions.py

from app.core.database import SessionLocal
from app.models import User, Transaction
from datetime import datetime, timedelta
import random

db = SessionLocal()

admin = db.query(User).filter(User.email == "admin@example.com").first()

if admin:
    print(f"Found admin: ID={admin.id}")
    
    # Check existing transactions
    tx_count = db.query(Transaction).filter(Transaction.user_id == admin.id).count()
    print(f"Admin has {tx_count} transactions")
    
    if tx_count == 0:
        transaction_types = ["send_money", "pay_bill", "buy_goods", "withdraw"]
        counterparties = [
            "254712345678", "254723456789", "254734567890", 
            "254745678901", "254756789012"
        ]
        
        for i in range(20):
            days_ago = random.randint(0, 30)
            tx = Transaction(
                transaction_id=f"ADMIN_TXN{1000 + i}",
                amount=random.randint(500, 10000),
                transaction_type=random.choice(transaction_types),
                counterparty=random.choice(counterparties),
                timestamp=datetime.now() - timedelta(days=days_ago),
                user_id=admin.id
            )
            db.add(tx)
        
        db.commit()
        print(f"✅ Added 20 transactions for admin")
    else:
        print(f"Admin already has {tx_count} transactions")
else:
    print("Admin user not found!")

db.close()