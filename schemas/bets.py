from datetime import datetime
from decimal import Decimal
from pydantic import BaseModel, Field


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
    status: str

    @field_validator("amount")
    @classmethod
    def amount_positive(cls, v):
        if v <= 0:
            raise ValueError("amount must be greater than 0")
        return v

    @field_validator("outcome")
    @classmethod
    def outcome_valid(cls, v):
        if v not in VALID_OUTCOMES:
            raise ValueError("outcome must be one of: " + ", ".join(sorted(VALID_OUTCOMES)))
        return v


class BetLegCreate(BaseModel):
    event_id: int
    outcome: str

    @field_validator("outcome")
    @classmethod
    def outcome_valid(cls, v):
        if v not in VALID_OUTCOMES:
            raise ValueError("outcome must be one of: " + ", ".join(sorted(VALID_OUTCOMES)))
        return v


class BetCreateExpress(BaseModel):
    legs: list[BetLegCreate]
    amount: float

    @field_validator("amount")
    @classmethod
    def amount_positive(cls, v):
        if v <= 0:
            raise ValueError("amount must be greater than 0")
        return v

    @field_validator("legs")
    @classmethod
    def legs_valid(cls, v):
        if len(v) < 2:
            raise ValueError("express bet requires at least 2 legs")
        by_event: dict[int, list[str]] = {}
        for leg in v:
            by_event.setdefault(leg.event_id, []).append(leg.outcome)
        for event_id, outcomes in by_event.items():
            for i in range(len(outcomes)):
                for j in range(i + 1, len(outcomes)):
                    if _outcomes_conflict(outcomes[i], outcomes[j]):
                        raise ValueError(
                            f"express bet has conflicting outcomes on event {event_id}: "
                            f"{outcomes[i]} and {outcomes[j]}"
                        )
        return v


class BetLegResponse(BaseModel):
    model_config = {"from_attributes": True}
    id: int
    event_id: int
    outcome: str
    odd: float
    line_value: float | None
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