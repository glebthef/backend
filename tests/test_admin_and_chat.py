"""Права администратора и чат поддержки."""
from datetime import datetime, timedelta, timezone


def test_only_admin_can_create_events(client, make_user):
    admin = make_user("admin", admin=True)
    alice = make_user("alice")
    event = {
        "sport_slug": "football",
        "league": "АПЛ",
        "home": "Arsenal",
        "away": "Chelsea",
        "starts_at": (datetime.now(timezone.utc) + timedelta(days=1)).isoformat(),
        "odd_p1": 2.1,
        "odd_x": 3.3,
        "odd_p2": 3.6,
    }

    assert client.post("/events", json=event, headers=alice["headers"]).status_code == 403

    r = client.post("/events", json=event, headers=admin["headers"])
    assert r.status_code == 200, r.text
    assert r.json()["status"] == "upcoming"


def test_only_admin_can_credit_balance(client, make_user, balance_of):
    admin = make_user("admin", admin=True)
    alice = make_user("alice", balance="100")

    # Сам себе пользователь начислить не может.
    r = client.post(f"/users/{alice['id']}/balance", json={"amount": 5000}, headers=alice["headers"])
    assert r.status_code == 403
    assert balance_of(alice["id"]) == 100

    # Нулевая и отрицательная сумма отклоняются валидацией.
    for bad in (0, -50):
        r = client.post(f"/users/{alice['id']}/balance", json={"amount": bad}, headers=admin["headers"])
        assert r.status_code == 422

    r = client.post(f"/users/{alice['id']}/balance", json={"amount": 500}, headers=admin["headers"])
    assert r.status_code == 200, r.text
    assert r.json()["balance"] == 600
    assert balance_of(alice["id"]) == 600


def test_support_chat_roundtrip(client, make_user):
    admin = make_user("admin", admin=True)
    alice = make_user("alice")
    bob = make_user("bob")

    r = client.post(f"/users/{alice['id']}/chat", json={"text": "Не пришёл выигрыш"}, headers=alice["headers"])
    assert r.status_code == 200 and r.json()["sender"] == "user"

    # Админ пишет в тред Алисы — сообщение уходит от имени поддержки.
    r = client.post(f"/users/{alice['id']}/chat", json={"text": "Сейчас проверим"}, headers=admin["headers"])
    assert r.status_code == 200 and r.json()["sender"] == "support"

    r = client.get(f"/users/{alice['id']}/chat", headers=alice["headers"])
    assert [m["sender"] for m in r.json()] == ["user", "support"]

    # Чужую переписку читать нельзя.
    assert client.get(f"/users/{alice['id']}/chat", headers=bob["headers"]).status_code == 403


def test_event_odds_must_be_above_one(client, make_user):
    admin = make_user("admin", admin=True)
    event = {
        "sport_slug": "football", "league": "АПЛ", "home": "A", "away": "B",
        "starts_at": (datetime.now(timezone.utc) + timedelta(days=1)).isoformat(),
        "odd_p1": 1.0, "odd_p2": 3.0,
    }
    assert client.post("/events", json=event, headers=admin["headers"]).status_code == 422
