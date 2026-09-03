from typing import Annotated
from fastapi import APIRouter, Depends, Body, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import selectinload
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
        raise HTTPException(status_code=404, detail="Event not found")
    return event


@router.put("/events/{event_id}", response_model=EventResponse)
async def update_event(
        event_id: int,
        event_data: Annotated[EventCreate, Body()],
        session: Annotated[AsyncSession, Depends(get_session)],
):
    event = await session.scalar(select(Event).where(Event.id == event_id))
    if event is None:
        raise HTTPException(status_code=404, detail="Event not found")
    event.sport_slug = event_data.sport_slug
    event.league = event_data.league
    event.home = event_data.home
    event.away = event_data.away
    event.starts_at = event_data.starts_at
    event.odd_p1 = event_data.odd_p1
    event.odd_x = event_data.odd_x
    event.odd_p2 = event_data.odd_p2
    event.total_value = event_data.total_value
    event.odd_total_over = event_data.odd_total_over
    event.odd_total_under = event_data.odd_total_under
    event.handicap_value = event_data.handicap_value
    event.odd_handicap_home = event_data.odd_handicap_home
    event.odd_handicap_away = event_data.odd_handicap_away
    await session.commit()
    await session.refresh(event)
    return event


@router.delete("/events/{event_id}")
async def delete_event(event_id: int, session: Annotated[AsyncSession, Depends(get_session)]):
    event = await session.scalar(select(Event).where(Event.id == event_id))
    if event is None:
        raise HTTPException(status_code=404, detail="Event not found")
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

    result = "p1" if data.home_score > data.away_score else ("p2" if data.home_score < data.away_score else "x")
    total_goals = data.home_score + data.away_score
    event.home_score = data.home_score
    event.away_score = data.away_score
    event.result = result
    event.status = "finished"
    # is_active intentionally left untouched here: it is the admin visibility
    # flag (see delete_event), not a "still open for betting" flag. Betting
    # eligibility is decided from status/starts_at in routes/bets.py.

    legs = list(await session.scalars(
        select(BetLeg).where(BetLeg.event_id == event_id, BetLeg.status == "pending")
    ))
    for leg in legs:
        if leg.outcome in ("p1", "x", "p2"):
            leg.status = "won" if leg.outcome == result else "lost"
        elif leg.outcome in ("total_over", "total_under"):
            line = leg.line_value
            if line is None or total_goals == line:
                leg.status = "refund"
            elif leg.outcome == "total_over":
                leg.status = "won" if total_goals > line else "lost"
            else:
                leg.status = "won" if total_goals < line else "lost"
        else:  # handicap_home / handicap_away
            line = leg.line_value or 0.0
            diff = (data.home_score + line) - data.away_score
            if diff == 0:
                leg.status = "refund"
            elif leg.outcome == "handicap_home":
                leg.status = "won" if diff > 0 else "lost"
            else:
                leg.status = "won" if diff < 0 else "lost"

    await session.flush()

    won, lost, refunded = 0, 0, 0
    for bet_id in {leg.bet_id for leg in legs}:
        bet = await session.scalar(
            select(Bet).where(Bet.id == bet_id).options(selectinload(Bet.legs))
        )
        if bet.status != "pending" or any(l.status == "pending" for l in bet.legs):
            continue  # other legs of this (express) bet are on events that haven't finished yet

        if any(l.status == "lost" for l in bet.legs):
            bet.status = "lost"
            lost += 1
            continue

        user = await session.scalar(select(User).where(User.id == bet.user_id).with_for_update())
        if all(l.status == "refund" for l in bet.legs):
            bet.status = "refund"
            if user:
                user.balance += bet.amount
            refunded += 1
        else:
            payout_odd = 1.0
            for l in bet.legs:
                if l.status == "won":
                    payout_odd *= l.odd
            bet.status = "won"
            if user:
                user.balance += bet.amount * payout_odd
            won += 1

    await session.commit()
    return {"result": result, "score": f"{data.home_score}:{data.away_score}",
            "bets_won": won, "bets_lost": lost, "bets_refunded": refunded}