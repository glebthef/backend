from decimal import Decimal
from pydantic import BaseModel, Field


class DepositCreate(BaseModel):
    amount: Decimal = Field(ge=50, le=100000)
    return_url: str


class DepositResponse(BaseModel):
    payment_id: str
    confirmation_url: str


class DepositStatusResponse(BaseModel):
    status: str
    balance: float


class DepositSyncResponse(BaseModel):
    credited: float
    pending: int
    balance: float
