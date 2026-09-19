from tests.conftest import HEADERS


def test_week_aggregation(client):
    body = client.get("/api/trends", headers=HEADERS).json()
    series = body["data"]["series"]
    assert body["data"]["granularity"] == "week"
    assert len(series) == 2
    first = series[0]
    assert set(first) == {"period", "commit_count", "avg_risk", "high_risk_count"}
    assert first["high_risk_count"] == 1
    assert first["period"].startswith("2026-W")


def test_invalid_granularity(client):
    resp = client.get("/api/trends", params={"granularity": "day"}, headers=HEADERS)
    assert resp.status_code == 400
    body = resp.json()
    assert body["code"] == 40001
    assert "granularity" in body["message"]


def test_empty_range_is_not_error(client):
    body = client.get(
        "/api/trends",
        params={"start_time": "2030-01-01T00:00:00Z", "end_time": "2030-12-31T00:00:00Z"},
        headers=HEADERS,
    ).json()
    assert body["code"] == 0
    assert body["data"]["series"] == []
