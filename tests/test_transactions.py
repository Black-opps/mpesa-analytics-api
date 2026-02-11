import uuid

def test_ingest_transactions(client):
    # register user
    client.post(
        "/auth/register",
        json={
            "email": "test@example.com",
            "password": "password123",
        },
    )

    # login
    login = client.post(
        "/auth/login",
        data={
            "username": "test@example.com",
            "password": "password123",
        },
    )

    token = login.json()["access_token"]

    # Generate a unique transaction ID
    tx_id = f"TXN-{uuid.uuid4()}"
    print(f"Generated transaction ID: {tx_id}")  # DEBUG
    
    payload = [{
        "transaction_id": tx_id,  # Use the same ID consistently
        "amount": 500,
        "transaction_type": "credit",
        "counterparty": "John Doe", 
        "timestamp": "2024-01-01T10:00:00",
    }]

    # first request
    r1 = client.post(
        "/transactions",
        json=payload,
        headers={"Authorization": f"Bearer {token}"},
    )

    # DEBUG prints
    print(f"First request status code: {r1.status_code}")
    print(f"First request response: {r1.json()}")
    
    assert r1.status_code == 200
    response = r1.json()
    
    assert response == {"inserted": 1, "skipped": 0}

    # retry same transaction
    r2 = client.post(
        "/transactions",
        json=payload,  # Same payload, same transaction ID
        headers={"Authorization": f"Bearer {token}"},
    )

    # DEBUG prints for second request
    print(f"Second request status code: {r2.status_code}")
    print(f"Second request response: {r2.json()}")

    assert r2.status_code == 200
    assert r2.json()["inserted"] == 0
    assert r2.json()["skipped"] == 1