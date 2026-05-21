import pytest
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

from app.database import Base
from app.services.auth import (
    hash_password,
    verify_password,
    create_access_token,
    decode_token,
    create_user,
    authenticate_user,
)


@pytest.fixture
async def engine():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    await engine.dispose()


@pytest.fixture
async def session(engine):
    factory = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with factory() as s:
        yield s


def test_hash_password_is_not_plaintext():
    h = hash_password("mysecret")
    assert h != "mysecret"
    assert len(h) > 20


def test_verify_password_correct():
    h = hash_password("mysecret")
    assert verify_password("mysecret", h) is True


def test_verify_password_wrong():
    h = hash_password("mysecret")
    assert verify_password("wrong", h) is False


def test_create_and_decode_token():
    token = create_access_token({"sub": "user-id-123"})
    payload = decode_token(token)
    assert payload["sub"] == "user-id-123"


def test_decode_invalid_token_raises():
    with pytest.raises(Exception):
        decode_token("not.a.valid.token")


async def test_create_user(session):
    user = await create_user(session, "alice@example.com", "password123")
    assert user.id is not None
    assert user.email == "alice@example.com"
    assert user.hashed_password != "password123"


async def test_create_user_duplicate_email(session):
    await create_user(session, "bob@example.com", "pass1")
    with pytest.raises(Exception):
        await create_user(session, "bob@example.com", "pass2")


async def test_authenticate_user_success(session):
    await create_user(session, "carol@example.com", "mypass")
    user = await authenticate_user(session, "carol@example.com", "mypass")
    assert user is not None
    assert user.email == "carol@example.com"


async def test_authenticate_user_wrong_password(session):
    await create_user(session, "dave@example.com", "rightpass")
    result = await authenticate_user(session, "dave@example.com", "wrongpass")
    assert result is None


async def test_authenticate_user_not_found(session):
    result = await authenticate_user(session, "nobody@example.com", "pass")
    assert result is None
