from datetime import datetime
from pydantic import BaseModel, field_validator


class EventCreate(BaseModel):
    sport_slug: str
    league: str
    home: str
    away: str
    starts_at: datetime
    odd_p1: float
    odd_x: float | None = None
    odd_p2: float

    @field_validator("starts_at")
    @classmethod
    def remove_timezone(cls, v):
        return v.replace(tzinfo=None)


class EventResponse(BaseModel):
    model_config = {"from_attributes": True}
    id: int
    sport_slug: str
    league: str
    home: str
    away: str
    starts_at: datetime
    odd_p1: float
    odd_x: float | None
    odd_p2: float
    is_active: bool
    status: str
    home_score: int | None
    away_score: int | None
    result: str | None


class EventFinish(BaseModel):
    home_score: int
    away_score: int