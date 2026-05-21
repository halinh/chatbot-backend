import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import get_current_user_http, get_db
from app.models.message import Message
from app.models.user import User
from app.schemas.chat import MessageOut, SessionOut

router = APIRouter(tags=["chat"])


@router.get("/chat/sessions", response_model=list[SessionOut])
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


@router.get("/chat/sessions/{session_id}/messages", response_model=list[MessageOut])
async def get_session_messages(
    session_id: uuid.UUID,
    current_user: User = Depends(get_current_user_http),
    db: AsyncSession = Depends(get_db),
):
    check = await db.execute(
        select(Message).where(
            Message.session_id == session_id,
            Message.user_id == current_user.id,
        ).limit(1)
    )
    if check.scalar_one_or_none() is None:
        all_msgs = await db.execute(
            select(Message).where(Message.session_id == session_id).limit(1)
        )
        if all_msgs.scalar_one_or_none() is not None:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")
        return []

    result = await db.execute(
        select(Message)
        .where(Message.session_id == session_id)
        .order_by(Message.created_at.asc())
    )
    return [MessageOut.model_validate(m) for m in result.scalars().all()]
