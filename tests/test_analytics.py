def test_analytics(client):
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

    response = client.get(
        "/analytics",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 200

