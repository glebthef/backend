from decimal import Decimal
from typing import Annotated
from argon2 import PasswordHasher
from fastapi import APIRouter, Depends, Body, HTTPException
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from dependencies import get_session, get_authenticated_user
from models import User
from schemas.user import UserCreate, UserResponse

router = APIRouter()


@router.post("/users", response_model=UserResponse)
async def create_user(
        user_data: Annotated[UserCreate, Body()],
        session: Annotated[AsyncSession, Depends(get_session)],
):
    ph = PasswordHasher()
    new_user = User(login=user_data.login, password_hash=ph.hash(user_data.password), balance=Decimal("0.00"))
    session.add(new_user)
    try:
        await session.commit()
    except IntegrityError:
        await session.rollback()
        raise HTTPException(status_code=400, detail="Login already taken")
    await session.refresh(new_user)
    return new_user


@router.get("/users/{user_id}", response_model=UserResponse)
async def get_user(user_id: int, session: Annotated[AsyncSession, Depends(get_session)]):
    user = await session.scalar(select(User).where(User.id == user_id))
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")
    return user


@router.patch("/users/{user_id}/balance", response_model=UserResponse)
async def update_balance(
        user_id: int,
        amount: Annotated[Decimal, Body(embed=True)],
        authenticated_user: Annotated[User, Depends(get_authenticated_user)],  # теперь требует авторизацию
        session: Annotated[AsyncSession, Depends(get_session)],
):

    if authenticated_user.id != user_id:
        raise HTTPException(403, "Access denied")
    if amount <= 0:
        raise HTTPException(400, "Amount must be positive")
    authenticated_user.balance += amount
    await session.commit()
    await session.refresh(authenticated_user)
    return authenticated_user


@router.delete("/users/{user_id}")
async def delete_user(
        user_id: int,
        authenticated_user: Annotated[User, Depends(get_authenticated_user)],
        session: Annotated[AsyncSession, Depends(get_session)],
):
    if authenticated_user.id != user_id:
        raise HTTPException(403, "Access denied")
    await session.delete(authenticated_user)
    await session.commit()
    return {"detail": "User deleted"}