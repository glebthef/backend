from datetime import datetime
from sqlalchemy import ForeignKey
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


engine = create_async_engine(
    "postgresql+asyncpg://postgres:@127.0.0.1:5432/primebet",
    echo=True,
)

class Base(DeclarativeBase):
    pass

class User(Base):
    __tablename__ = "user"
    id: Mapped[int] = mapped_column(primary_key=True)
    login: Mapped[str] = mapped_column(unique=True)
    password: Mapped[str]
    balance: Mapped[float] = mapped_column(default=0)

class Sport(Base):
    __tablename__ = "sport"
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str]
    icon: Mapped[str]
    slug: Mapped[str] = mapped_column(unique=True)

class  Event(Base):
    __tablename__ = "event"
    id: Mapped[int] = mapped_column(primary_key=True)
    sport_id: Mapped[int] = mapped_column(ForeignKey("sport.id"))
    league: Mapped[str]
    home: Mapped[str]
    away: Mapped[str]
    starts_at: Mapped[datetime]
    odd_p1: Mapped[float]  # Победа хозяев
    odd_x: Mapped[float]  # Ничья
    odd_p2: Mapped[float]  # Победа гостей
    is_active: Mapped[bool] = mapped_column(default=True)

class Bet(Base):
    __tablename__ = "bet"
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[User] = mapped_column(ForeignKey("user.id"))
    event_id: Mapped[Event] = mapped_column(ForeignKey("event.id"))
    outcome: Mapped[str]  # "p1", "x", "p2"
    amount: Mapped[float]  # сумма ставки
    odd: Mapped[float]  # коэффициент на момент ставки
    created_at: Mapped[datetime] = mapped_column(default=datetime.utcnow)

class LoginSession(Base):
    __tablename__ = "login_session"
    id: Mapped[int] = mapped_column(primary_key=True)
    secret: Mapped[str]
    expires_at: Mapped[datetime]
    user_id: Mapped[int] = mapped_column(ForeignKey("user.id"))


