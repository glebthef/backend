from datetime import datetime
from sqlalchemy import ForeignKey
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

engine = create_async_engine(
    "postgresql+asyncpg://postgres:6996@127.0.0.1:5432/primebet",
    echo=True,
)

class Base(DeclarativeBase):
    pass

class User(Base):
    __tablename__ = "user"
    id: Mapped[int] = mapped_column(primary_key=True)
    login: Mapped[str] = mapped_column(unique=True)
    password_hash: Mapped[str]
    balance: Mapped[float] = mapped_column(default=0.0)

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

    # Основные коэффициенты
    odd_p1: Mapped[float]
    odd_x: Mapped[float | None] = mapped_column(default=None)
    odd_p2: Mapped[float]

    # Тотал
    total_value: Mapped[float | None] = mapped_column(default=2.5)
    odd_total_over: Mapped[float | None] = mapped_column(default=None)
    odd_total_under: Mapped[float | None] = mapped_column(default=None)

    # Фора
    handicap_value: Mapped[float | None] = mapped_column(default=1.0)
    odd_handicap_home: Mapped[float | None] = mapped_column(default=None)
    odd_handicap_away: Mapped[float | None] = mapped_column(default=None)

    is_active: Mapped[bool] = mapped_column(default=True)
    status: Mapped[str] = mapped_column(default="upcoming")
    home_score: Mapped[int | None] = mapped_column(default=None)
    away_score: Mapped[int | None] = mapped_column(default=None)
    result: Mapped[str | None] = mapped_column(default=None)

class Bet(Base):
    __tablename__ = "bet"
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("user.id"))
    event_id: Mapped[int] = mapped_column(ForeignKey("event.id"))
    # outcome: p1|x|p2|total_over|total_under|handicap_home|handicap_away
    outcome: Mapped[str]
    amount: Mapped[float]
    odd: Mapped[float]
    status: Mapped[str] = mapped_column(default="pending")
    created_at: Mapped[datetime] = mapped_column(default=datetime.utcnow)

class LoginSession(Base):
    __tablename__ = "login_session"
    id: Mapped[int] = mapped_column(primary_key=True)
    secret: Mapped[str]
    expires_at: Mapped[datetime]
    user_id: Mapped[int] = mapped_column(ForeignKey("user.id"))