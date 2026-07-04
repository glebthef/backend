from typing import Annotated
from argon2 import PasswordHasher
from fastapi import APIRouter, Depends, HTTPException, Body, Header
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from models import User, LoginSession
from dependencies import get_session
from uuid import uuid4
from datetime import datetime, timedelta
router = APIRouter()

class LoginSessionResponse(BaseModel):
    user_id: int
    secret: str
@router.post(
    "/sessions",
    response_model=LoginSessionResponse,
)
async def create_session(
        login: Annotated[str, Header()],
        password: Annotated[str, Header()],
        session: Annotated[AsyncSession, Depends(get_session)],
):
    ph = PasswordHasher()

    # Идентификация
    # 1. получить пользователя по логину
    stmt = select(User).where(User.login == login)
    user = await session.scalar(stmt)
    if user is None:
        dummy_hash = ("$argon2id$v=19$m=65536,t=3,p=4$1/kKopFhFTmJP0aLfW"
                      "15XQ$fwP4HIJ1Dwtk7Fb5XzW8HDenJ7WroA6fiz0FAynO1cA")
        dummy_password = "dummy password horse battery"
        ph.verify(dummy_hash, dummy_password)
        raise HTTPException(status_code=401, detail="Not authenticated")

    # Аутентификация
    # 2. проверить пароль
    if not ph.verify(user.password_hash, password):
        raise HTTPException(status_code=401, detail="Not authenticated")

    # Создаём сессию в БД
    new_login_session = LoginSession(
        user_id=user.id,
        secret=str(uuid4()),
        expires_at=datetime.utcnow() + timedelta(days=7),
    )
    session.add(new_login_session)
    await session.commit()

    return LoginSessionResponse(
        user_id=new_login_session.user_id,
        secret=new_login_session.secret,
    )