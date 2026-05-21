from collections.abc import AsyncIterator

import ollama

from app.config import settings


async def stream_chat(
    messages: list[dict],
    model: str | None = None,
) -> AsyncIterator[str]:
    resolved_model = model or settings.OLLAMA_MODEL
    client = ollama.AsyncClient(host=settings.OLLAMA_BASE_URL)
    stream = await client.chat(
        model=resolved_model,
        messages=messages,
        stream=True,
    )
    async for chunk in stream:
        token = chunk.message.content
        if token:
            yield token
