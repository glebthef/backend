from datetime import datetime
from pydantic import BaseModel, field_serializer, field_validator


class EventCreate(BaseModel):
    sport_slug: str
    league: str
    home: str
    away: str
    starts_at: datetime
    odd_p1: float
    odd_x: float | None = None
    odd_p2: float
    # Тотал
    total_value: float | None = 2.5
    odd_total_over: float | None = None
    odd_total_under: float | None = None
    # Фора
    handicap_value: float | None = 1.0
    odd_handicap_home: float | None = None
    odd_handicap_away: float | None = None

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
        # Stored naive-but-UTC; without an explicit "Z" a browser's Date()
        # parses this as *local* time, silently shifting every live/finished
        # check and displayed kickoff time by the viewer's UTC offset.
        return dt.isoformat() + "Z"


class EventFinish(BaseModel):
    home_score: int
    away_score: int
