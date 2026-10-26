"""健康检查与运行状态（observability capability）：GET /api/health。

覆盖 specs/observability/spec.md 的 Scenario：健康 / DB 不可达降级 / 无模型，
并断言响应不回显连接串或堆栈（契约三）。
"""

from tests.conftest import HEADERS


def test_health_ok_reports_counts_and_models(client):
    body = client.get("/api/health", headers=HEADERS).json()
    assert body["code"] == 0
    data = body["data"]
    assert data["status"] == "ok"
    assert data["db"] == "up"
    assert data["models_loaded"] >= 1
    assert data["model_names"]
    assert data["commit_count"] >= 1
    assert data["prediction_count"] >= 1
    assert data["labeled_count"] >= 0
    assert data["server_time"].endswith("Z")
    assert "last_sync_at" in data


def test_health_does_not_leak_connection_details(client):
    raw = client.get("/api/health", headers=HEADERS).text
    assert "mysql+pymysql" not in raw
    assert "Traceback" not in raw
    assert "password" not in raw.lower()


def test_health_degraded_when_db_unreachable(client, monkeypatch):
    from app.services import health as health_module

    class _BrokenSession:
        def __enter__(self):
            raise RuntimeError("db down")

        def __exit__(self, *exc):
            return False

    monkeypatch.setattr(health_module, "SessionLocal", lambda: _BrokenSession())
    body = client.get("/api/health", headers=HEADERS).json()
    assert body["code"] == 0, "健康检查 MUST NOT 抛 50000"
    data = body["data"]
    assert data["status"] == "degraded"
    assert data["db"] == "down"
    assert data["commit_count"] == 0


def test_health_degraded_when_no_model_loaded(client, monkeypatch):
    from app import model_registry

    monkeypatch.setattr(model_registry, "all_models", lambda: [])
    data = client.get("/api/health", headers=HEADERS).json()["data"]
    assert data["models_loaded"] == 0
    assert data["model_names"] == []
    assert data["status"] == "degraded"
