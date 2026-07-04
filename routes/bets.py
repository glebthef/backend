from typing import Annotated

from fastapi import APIRouter, Depends, Body, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from dependencies import get_session, get_authenticated_user
from models import Event,Bet,User
from schemas.bets import BetCreate, BetResponse

router = APIRouter()
@router.post("/users/{user_id}/bets", response_model=BetResponse)
async def create_bet(
        user_id:int,
        authenticated_user: Annotated[User, Depends(get_authenticated_user)],
        bet_data: Annotated[BetCreate, Body()],
        session:Annotated[AsyncSession, Depends(get_session)],
):
    if authenticated_user.id != user_id:
        raise HTTPException(status_code=403, detail="Unauthorized")
    stmt = select(Event).where(Event.id == bet_data.event_id)
    event = await session.scalar(stmt)
    if event is None or not event.is_active:
        raise HTTPException(status_code=403, detail="Unauthorized")
    if bet_data.outcome not in ("p1", "x", "p2"):
        raise HTTPException(status_code=400, detail="Invalid outcome")
    if authenticated_user.balance < bet_data.amount:
        raise HTTPException(status_code=400, detail="Not enough money")
    odd_map = {"p1": event.odd_p1,"x": event.odd_x,"p2":event.odd_p2 }
    odd = odd_map[bet_data.outcome]
    authenticated_user.balance -= bet_data.amount
    new_bet=Bet(
        user_id=user_id,
        event_id=bet_data.event_id,
        outcome=bet_data.bet_data.outcome,
        amount=bet_data.bet_data.amount,
        odd=odd,
    )
    session.add(new_bet)
    await session.commit()
    return BetResponse(
        id=new_bet.id,
        event_id = new_bet.event_id,
        outcome=new_bet.outcome,
        amount= new_bet.amount,
        odd= new_bet.odd,
        created_at= new_bet.created_at,
    )

@router.get("/users/{user_id}/bets", response_model=BetResponse)
async def get_bets(
        user_id:int,
        authenticated_user: Annotated[User, Depends(get_authenticated_user)],
        session:Annotated[AsyncSession, Depends(get_session)],

):
    if authenticated_user.id != user_id:
        raise HTTPException(status_code=403, detail="Unauthorized")
    stmt = select(Bet).where(Bet.user_id == user_id)
    bets = await session.scalars(stmt)
    return[
        BetResponse(
            id=b.id, event=b.event, outcome=b.outcome, amount=b.amount, odd=b.odd,
            created_at=b.created_at,
        )
        for b in bets

    ]
@router.delete("users/{user_id}/bets/{bet_id}", response_model=BetResponse)
async def delete_bets(
        user_id:int,
        bet_id:int,
        authenticated_user: Annotated[User, Depends(get_authenticated_user)],
        session:Annotated[AsyncSession, Depends(get_session)],

):
    if authenticated_user.id != user_id:
        raise HTTPException(status_code=403, detail="Unauthorized")
    stmt = select(Bet).where(Bet.user_id == user_id, Bet.id == bet_id)
    bet = await session.scalar(stmt)
    if bet is None:
        raise HTTPException(status_code=404, detail="Not found")
    authenticated_user.balance += bet.amount
    await session.delete(bet)
    await session.commit()
    return {"detail": "Bet cancelled, amount returned"}



