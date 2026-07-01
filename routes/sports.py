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
        session:Annotated[AsyncSession, Depends(get_session)]
):
    new_sport=Sport(
        name=sport_data.name,
        icon=sport_data.icon,
        slug=sport_data.slug,
    )
    session.add(new_sport)
    await session.commit()
    return SportResponse(
        id=new_sport.id,
        name=new_sport.name,
        icon=new_sport.icon,
        slug=new_sport.slug,
    )

@router.get("/sports/{sport_id}", response_model=SportResponse)
async def get_sport(
        sport_id: int,
        session: Annotated[AsyncSession, Depends(get_session)]
):
    stmt = select(Sport).where(Sport.id == sport_id)
    sport = await session.scalar(stmt)
    await session.commit()
    return SportResponse(
        id=sport.id,
        name=sport.name,
        icon=sport.icon,
        slug=sport.slug,
    )
@router.get("/sports", response_model=SportResponse)
async def get_sports(
        session: Annotated[AsyncSession, Depends(get_session)]
):
    stmt = select(Sport)
    sports = await session.scalars(stmt)
    await session.commit()
    return sports

@router.put("/sports/{sport_id}", response_model=SportResponse)
async def update_sport(
        sport_id: int,
        sport_data: Annotated[SportCreate, Body()],
        session: Annotated[AsyncSession, Depends(get_session)]
):
    stmt = select(Sport).where(Sport.id == sport_id)
    sport = await session.scalar(stmt)
    if sport is None:
        raise HTTPException(status_code=404, detail="Sport not found")
    sport.name = sport_data.name
    sport.icon = sport_data.icon
    sport.slug = sport_data.slug
    await session.commit()
    return SportResponse(
        name=sport.name,
        icon=sport.icon,
        slug=sport.slug,
    )
@router.delete("/sports/{sport_id}", response_model=SportResponse)
async def delete_sport(
        sport_id: int,
        session: Annotated[AsyncSession, Depends(get_session)]
):
    stmt = select(Sport).where(Sport.id == sport_id)
    sport = await session.scalar(stmt)
    if sport is None:
        raise HTTPException(status_code=404, detail="Sport not found")
    await session.delete(sport)
    await session.commit()
    return {"detail": "Sport deleted"}