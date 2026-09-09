from decimal import Decimal
from pydantic import BaseModel, Field


class DepositCreate(BaseModel):
    # Внутренний баланс у нас в рублях; Stripe в тестовом режиме не
    # поддерживает RUB (Stripe ушёл из России), поэтому сама тестовая
    # страница оплаты показывает условный эквивалент в USD — см. routes/payments.py.
    amount: Decimal = Field(ge=50, le=100000)
    # Куда Stripe вернёт браузер после (тестовой) оплаты, например
    # https://.../profile — фронт сам хранит id сессии и опрашивает её статус,
    # когда пользователь возвращается на эту страницу.
    return_url: str


class DepositResponse(BaseModel):
    payment_id: str
    confirmation_url: str


class DepositStatusResponse(BaseModel):
    status: str
    balance: float
