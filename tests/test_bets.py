"""Ставки: списание баланса, проверки и расчёт после завершения события."""
from decimal import Decimal


def place_single(client, user, event_id, outcome, amount):
    return client.post(
        f"/users/{user['id']}/bets/single",
        json={"event_id": event_id, "outcome": outcome, "amount": amount},
        headers=user["headers"],
    )


def place_express(client, user, legs, amount):
    return client.post(
        f"/users/{user['id']}/bets/express",
        json={"amount": amount, "legs": [{"event_id": e, "outcome": o} for e, o in legs]},
        headers=user["headers"],
    )


def finish(client, admin, event_id, home, away):
    r = client.post(
        f"/events/{event_id}/finish",
        json={"home_score": home, "away_score": away},
        headers=admin["headers"],
    )
    assert r.status_code == 200, r.text


def bet_status(client, user):
    r = client.get(f"/users/{user['id']}/bets", headers=user["headers"])
    assert r.status_code == 200, r.text
    return r.json()[0]["status"]


def test_single_bet_deducts_balance_and_uses_server_odds(client, make_user, make_event, balance_of):
    alice = make_user("alice", balance="1000")
    event_id = make_event(odd_p1=Decimal("2.50"))

    # Клиент присылает только исход — коэффициент берётся из БД, подделать нельзя.
    r = place_single(client, alice, event_id, "p1", 100)
    assert r.status_code == 200, r.text
    bet = r.json()
    assert Decimal(bet["combined_odd"]) == Decimal("2.50")
    assert Decimal(bet["potential_payout"]) == Decimal("250.00")
    assert bet["status"] == "pending"

    assert balance_of(alice["id"]) == Decimal("900.00")


def test_bet_rejected_when_balance_is_insufficient(client, make_user, make_event, balance_of):
    alice = make_user("alice", balance="50")
    event_id = make_event()

    r = place_single(client, alice, event_id, "p1", 100)
    assert r.status_code == 400
    assert balance_of(alice["id"]) == Decimal("50.00")


def test_cannot_bet_on_started_event(client, make_user, make_event, balance_of):
    alice = make_user("alice", balance="1000")
    event_id = make_event(starts_in=-1)  # матч начался час назад

    r = place_single(client, alice, event_id, "p1", 100)
    assert r.status_code == 400
    assert "started" in r.json()["detail"]
    assert balance_of(alice["id"]) == Decimal("1000.00")


def test_express_rejects_conflicting_outcomes(client, make_user, make_event, balance_of):
    alice = make_user("alice", balance="1000")
    event_id = make_event()

    r = place_express(client, alice, [(event_id, "p1"), (event_id, "p2")], 100)
    assert r.status_code == 400
    assert balance_of(alice["id"]) == Decimal("1000.00")


def test_express_win_pays_out(client, make_user, make_event, balance_of):
    admin = make_user("admin", admin=True)
    alice = make_user("alice", balance="1000")
    e1 = make_event(odd_p1=Decimal("2.00"))
    e2 = make_event(odd_p1=Decimal("1.50"))

    r = place_express(client, alice, [(e1, "p1"), (e2, "p1")], 100)
    assert r.status_code == 200, r.text
    assert Decimal(r.json()["combined_odd"]) == Decimal("3.0000")
    assert balance_of(alice["id"]) == Decimal("900.00")

    finish(client, admin, e1, 2, 0)
    # Пока второе событие не завершено, экспресс остаётся в ожидании.
    assert bet_status(client, alice) == "pending"

    finish(client, admin, e2, 1, 0)
    assert bet_status(client, alice) == "won"
    assert balance_of(alice["id"]) == Decimal("1200.00")  # 900 + 100 × 3.0


def test_express_loses_if_any_leg_loses(client, make_user, make_event, balance_of):
    admin = make_user("admin", admin=True)
    alice = make_user("alice", balance="1000")
    e1 = make_event()
    e2 = make_event()

    place_express(client, alice, [(e1, "p1"), (e2, "p1")], 100)
    finish(client, admin, e1, 2, 0)  # эта нога выиграла
    finish(client, admin, e2, 0, 1)  # а эта проиграла

    assert bet_status(client, alice) == "lost"
    assert balance_of(alice["id"]) == Decimal("900.00")


def test_total_exactly_on_line_is_refunded(client, make_user, make_event, balance_of):
    admin = make_user("admin", admin=True)
    alice = make_user("alice", balance="1000")
    event_id = make_event(total_value=Decimal("3.0"), odd_total_over=Decimal("1.90"))

    place_single(client, alice, event_id, "total_over", 100)
    finish(client, admin, event_id, 2, 1)  # тотал ровно 3 — ни больше, ни меньше

    assert bet_status(client, alice) == "refund"
    assert balance_of(alice["id"]) == Decimal("1000.00")
