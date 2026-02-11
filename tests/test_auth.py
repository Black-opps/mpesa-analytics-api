import uuid

TEST_EMAIL = f"{uuid.uuid4()}@example.com"
TEST_PASSWORD = "password123"


def test_register_user(client):
    response = client.post(
        "/auth/register",
        json={
            "email": TEST_EMAIL,
            "password": TEST_PASSWORD,
        },
    )

    assert response.status_code == 200

    data = response.json()
    assert data["email"] == TEST_EMAIL
    assert "id" in data


def test_login_user(client):
    # register first
    client.post(
        "/auth/register",
        json={
            "email": TEST_EMAIL,
            "password": TEST_PASSWORD,
        },
    )

    response = client.post(
        "/auth/login",
        data={
            "username": TEST_EMAIL,  # IMPORTANT
            "password": TEST_PASSWORD,
        },
    )

    assert response.status_code == 200
    assert "access_token" in response.json()


def test_me_requires_auth(client):
    response = client.get("/me")
    assert response.status_code == 401


def test_me_with_token(client):
    # register
    client.post(
        "/auth/register",
        json={
            "email": TEST_EMAIL,
            "password": TEST_PASSWORD,
        },
    )

    # login
    login = client.post(
        "/auth/login",
        data={
            "username": TEST_EMAIL,  # IMPORTANT
            "password": TEST_PASSWORD,
        },
    )

    token = login.json()["access_token"]

    response = client.get(
        "/me",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 200
    assert response.json()["email"] == TEST_EMAIL
