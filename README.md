# Chatbot Backend

A FastAPI backend for a multi-turn conversational AI chatbot. Users authenticate, create chat sessions, and exchange streaming messages with a locally hosted LLM via [Ollama](https://ollama.com).

## Features

- JWT authentication with Argon2 password hashing
- Multi-session chat — each user can have independent conversations
- Real-time token-by-token streaming responses over WebSocket
- Full message history persisted to PostgreSQL
- Model selection per message (any Ollama-compatible model)
- Async throughout (FastAPI + SQLAlchemy 2.0 + asyncpg)
- Database migrations via Alembic

## Tech Stack

| Layer | Technology |
|---|---|
| Language | Python 3.14 |
| Framework | FastAPI |
| Database | PostgreSQL (asyncpg driver) |
| ORM / Migrations | SQLAlchemy 2.0 (async) + Alembic |
| Auth | JWT (`python-jose`) + Argon2 (`argon2-cffi`) |
| LLM | Ollama (local, streaming) |
| Testing | pytest + pytest-asyncio + httpx |
| Package manager | uv |

## Prerequisites

- Python ≥ 3.14
- [uv](https://docs.astral.sh/uv/) — fast Python package manager
- PostgreSQL running and accessible
- [Ollama](https://ollama.com) running locally with at least one model pulled (e.g. `ollama pull llama3.2`)

## Installation

```bash
# Clone and enter the repo
git clone <repo-url>
cd chatbot-backend

# Install dependencies
uv sync

# Copy and configure environment variables
cp .env.example .env
# Edit .env — see Configuration section below
```

## Configuration

| Variable | Default | Description |
|---|---|---|
| `DATABASE_URL` | `postgresql+asyncpg://postgres:postgres@localhost:5432/chatbot` | Async PostgreSQL connection string |
| `SECRET_KEY` | *(must be set)* | JWT signing secret — never use the default in production |
| `ALGORITHM` | `HS256` | JWT algorithm |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | `60` | Token lifetime in minutes |
| `OLLAMA_BASE_URL` | `http://localhost:11434` | Ollama service URL |
| `OLLAMA_MODEL` | `llama3.2` | Default model (overridable per message) |
| `CORS_ORIGINS` | `["http://localhost:5173"]` | Allowed frontend origins (JSON array) |

> **Security:** `SECRET_KEY` is validated at startup — the app will refuse to start if it equals the default placeholder value.

## Database Setup

```bash
# Apply all migrations
alembic upgrade head
```

To create a new migration after changing models:

```bash
alembic revision --autogenerate -m "describe your change"
alembic upgrade head
```

## Running

```bash
# Development (auto-reload enabled when ENV=development)
python main.py

# Production
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

The server starts on `http://0.0.0.0:8000`. Interactive API docs are available at `/docs`.

## API Reference

### Authentication

#### `POST /auth/register`

Register a new user.

**Request:**
```json
{ "email": "user@example.com", "password": "minlength8" }
```

**Response `201`:**
```json
{ "access_token": "<jwt>", "token_type": "bearer", "expires_in": 3600 }
```

**Errors:** `409` if email is already registered.

---

#### `POST /auth/login`

Authenticate and receive a token.

**Request:**
```json
{ "email": "user@example.com", "password": "yourpassword" }
```

**Response `200`:**
```json
{ "access_token": "<jwt>", "token_type": "bearer", "expires_in": 3600 }
```

**Errors:** `401` for invalid credentials.

---

### Chat — REST

All REST chat endpoints require `Authorization: Bearer <token>`.

#### `GET /chat/sessions`

List all chat sessions for the current user.

**Response `200`:**
```json
[
  {
    "session_id": "550e8400-e29b-41d4-a716-446655440000",
    "message_count": 5,
    "last_message_at": "2024-01-15T10:30:00Z"
  }
]
```

---

#### `GET /chat/sessions/{session_id}/messages`

Get message history for a session.

**Response `200`:**
```json
[
  {
    "id": "...",
    "session_id": "...",
    "user_id": "...",
    "role": "user",
    "content": "Hello!",
    "created_at": "2024-01-15T10:00:00Z"
  },
  {
    "id": "...",
    "session_id": "...",
    "user_id": "...",
    "role": "assistant",
    "content": "Hi there! How can I help you?",
    "created_at": "2024-01-15T10:00:01Z"
  }
]
```

---

### Chat — WebSocket

#### `WS /ws/chat`

Real-time streaming chat connection.

**Query parameters:**

| Parameter | Required | Description |
|---|---|---|
| `token` | Yes | JWT access token |
| `session_id` | No | UUID of an existing session; a new session is created if omitted |

**Send a message:**
```json
{ "content": "What is the capital of France?", "model": "llama3.2" }
```

`model` is optional and defaults to `OLLAMA_MODEL` from config.

**Receive — streaming chunks:**
```json
{ "type": "chunk", "content": "Paris" }
```

**Receive — stream complete:**
```json
{ "type": "done", "session_id": "550e8400-...", "message_id": "..." }
```

**Receive — error:**
```json
{ "type": "error", "message": "Description of error" }
```

The full conversation history is loaded from the database at connect time and sent to the model as context, enabling multi-turn conversations.

## Project Structure

```
chatbot-backend/
├── app/
│   ├── main.py           # FastAPI app and middleware setup
│   ├── config.py         # Settings (pydantic-settings, reads .env)
│   ├── database.py       # Async SQLAlchemy engine and session
│   ├── dependencies.py   # Auth dependency injection (HTTP + WS)
│   ├── models/
│   │   ├── user.py       # User ORM model
│   │   └── message.py    # Message ORM model
│   ├── routers/
│   │   ├── auth.py       # /auth endpoints
│   │   └── chat.py       # /chat and /ws/chat endpoints
│   ├── schemas/
│   │   ├── auth.py       # Pydantic request/response schemas for auth
│   │   └── chat.py       # Pydantic request/response schemas for chat
│   └── services/
│       ├── auth.py       # Password hashing, JWT, user CRUD
│       └── ollama.py     # Streaming LLM client
├── alembic/              # Database migrations
├── tests/                # pytest test suite
├── main.py               # Entry point (runs uvicorn)
├── pyproject.toml        # Project metadata and dependencies
├── alembic.ini           # Alembic config
└── .env.example          # Environment variable template
```

## Running Tests

```bash
# Run all tests
uv run pytest

# With coverage
uv run pytest --cov=app tests/

# A specific test file
uv run pytest tests/test_chat_ws.py -v
```

Tests use an in-memory SQLite database and mock the Ollama service — no external services required.

## Quick Start Example

```bash
# Start PostgreSQL
docker run -d --name postgres \
  -e POSTGRES_PASSWORD=postgres \
  -p 5432:5432 postgres

# Start Ollama and pull a model
ollama serve &
ollama pull llama3.2

# Run the backend
python main.py
```

```bash
# Register a user
curl -s -X POST http://localhost:8000/auth/register \
  -H "Content-Type: application/json" \
  -d '{"email":"you@example.com","password":"password123"}' | jq .

# Connect via WebSocket (e.g. with websocat)
TOKEN="<access_token from above>"
websocat "ws://localhost:8000/ws/chat?token=$TOKEN"
# Then type: {"content": "Hello!", "model": "llama3.2"}
```
