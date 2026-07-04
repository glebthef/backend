from typing import Annotated
from fastapi import APIRouter, Depends, Body, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from dependencies import get_session
from models import User
from argon2 import PasswordHasher
from schemas.user import UserCreate, UserResponse

router = APIRouter()
@router.post("/users", response_model=UserResponse)
async def create_user(
        user_data:Annotated[UserCreate, Body()],
        session:  Annotated[AsyncSession, Depends(get_session)]
):
    ph = PasswordHasher()
    new_user = User(
        login=user_data.login,
        password_hash=ph.hash(user_data.password),
        balance=0.0
    )
    session.add(new_user)
    await session.commit()
    return UserResponse(
        id=new_user.id,
        login=new_user.login,
        balance=new_user.balance,
    )

@router.get("/users/{user_id}", response_model=UserResponse)
async def get_user(
        user_id: int,
        session: Annotated[AsyncSession, Depends(get_session)]
):
    stmt = select(User).where(User.id == user_id)
    user=await session.scalar(stmt)
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")
    return UserResponse(
        id=user.id,
        login=user.login,
        balance=user.balance,
    )
@router.get("/users", response_model=list[UserResponse])
async def get_all_users(session: Annotated[AsyncSession, Depends(get_session)]):
    stmt=select(User)
    user = await session.scalars(stmt)
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")
    return list(user)

@router.patch("/users/{user_id}/balance", response_model=UserResponse)
async def update_balance(
        user_id: int,
        amount: Annotated[float,Body(embed=True)],
        session: Annotated[AsyncSession, Depends(get_session)]
):
    stmt = select(User).where(User.id == user_id)
    user = await session.scalar(stmt)
    if user is  None:
        raise HTTPException(status_code=404, detail="User not found")
    user.balance += amount
    await session.commit()
    return UserResponse(
        id=user.id,
        login=user.login,
        balance=user.balance,
    )
@router.delete("/users/{user_id}", response_model=UserResponse)
async def delete_user(
        user_id: int,
        session: Annotated[AsyncSession, Depends(get_session)]
):
    stmt = select(User).where(User.id == user_id)
    user = await session.scalar(stmt)
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")
    await session.delete(user)
    await session.commit()
    return {"detail": "User deleted"}
