import uuid
from datetime import datetime, timezone

from app.schemas.auth import RegisterRequest, LoginRequest, TokenResponse, UserOut
from app.schemas.chat import ChatInput, WSChunk, WSDone, WSError, SessionOut, MessageOut


def test_register_request_validation():
    req = RegisterRequest(email="user@example.com", password="secret123")
    assert req.email == "user@example.com"


def test_login_request_validation():
    req = LoginRequest(email="user@example.com", password="secret123")
    assert req.password == "secret123"


def test_token_response_fields():
    t = TokenResponse(access_token="tok", token_type="bearer", expires_in=3600)
    assert t.token_type == "bearer"
    assert t.expires_in == 3600


def test_user_out_no_password():
    u = UserOut(id=uuid.uuid4(), email="x@x.com", created_at=datetime.now(timezone.utc))
    assert not hasattr(u, "hashed_password")


def test_chat_input():
    c = ChatInput(content="Hello", model="llama3.2")
    assert c.model == "llama3.2"


def test_ws_chunk():
    chunk = WSChunk(content="tok")
    assert chunk.type == "chunk"


def test_ws_done():
    done = WSDone(session_id=uuid.uuid4(), message_id=uuid.uuid4())
    assert done.type == "done"


def test_ws_error():
    err = WSError(message="oops")
    assert err.type == "error"


def test_session_out():
    s = SessionOut(
        session_id=uuid.uuid4(),
        message_count=5,
        last_message_at=datetime.now(timezone.utc),
    )
    assert s.message_count == 5


def test_message_out():
    m = MessageOut(
        id=uuid.uuid4(),
        session_id=uuid.uuid4(),
        user_id=uuid.uuid4(),
        role="user",
        content="hi",
        created_at=datetime.now(timezone.utc),
    )
    assert m.role == "user"
