from pydantic import BaseModel
from datetime import datetime
class EventCreate(BaseModel):
    sport_id:int
    league:str
    home:str
    away:str
    starts_at: datetime
    odd_p1: float
    odd_x: float
    odd_p2: float

class EventResponse(BaseModel):
    id:int
    sport_id:int
    league:str
    home:str
    away:str
    starts_at: datetime
    odd_p1: float
    odd_x: float
    odd_p2: float
    is_active: bool
