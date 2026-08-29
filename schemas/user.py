from pydantic import BaseModel, Field


class UserCreate(BaseModel):
    login: str = Field(min_length=3, max_length=50)
    password: str = Field(min_length=6, max_length=50)


class UserResponse(BaseModel):
    model_config = {"from_attributes": True}
    id: int
    login: str
    balance: float