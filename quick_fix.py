# quick_fix.py

from app.core.database import SessionLocal, engine, Base
from app.models import User, Transaction
from app.core.security import get_password_hash
from datetime import datetime, timedelta
import random

print("🔧 Running quick database fix...")

# Create tables if they don't exist
Base.metadata.create_all(bind=engine)

# Create session
db = SessionLocal()

try:
    # Check if we have any users
    users = db.query(User).all()
    print(f"Found {len(users)} users")
    
    if len(users) == 0:
        # Create test user
        test_user = User(
            email="test@example.com",
            hashed_password=get_password_hash("password123"),
            role="user"
        )
        db.add(test_user)
        db.commit()
        db.refresh(test_user)
        print("Created test user")
    else:
        test_user = users[0]
        print(f"Using existing user: {test_user.email}")
    
    # Check if we have any transactions
    transactions = db.query(Transaction).filter(Transaction.user_id == test_user.id).count()
    print(f"User has {transactions} transactions")
    
    if transactions == 0:
        # Create sample transactions
        transaction_types = ["send_money", "pay_bill", "buy_goods", "withdraw"]
        counterparties = [
            "254712345678", "254723456789", "254734567890", 
            "254745678901", "254756789012", "254767890123"
        ]

        new_transactions = []
        for i in range(1, 21):
            amount = random.randint(100, 5000)
            days_ago = random.randint(0, 30)
            
            tx = Transaction(
                transaction_id=f"TXN{10000 + i}",
                amount=amount,
                transaction_type=random.choice(transaction_types),
                counterparty=random.choice(counterparties),
                timestamp=datetime.now() - timedelta(days=days_ago),
                user_id=test_user.id
            )
            new_transactions.append(tx)

        db.add_all(new_transactions)
        db.commit()
        print(f"✅ Added {len(new_transactions)} transactions")
    
    # Test database connection
    db.execute("SELECT 1")
    print("✅ Database connection successful")

except Exception as e:
    print(f"❌ Error: {e}")
    db.rollback()
finally:
    db.close()