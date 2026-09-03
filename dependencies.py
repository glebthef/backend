from datetime import datetime
from typing import Annotated
from fastapi import Header, HTTPException, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from models import engine, User, LoginSession


async def get_session():
    conn = await engine.connect()
    session = AsyncSession(conn, expire_on_commit=False)
    try:
        yield session
    finally:
        await session.close()
        await conn.close()


async def get_authenticated_user(
        session_secret: Annotated[str, Header()],
        session: Annotated[AsyncSession, Depends(get_session)],
):
    login_session = await session.scalar(
        select(LoginSession).where(LoginSession.secret == session_secret)
    )
    if login_session is None:
        raise HTTPException(status_code=401, detail="Not authenticated")

    if login_session.expires_at < datetime.utcnow():
        await session.delete(login_session)
        await session.commit()
        raise HTTPException(status_code=401, detail="Session expired")

    user = await session.scalar(select(User).where(User.id == login_session.user_id))
    if user is None:
        raise HTTPException(status_code=401, detail="Not authenticated")
    return user