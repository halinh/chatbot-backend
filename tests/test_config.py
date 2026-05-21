from app.config import settings


def test_settings_have_defaults():
    assert settings.ALGORITHM == "HS256"
    assert settings.OLLAMA_MODEL == "llama3.2"
    assert "http://localhost:5173" in settings.CORS_ORIGINS
    assert settings.ACCESS_TOKEN_EXPIRE_MINUTES == 60
