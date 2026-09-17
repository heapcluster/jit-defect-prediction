from app.auth import MISSING_OR_INVALID_TOKEN


def test_missing_token(client):
    resp = client.get("/api/commits")
    assert resp.status_code == 401
    body = resp.json()
    assert body["code"] == 40100
    assert body["message"] == MISSING_OR_INVALID_TOKEN


def test_invalid_token(client):
    resp = client.get("/api/commits", headers={"X-API-Key": "wrong"})
    assert resp.status_code == 401
    assert resp.json()["code"] == 40100


def test_envelope_on_success(client):
    resp = client.get("/api/commits", headers={"X-API-Key": "test-token"})
    body = resp.json()
    assert body["code"] == 0
    assert body["message"] == "ok"
    assert "items" in body["data"]
