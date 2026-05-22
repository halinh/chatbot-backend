import uuid
import pytest
from app.models.user import User
from app.models.message import Message
from app.services.auth import hash_password
from sqlalchemy import select


@pytest.fixture
async def auth_token(client):
    resp = await client.post(
        "/auth/register",
        json={"email": "chat_rest@example.com", "password": "pass12345"},
    )
    return resp.json()["access_token"]


async def test_list_sessions_empty(client, auth_token):
    response = await client.get(
        "/chat/sessions",
        headers={"Authorization": f"Bearer {auth_token}"},
    )
    assert response.status_code == 200
    assert response.json() == []


async def test_list_sessions_requires_auth(client):
    response = await client.get("/chat/sessions")
    assert response.status_code == 401


async def test_get_session_messages_returns_messages(client, auth_token, db_session):
    result = await db_session.execute(
        select(User).where(User.email == "chat_rest@example.com")
    )
    user = result.scalar_one()

    session_id = uuid.uuid4()
    msg = Message(session_id=session_id, user_id=user.id, role="user", content="Hello")
    db_session.add(msg)
    await db_session.commit()

    response = await client.get(
        f"/chat/sessions/{session_id}/messages",
        headers={"Authorization": f"Bearer {auth_token}"},
    )
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["content"] == "Hello"
    assert data[0]["role"] == "user"


async def test_get_session_messages_wrong_user(client, db_session):
    other_user = User(email="other@example.com", hashed_password=hash_password("p"))
    db_session.add(other_user)
    await db_session.commit()
    await db_session.refresh(other_user)

    session_id = uuid.uuid4()
    msg = Message(session_id=session_id, user_id=other_user.id, role="user", content="secret")
    db_session.add(msg)
    await db_session.commit()

    resp = await client.post(
        "/auth/register",
        json={"email": "intruder@example.com", "password": "intruderpass"},
    )
    token = resp.json()["access_token"]

    response = await client.get(
        f"/chat/sessions/{session_id}/messages",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200
    assert response.json() == []
