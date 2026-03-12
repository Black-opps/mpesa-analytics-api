# check_db.py

from app.core.database import SessionLocal
from app.models import User, Transaction
from sqlalchemy import text

db = SessionLocal()

try:
    # Check if tables exist
    print("📊 Database Inspection Report")
    print("=" * 50)
    
    # Check Users
    users = db.query(User).all()
    print(f"\n👥 Users found: {len(users)}")
    for user in users:
        print(f"   - ID: {user.id}, Email: {user.email}, Created: {user.created_at}")
    
    # Check Transactions
    transactions = db.query(Transaction).all()
    print(f"\n💰 Transactions found: {len(transactions)}")
    
    if transactions:
        # Show first 5 transactions
        print("\n📝 Recent transactions:")
        for tx in transactions[:5]:
            print(f"   - {tx.transaction_id}: KES {tx.amount} ({tx.transaction_type}) - {tx.timestamp}")
        
        # Calculate totals
        total = sum(tx.amount for tx in transactions)
        print(f"\n📈 Total volume: KES {total}")
    else:
        print("   No transactions found - database is empty!")
    
    # Get database file size
    import os
    db_path = "mpesa.db"
    if os.path.exists(db_path):
        size_kb = os.path.getsize(db_path) / 1024
        print(f"\n💾 Database file size: {size_kb:.2f} KB")

except Exception as e:
    print(f"❌ Error: {e}")
finally:
    db.close()