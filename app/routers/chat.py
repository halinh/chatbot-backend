import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, WebSocket, WebSocketDisconnect, status
from jose import JWTError
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import get_current_user_http, get_db
from app.models.message import Message
from app.models.user import User
from app.schemas.chat import ChatInput, MessageOut, SessionOut, WSChunk, WSDone, WSError
from app.services.auth import decode_token
from app.services.ollama import stream_chat

router = APIRouter(prefix="/chat", tags=["chat"])
ws_router = APIRouter(tags=["chat"])


@router.get("/sessions", response_model=list[SessionOut])
async def list_sessions(
    current_user: User = Depends(get_current_user_http),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(
            Message.session_id,
            func.count(Message.id).label("message_count"),
            func.max(Message.created_at).label("last_message_at"),
        )
        .where(Message.user_id == current_user.id)
        .group_by(Message.session_id)
        .order_by(func.max(Message.created_at).desc())
    )
    rows = result.all()
    return [
        SessionOut(
            session_id=row.session_id,
            message_count=row.message_count,
            last_message_at=row.last_message_at,
        )
        for row in rows
    ]


@router.get("/sessions/{session_id}/messages", response_model=list[MessageOut])
async def get_session_messages(
    session_id: uuid.UUID,
    current_user: User = Depends(get_current_user_http),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Message)
        .where(Message.session_id == session_id)
        .order_by(Message.created_at.asc())
    )
    messages = result.scalars().all()
    if not messages:
        return []
    if messages[0].user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")
    return messages


@ws_router.websocket("/ws/chat")
async def websocket_chat(
    websocket: WebSocket,
    token: str = Query(default=None),
    session_id: str = Query(default=None),
    db: AsyncSession = Depends(get_db),
):
    await websocket.accept()

    if not token:
        await websocket.send_text(WSError(message="Missing token").model_dump_json())
        await websocket.close(code=1008)
        return

    try:
        payload = decode_token(token)
        user_id = uuid.UUID(payload["sub"])
    except (JWTError, KeyError, ValueError):
        await websocket.send_text(WSError(message="Invalid token").model_dump_json())
        await websocket.close(code=1008)
        return

    db_result = await db.execute(select(User).where(User.id == user_id))
    user = db_result.scalar_one_or_none()
    if user is None:
        await websocket.send_text(WSError(message="User not found").model_dump_json())
        await websocket.close(code=1008)
        return

    resolved_session_id = uuid.UUID(session_id) if session_id else uuid.uuid4()

    try:
        while True:
            raw = await websocket.receive_text()
            chat_input = ChatInput.model_validate_json(raw)

            history_result = await db.execute(
                select(Message)
                .where(Message.session_id == resolved_session_id)
                .order_by(Message.created_at.asc())
            )
            history = [
                {"role": m.role, "content": m.content}
                for m in history_result.scalars().all()
            ]
            history.append({"role": "user", "content": chat_input.content})

            user_msg = Message(
                session_id=resolved_session_id,
                user_id=user.id,
                role="user",
                content=chat_input.content,
            )
            db.add(user_msg)
            await db.commit()
            await db.refresh(user_msg)

            full_response = ""
            async for token_text in stream_chat(history, model=chat_input.model):
                full_response += token_text
                await websocket.send_text(WSChunk(content=token_text).model_dump_json())

            assistant_msg = Message(
                session_id=resolved_session_id,
                user_id=user.id,
                role="assistant",
                content=full_response,
            )
            db.add(assistant_msg)
            await db.commit()
            await db.refresh(assistant_msg)

            await websocket.send_text(
                WSDone(
                    session_id=resolved_session_id,
                    message_id=assistant_msg.id,
                ).model_dump_json()
            )

    except WebSocketDisconnect:
        pass
    except Exception as exc:
        try:
            await websocket.send_text(WSError(message=str(exc)).model_dump_json())
        except RuntimeError:
            pass
