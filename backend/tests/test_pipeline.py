from __future__ import annotations

import io
import time
from pathlib import Path

from app import config
from tests.helpers import expert_rows, make_job


def _uid(client) -> str:
    return client.get("/api/auth/me").json()["data"]["user_id"]


def _wait(client, job_id: str, timeout: int = 120) -> dict:
    deadline = time.time() + timeout
    while time.time() < deadline:
        data = client.get(f"/api/jobs/{job_id}").json()["data"]
        if data["status"] in ("success", "failed", "cancelled"):
            return data
        time.sleep(0.3)
    raise AssertionError(f"任务超时：{job_id}")


def _make_dataset(client) -> str:
    uid = _uid(client)
    job_id = make_job(uid, "collect", expert_rows(40))
    return client.post("/api/datasets", json={"job_id": job_id, "name": "train-src"}).json()["data"]["dataset_id"]


def test_train_predict_evaluate_pipeline(user_client):
    client = user_client
    dataset_id = _make_dataset(client)

    precheck = client.post("/api/train/precheck", json={"dataset_id": dataset_id}).json()["data"]
    assert precheck["sample_count"] == 40
    assert len(precheck["algorithms"]) == 13

    run = client.post("/api/train/run", json={
        "source": {"kind": "dataset", "id": dataset_id},
        "algorithms": [{"algo": "lr", "params": {"max_iter": 300}}],
        "split": {"mode": "time", "ratios": {"train": 70, "valid": 15, "test": 15}},
    })
    assert run.status_code == 202, run.text
    job_id = run.json()["data"]["job_id"]
    assert run.json()["data"]["total"] == 1
    job = _wait(client, job_id)
    assert job["status"] == "success", job

    result = client.get(f"/api/train/results/{job_id}").json()["data"]
    assert result["split_counts"] == {"train": 28, "valid": 6, "test": 6}
    assert len(result["models"]) == 1
    model_name = result["models"][0]["model_name"]
    assert result["models"][0]["format"] == "pkl"

    saved = client.post("/api/train/save", json={
        "job_id": job_id, "model_names": [model_name], "save_test": True, "test_name": "split-test",
    }).json()["data"]
    assert saved["saved_models"] == [model_name]
    assert saved["test_dataset_id"].startswith("ds_")

    download = client.get(f"/api/train/outputs/{job_id}/{model_name}")
    assert download.status_code == 200
    assert download.headers["content-disposition"].endswith(".pkl")

    predict_run = client.post("/api/predict/run", json={
        "source": {"kind": "dataset", "id": dataset_id},
        "model": {"kind": "saved", "name": model_name},
        "threshold": 0.5,
    })
    assert predict_run.status_code == 202, predict_run.text
    predict_job = predict_run.json()["data"]["job_id"]
    assert predict_run.json()["data"]["total"] == 40
    assert _wait(client, predict_job)["status"] == "success"

    rows = client.get(f"/api/predict/results/{predict_job}/rows", params={"page_size": 100}).json()["data"]
    assert rows["total"] == 40
    assert set(rows["items"][0]) == {
        "commit_hash", "commit_message", "author_name", "commit_time", "bug", "risk_score", "predicted_label"
    }
    commit_hash = rows["items"][0]["commit_hash"]

    detail = client.get(f"/api/predict/results/{predict_job}/commits/{commit_hash}").json()["data"]
    assert detail["commit_hash"] == commit_hash
    assert detail["model"] == model_name

    explain = client.post("/api/predict/explain", json={
        "job_id": predict_job, "commit_hash": commit_hash, "technique": "permutation",
    })
    assert explain.status_code == 200, explain.text
    explain_data = explain.json()["data"]
    assert len(explain_data["items"]) == 14
    assert set(explain_data["items"][0]) == {"feature", "contribution", "direction"}

    localize = client.post("/api/predict/localize", json={"job_id": predict_job, "commit_hash": commit_hash})
    assert localize.status_code == 409
    assert localize.json()["code"] == 40901

    saved_prediction = client.post("/api/predict/save", json={"job_id": predict_job, "name": "predds"})
    assert saved_prediction.status_code == 200, saved_prediction.text
    pred_dataset_id = saved_prediction.json()["data"]["dataset_id"]

    import shutil

    shutil.rmtree(config.OUTPUTS_DIR / _uid(client) / predict_job, ignore_errors=True)
    rows_after = client.get(f"/api/predict/results/{predict_job}/rows", params={"page_size": 100}).json()["data"]
    assert rows_after["total"] == 40

    precheck_eval = client.post("/api/evaluate/precheck", json={"dataset_id": pred_dataset_id}).json()["data"]
    assert precheck_eval["sample_count"] == 40
    assert precheck_eval["pos"] == 20

    eval_run = client.post("/api/evaluate/run", json={
        "source": {"kind": "dataset", "id": pred_dataset_id},
        "metrics": ["accuracy", "precision", "recall", "f1", "auc", "ap", "mcc"],
        "threshold": 0.5,
    })
    assert eval_run.status_code == 202, eval_run.text
    assert eval_run.json()["data"]["total_figures"] == 4
    eval_job = eval_run.json()["data"]["job_id"]
    assert _wait(client, eval_job)["status"] == "success"

    eval_result = client.get(f"/api/evaluate/results/{eval_job}").json()["data"]
    assert set(eval_result["metrics"]) == {"accuracy", "precision", "recall", "f1", "auc", "ap", "mcc"}
    assert {item["type"] for item in eval_result["figures"]} == {"roc", "pr", "confusion", "bar"}
    figure = client.get(f"/api/evaluate/results/{eval_job}/figures/roc")
    assert figure.status_code == 200
    assert figure.headers["content-type"].startswith("image/png")

    evaluation_id = client.post("/api/evaluate/save", json={"job_id": eval_job, "name": "eval-1"}).json()["data"]["evaluation_id"]
    history = client.get("/api/evaluate/history").json()["data"]
    assert history["total"] == 1
    assert history["items"][0]["evaluation_id"] == evaluation_id
    detail_eval = client.get(f"/api/evaluate/history/{evaluation_id}").json()["data"]
    assert len(detail_eval["figures"]) == 4
    assert client.get(f"/api/evaluate/history/{evaluation_id}/figures/bar").status_code == 200
    assert client.delete(f"/api/evaluate/history/{evaluation_id}").json()["data"] == {"deleted": True}
    assert client.get(f"/api/evaluate/history/{evaluation_id}").status_code == 404


def test_import_model_roundtrip(user_client):
    client = user_client
    import joblib
    from sklearn.linear_model import LogisticRegression
    import numpy as np

    from app.constants import EXPERT_FEATURES

    rows = expert_rows(30)
    X = np.array([[float(row[name]) for name in EXPERT_FEATURES] for row in rows])
    y = np.array([int(row["bug"]) for row in rows])
    model = LogisticRegression(max_iter=300).fit(X, y)
    folder = Path(config.TEMP_ROOT) / "tests"
    folder.mkdir(parents=True, exist_ok=True)
    path = folder / "uploaded.pkl"
    joblib.dump(model, path)

    response = client.post(
        "/api/predict/import-model",
        files={"file": ("uploaded.pkl", path.read_bytes(), "application/octet-stream")},
        data={"line": "expert"},
    )
    assert response.status_code == 200, response.text
    data = response.json()["data"]
    assert data["framework"] == "sklearn"
    assert data["format"] == "pkl"
    assert data["n_features"] == 14
    assert data["label"] == "uploaded"

    saved = client.post("/api/predict/save-model", json={"model_ref": data["model_ref"]})
    assert saved.status_code == 200, saved.text
    model_name = saved.json()["data"]["model_name"]
    again = client.post("/api/predict/save-model", json={"model_ref": data["model_ref"]})
    assert again.json()["data"]["model_name"] == model_name

    listing = client.get("/api/storage/files", params={"type": "model"}).json()["data"]
    assert listing["total"] == 1
    download = client.get(f"/api/storage/files/{model_name}/download")
    assert download.status_code == 200
    assert download.headers["content-disposition"].endswith(".pkl")
    assert client.delete(f"/api/models/{model_name}").json()["data"] == {"deleted": True}
    assert client.get("/api/storage/files", params={"type": "model"}).json()["data"]["total"] == 0


def test_storage_config_and_algorithms(user_client):
    client = user_client
    algos = client.get("/api/algorithms").json()["data"]["items"]
    assert len(algos) == 26
    expert = client.get("/api/algorithms", params={"line": "expert"}).json()["data"]["items"]
    assert len(expert) == 13

    assert client.get("/api/config").json()["data"]["items"] == {}
    saved = client.put("/api/config", json={"items": {"estimate_warn_minutes": 15, "estimate_danger_minutes": 45}})
    assert saved.status_code == 200
    assert saved.json()["data"]["items"] == {"estimate_warn_minutes": 15, "estimate_danger_minutes": 45}
    bad = client.put("/api/config", json={"items": {"estimate_warn_minutes": 60}})
    assert bad.status_code == 400
    unknown = client.put("/api/config", json={"items": {"x": 1}})
    assert unknown.status_code == 400
