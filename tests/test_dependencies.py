import pytest
import uuid
from fastapi import HTTPException
from fastapi.security import HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

from app.database import Base
from app.models.user import User
from app.services.auth import hash_password, create_access_token
from app.dependencies import get_current_user, get_current_user_http


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


async def test_get_current_user_valid_token(session):
    user = User(email="dep@example.com", hashed_password=hash_password("pass"))
    session.add(user)
    await session.commit()
    await session.refresh(user)

    token = create_access_token({"sub": str(user.id)})
    result = await get_current_user(token=token, db=session)
    assert result.id == user.id


async def test_get_current_user_invalid_token(session):
    with pytest.raises(HTTPException) as exc_info:
        await get_current_user(token="bad.token.here", db=session)
    assert exc_info.value.status_code == 401


async def test_get_current_user_nonexistent_user(session):
    token = create_access_token({"sub": str(uuid.uuid4())})
    with pytest.raises(HTTPException) as exc_info:
        await get_current_user(token=token, db=session)
    assert exc_info.value.status_code == 401


async def test_get_current_user_http_valid(session):
    user = User(email="http_dep@example.com", hashed_password=hash_password("pass"))
    session.add(user)
    await session.commit()
    await session.refresh(user)

    token = create_access_token({"sub": str(user.id)})
    creds = HTTPAuthorizationCredentials(scheme="Bearer", credentials=token)
    result = await get_current_user_http(credentials=creds, db=session)
    assert result.id == user.id


async def test_get_current_user_http_no_creds(session):
    with pytest.raises(HTTPException) as exc_info:
        await get_current_user_http(credentials=None, db=session)
    assert exc_info.value.status_code == 401
