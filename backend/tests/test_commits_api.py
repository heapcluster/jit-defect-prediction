from tests.conftest import C1, C3, FEATURE_VALUES, HEADERS, UNKNOWN


def test_list_sorted_and_paged(client):
    body = client.get("/api/commits", headers=HEADERS).json()
    items = body["data"]["items"]
    assert [item["risk_score"] for item in items] == sorted(
        (item["risk_score"] for item in items), reverse=True
    )
    assert body["data"]["total"] == 2
    assert body["data"]["page"] == 1 and body["data"]["size"] == 20


def test_size_over_limit(client):
    resp = client.get("/api/commits", params={"size": 101}, headers=HEADERS)
    assert resp.status_code == 400
    body = resp.json()
    assert body["code"] == 40001
    assert "size" in body["message"]


def test_size_at_limit(client):
    resp = client.get("/api/commits", params={"size": 100}, headers=HEADERS)
    assert resp.status_code == 200


def test_min_risk_filter_empty_is_not_error(client):
    body = client.get("/api/commits", params={"min_risk": 0.99}, headers=HEADERS).json()
    assert body["code"] == 0
    assert body["data"]["items"] == []
    assert body["data"]["total"] == 0


def test_detail_features_and_explanation(client):
    body = client.get(f"/api/commits/{C1}", headers=HEADERS).json()
    data = body["data"]
    assert set(data["features"]) == set(FEATURE_VALUES)
    assert data["risk_score"] == 0.8732
    assert isinstance(data["explanation"], list)


def test_detail_without_prediction_returns_nulls(client):
    body = client.get(f"/api/commits/{C3}", headers=HEADERS).json()
    data = body["data"]
    assert body["code"] == 0
    assert data["risk_score"] is None
    assert data["model_name"] is None
    assert data["explanation"] == []
    assert data["features"] is None


def test_detail_unknown_hash(client):
    resp = client.get(f"/api/commits/{UNKNOWN}", headers=HEADERS)
    assert resp.status_code == 404
    assert resp.json()["message"] == "commit not found"


def test_detail_bad_hash_format(client):
    resp = client.get(f"/api/commits/{'a' * 39}", headers=HEADERS)
    assert resp.status_code == 400
    assert resp.json()["code"] == 40001
