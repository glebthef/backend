from datetime import datetime
from typing import Annotated

from pydantic import BaseModel, Field, field_serializer, field_validator

Odd = Annotated[float, Field(gt=1, le=1000)]


class EventCreate(BaseModel):
    sport_slug: str
    league: str
    home: str
    away: str
    starts_at: datetime
    odd_p1: Odd
    odd_x: Odd | None = None
    odd_p2: Odd
    # Тотал
    total_value: float | None = Field(default=2.5, gt=0)
    odd_total_over: Odd | None = None
    odd_total_under: Odd | None = None
    # Фора
    handicap_value: float | None = 1.0
    odd_handicap_home: Odd | None = None
    odd_handicap_away: Odd | None = None

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
    total_value: float | None
    odd_total_over: float | None
    odd_total_under: float | None
    handicap_value: float | None
    odd_handicap_home: float | None
    odd_handicap_away: float | None
    is_active: bool
    status: str
    home_score: int | None
    away_score: int | None
    result: str | None

    @field_serializer("starts_at")
    def serialize_starts_at(self, dt: datetime) -> str:
        return dt.isoformat() + "Z"


class EventFinish(BaseModel):
    home_score: int
    away_score: int
