from datetime import datetime, timedelta
from typing import Annotated
from uuid import uuid4
from argon2 import PasswordHasher
from argon2.exceptions import VerificationError
from fastapi import APIRouter, Depends, HTTPException, Header
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from dependencies import get_session
from models import User, LoginSession

router = APIRouter()


class LoginSessionResponse(BaseModel):
    user_id: int
    secret: str


@router.post("/sessions", response_model=LoginSessionResponse)
async def create_session(
        login: Annotated[str, Header()],
        password: Annotated[str, Header()],
        session: Annotated[AsyncSession, Depends(get_session)],
):
    ph = PasswordHasher()
    stmt = select(User).where(User.login == login)
    user = await session.scalar(stmt)
    if user is None:
        dummy_hash = ("$argon2id$v=19$m=65536,t=3,p=4$1/kKopFhFTmJP0aLfW"
                      "15XQ$fwP4HIJ1Dwtk7Fb5XzW8HDenJ7WroA6fiz0FAynO1cA")
        ph.verify(dummy_hash, "dummy password horse battery")
        raise HTTPException(status_code=401, detail="Not authenticated")
    try:
        ph.verify(user.password_hash, password)
    except VerificationError:
        raise HTTPException(status_code=401, detail="Not authenticated")

    new_session = LoginSession(
        user_id=user.id,
        secret=str(uuid4()),
        expires_at=datetime.utcnow() + timedelta(days=7),
    )
    session.add(new_session)
    await session.commit()
    return LoginSessionResponse(user_id=new_session.user_id, secret=new_session.secret)


@router.delete("/sessions")
async def delete_session(
        session_secret: Annotated[str, Header()],
        session: Annotated[AsyncSession, Depends(get_session)],
):
    login_session = await session.scalar(
        select(LoginSession).where(LoginSession.secret == session_secret)
    )
    if login_session is None:
        raise HTTPException(status_code=404, detail="Session not found")
    await session.delete(login_session)
    await session.commit()
    return {"detail": "Logged out"}