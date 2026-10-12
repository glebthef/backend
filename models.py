import enum
import os
from datetime import datetime
from decimal import Decimal
from sqlalchemy import Enum, ForeignKey, Numeric
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql+asyncpg://postgres:postgres@127.0.0.1:5432/primebet"
)

engine = create_async_engine(DATABASE_URL, echo=False)


class Base(DeclarativeBase):
    pass


class StrEnum(str, enum.Enum):
    def __str__(self):
        return self.value


class BetType(StrEnum):
    SINGLE = "single"
    EXPRESS = "express"


class BetStatus(StrEnum):
    PENDING = "pending"
    WON = "won"
    LOST = "lost"
    REFUND = "refund"
    CANCELLED = "cancelled"


class BetOutcome(StrEnum):
    P1 = "p1"
    X = "x"
    P2 = "p2"
    TOTAL_OVER = "total_over"
    TOTAL_UNDER = "total_under"
    HANDICAP_HOME = "handicap_home"
    HANDICAP_AWAY = "handicap_away"


class EventStatus(StrEnum):
    UPCOMING = "upcoming"
    FINISHED = "finished"


class PaymentStatus(StrEnum):
    PENDING = "pending"
    SUCCEEDED = "succeeded"
    CANCELED = "canceled"


class ChatSender(StrEnum):
    USER = "user"
    SUPPORT = "support"


def pg_enum(cls, name):
    return Enum(cls, name=name, values_callable=lambda e: [m.value for m in e])


class User(Base):
    __tablename__ = "user"
    id: Mapped[int] = mapped_column(primary_key=True)
    login: Mapped[str] = mapped_column(unique=True)
    password_hash: Mapped[str]
    balance: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=Decimal("0.00"))
    is_admin: Mapped[bool] = mapped_column(default=False)
    is_banned: Mapped[bool] = mapped_column(default=False)

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
    status: Mapped[EventStatus] = mapped_column(pg_enum(EventStatus, "event_status"), default=EventStatus.UPCOMING)
    home_score: Mapped[int | None] = mapped_column(default=None)
    away_score: Mapped[int | None] = mapped_column(default=None)
    result: Mapped[str | None] = mapped_column(default=None)


class Bet(Base):
    __tablename__ = "bet"
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("user.id"))
    type: Mapped[BetType] = mapped_column(pg_enum(BetType, "bet_type"), default=BetType.SINGLE)
    amount: Mapped[Decimal] = mapped_column(Numeric(12, 2))
    combined_odd: Mapped[Decimal] = mapped_column(Numeric(10, 4))
    potential_payout: Mapped[Decimal] = mapped_column(Numeric(12, 2))
    status: Mapped[BetStatus] = mapped_column(pg_enum(BetStatus, "bet_status"), default=BetStatus.PENDING)
    created_at: Mapped[datetime] = mapped_column(default=datetime.utcnow)


class BetLeg(Base):
    __tablename__ = "bet_leg"
    id: Mapped[int] = mapped_column(primary_key=True)
    bet_id: Mapped[int] = mapped_column(ForeignKey("bet.id"))
    event_id: Mapped[int] = mapped_column(ForeignKey("event.id"))
    outcome: Mapped[BetOutcome] = mapped_column(pg_enum(BetOutcome, "bet_outcome"))
    odd: Mapped[Decimal] = mapped_column(Numeric(6, 2))
    line_value: Mapped[Decimal | None] = mapped_column(Numeric(6, 2), default=None)
    status: Mapped[BetStatus] = mapped_column(pg_enum(BetStatus, "bet_status"), default=BetStatus.PENDING)


class Payment(Base):
    __tablename__ = "payment"
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("user.id"))
    provider_payment_id: Mapped[str] = mapped_column(unique=True)
    amount: Mapped[Decimal] = mapped_column(Numeric(12, 2))
    status: Mapped[PaymentStatus] = mapped_column(pg_enum(PaymentStatus, "payment_status"), default=PaymentStatus.PENDING)
    created_at: Mapped[datetime] = mapped_column(default=datetime.utcnow)


class ChatMessage(Base):
    __tablename__ = "chat_message"
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("user.id"))
    sender: Mapped[ChatSender] = mapped_column(pg_enum(ChatSender, "chat_sender"))
    text: Mapped[str]
    created_at: Mapped[datetime] = mapped_column(default=datetime.utcnow)


class LoginSession(Base):
    __tablename__ = "login_session"
    id: Mapped[int] = mapped_column(primary_key=True)
    secret: Mapped[str]
    expires_at: Mapped[datetime]
    user_id: Mapped[int] = mapped_column(ForeignKey("user.id"))
