# === AI 辅助说明 ===
# 本文件共 7 条测试用例
# [AI生成]：0 条
# [AI生成-人工修改]：7 条（AI 生成骨架，人工补充核心断言）
# [手写]：0 条
# 使用工具：原始生成记录未归档（标注依据代码特征判断，作者于 2026-11-17 确认）
# 提示词见：docs/README.md

from datetime import datetime

import pytest
from app import config
from app.db import SessionLocal
from app.models import Model, ModelFigure
from app.services import evaluate_run, figure_store, output_store
from app.services import file_contracts as fc

from tests.conftest import HEADERS

MODEL = "figure_fixture_v1"
TYPES = ("roc", "pr", "confusion", "calibration", "effort_unaware", "effort_aware", "feat_importance")
# 契约要求 PNG 魔数校验，伪造格式不得冒充可用图。
PNG = b"\x89PNG\r\n\x1a\n" + b"figure payload"
METRIC_COLUMNS = (
    "model_name", "line", "metric", "value", "threshold", "n", "pos_rate",
    "dataset_version", "model_version", "computed_at",
)


def _seed(model=MODEL, line="expert", *, files=None, effort=None):
    """登记六类图；files 指定落盘内容（None 表示不落盘），返回 type -> file_path。"""
    paths = {}
    with SessionLocal() as session:
        session.add(Model(model_name=model, line=line))
        for figure_type in TYPES:
            filename = f"{figure_type}_{effort}.png" if effort and figure_type.startswith("effort") else f"{figure_type}.png"
            file_path = f"/static/figures/{line}/{model}/{filename}"
            paths[figure_type] = file_path
            session.add(ModelFigure(
                job_id="",
                model_name=model,
                figure_type=figure_type,
                figure_name=filename,
                title=filename,
                file_path=file_path,
                generated_at=datetime(2026, 11, 1, 8, 0, 0),
            ))
            content = files.get(figure_type) if files else None
            if content is not None:
                disk = config.FIGURES_DIR.parent / file_path.removeprefix("/static/")
                disk.parent.mkdir(parents=True, exist_ok=True)
                disk.write_bytes(content)
        session.commit()
    return paths


def _evaluate_batch(job_id="j-eval-1"):
    """发布一个已登记的 evaluate 批次，指标为 §3.6 长表。"""
    registered = evaluate_run._metrics().metric_keys()
    assert registered
    rows = []
    for metric in registered:
        rows.append({
            "model_name": MODEL, "line": "expert", "metric": metric, "value": 0.75,
            "threshold": 0.5, "n": 10, "pos_rate": 0.4,
            "dataset_version": "ds-v1", "model_version": "mv1",
            "computed_at": "2026-11-01T08:00:00Z",
        })
    rows.append({**rows[0], "model_name": "other_model", "value": 0.1})
    # 批次查询以 model_figure.job_id 定位；登记该批次的 7 类图（文件是否存在由缺失检测单独覆盖）。
    with SessionLocal() as session:
        for figure_type in TYPES:
            filename = f"{figure_type}.png"
            session.add(ModelFigure(
                job_id=job_id, model_name=MODEL, figure_type=figure_type, figure_name=filename,
                title=filename, file_path=f"/static/figures/expert/{MODEL}/{filename}",
                generated_at=datetime(2026, 11, 1, 8, 0, 0),
            ))
        session.commit()
    artifacts = {f"evaluate_metrics_{job_id}.csv": fc.encode_table(METRIC_COLUMNS, rows, "csv")}
    output_store.publish_output("evaluate", artifacts, inputs=[], config={}, job_id=job_id)
    return registered


def test_figures_returns_new_contract_with_effort_kind_and_checksum(client, tmp_path, monkeypatch):
    monkeypatch.setattr(config, "FIGURES_DIR", tmp_path / "static" / "figures")
    monkeypatch.setattr(output_store, "OUTPUT_ROOT", tmp_path / "outputs")
    paths = _seed(files={figure_type: PNG for figure_type in TYPES}, effort="aware")

    data = client.get("/api/figures", params={"model_name": MODEL}, headers=HEADERS).json()["data"]
    assert set(data) == {
        "model_name", "line", "source_job_id", "batches", "metrics", "metrics_unavailable", "figures", "missing",
    }
    assert data["model_name"] == MODEL and data["line"] == "expert"
    assert data["source_job_id"] is None
    assert data["metrics"] == [] and data["metrics_unavailable"] == "evaluate_batch_missing"
    assert data["missing"] == []
    assert [item["figure_type"] for item in data["figures"]] == list(TYPES)
    for item in data["figures"]:
        assert set(item) == {
            "figure_type", "effort_kind", "title", "figure_name", "file_path", "checksum_sha256", "source_job_id",
        }
        assert item["file_path"] == paths[item["figure_type"]]
        assert item["checksum_sha256"] == fc.sha256(PNG)
        assert item["source_job_id"] is None
    kinds = {item["figure_type"]: item["effort_kind"] for item in data["figures"]}
    assert kinds["effort_unaware"] == "unaware" and kinds["effort_aware"] == "aware"
    assert all(value is None for key, value in kinds.items() if not key.startswith("effort"))


def test_figures_reads_evaluate_metrics_as_long_table(client, tmp_path, monkeypatch):
    monkeypatch.setattr(config, "FIGURES_DIR", tmp_path / "static" / "figures")
    monkeypatch.setattr(output_store, "OUTPUT_ROOT", tmp_path / "outputs")
    _seed(files={figure_type: PNG for figure_type in TYPES})
    job_id = "j-eval-1"
    registered = _evaluate_batch(job_id)

    data = client.get(
        "/api/figures", params={"model_name": MODEL, "job_id": job_id}, headers=HEADERS
    ).json()["data"]
    assert data["source_job_id"] == job_id
    assert data["metrics_unavailable"] is None
    assert [row["metric"] for row in data["metrics"]] == registered
    for row in data["metrics"]:
        assert set(row) == set(METRIC_COLUMNS)
        assert row["model_name"] == MODEL and row["line"] == "expert"
        assert row["value"] == pytest.approx(0.75)
        assert row["n"] == 10 and row["pos_rate"] == pytest.approx(0.4)

    # 不存在的批次按 docs/api/figures.md 返回 404，而不是伪造空图集。
    missing_batch = client.get(
        "/api/figures", params={"model_name": MODEL, "job_id": "j-nope"}, headers=HEADERS
    )
    assert missing_batch.status_code == 404


def test_figures_filters_by_figure_type(client, tmp_path, monkeypatch):
    monkeypatch.setattr(config, "FIGURES_DIR", tmp_path / "static" / "figures")
    _seed(files={figure_type: PNG for figure_type in TYPES})
    data = client.get(
        "/api/figures", params={"model_name": MODEL, "figure_type": "roc"}, headers=HEADERS
    ).json()["data"]
    assert [item["figure_type"] for item in data["figures"]] == ["roc"]
    assert data["missing"] == []


def test_figures_hides_missing_files_and_reports_them(client, tmp_path, monkeypatch):
    monkeypatch.setattr(config, "FIGURES_DIR", tmp_path / "static" / "figures")
    paths = _seed(files={"roc": PNG, "pr": b"not a png"})

    data = client.get("/api/figures", params={"model_name": MODEL}, headers=HEADERS).json()["data"]
    assert [item["figure_type"] for item in data["figures"]] == ["roc"]
    visible_paths = {item["file_path"] for item in data["figures"]}
    reasons = {item["figure_type"]: item["reason"] for item in data["missing"]}
    assert reasons == {
        "pr": "invalid_png",
        "confusion": "file_missing",
        "calibration": "file_missing",
        "effort_unaware": "file_missing",
        "effort_aware": "file_missing",
        "feat_importance": "file_missing",
    }
    for item in data["missing"]:
        assert set(item) == {"figure_type", "file_path", "reason"}
        assert item["file_path"] == paths[item["figure_type"]]
        assert item["file_path"] not in visible_paths


def test_figures_unknown_model_is_40400(client):
    resp = client.get("/api/figures", params={"model_name": "no_such_model"}, headers=HEADERS)
    assert resp.status_code == 404
    assert resp.json()["code"] == 40400


def test_figures_rejects_unknown_figure_type_and_query_params(client, tmp_path, monkeypatch):
    monkeypatch.setattr(config, "FIGURES_DIR", tmp_path / "static" / "figures")
    _seed(files={figure_type: PNG for figure_type in TYPES})
    for params in (
        {"model_name": MODEL, "figure_type": "bogus"},
        {"model_name": MODEL, "unknown": "1"},
    ):
        response = client.get("/api/figures", params=params, headers=HEADERS)
        assert response.status_code == 400
        assert response.json()["code"] == 40001


def test_sync_figures_copies_missing_only(tmp_path, monkeypatch):
    pipelines = tmp_path / "pipelines"
    figures = tmp_path / "static" / "figures"
    source = pipelines / "expert" / "reports" / "figs_by_model" / MODEL
    source.mkdir(parents=True)
    (source / "roc.png").write_bytes(b"png")
    monkeypatch.setattr(config, "PIPELINES_DIR", pipelines)
    monkeypatch.setattr(config, "FIGURES_DIR", figures)

    assert figure_store.sync_figures() == 1
    assert (figures / "expert" / MODEL / "roc.png").is_file()
    assert figure_store.sync_figures() == 0
