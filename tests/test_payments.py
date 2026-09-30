from decimal import Decimal

from sqlalchemy import text

from models import Payment


def add_payment(db, user_id, amount="500", session_id="cs_test_1"):
    with db.begin() as conn:
        conn.execute(Payment.__table__.insert().values(
            user_id=user_id, provider_payment_id=session_id,
            amount=Decimal(amount), status="pending",
        ))


def payment_status(db, session_id="cs_test_1"):
    with db.connect() as conn:
        return conn.execute(
            text("SELECT status FROM payment WHERE provider_payment_id = :s"), {"s": session_id}
        ).scalar_one()


def fake_stripe(monkeypatch, answer):
    async def fetch(session_id):
        return answer
    monkeypatch.setattr("routes.payments.fetch_checkout_session", fetch)


def test_sync_credits_paid_deposit_exactly_once(client, make_user, db, balance_of, monkeypatch):
    alice = make_user("alice", balance="100")
    add_payment(db, alice["id"])
    fake_stripe(monkeypatch, {"payment_status": "paid", "status": "complete"})

    r = client.post(f"/users/{alice['id']}/deposits/sync", headers=alice["headers"])
    assert r.status_code == 200, r.text
    assert r.json() == {"credited": 500.0, "pending": 0, "balance": 600.0}
    assert payment_status(db) == "succeeded"

    r = client.post(f"/users/{alice['id']}/deposits/sync", headers=alice["headers"])
    assert r.json()["credited"] == 0
    assert balance_of(alice["id"]) == Decimal("600.00")


def test_sync_cancels_expired_deposit(client, make_user, db, balance_of, monkeypatch):
    alice = make_user("alice", balance="100")
    add_payment(db, alice["id"])
    fake_stripe(monkeypatch, {"payment_status": "unpaid", "status": "expired"})

    r = client.post(f"/users/{alice['id']}/deposits/sync", headers=alice["headers"])
    assert r.json()["credited"] == 0
    assert payment_status(db) == "canceled"
    assert balance_of(alice["id"]) == Decimal("100.00")


def test_unpaid_deposit_stays_pending(client, make_user, db, monkeypatch):
    alice = make_user("alice")
    add_payment(db, alice["id"])
    fake_stripe(monkeypatch, {"payment_status": "unpaid", "status": "open"})

    r = client.post(f"/users/{alice['id']}/deposits/sync", headers=alice["headers"])
    assert r.json() == {"credited": 0.0, "pending": 1, "balance": 0.0}


def test_cannot_sync_someone_elses_deposits(client, make_user):
    alice = make_user("alice")
    bob = make_user("bob")
    assert client.post(f"/users/{alice['id']}/deposits/sync", headers=bob["headers"]).status_code == 403
