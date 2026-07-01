from typing import Annotated

from fastapi import APIRouter, Depends, Body, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from dependencies import get_session, get_authenticated_user
from models import Event,Bet,User
from schemas.bets import BetCreate, BetResponse

router = APIRouter()
@router.post("/bets", response_model=BetResponse)
async def create_bet(
        user_id:int,
        authenticated_user: Annotated[User, Depends(get_authenticated_user)],
        bet_data: Annotated[BetCreate, Body()],
        session:Annotated[AsyncSession, Depends(get_session)],
):
    if authenticated_user.id != user_id:
        raise HTTPException(status_code=403, detail="Unauthorized")
    stmt = select(Event).where(Event.id == bet_data.event_id)
    event = session.scalar(stmt)
    