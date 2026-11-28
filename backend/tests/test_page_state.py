from __future__ import annotations

from tests.helpers import expert_rows, make_job


def test_page_state_roundtrip(user_client):
    client = user_client
    assert client.get("/api/page-state/collect").json()["data"] is None
    payload = {"step": 2, "form": {"repo_url": "https://github.com/a/b", "branch": "main", "mode": "expert"},
               "job_id": None, "result_ref": None}
    put = client.put("/api/page-state/collect", json=payload)
    assert put.status_code == 200
    stored = client.get("/api/page-state/collect").json()["data"]
    assert stored["page"] == "collect"
    assert stored["state"] == payload
    assert client.delete("/api/page-state/collect").status_code == 200
    assert client.get("/api/page-state/collect").json()["data"] is None


def test_page_state_invalid_page(user_client):
    response = user_client.put("/api/page-state/unknown", json={})
    assert response.status_code == 400
    assert response.json()["code"] == 40001


def test_page_state_isolated_by_user(user_client, other_client):
    user_client.put("/api/page-state/storage", json={"section": "config"})
    assert other_client.get("/api/page-state/storage").json()["data"] is None


def test_page_state_delete_cleans_uploads(user_client):
    from app.services import uploads

    result = uploads.save_data_upload(
        _user_id(user_client), "data.csv", _csv_bytes(expert_rows(3)), "clean", require_unique=False
    )
    user_client.put("/api/page-state/clean", json={"source": {"kind": "file", "id": result["meta"]["file_id"]}})
    assert result["path"].exists()
    assert user_client.delete("/api/page-state/clean").status_code == 200
    assert not result["path"].parent.exists()


def _user_id(client) -> str:
    return client.get("/api/auth/me").json()["data"]["user_id"]


def _csv_bytes(rows) -> bytes:
    from app.constants import EXPERT_COLUMNS
    from app.services import artifacts

    buffer = artifacts.table_bytes(EXPERT_COLUMNS, rows, "csv")
    return buffer
