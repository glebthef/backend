from decimal import Decimal, ROUND_HALF_UP
from typing import Annotated

from fastapi import APIRouter, Depends, Body, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession

from dependencies import get_session, get_authenticated_user
from models import Bet, BetLeg, Event, User
from schemas.bets import SingleBetCreate, ExpressBetCreate, BetResponse

router = APIRouter()

VALID_OUTCOMES = {"p1", "x", "p2", "total_over", "total_under", "handicap_home", "handicap_away"}


CONFLICT_GROUPS = [
    {"p1", "x", "p2"},
    {"total_over", "total_under"},
    {"handicap_home", "handicap_away"},
]


def get_odd_for_outcome(event: Event, outcome: str) -> Decimal | None:
    mapping = {
        "p1":            event.odd_p1,
        "x":             event.odd_x,
        "p2":            event.odd_p2,
        "total_over":    event.odd_total_over,
        "total_under":   event.odd_total_under,
        "handicap_home": event.odd_handicap_home,
        "handicap_away": event.odd_handicap_away,
    }
    return mapping.get(outcome)


def check_conflict(a: str, b: str) -> bool:
    return any(a in g and b in g for g in CONFLICT_GROUPS)


@router.post("/users/{user_id}/bets/single", response_model=BetResponse)
async def create_single_bet(
        user_id: int,
        bet_data: Annotated[SingleBetCreate, Body()],
        authenticated_user: Annotated[User, Depends(get_authenticated_user)],
        session: Annotated[AsyncSession, Depends(get_session)],
):
    if authenticated_user.id != user_id:
        raise HTTPException(403, "Access denied")

    event = await session.scalar(select(Event).where(Event.id == bet_data.event_id))
    if event is None or not event.is_active:
        raise HTTPException(404, "Event not found or inactive")

    if bet_data.outcome not in VALID_OUTCOMES:
        raise HTTPException(400, "Invalid outcome")

    odd = get_odd_for_outcome(event, bet_data.outcome)
    if odd is None:
        raise HTTPException(400, f"Outcome '{bet_data.outcome}' not available")

    amount = bet_data.amount.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

    if authenticated_user.balance < amount:
        raise HTTPException(400, "Not enough balance")


    existing = await session.scalar(
        select(BetLeg).join(Bet).where(
            Bet.user_id == user_id,
            Bet.status == "pending",
            BetLeg.event_id == bet_data.event_id,
            BetLeg.outcome == bet_data.outcome,
        )
    )
    if existing:
        raise HTTPException(400, "Вы уже сделали ставку на этот исход")

    potential = (amount * odd).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

    authenticated_user.balance -= amount

    bet = Bet(
        user_id=user_id,
        type="single",
        amount=amount,
        combined_odd=odd,
        potential_payout=potential,
    )
    session.add(bet)
    await session.flush()

    leg = BetLeg(bet_id=bet.id, event_id=bet_data.event_id, outcome=bet_data.outcome, odd=odd)
    session.add(leg)

    await session.commit()
    await session.refresh(bet)


    legs = list(await session.scalars(select(BetLeg).where(BetLeg.bet_id == bet.id)))
    return _bet_to_response(bet, legs)


@router.post("/users/{user_id}/bets/express", response_model=BetResponse)
async def create_express_bet(
        user_id: int,
        bet_data: Annotated[ExpressBetCreate, Body()],
        authenticated_user: Annotated[User, Depends(get_authenticated_user)],
        session: Annotated[AsyncSession, Depends(get_session)],
):
    if authenticated_user.id != user_id:
        raise HTTPException(403, "Access denied")

    if len(bet_data.legs) < 2:
        raise HTTPException(400, "Express requires at least 2 legs")

    amount = bet_data.amount.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

    validated_legs = []
    seen_per_event: dict[int, list[str]] = {}

    for leg in bet_data.legs:
        if leg.outcome not in VALID_OUTCOMES:
            raise HTTPException(400, f"Invalid outcome: {leg.outcome}")

        event = await session.scalar(select(Event).where(Event.id == leg.event_id))
        if event is None or not event.is_active:
            raise HTTPException(404, f"Event {leg.event_id} not found or inactive")

        odd = get_odd_for_outcome(event, leg.outcome)
        if odd is None:
            raise HTTPException(400, f"Outcome '{leg.outcome}' not available for event {leg.event_id}")

        if leg.event_id in seen_per_event:
            for existing_outcome in seen_per_event[leg.event_id]:
                if check_conflict(existing_outcome, leg.outcome):
                    raise HTTPException(
                        400,
                        f"Conflicting outcomes for event {leg.event_id}: "
                        f"'{existing_outcome}' and '{leg.outcome}'"
                    )
            seen_per_event[leg.event_id].append(leg.outcome)
        else:
            seen_per_event[leg.event_id] = [leg.outcome]

        existing = await session.scalar(
            select(BetLeg).join(Bet).where(
                Bet.user_id == user_id,
                Bet.status == "pending",
                BetLeg.event_id == leg.event_id,
                BetLeg.outcome == leg.outcome,
            )
        )
        if existing:
            raise HTTPException(400, f"Вы уже сделали ставку на исход '{leg.outcome}' события {leg.event_id}")

        validated_legs.append((leg.event_id, leg.outcome, odd))

    combined_odd = Decimal("1")
    for _, _, odd in validated_legs:
        combined_odd *= odd
    combined_odd = combined_odd.quantize(Decimal("0.0001"), rounding=ROUND_HALF_UP)

    potential = (amount * combined_odd).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

    if authenticated_user.balance < amount:
        raise HTTPException(400, "Not enough balance")

    authenticated_user.balance -= amount

    bet = Bet(
        user_id=user_id,
        type="express",
        amount=amount,
        combined_odd=combined_odd,
        potential_payout=potential,
    )
    session.add(bet)
    await session.flush()

    for event_id, outcome, odd in validated_legs:
        leg = BetLeg(bet_id=bet.id, event_id=event_id, outcome=outcome, odd=odd)
        session.add(leg)

    await session.commit()
    await session.refresh(bet)

    legs = list(await session.scalars(select(BetLeg).where(BetLeg.bet_id == bet.id)))
    return _bet_to_response(bet, legs)


@router.get("/users/{user_id}/bets", response_model=list[BetResponse])
async def get_bets(
        user_id: int,
        authenticated_user: Annotated[User, Depends(get_authenticated_user)],
        session: Annotated[AsyncSession, Depends(get_session)],
):
    if authenticated_user.id != user_id:
        raise HTTPException(403, "Access denied")

    bets = list(await session.scalars(
        select(Bet).where(Bet.user_id == user_id).order_by(Bet.created_at.desc())
    ))

    result = []
    for bet in bets:
        legs = list(await session.scalars(select(BetLeg).where(BetLeg.bet_id == bet.id)))
        result.append(_bet_to_response(bet, legs))
    return result


@router.delete("/users/{user_id}/bets/{bet_id}")
async def cancel_bet(
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


def _bet_to_response(bet: Bet, legs: list[BetLeg]) -> BetResponse:
    return BetResponse(
        id=bet.id,
        type=bet.type,
        amount=bet.amount,
        combined_odd=bet.combined_odd,
        potential_payout=bet.potential_payout,
        status=bet.status,
        created_at=bet.created_at,
        legs=[BetLegResponse(
            id=l.id, event_id=l.event_id,
            outcome=l.outcome, odd=l.odd, status=l.status
        ) for l in legs],
    )


from schemas.bets import BetLegResponse