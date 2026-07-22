from pydantic import BaseModel


class UserCreate(BaseModel):
    login: str
    password: str


class UserResponse(BaseModel):
    model_config = {"from_attributes": True}
    id: int
    login: str
    balance: float