from __future__ import annotations

from tests.conftest import create_account, login


def test_health_without_login(client):
    response = client.get("/api/health")
    assert response.status_code == 200
    assert response.json() == {"code": 0, "message": "ok", "data": {"status": "ok"}}


def test_me_requires_login(client):
    response = client.get("/api/auth/me")
    assert response.status_code == 401
    assert response.json()["code"] == 40101


def test_login_wrong_password(client):
    create_account("alice")
    response = client.post("/api/auth/login", json={"username": "alice", "password": "bad"})
    assert response.status_code == 401
    assert response.json()["code"] == 40101


def test_login_me_logout(client):
    create_account("alice", "pass123", "Alice")
    login(client, "alice")
    me = client.get("/api/auth/me").json()["data"]
    assert me["username"] == "alice"
    assert me["display_name"] == "Alice"
    assert me["counts"] == {"datasets": 0, "models": 0}
    old_cookie = client.cookies.get("jit_session")
    assert old_cookie
    assert client.post("/api/auth/logout").status_code == 200
    client.cookies.set("jit_session", old_cookie)
    response = client.get("/api/auth/me")
    assert response.status_code == 401


def test_username_case_sensitive(client):
    create_account("Alice")
    create_account("alice")
    login(client, "Alice")
    assert client.get("/api/auth/me").json()["data"]["username"] == "Alice"
    client.post("/api/auth/logout")
    login(client, "alice")
    assert client.get("/api/auth/me").json()["data"]["username"] == "alice"


def test_login_empty_fields(client):
    response = client.post("/api/auth/login", json={"username": "", "password": ""})
    assert response.status_code == 400
    assert response.json()["code"] == 40001
