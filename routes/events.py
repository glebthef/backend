from decimal import Decimal, ROUND_HALF_UP
from typing import Annotated

from fastapi import APIRouter, Depends, Body, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from dependencies import get_session
from models import Event, Bet, BetLeg, User
from schemas.events import EventCreate, EventResponse, EventFinish

router = APIRouter()


@router.post("/events", response_model=EventResponse)
async def create_event(
        event_data: Annotated[EventCreate, Body()],
        session: Annotated[AsyncSession, Depends(get_session)],
):
    new_event = Event(
        sport_slug=event_data.sport_slug,
        league=event_data.league,
        home=event_data.home,
        away=event_data.away,
        starts_at=event_data.starts_at,
        odd_p1=event_data.odd_p1,
        odd_x=event_data.odd_x,
        odd_p2=event_data.odd_p2,
        total_value=event_data.total_value,
        odd_total_over=event_data.odd_total_over,
        odd_total_under=event_data.odd_total_under,
        handicap_value=event_data.handicap_value,
        odd_handicap_home=event_data.odd_handicap_home,
        odd_handicap_away=event_data.odd_handicap_away,
    )
    session.add(new_event)
    await session.commit()
    await session.refresh(new_event)
    return new_event


@router.get("/events", response_model=list[EventResponse])
async def get_all_events(
        session: Annotated[AsyncSession, Depends(get_session)],
        sport_slug: str = None,
):
    stmt = select(Event).where(Event.is_active == True)
    if sport_slug:
        stmt = stmt.where(Event.sport_slug == sport_slug)
    return list(await session.scalars(stmt))


@router.get("/events/{event_id}", response_model=EventResponse)
async def get_event(event_id: int, session: Annotated[AsyncSession, Depends(get_session)]):
    event = await session.scalar(select(Event).where(Event.id == event_id))
    if event is None:
        raise HTTPException(404, "Event not found")
    return event


@router.put("/events/{event_id}", response_model=EventResponse)
async def update_event(
        event_id: int,
        event_data: Annotated[EventCreate, Body()],
        session: Annotated[AsyncSession, Depends(get_session)],
):
    event = await session.scalar(select(Event).where(Event.id == event_id))
    if event is None:
        raise HTTPException(404, "Event not found")
    for field in ['sport_slug', 'league', 'home', 'away', 'starts_at',
                  'odd_p1', 'odd_x', 'odd_p2', 'total_value',
                  'odd_total_over', 'odd_total_under',
                  'handicap_value', 'odd_handicap_home', 'odd_handicap_away']:
        setattr(event, field, getattr(event_data, field))
    await session.commit()
    await session.refresh(event)
    return event


@router.delete("/events/{event_id}")
async def delete_event(event_id: int, session: Annotated[AsyncSession, Depends(get_session)]):
    event = await session.scalar(select(Event).where(Event.id == event_id))
    if event is None:
        raise HTTPException(404, "Event not found")
    event.is_active = False
    await session.commit()
    return {"detail": "Event deactivated"}


@router.post("/events/{event_id}/finish")
async def finish_event(
        event_id: int,
        data: Annotated[EventFinish, Body()],
        session: Annotated[AsyncSession, Depends(get_session)],
):
    event = await session.scalar(select(Event).where(Event.id == event_id))
    if event is None:
        raise HTTPException(404, "Event not found")
    if event.status == "finished":
        raise HTTPException(400, "Event already finished")

    hs, as_ = data.home_score, data.away_score
    total = Decimal(hs + as_)
    main_result = "p1" if hs > as_ else ("p2" if hs < as_ else "x")

    event.home_score = hs
    event.away_score = as_
    event.result = main_result
    event.status = "finished"
    # is_active intentionally left untouched here: it is the admin visibility
    # flag (see delete_event), not a "still open for betting" flag. Betting
    # eligibility is decided from status/starts_at in routes/bets.py.

    legs = list(await session.scalars(
        select(BetLeg).where(BetLeg.event_id == event_id, BetLeg.status == "pending")
    ))

    for leg in legs:
        if leg.outcome in ("p1", "x", "p2"):
            leg.status = "won" if leg.outcome == main_result else "lost"
        elif leg.outcome in ("total_over", "total_under"):
            line = leg.line_value if leg.line_value is not None else (event.total_value or Decimal("2.5"))
            if total == line:
                leg.status = "refund"
            elif leg.outcome == "total_over":
                leg.status = "won" if total > line else "lost"
            else:
                leg.status = "won" if total < line else "lost"
        else:  # handicap_home / handicap_away
            line = leg.line_value if leg.line_value is not None else (event.handicap_value or Decimal("1.0"))
            diff = (Decimal(hs) + line) - Decimal(as_)
            if diff == 0:
                leg.status = "refund"
            elif leg.outcome == "handicap_home":
                leg.status = "won" if diff > 0 else "lost"
            else:
                leg.status = "won" if diff < 0 else "lost"

    await session.flush()

    bets_won, bets_lost, bets_refunded = 0, 0, 0
    for bet_id in {leg.bet_id for leg in legs}:
        bet = await session.scalar(select(Bet).where(Bet.id == bet_id))
        if bet is None or bet.status != "pending":
            continue

        all_legs = list(await session.scalars(select(BetLeg).where(BetLeg.bet_id == bet_id)))
        statuses = [l.status for l in all_legs]

        # A single lost leg kills the whole express immediately -- no need to
        # wait for the bet's other events to finish, the parlay can't win.
        if "lost" in statuses:
            bet.status = "lost"
            bets_lost += 1
            continue

        if "pending" in statuses:
            continue  # other legs of this (express) bet are on events that haven't finished yet

        user = await session.scalar(select(User).where(User.id == bet.user_id).with_for_update())
        if all(s == "refund" for s in statuses):
            bet.status = "refund"
            if user:
                user.balance += bet.amount
            bets_refunded += 1
        else:
            payout_odd = Decimal("1")
            for l in all_legs:
                if l.status == "won":
                    payout_odd *= l.odd
            payout = (bet.amount * payout_odd).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
            bet.status = "won"
            if user:
                user.balance += payout
            bets_won += 1

    await session.commit()

    return {
        "result": main_result,
        "score": f"{hs}:{as_}",
        "total_goals": int(total),
        "legs_won": sum(1 for l in legs if l.status == "won"),
        "legs_lost": sum(1 for l in legs if l.status == "lost"),
        "legs_refunded": sum(1 for l in legs if l.status == "refund"),
        "bets_won": bets_won,
        "bets_lost": bets_lost,
        "bets_refunded": bets_refunded,
    }
