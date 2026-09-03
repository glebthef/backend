from datetime import datetime
from typing import Annotated
from fastapi import APIRouter, Depends, Body, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession
from dependencies import get_session, get_authenticated_user
from models import Bet, BetLeg, Event, User
from schemas.bets import BetCreateSingle, BetCreateExpress, BetResponse

router = APIRouter()

OUTCOME_ODD_FIELD = {
    "p1": "odd_p1",
    "x": "odd_x",
    "p2": "odd_p2",
    "total_over": "odd_total_over",
    "total_under": "odd_total_under",
    "handicap_home": "odd_handicap_home",
    "handicap_away": "odd_handicap_away",
}
OUTCOME_LINE_FIELD = {
    "total_over": "total_value",
    "total_under": "total_value",
    "handicap_home": "handicap_value",
    "handicap_away": "handicap_value",
}


async def _load_and_price_leg(session: AsyncSession, event_id: int, outcome: str) -> tuple[Event, float, float | None]:
    event = await session.scalar(select(Event).where(Event.id == event_id))
    if event is None or not event.is_active:
        raise HTTPException(404, f"Event {event_id} not found or inactive")
    if event.status == "finished":
        raise HTTPException(400, f"Event {event_id} has already finished")
    if event.starts_at <= datetime.utcnow():
        raise HTTPException(400, f"Event {event_id} has already started")
    odd = getattr(event, OUTCOME_ODD_FIELD[outcome])
    if odd is None:
        raise HTTPException(400, f"Outcome {outcome} is not available for event {event_id}")
    line_value = getattr(event, OUTCOME_LINE_FIELD[outcome]) if outcome in OUTCOME_LINE_FIELD else None
    return event, odd, line_value


async def _lock_user(session: AsyncSession, user_id: int) -> User:
    # populate_existing is required: get_authenticated_user already loaded this
    # User into the session's identity map *before* the lock was taken, so
    # without it SQLAlchemy would hand back that stale (pre-lock) balance
    # instead of the fresh, just-locked row.
    stmt = (
        select(User).where(User.id == user_id)
        .with_for_update()
        .execution_options(populate_existing=True)
    )
    return await session.scalar(stmt)


@router.post("/users/{user_id}/bets/single", response_model=BetResponse)
async def create_single_bet(
        user_id: int,
        bet_data: Annotated[BetCreateSingle, Body()],
        authenticated_user: Annotated[User, Depends(get_authenticated_user)],
        session: Annotated[AsyncSession, Depends(get_session)],
):
    if authenticated_user.id != user_id:
        raise HTTPException(403, "Access denied")

    event, odd, line_value = await _load_and_price_leg(session, bet_data.event_id, bet_data.outcome)

    user = await _lock_user(session, user_id)
    if user.balance < bet_data.amount:
        raise HTTPException(400, "Not enough balance")
    user.balance -= bet_data.amount

    new_bet = Bet(user_id=user_id, bet_type="single", amount=bet_data.amount, combined_odd=odd)
    session.add(new_bet)
    await session.flush()
    session.add(BetLeg(bet_id=new_bet.id, event_id=event.id, outcome=bet_data.outcome, odd=odd, line_value=line_value))

    await session.commit()
    return await session.scalar(
        select(Bet).where(Bet.id == new_bet.id).options(selectinload(Bet.legs))
    )


@router.post("/users/{user_id}/bets/express", response_model=BetResponse)
async def create_express_bet(
        user_id: int,
        bet_data: Annotated[BetCreateExpress, Body()],
        authenticated_user: Annotated[User, Depends(get_authenticated_user)],
        session: Annotated[AsyncSession, Depends(get_session)],
):
    if authenticated_user.id != user_id:
        raise HTTPException(403, "Access denied")

    priced_legs = []
    combined_odd = 1.0
    for leg in bet_data.legs:
        event, odd, line_value = await _load_and_price_leg(session, leg.event_id, leg.outcome)
        priced_legs.append((event, leg.outcome, odd, line_value))
        combined_odd *= odd

    user = await _lock_user(session, user_id)
    if user.balance < bet_data.amount:
        raise HTTPException(400, "Not enough balance")
    user.balance -= bet_data.amount

    new_bet = Bet(user_id=user_id, bet_type="express", amount=bet_data.amount, combined_odd=combined_odd)
    session.add(new_bet)
    await session.flush()
    for event, outcome, odd, line_value in priced_legs:
        session.add(BetLeg(bet_id=new_bet.id, event_id=event.id, outcome=outcome, odd=odd, line_value=line_value))

    await session.commit()
    return await session.scalar(
        select(Bet).where(Bet.id == new_bet.id).options(selectinload(Bet.legs))
    )


@router.get("/users/{user_id}/bets", response_model=list[BetResponse])
async def get_bets(
        user_id: int,
        authenticated_user: Annotated[User, Depends(get_authenticated_user)],
        session: Annotated[AsyncSession, Depends(get_session)],
):
    if authenticated_user.id != user_id:
        raise HTTPException(403, "Access denied")
    stmt = select(Bet).where(Bet.user_id == user_id).options(selectinload(Bet.legs))
    return list(await session.scalars(stmt))


@router.delete("/users/{user_id}/bets/{bet_id}")
async def cancel_bet(
        user_id: int,
        bet_id: int,
        authenticated_user: Annotated[User, Depends(get_authenticated_user)],
        session: Annotated[AsyncSession, Depends(get_session)],
):
    if authenticated_user.id != user_id:
        raise HTTPException(403, "Access denied")
    bet = await session.scalar(
        select(Bet).where(Bet.id == bet_id, Bet.user_id == user_id).options(selectinload(Bet.legs))
    )
    if bet is None:
        raise HTTPException(404, "Bet not found")
    if bet.status != "pending":
        raise HTTPException(400, "Cannot cancel a settled bet")

    user = await _lock_user(session, user_id)
    user.balance += bet.amount
    bet.status = "cancelled"
    for leg in bet.legs:
        leg.status = "cancelled"

    await session.commit()
    return {"detail": "Bet cancelled"}
