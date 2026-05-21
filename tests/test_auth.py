async def test_register_success(client):
    response = await client.post(
        "/auth/register",
        json={"email": "newuser@example.com", "password": "strongpass123"},
    )
    assert response.status_code == 201
    data = response.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"
    assert data["expires_in"] == 3600


async def test_register_duplicate_email(client):
    await client.post(
        "/auth/register",
        json={"email": "dup@example.com", "password": "pass123"},
    )
    response = await client.post(
        "/auth/register",
        json={"email": "dup@example.com", "password": "pass456"},
    )
    assert response.status_code == 409


async def test_login_success(client):
    await client.post(
        "/auth/register",
        json={"email": "login@example.com", "password": "mypassword"},
    )
    response = await client.post(
        "/auth/login",
        json={"email": "login@example.com", "password": "mypassword"},
    )
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"


async def test_login_wrong_password(client):
    await client.post(
        "/auth/register",
        json={"email": "badpass@example.com", "password": "correctpass"},
    )
    response = await client.post(
        "/auth/login",
        json={"email": "badpass@example.com", "password": "wrongpass"},
    )
    assert response.status_code == 401


async def test_login_unknown_email(client):
    response = await client.post(
        "/auth/login",
        json={"email": "ghost@example.com", "password": "anything"},
    )
    assert response.status_code == 401
