# test_data.py

import requests
import json
from datetime import datetime, timedelta
import random

# First, login to get token
login_data = {
    "username": "test@example.com",
    "password": "password123"
}

response = requests.post(
    "http://localhost:8000/auth/login",
    data=login_data,
    headers={"Content-Type": "application/x-www-form-urlencoded"}
)

if response.status_code == 200:
    token = response.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    
    # Create sample transactions
    transactions = []
    for i in range(20):
        days_ago = random.randint(0, 30)
        transactions.append({
            "transaction_id": f"TXN{1000 + i}",
            "amount": random.randint(100, 5000),
            "transaction_type": random.choice(["send_money", "pay_bill", "buy_goods", "withdraw"]),
            "counterparty": f"2547{random.randint(10000000, 99999999)}",
            "timestamp": (datetime.now() - timedelta(days=days_ago)).isoformat()
        })
    
    # Add transactions
    response = requests.post(
        "http://localhost:8000/transactions",
        json=transactions,
        headers=headers
    )
    print("Sample data added:", response.json())
else:
    # Register if login fails
    register_data = {
        "email": "test@example.com",
        "password": "password123"
    }
    response = requests.post(
        "http://localhost:8000/auth/register",
        json=register_data
    )
    print("User created:", response.json())