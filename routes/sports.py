from typing import Annotated
from fastapi import APIRouter, Depends, Body, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from dependencies import get_session
from models import Sport
from schemas.sports import SportCreate, SportResponse

router = APIRouter()


@router.post("/sports", response_model=SportResponse)
async def create_sport(
        sport_data: Annotated[SportCreate, Body()],
        session: Annotated[AsyncSession, Depends(get_session)],
):
    new_sport = Sport(**sport_data.model_dump())
    session.add(new_sport)
    await session.commit()
    await session.refresh(new_sport)
    return new_sport


@router.get("/sports", response_model=list[SportResponse])
async def get_all_sports(session: Annotated[AsyncSession, Depends(get_session)]):
    return list(await session.scalars(select(Sport)))


@router.get("/sports/{sport_id}", response_model=SportResponse)
async def get_sport(sport_id: int, session: Annotated[AsyncSession, Depends(get_session)]):
    sport = await session.scalar(select(Sport).where(Sport.id == sport_id))
    if sport is None:
        raise HTTPException(404, "Sport not found")
    return sport


@router.put("/sports/{sport_id}", response_model=SportResponse)
async def update_sport(
        sport_id: int,
        sport_data: Annotated[SportCreate, Body()],
        session: Annotated[AsyncSession, Depends(get_session)],
):
    sport = await session.scalar(select(Sport).where(Sport.id == sport_id))
    if sport is None:
        raise HTTPException(404, "Sport not found")
    for k, v in sport_data.model_dump().items():
        setattr(sport, k, v)
    await session.commit()
    await session.refresh(sport)
    return sport


@router.delete("/sports/{sport_id}")
async def delete_sport(sport_id: int, session: Annotated[AsyncSession, Depends(get_session)]):
    sport = await session.scalar(select(Sport).where(Sport.id == sport_id))
    if sport is None:
        raise HTTPException(404, "Sport not found")
    await session.delete(sport)
    await session.commit()
    return {"detail": "Sport deleted"}