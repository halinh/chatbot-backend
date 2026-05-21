import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel


class ChatInput(BaseModel):
    content: str
    model: str = "llama3.2"


class WSChunk(BaseModel):
    type: Literal["chunk"] = "chunk"
    content: str


class WSDone(BaseModel):
    type: Literal["done"] = "done"
    session_id: uuid.UUID
    message_id: uuid.UUID


class WSError(BaseModel):
    type: Literal["error"] = "error"
    message: str


class SessionOut(BaseModel):
    session_id: uuid.UUID
    message_count: int
    last_message_at: datetime


class MessageOut(BaseModel):
    id: uuid.UUID
    session_id: uuid.UUID
    user_id: uuid.UUID
    role: str
    content: str
    created_at: datetime

    model_config = {"from_attributes": True}
