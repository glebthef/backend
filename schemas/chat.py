from datetime import datetime
from pydantic import BaseModel, Field


class ChatMessageCreate(BaseModel):
    text: str = Field(min_length=1, max_length=2000)


class ChatMessageResponse(BaseModel):
    model_config = {"from_attributes": True}
    id: int
    user_id: int
    sender: str
    text: str
    created_at: datetime


class ChatThreadResponse(BaseModel):
    user_id: int
    login: str
    last_text: str
    last_sender: str
    last_at: datetime
