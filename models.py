import os
from datetime import datetime
from decimal import Decimal
from sqlalchemy import ForeignKey, Numeric
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql+asyncpg://postgres:postgres@127.0.0.1:5432/primebet"
)

engine = create_async_engine(DATABASE_URL, echo=False)


class Base(DeclarativeBase):
    pass


class User(Base):
    __tablename__ = "user"
    id: Mapped[int] = mapped_column(primary_key=True)
    login: Mapped[str] = mapped_column(unique=True)
    password_hash: Mapped[str]
    balance: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=Decimal("0.00"))


class Sport(Base):
    __tablename__ = "sport"
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str]
    icon: Mapped[str]
    slug: Mapped[str] = mapped_column(unique=True)


class Event(Base):
    __tablename__ = "event"
    id: Mapped[int] = mapped_column(primary_key=True)
    sport_slug: Mapped[str]
    league: Mapped[str]
    home: Mapped[str]
    away: Mapped[str]
    starts_at: Mapped[datetime]
    odd_p1: Mapped[Decimal] = mapped_column(Numeric(6, 2))
    odd_x: Mapped[Decimal | None] = mapped_column(Numeric(6, 2), default=None)
    odd_p2: Mapped[Decimal] = mapped_column(Numeric(6, 2))
    total_value: Mapped[Decimal | None] = mapped_column(Numeric(6, 2), default=Decimal("2.5"))
    odd_total_over: Mapped[Decimal | None] = mapped_column(Numeric(6, 2), default=None)
    odd_total_under: Mapped[Decimal | None] = mapped_column(Numeric(6, 2), default=None)
    handicap_value: Mapped[Decimal | None] = mapped_column(Numeric(6, 2), default=Decimal("1.0"))
    odd_handicap_home: Mapped[Decimal | None] = mapped_column(Numeric(6, 2), default=None)
    odd_handicap_away: Mapped[Decimal | None] = mapped_column(Numeric(6, 2), default=None)
    is_active: Mapped[bool] = mapped_column(default=True)
    status: Mapped[str] = mapped_column(default="upcoming")
    home_score: Mapped[int | None] = mapped_column(default=None)
    away_score: Mapped[int | None] = mapped_column(default=None)
    result: Mapped[str | None] = mapped_column(default=None)


class Bet(Base):
    __tablename__ = "bet"
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("user.id"))
    type: Mapped[str] = mapped_column(default="single")   # single | express
    amount: Mapped[Decimal] = mapped_column(Numeric(12, 2))
    combined_odd: Mapped[Decimal] = mapped_column(Numeric(10, 4))
    potential_payout: Mapped[Decimal] = mapped_column(Numeric(12, 2))
    status: Mapped[str] = mapped_column(default="pending")  # pending | won | lost
    created_at: Mapped[datetime] = mapped_column(default=datetime.utcnow)


class BetLeg(Base):
    __tablename__ = "bet_leg"
    id: Mapped[int] = mapped_column(primary_key=True)
    bet_id: Mapped[int] = mapped_column(ForeignKey("bet.id"))
    event_id: Mapped[int] = mapped_column(ForeignKey("event.id"))
    outcome: Mapped[str]
    odd: Mapped[Decimal] = mapped_column(Numeric(6, 2))
    status: Mapped[str] = mapped_column(default="pending")  # pending | won | lost


class LoginSession(Base):
    __tablename__ = "login_session"
    id: Mapped[int] = mapped_column(primary_key=True)
    secret: Mapped[str]
    expires_at: Mapped[datetime]
    user_id: Mapped[int] = mapped_column(ForeignKey("user.id"))