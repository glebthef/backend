from typing import Annotated

from fastapi import APIRouter, Depends, Body, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from dependencies import get_session
from models import Event
from schemas.events import EventCreate, EventResponse

router = APIRouter()

@router.post("/events", response_model=EventResponse)
async def create_event(
        event_data: Annotated[EventCreate, Body()],
        session: Annotated[AsyncSession, Depends(get_session)]
):
    new_event = Event(
        sport_id=event_data.sport_id,
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
@router.get("/events/{event_id}", response_model=EventResponse)
async def get_event(
        event_id: int,
        session: Annotated[AsyncSession, Depends(get_session)]
):
    stmt = select(Event).where(Event.id == event_id)
    event = await session.scalar(stmt)

    if event is None:
        raise HTTPException(status_code=404, detail="Event not found")
    return EventResponse(
        id = event.id,
        sport_id=event.sport_id,
        league=event.league,
        home=event.home,
        away=event.away,
        starts_at=event.starts_at,
        odd_p1=event.odd_p1,
        odd_x=event.odd_x,
        odd_p2=event.odd_p2,
        is_active= event.is_active,
    )


@router.get("/events", response_model=list[EventResponse])
async def get_all_events(
        session: Annotated[AsyncSession, Depends(get_session)],
        sport_id: int = None,
):
    stmt = select(Event).where(Event.is_active == True)
    if sport_id is not None:
        stmt = stmt.where(Event.sport_id == sport_id)

    events = await session.scalars(stmt)

    return [
        EventResponse(
            id=e.id, sport_id=e.sport_id, league=e.league,
            home=e.home, away=e.away, starts_at=e.starts_at,
            odd_p1=e.odd_p1, odd_x=e.odd_x, odd_p2=e.odd_p2,
            is_active=e.is_active,
        )
        for e in events
    ]

@router.put("/events/{event_id}", response_model=EventResponse)
async def update_event(
        event_id: int,
        event_data:Annotated[EventCreate, Body()],
        session: Annotated[AsyncSession, Depends(get_session)]
):
    stmt = select(Event).where(Event.id == event_id)
    event = await session.scalar(stmt)
    if event is None:
        raise HTTPException(status_code=404, detail="Event not found")
    event.league = event_data.league
    event.home = event_data.home
    event.away = event_data.away
    event.starts_at = event_data.starts_at
    event.odd_p1 = event_data.odd_p1
    event.odd_x = event_data.odd_x
    event.odd_p2 = event_data.odd_p2
    await session.commit()
    return EventResponse(
        id=event.id, sport_id=event.sport_id, league=event.league,
        home=event.home, away=event.away, starts_at=event.starts_at,
        odd_p1=event.odd_p1, odd_x=event.odd_x, odd_p2=event.odd_p2,
        is_active=event.is_active,
    )


@router.delete("/events/{event_id}")
async def delete_event(
        event_id: int,
        session: Annotated[AsyncSession, Depends(get_session)],
):
    stmt = select(Event).where(Event.id == event_id)
    event = await session.scalar(stmt)
    if event is None:
        raise HTTPException(status_code=404, detail="Event not found")

    event.is_active = False
    await session.commit()

    return {"detail": "Event deactivated"}