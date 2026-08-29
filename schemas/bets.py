from dataclasses import Field
from datetime import datetime
from pydantic import BaseModel, Field



class BetCreate(BaseModel):
    event_id: int
    outcome: str
    amount: float


class BetResponse(BaseModel):
    model_config = {"from_attributes": True}
    id: int
    event_id: int
    outcome: str
    amount: float= Field(gt=0)
    odd: float
    status: str
    created_at: datetime