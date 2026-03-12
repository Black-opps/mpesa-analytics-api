# add_test_data.py

import requests
import json
from datetime import datetime, timedelta
import random

# Configuration
BASE_URL = "http://localhost:8000"
EMAIL = "test@example.com"
PASSWORD = "password123"

def main():
    # First, try to login
    session = requests.Session()
    
    print("1. Logging in...")
    login_data = {
        "username": EMAIL,
        "password": PASSWORD
    }
    
    response = session.post(
        f"{BASE_URL}/auth/login",
        data=login_data,
        headers={"Content-Type": "application/x-www-form-urlencoded"}
    )
    
    if response.status_code != 200:
        print("Login failed. Trying to register...")
        # Try to register
        register_data = {
            "email": EMAIL,
            "password": PASSWORD
        }
        response = session.post(
            f"{BASE_URL}/auth/register",
            json=register_data
        )
        if response.status_code != 200:
            print(f"Registration failed: {response.text}")
            return
        
        print("Registration successful. Logging in...")
        response = session.post(
            f"{BASE_URL}/auth/login",
            data=login_data,
            headers={"Content-Type": "application/x-www-form-urlencoded"}
        )
    
    token = response.json().get("access_token")
    print(f"✅ Login successful. Token: {token[:20]}...")
    
    # Set authorization header
    headers = {"Authorization": f"Bearer {token}"}
    
    # Create sample transactions
    print("\n2. Creating sample transactions...")
    
    transaction_types = ["send_money", "pay_bill", "buy_goods", "withdraw"]
    counterparties = [
        "254712345678", "254723456789", "254734567890", 
        "254745678901", "254756789012", "254767890123"
    ]
    
    transactions = []
    for i in range(1, 21):  # Create 20 transactions
        days_ago = random.randint(0, 30)
        transactions.append({
            "transaction_id": f"TXN{1000 + i}",
            "amount": random.randint(100, 5000),
            "transaction_type": random.choice(transaction_types),
            "counterparty": random.choice(counterparties),
            "timestamp": (datetime.now() - timedelta(days=days_ago)).isoformat()
        })
    
    response = session.post(
        f"{BASE_URL}/transactions",
        json=transactions,
        headers=headers
    )
    
    if response.status_code == 201 or response.status_code == 200:
        print(f"✅ Created {len(transactions)} transactions")
        print(f"Response: {response.json()}")
    else:
        print(f"❌ Failed to create transactions: {response.text}")
    
    # Check analytics
    print("\n3. Checking analytics...")
    response = session.get(
        f"{BASE_URL}/analytics",
        headers=headers
    )
    
    if response.status_code == 200:
        analytics = response.json()
        print(f"✅ Analytics: {analytics}")
    else:
        print(f"❌ Failed to get analytics: {response.text}")
    
    # Check transactions
    print("\n4. Checking transactions list...")
    response = session.get(
        f"{BASE_URL}/transactions?skip=0&limit=100",
        headers=headers
    )
    
    if response.status_code == 200:
        transactions = response.json()
        print(f"✅ Found {len(transactions)} transactions")
        if transactions:
            print(f"First transaction: {transactions[0]}")
    else:
        print(f"❌ Failed to get transactions: {response.text}")

if __name__ == "__main__":
    main()