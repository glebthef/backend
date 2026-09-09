from typing import Annotated

from fastapi import APIRouter, Body, Depends, HTTPException
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from dependencies import get_admin_user, get_authenticated_user, get_session
from models import ChatMessage, User
from schemas.chat import ChatMessageCreate, ChatMessageResponse, ChatThreadResponse

router = APIRouter()


@router.get("/chats", response_model=list[ChatThreadResponse])
async def list_chats(
        admin: Annotated[User, Depends(get_admin_user)],
        session: Annotated[AsyncSession, Depends(get_session)],
):
    # One row per user: their most recent message, for an admin inbox list.
    last_ids = (
        select(func.max(ChatMessage.id))
        .group_by(ChatMessage.user_id)
        .scalar_subquery()
    )
    stmt = (
        select(ChatMessage, User.login)
        .join(User, User.id == ChatMessage.user_id)
        .where(ChatMessage.id.in_(last_ids))
        .order_by(ChatMessage.created_at.desc())
    )
    rows = (await session.execute(stmt)).all()
    return [
        ChatThreadResponse(
            user_id=msg.user_id,
            login=login,
            last_text=msg.text,
            last_sender=msg.sender,
            last_at=msg.created_at,
        )
        for msg, login in rows
    ]


@router.get("/users/{user_id}/chat", response_model=list[ChatMessageResponse])
async def get_chat_messages(
        user_id: int,
        authenticated_user: Annotated[User, Depends(get_authenticated_user)],
        session: Annotated[AsyncSession, Depends(get_session)],
):
    if authenticated_user.id != user_id and not authenticated_user.is_admin:
        raise HTTPException(403, "Access denied")
    stmt = (
        select(ChatMessage)
        .where(ChatMessage.user_id == user_id)
        .order_by(ChatMessage.created_at)
    )
    return list(await session.scalars(stmt))


@router.post("/users/{user_id}/chat", response_model=ChatMessageResponse)
async def send_chat_message(
        user_id: int,
        data: Annotated[ChatMessageCreate, Body()],
        authenticated_user: Annotated[User, Depends(get_authenticated_user)],
        session: Annotated[AsyncSession, Depends(get_session)],
):
    if authenticated_user.id == user_id:
        sender = "user"
    elif authenticated_user.is_admin:
        # An admin replying into someone else's thread acts as support.
        sender = "support"
    else:
        raise HTTPException(403, "Access denied")

    target = await session.scalar(select(User).where(User.id == user_id))
    if target is None:
        raise HTTPException(404, "User not found")

    message = ChatMessage(user_id=user_id, sender=sender, text=data.text)
    session.add(message)
    await session.commit()
    await session.refresh(message)
    return message
