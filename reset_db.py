# reset_db.py

from app.core.database import SessionLocal, engine, Base
from app.models import User, Transaction
from app.core.security import get_password_hash
from datetime import datetime, timedelta
import random
import os

print("🔄 Resetting database...")

# Delete old database file (optional - be careful!)
db_path = "mpesa.db"
if os.path.exists(db_path):
    backup_name = f"mpesa_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.db"
    os.rename(db_path, backup_name)
    print(f"📦 Backed up old database to {backup_name}")

# Create new database
print("📦 Creating new database...")
Base.metadata.create_all(bind=engine)

# Create session
db = SessionLocal()

try:
    print("👤 Creating test user...")
    # Create test user
    test_user = User(
        email="test@example.com",
        hashed_password=get_password_hash("password123"),
        role="user"
    )
    db.add(test_user)
    db.commit()
    db.refresh(test_user)
    print(f"   ✅ User created with ID: {test_user.id}")

    # Create sample transactions
    print("💰 Creating sample transactions...")
    
    transaction_types = ["send_money", "pay_bill", "buy_goods", "withdraw"]
    counterparties = [
        "254712345678", "254723456789", "254734567890", 
        "254745678901", "254756789012", "254767890123"
    ]

    transactions = []
    total_amount = 0
    
    for i in range(1, 31):  # Create 30 transactions
        amount = random.randint(100, 10000)
        total_amount += amount
        days_ago = random.randint(0, 45)
        
        tx = Transaction(
            transaction_id=f"TXN{10000 + i}",
            amount=amount,
            transaction_type=random.choice(transaction_types),
            counterparty=random.choice(counterparties),
            timestamp=datetime.now() - timedelta(days=days_ago),
            user_id=test_user.id
        )
        transactions.append(tx)

    db.add_all(transactions)
    db.commit()
    
    print(f"   ✅ Created {len(transactions)} transactions")
    print(f"   💰 Total volume: KES {total_amount:,}")
    
    # Create a second user with some transactions
    print("\n👤 Creating second test user...")
    user2 = User(
        email="demo@example.com",
        hashed_password=get_password_hash("demo123"),
        role="user"
    )
    db.add(user2)
    db.commit()
    db.refresh(user2)
    
    # Add a few transactions for second user
    tx2 = Transaction(
        transaction_id="TXN99999",
        amount=5000,
        transaction_type="send_money",
        counterparty="254700000000",
        timestamp=datetime.now() - timedelta(days=2),
        user_id=user2.id
    )
    db.add(tx2)
    db.commit()
    print(f"   ✅ User 2 created with 1 transaction")

    # Verify data
    print("\n📊 Database Summary:")
    print(f"   - Total users: {db.query(User).count()}")
    print(f"   - Total transactions: {db.query(Transaction).count()}")
    
    # Test analytics for user1
    user1_txs = db.query(Transaction).filter(Transaction.user_id == test_user.id).all()
    user1_total = sum(tx.amount for tx in user1_txs)
    print(f"   - User 1 transactions: {len(user1_txs)}")
    print(f"   - User 1 total volume: KES {user1_total:,}")

except Exception as e:
    print(f"❌ Error: {e}")
    db.rollback()
finally:
    db.close()

print("\n✅ Database reset complete!")
print("📝 You can now login with:")
print("   Email: test@example.com")
print("   Password: password123")