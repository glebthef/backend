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
    stmt = select(LoginSession).where(LoginSession.secret==session_secret)
    login_session = await session.scalar(stmt)
    if login_session is None:
        raise HTTPException(status_code=401 , detail="Authenticated")
    stmt = select(User).where(User.id == login_session.user_id)
    authenticated_user = await session.scalar(stmt)
    return authenticated_user