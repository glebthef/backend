from typing import Annotated
from fastapi import APIRouter, Depends, Body, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from dependencies import get_session, get_authenticated_user
from models import Bet, Event, User
from schemas.bets import BetCreate, BetResponse

router = APIRouter()


@router.post("/users/{user_id}/bets", response_model=BetResponse)
async def create_bet(
        user_id: int,
        bet_data: Annotated[BetCreate, Body()],
        authenticated_user: Annotated[User, Depends(get_authenticated_user)],
        session: Annotated[AsyncSession, Depends(get_session)],
):
    if authenticated_user.id != user_id:
        raise HTTPException(403, "Access denied")
    event = await session.scalar(select(Event).where(Event.id == bet_data.event_id))
    if event is None or not event.is_active:
        raise HTTPException(404, "Event not found or inactive")
    if bet_data.outcome not in ("p1", "x", "p2"):
        raise HTTPException(400, "outcome must be p1, x or p2")
    if authenticated_user.balance < bet_data.amount:
        raise HTTPException(400, "Not enough balance")
    odd_map = {"p1": event.odd_p1, "x": event.odd_x, "p2": event.odd_p2}
    odd = odd_map[bet_data.outcome]
    if odd is None:
        raise HTTPException(400, "This outcome is not available")
    authenticated_user.balance -= bet_data.amount
    new_bet = Bet(user_id=user_id, event_id=bet_data.event_id,
                  outcome=bet_data.outcome, amount=bet_data.amount, odd=odd)
    session.add(new_bet)
    await session.commit()
    await session.refresh(new_bet)
    return new_bet


@router.get("/users/{user_id}/bets", response_model=list[BetResponse])
async def get_bets(
        user_id: int,
        authenticated_user: Annotated[User, Depends(get_authenticated_user)],
        session: Annotated[AsyncSession, Depends(get_session)],
):
    if authenticated_user.id != user_id:
        raise HTTPException(403, "Access denied")
    return list(await session.scalars(select(Bet).where(Bet.user_id == user_id)))


@router.delete("/users/{user_id}/bets/{bet_id}")
async def delete_bet(
        user_id: int,
        bet_id: int,
        authenticated_user: Annotated[User, Depends(get_authenticated_user)],
        session: Annotated[AsyncSession, Depends(get_session)],
):
    if authenticated_user.id != user_id:
        raise HTTPException(403, "Access denied")
    bet = await session.scalar(select(Bet).where(Bet.id == bet_id, Bet.user_id == user_id))
    if bet is None:
        raise HTTPException(404, "Bet not found")
    if bet.status != "pending":
        raise HTTPException(400, "Cannot cancel settled bet")
    authenticated_user.balance += bet.amount
    await session.delete(bet)
    await session.commit()
    return {"detail": "Bet cancelled"}