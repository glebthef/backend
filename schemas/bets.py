from datetime import datetime
from decimal import Decimal
from pydantic import BaseModel, Field, field_serializer


MIN_BET = 10
MAX_BET = 100_000


class SingleBetCreate(BaseModel):
    event_id: int
    outcome: str
    amount: Decimal = Field(ge=MIN_BET, le=MAX_BET)
    # Коэффициент, который пользователь видел в купоне. Необязателен, но если
    # передан и не совпадает с текущим — ставка отклоняется (409).
    expected_odd: Decimal | None = None


class ExpressLeg(BaseModel):
    event_id: int
    outcome: str
    expected_odd: Decimal | None = None


class ExpressBetCreate(BaseModel):
    amount: Decimal = Field(ge=MIN_BET, le=MAX_BET)
    legs: list[ExpressLeg] = Field(min_length=2)


class BetLegEvent(BaseModel):
    """Матч, на который сделан исход — чтобы история ставок показывала
    команды, время начала, статус и счёт, а не только номер события."""
    model_config = {"from_attributes": True}
    id: int
    sport_slug: str
    league: str
    home: str
    away: str
    starts_at: datetime
    status: str
    is_active: bool
    home_score: int | None
    away_score: int | None

    @field_serializer("starts_at")
    def serialize_starts_at(self, dt: datetime) -> str:
        return dt.isoformat() + "Z"


class BetLegResponse(BaseModel):
    model_config = {"from_attributes": True}
    id: int
    event_id: int
    outcome: str
    odd: Decimal
    line_value: Decimal | None
    status: str
    event: BetLegEvent | None = None


class BetResponse(BaseModel):
    model_config = {"from_attributes": True}
    id: int
    type: str
    amount: Decimal
    combined_odd: Decimal
    potential_payout: Decimal
    # Фактически начисленная сумма: None, пока ставка не рассчитана.
    actual_payout: Decimal | None = None
    status: str
    created_at: datetime
    legs: list[BetLegResponse] = []

    @field_serializer("created_at")
    def serialize_created_at(self, dt: datetime) -> str:
        return dt.isoformat() + "Z"
