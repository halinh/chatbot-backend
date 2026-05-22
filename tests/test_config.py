import pytest
from pydantic import ValidationError

from app.config import Settings


def test_settings_have_defaults():
    s = Settings(SECRET_KEY="valid-test-secret-key")
    assert s.ALGORITHM == "HS256"
    assert s.OLLAMA_MODEL == "llama3.2"
    assert "http://localhost:5173" in s.CORS_ORIGINS
    assert s.ACCESS_TOKEN_EXPIRE_MINUTES == 60


def test_secret_key_default_is_rejected():
    with pytest.raises(ValidationError):
        Settings(SECRET_KEY="change-me-in-production")
