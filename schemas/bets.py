from datetime import datetime
from decimal import Decimal
from pydantic import BaseModel, Field, field_serializer


class SingleBetCreate(BaseModel):
    event_id: int
    outcome: str
    amount: Decimal = Field(gt=0)


class ExpressLeg(BaseModel):
    event_id: int
    outcome: str


class ExpressBetCreate(BaseModel):
    amount: Decimal = Field(gt=0)
    legs: list[ExpressLeg] = Field(min_length=2)


class BetLegResponse(BaseModel):
    model_config = {"from_attributes": True}
    id: int
    event_id: int
    outcome: str
    odd: Decimal
    line_value: Decimal | None
    status: str


class BetResponse(BaseModel):
    model_config = {"from_attributes": True}
    id: int
    type: str
    amount: Decimal
    combined_odd: Decimal
    potential_payout: Decimal
    status: str
    created_at: datetime
    legs: list[BetLegResponse] = []

    @field_serializer("created_at")
    def serialize_created_at(self, dt: datetime) -> str:
        return dt.isoformat() + "Z"
