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
    for field in ['sport_slug','league','home','away','starts_at',
                  'odd_p1','odd_x','odd_p2','total_value',
                  'odd_total_over','odd_total_under',
                  'handicap_value','odd_handicap_home','odd_handicap_away']:
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

    hs = data.home_score
    as_ = data.away_score
    total = hs + as_

    # Определяем результаты всех типов исходов
    result_map = {
        # Основной исход
        "p1": hs > as_,
        "x":  hs == as_,
        "p2": hs < as_,
        # Тотал
        "total_over":  total > (event.total_value or 2.5),
        "total_under": total < (event.total_value or 2.5),
        # Фора (handicap_value применяется к хозяевам)
        "handicap_home": (hs + (event.handicap_value or 1.0)) > as_,
        "handicap_away": (hs + (event.handicap_value or 1.0)) < as_,
    }

    # Определяем result для основного исхода
    main_result = "p1" if hs > as_ else ("p2" if hs < as_ else "x")

    event.home_score = hs
    event.away_score = as_
    event.result = main_result
    event.status = "finished"
    event.is_active = False

    bets = list(await session.scalars(select(Bet).where(Bet.event_id == event_id)))
    won, lost = 0, 0
    for bet in bets:
        # Для основных исходов p1/x/p2
        if bet.outcome in ("p1", "x", "p2"):
            bet_won = (bet.outcome == main_result)
        # Для тотала и форы
        elif bet.outcome in result_map:
            bet_won = result_map[bet.outcome]
        else:
            bet_won = False

        if bet_won:
            bet.status = "won"
            u = await session.scalar(select(User).where(User.id == bet.user_id))
            if u:
                u.balance += bet.amount * bet.odd
            won += 1
        else:
            bet.status = "lost"
            lost += 1

    await session.commit()
    return {
        "result": main_result,
        "score": f"{hs}:{as_}",
        "total_goals": total,
        "total_result": "over" if result_map["total_over"] else "under",
        "bets_won": won,
        "bets_lost": lost,
    }