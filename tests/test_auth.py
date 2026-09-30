def test_register_and_login(client):
    r = client.post("/users", json={"login": "alice", "password": "secret123"})
    assert r.status_code == 200, r.text
    user = r.json()
    assert user["login"] == "alice"
    assert user["balance"] == 0
    assert user["is_admin"] is False

    r = client.post("/sessions", headers={"login": "alice", "password": "secret123"})
    assert r.status_code == 200, r.text
    assert r.json()["user_id"] == user["id"]
    assert r.json()["secret"]


def test_duplicate_login_is_rejected(client):
    assert client.post("/users", json={"login": "alice", "password": "secret123"}).status_code == 200
    r = client.post("/users", json={"login": "alice", "password": "другой123"})
    assert r.status_code == 400


def test_login_with_wrong_password_fails(client):
    client.post("/users", json={"login": "alice", "password": "secret123"})
    r = client.post("/sessions", headers={"login": "alice", "password": "wrong-pass"})
    assert r.status_code == 401


def test_unknown_session_is_rejected(client, make_user):
    alice = make_user("alice")
    r = client.get(f"/users/{alice['id']}/bets", headers={"session-secret": "not-a-real-secret"})
    assert r.status_code == 401


def test_user_cannot_read_someone_elses_bets(client, make_user):
    alice = make_user("alice")
    bob = make_user("bob")
    r = client.get(f"/users/{alice['id']}/bets", headers=bob["headers"])
    assert r.status_code == 403


def test_user_cannot_top_up_balance_directly(client, make_user, balance_of):
    alice = make_user("alice")
    r = client.patch(f"/users/{alice['id']}/balance", json={"amount": 1000000}, headers=alice["headers"])
    assert r.status_code in (403, 404, 405)
    assert balance_of(alice["id"]) == 0


def test_banned_user_is_locked_out(client, make_user):
    admin = make_user("admin", admin=True)
    alice = make_user("alice")

    r = client.patch(f"/users/{alice['id']}/ban", json={"banned": True}, headers=admin["headers"])
    assert r.status_code == 200, r.text

    r = client.get(f"/users/{alice['id']}/bets", headers=alice["headers"])
    assert r.status_code == 403
    assert r.json()["detail"] == "Account banned"
