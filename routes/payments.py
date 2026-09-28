import os
from decimal import Decimal
from typing import Annotated

import httpx
from fastapi import APIRouter, Body, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from dependencies import get_authenticated_user, get_session
from locks import lock_user
from models import Payment, User
from schemas.payments import DepositCreate, DepositResponse, DepositStatusResponse, DepositSyncResponse

router = APIRouter()

STRIPE_SECRET_KEY = os.getenv("STRIPE_SECRET_KEY")
STRIPE_API_URL = "https://api.stripe.com/v1/checkout/sessions"

# Грубый курс только для того, чтобы тестовая страница Stripe показывала
# правдоподобную сумму в USD — Stripe не поддерживает расчёты в RUB.
# Реальный баланс пользователя как хранился, так и хранится в рублях.
RUB_TO_USD_RATE = Decimal("90")


@router.post("/users/{user_id}/deposits", response_model=DepositResponse)
async def create_deposit(
        user_id: int,
        data: Annotated[DepositCreate, Body()],
        authenticated_user: Annotated[User, Depends(get_authenticated_user)],
        session: Annotated[AsyncSession, Depends(get_session)],
):
    if authenticated_user.id != user_id:
        raise HTTPException(403, "Access denied")
    if not STRIPE_SECRET_KEY:
        raise HTTPException(503, "Платежи временно недоступны")

    usd_cents = int((data.amount / RUB_TO_USD_RATE * 100).to_integral_value())
    usd_cents = max(usd_cents, 50)  # минимум Stripe — $0.50

    form_data = {
        "mode": "payment",
        "success_url": f"{data.return_url}?session_id={{CHECKOUT_SESSION_ID}}",
        "cancel_url": data.return_url,
        "line_items[0][price_data][currency]": "usd",
        "line_items[0][price_data][product_data][name]": f"PrimeBet — пополнение баланса ({data.amount} ₽)",
        "line_items[0][price_data][unit_amount]": str(usd_cents),
        "line_items[0][quantity]": "1",
        "metadata[user_id]": str(user_id),
    }
    async with httpx.AsyncClient() as client:
        try:
            resp = await client.post(
                STRIPE_API_URL,
                data=form_data,
                auth=(STRIPE_SECRET_KEY, ""),
                timeout=15,
            )
        except httpx.HTTPError:
            raise HTTPException(502, "Не удалось связаться со Stripe")

    if resp.status_code >= 400:
        raise HTTPException(502, f"Ошибка Stripe: {resp.text}")
    result = resp.json()

    payment = Payment(
        user_id=user_id,
        provider_payment_id=result["id"],
        amount=data.amount,
        status="pending",
    )
    session.add(payment)
    await session.commit()

    return DepositResponse(payment_id=result["id"], confirmation_url=result["url"])


async def fetch_checkout_session(session_id: str) -> dict | None:
    """Текущее состояние Checkout Session в Stripe или None, если Stripe
    недоступен — тогда платёж просто останется pending до следующей проверки."""
    if not STRIPE_SECRET_KEY:
        return None
    async with httpx.AsyncClient() as client:
        try:
            resp = await client.get(
                f"{STRIPE_API_URL}/{session_id}",
                auth=(STRIPE_SECRET_KEY, ""),
                timeout=15,
            )
        except httpx.HTTPError:
            return None
    return resp.json() if resp.status_code < 400 else None


async def apply_stripe_status(session: AsyncSession, payment: Payment) -> Decimal:
    """Сверяет платёж со Stripe и, если он оплачен, зачисляет деньги.
    Строка платежа должна быть заблокирована вызывающим кодом.
    Возвращает зачисленную сумму (0, если ничего не зачислено)."""
    if payment.status != "pending":
        return Decimal("0")
    remote = await fetch_checkout_session(payment.provider_payment_id)
    if remote is None:
        return Decimal("0")
    if remote.get("payment_status") == "paid":
        user = await lock_user(session, payment.user_id)
        payment.status = "succeeded"
        user.balance += payment.amount
        return payment.amount
    if remote.get("status") == "expired":
        payment.status = "canceled"
    return Decimal("0")


@router.post("/users/{user_id}/deposits/sync", response_model=DepositSyncResponse)
async def sync_deposits(
        user_id: int,
        authenticated_user: Annotated[User, Depends(get_authenticated_user)],
        session: Annotated[AsyncSession, Depends(get_session)],
):
    """Проверяет все незавершённые платежи пользователя. Зачисление не
    зависит от того, вернулся ли пользователь со страницы Stripe в том же
    браузере: достаточно открыть профиль с любого устройства."""
    if authenticated_user.id != user_id:
        raise HTTPException(403, "Access denied")

    # FOR UPDATE: если две проверки пришли одновременно, вторая дождётся
    # первой и уже не увидит зачисленный платёж в статусе pending.
    payments = list(await session.scalars(
        select(Payment)
        .where(Payment.user_id == user_id, Payment.status == "pending")
        .with_for_update()
    ))
    credited = Decimal("0")
    for payment in payments:
        credited += await apply_stripe_status(session, payment)
    await session.commit()

    return DepositSyncResponse(
        credited=float(credited),
        pending=sum(1 for p in payments if p.status == "pending"),
        balance=float(authenticated_user.balance),
    )


@router.get("/users/{user_id}/deposits/{payment_id}", response_model=DepositStatusResponse)
async def get_deposit_status(
        user_id: int,
        payment_id: str,
        authenticated_user: Annotated[User, Depends(get_authenticated_user)],
        session: Annotated[AsyncSession, Depends(get_session)],
):
    if authenticated_user.id != user_id:
        raise HTTPException(403, "Access denied")

    # Блокируем строку платежа, чтобы два почти одновременных запроса
    # статуса (двойной клик, обновление страницы) не зачислили баланс дважды.
    payment = await session.scalar(
        select(Payment)
        .where(Payment.provider_payment_id == payment_id, Payment.user_id == user_id)
        .with_for_update()
    )
    if payment is None:
        raise HTTPException(404, "Payment not found")

    await apply_stripe_status(session, payment)
    await session.commit()

    return DepositStatusResponse(status=payment.status, balance=float(authenticated_user.balance))
