from __future__ import annotations

from tests.helpers import expert_rows, make_job


def _uid(client) -> str:
    return client.get("/api/auth/me").json()["data"]["user_id"]


def test_save_dataset_and_members(user_client):
    uid = _uid(user_client)
    job_id = make_job(uid, "collect", expert_rows(40))
    response = user_client.post("/api/datasets", json={"job_id": job_id, "name": "repo-main-expert"})
    assert response.status_code == 200, response.text
    dataset_id = response.json()["data"]["dataset_id"]
    assert dataset_id.startswith("ds_")

    detail = user_client.get(f"/api/datasets/{dataset_id}").json()["data"]
    assert detail["sample_count"] == 40
    assert detail["pos_count"] == 20
    assert detail["neg_count"] == 20
    assert detail["source_type"] == "git_repo"
    assert detail["columns"][:7] == [
        "project", "commit_id", "commit_time", "author_name", "author_email", "commit_message", "ns"
    ]
    members = detail["members"]
    assert members["total"] == 40
    assert len(members["items"]) == 20
    assert "ns" in members["items"][0]

    again = user_client.post("/api/datasets", json={"job_id": job_id, "name": "repo-main-expert"})
    assert again.json()["data"]["dataset_id"] == dataset_id


def test_dataset_overwrite_by_source(user_client):
    uid = _uid(user_client)
    first_job = make_job(uid, "collect", expert_rows(40))
    dataset_id = user_client.post("/api/datasets", json={"job_id": first_job, "name": "ds"}).json()["data"]["dataset_id"]
    created_at = user_client.get(f"/api/datasets/{dataset_id}").json()["data"]["created_at"]

    second_job = make_job(uid, "collect", expert_rows(30, repo="owner/repo"))
    result = user_client.post("/api/datasets", json={"job_id": second_job, "name": "ds-new"})
    assert result.json()["data"]["dataset_id"] == dataset_id
    detail = user_client.get(f"/api/datasets/{dataset_id}").json()["data"]
    assert detail["name"] == "ds-new"
    assert detail["sample_count"] == 30
    assert detail["created_at"] == created_at


def test_dataset_duplicate_hash_rejected(user_client):
    uid = _uid(user_client)
    rows = expert_rows(10)
    rows[1]["commit_id"] = rows[0]["commit_id"]
    job_id = make_job(uid, "collect", rows)
    response = user_client.post("/api/datasets", json={"job_id": job_id, "name": "bad"})
    assert response.status_code == 409
    assert response.json()["code"] == 40901


def test_dataset_zero_positive_rejected(user_client):
    uid = _uid(user_client)
    job_id = make_job(uid, "collect", expert_rows(20, positive=False))
    response = user_client.post("/api/datasets", json={"job_id": job_id, "name": "bad"})
    assert response.status_code == 409


def test_dataset_other_user_invisible(user_client, other_client):
    uid = _uid(user_client)
    job_id = make_job(uid, "collect", expert_rows(20))
    dataset_id = user_client.post("/api/datasets", json={"job_id": job_id, "name": "mine"}).json()["data"]["dataset_id"]
    assert other_client.get(f"/api/datasets/{dataset_id}").status_code == 404
    assert other_client.get("/api/datasets").json()["data"]["total"] == 0
    assert other_client.post("/api/datasets", json={"job_id": job_id, "name": "steal"}).status_code == 404


def test_dataset_delete(user_client):
    uid = _uid(user_client)
    job_id = make_job(uid, "collect", expert_rows(20))
    dataset_id = user_client.post("/api/datasets", json={"job_id": job_id, "name": "to-delete"}).json()["data"]["dataset_id"]
    assert user_client.delete(f"/api/datasets/{dataset_id}").json()["data"] is None
    assert user_client.get(f"/api/datasets/{dataset_id}").status_code == 404
