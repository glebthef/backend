from pydantic import BaseModel
from datetime import datetime

class BetCreate(BaseModel):
    event_id: int
    outcome: str
    amount: float

class BetResponse(BaseModel):
    id: int
    event_id: int
    outcome: str
    amount: float
    odd: float
    created_at: datetime
