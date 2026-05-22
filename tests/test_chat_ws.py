import json
import uuid
import pytest
from unittest.mock import patch

from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker

from app.database import Base
from app.dependencies import get_db


@pytest.fixture
async def ws_engine():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()


@pytest.fixture
async def ws_app(ws_engine):
    from app.main import app

    factory = async_sessionmaker(ws_engine, class_=AsyncSession, expire_on_commit=False)

    async def override_get_db():
        async with factory() as session:
            yield session

    app.dependency_overrides[get_db] = override_get_db
    yield app
    app.dependency_overrides.clear()


@pytest.fixture
async def ws_token(ws_app):
    async with AsyncClient(
        transport=ASGITransport(app=ws_app), base_url="http://test"
    ) as ac:
        resp = await ac.post(
            "/auth/register",
            json={"email": "ws_user@example.com", "password": "wspassword"},
        )
    return resp.json()["access_token"]


async def test_ws_rejects_missing_token(ws_app):
    from starlette.testclient import TestClient
    with TestClient(ws_app) as tc:
        with tc.websocket_connect("/ws/chat") as ws:
            data = json.loads(ws.receive_text())
            assert data["type"] == "error"


async def test_ws_rejects_bad_token(ws_app):
    from starlette.testclient import TestClient
    with TestClient(ws_app) as tc:
        with tc.websocket_connect("/ws/chat?token=bad.token.here") as ws:
            data = json.loads(ws.receive_text())
            assert data["type"] == "error"


async def test_ws_streams_and_persists(ws_app, ws_token, ws_engine):
    async def fake_stream(messages, model=None):
        for token in ["Hi", " there"]:
            yield token

    session_id = str(uuid.uuid4())

    with patch("app.routers.chat.stream_chat", side_effect=fake_stream):
        from starlette.testclient import TestClient
        with TestClient(ws_app) as tc:
            with tc.websocket_connect(
                f"/ws/chat?token={ws_token}&session_id={session_id}"
            ) as ws:
                ws.send_text(json.dumps({"content": "Hello", "model": "llama3.2"}))

                messages = []
                while True:
                    raw = ws.receive_text()
                    msg = json.loads(raw)
                    messages.append(msg)
                    if msg["type"] in ("done", "error"):
                        break

    chunk_messages = [m for m in messages if m["type"] == "chunk"]
    done_messages = [m for m in messages if m["type"] == "done"]

    assert [c["content"] for c in chunk_messages] == ["Hi", " there"]
    assert len(done_messages) == 1
    assert done_messages[0]["session_id"] == session_id

    from sqlalchemy import select
    from app.models.message import Message

    factory = async_sessionmaker(ws_engine, class_=AsyncSession, expire_on_commit=False)
    async with factory() as db:
        result = await db.execute(
            select(Message)
            .where(Message.session_id == uuid.UUID(session_id))
            .order_by(Message.created_at)
        )
        msgs = result.scalars().all()

    assert len(msgs) == 2
    assert msgs[0].role == "user" and msgs[0].content == "Hello"
    assert msgs[1].role == "assistant" and msgs[1].content == "Hi there"


async def test_ws_uses_existing_session_id(ws_app, ws_token, ws_engine):
    session_id = str(uuid.uuid4())

    async def fake_stream(messages, model=None):
        yield "ok"

    with patch("app.routers.chat.stream_chat", side_effect=fake_stream):
        from starlette.testclient import TestClient
        with TestClient(ws_app) as tc:
            for _ in range(2):
                with tc.websocket_connect(
                    f"/ws/chat?token={ws_token}&session_id={session_id}"
                ) as ws:
                    ws.send_text(json.dumps({"content": "ping", "model": "llama3.2"}))
                    while True:
                        msg = json.loads(ws.receive_text())
                        if msg["type"] in ("done", "error"):
                            break

    from sqlalchemy import select
    from app.models.message import Message

    factory = async_sessionmaker(ws_engine, class_=AsyncSession, expire_on_commit=False)
    async with factory() as db:
        result = await db.execute(
            select(Message).where(Message.session_id == uuid.UUID(session_id))
        )
        msgs = result.scalars().all()

    # 2 turns × (user + assistant) = 4 messages, all in the same session
    assert len(msgs) == 4
