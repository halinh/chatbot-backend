from unittest.mock import AsyncMock, MagicMock, patch

from app.services.ollama import stream_chat


async def test_stream_chat_yields_tokens():
    fake_chunks = [
        MagicMock(message=MagicMock(content="Hello")),
        MagicMock(message=MagicMock(content=" world")),
        MagicMock(message=MagicMock(content="!")),
    ]

    async def fake_async_iter():
        for chunk in fake_chunks:
            yield chunk

    mock_client = MagicMock()
    mock_client.chat = AsyncMock(return_value=fake_async_iter())

    with patch("app.services.ollama.ollama.AsyncClient", return_value=mock_client):
        tokens = []
        async for token in stream_chat([{"role": "user", "content": "Hi"}]):
            tokens.append(token)

    assert tokens == ["Hello", " world", "!"]


async def test_stream_chat_passes_model_override():
    fake_chunks = [MagicMock(message=MagicMock(content="ok"))]

    async def fake_async_iter():
        for chunk in fake_chunks:
            yield chunk

    mock_client = MagicMock()
    mock_client.chat = AsyncMock(return_value=fake_async_iter())

    with patch("app.services.ollama.ollama.AsyncClient", return_value=mock_client):
        async for _ in stream_chat([{"role": "user", "content": "Hi"}], model="mistral"):
            pass

    call_kwargs = mock_client.chat.call_args
    assert call_kwargs.kwargs["model"] == "mistral"
