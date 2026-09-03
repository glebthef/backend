from datetime import datetime
from pydantic import BaseModel, computed_field, field_serializer, field_validator

VALID_OUTCOMES = {
    "p1", "x", "p2",
    "total_over", "total_under",
    "handicap_home", "handicap_away",
}

# Same-match outcomes that bet against each other and can never both be true.
# Picking one outcome per group on the same event is a normal same-game
# combo (e.g. p1 + total_over); picking two from the same group is not.
CONFLICT_GROUPS = [
    {"p1", "x", "p2"},
    {"total_over", "total_under"},
    {"handicap_home", "handicap_away"},
]


def _outcomes_conflict(a: str, b: str) -> bool:
    if a == b:
        return True
    return any(a in g and b in g for g in CONFLICT_GROUPS)


class BetCreateSingle(BaseModel):
    event_id: int
    outcome: str
    amount: float

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
    bet_type: str
    amount: float
    combined_odd: float
    status: str
    created_at: datetime
    legs: list[BetLegResponse]

    @field_serializer("created_at")
    def serialize_created_at(self, dt: datetime) -> str:
        return dt.isoformat() + "Z"

    @computed_field
    @property
    def potential_payout(self) -> float:
        return round(self.amount * self.combined_odd, 2)
