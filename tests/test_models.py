import pytest
import uuid
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

from app.database import Base
from app.models.user import User
from app.models.message import Message


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


async def test_user_model_columns(session):
    user = User(email="test@example.com", hashed_password="hashed")
    session.add(user)
    await session.commit()
    await session.refresh(user)

    assert user.id is not None
    assert user.email == "test@example.com"
    assert user.created_at is not None


async def test_message_model_columns(session):
    user = User(email="msg@example.com", hashed_password="hashed")
    session.add(user)
    await session.commit()
    await session.refresh(user)

    session_id = uuid.uuid4()
    msg = Message(
        session_id=session_id,
        user_id=user.id,
        role="user",
        content="Hello",
    )
    session.add(msg)
    await session.commit()
    await session.refresh(msg)

    assert msg.id is not None
    assert msg.role == "user"
    assert msg.content == "Hello"
    assert msg.created_at is not None
