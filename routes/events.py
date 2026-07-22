from typing import Annotated
from fastapi import APIRouter, Depends, Body, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from dependencies import get_session
from models import Event, Bet, User
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
    event.home_score = data.home_score
    event.away_score = data.away_score
    event.result = result
    event.status = "finished"
    event.is_active = False

    bets = list(await session.scalars(select(Bet).where(Bet.event_id == event_id)))
    won, lost = 0, 0
    for bet in bets:
        if bet.outcome == result:
            bet.status = "won"
            u = await session.scalar(select(User).where(User.id == bet.user_id))
            if u:
                u.balance += bet.amount * bet.odd
            won += 1
        else:
            bet.status = "lost"
            lost += 1

    await session.commit()
    return {"result": result, "score": f"{data.home_score}:{data.away_score}",
            "bets_won": won, "bets_lost": lost}