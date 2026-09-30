import os
from datetime import datetime, timedelta, timezone
from decimal import Decimal

import psycopg
import pytest
from sqlalchemy import create_engine, text, update

TEST_PG = os.getenv("TEST_PG", "postgres:postgres@127.0.0.1:5432")
TEST_DB = "primebet_test"

os.environ["DATABASE_URL"] = f"postgresql+asyncpg://{TEST_PG}/{TEST_DB}"

from fastapi.testclient import TestClient  # noqa: E402
from main import app  # noqa: E402
from models import Base, Event, User  # noqa: E402


def _ensure_test_database():
    with psycopg.connect(f"postgresql://{TEST_PG}/postgres", autocommit=True) as conn:
        exists = conn.execute(
            "SELECT 1 FROM pg_database WHERE datname = %s", (TEST_DB,)
        ).fetchone()
        if not exists:
            conn.execute(f'CREATE DATABASE "{TEST_DB}"')


@pytest.fixture(scope="session")
def db():
    _ensure_test_database()
    engine = create_engine(f"postgresql+psycopg://{TEST_PG}/{TEST_DB}")
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    yield engine
    engine.dispose()


@pytest.fixture(scope="session")
def client(db):
    with TestClient(app) as c:
        yield c


@pytest.fixture(autouse=True)
def clean_tables(db):
    tables = ", ".join(f'"{t.name}"' for t in Base.metadata.sorted_tables)
    with db.begin() as conn:
        conn.execute(text(f"TRUNCATE {tables} RESTART IDENTITY CASCADE"))
    yield


@pytest.fixture
def make_user(client, db):
    def _make(login, balance="0", admin=False, password="secret123"):
        r = client.post("/users", json={"login": login, "password": password})
        assert r.status_code == 200, r.text
        user_id = r.json()["id"]
        with db.begin() as conn:
            conn.execute(
                update(User).where(User.id == user_id)
                .values(balance=Decimal(balance), is_admin=admin)
            )
        r = client.post("/sessions", headers={"login": login, "password": password})
        assert r.status_code == 200, r.text
        secret = r.json()["secret"]
        return {"id": user_id, "headers": {"session-secret": secret}}
    return _make


@pytest.fixture
def make_event(db):
    def _make(starts_in=24, **fields):
        now = datetime.now(timezone.utc).replace(tzinfo=None)
        values = {
            "sport_slug": "football",
            "league": "Test League",
            "home": "Home",
            "away": "Away",
            "starts_at": now + timedelta(hours=starts_in),
            "odd_p1": Decimal("2.00"),
            "odd_x": Decimal("3.00"),
            "odd_p2": Decimal("4.00"),
        }
        values.update(fields)
        with db.begin() as conn:
            return conn.execute(
                Event.__table__.insert().values(**values).returning(Event.id)
            ).scalar_one()
    return _make


@pytest.fixture
def balance_of(db):
    def _balance(user_id):
        with db.connect() as conn:
            return conn.execute(
                text('SELECT balance FROM "user" WHERE id = :id'), {"id": user_id}
            ).scalar_one()
    return _balance
