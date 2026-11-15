# [AI生成-人工修改] 覆盖图集接口的缺图降级与静态目录自动落地。
from datetime import datetime

from app import config
from app.db import SessionLocal
from app.models import Model, ModelFigure
from app.services import figure_store

from tests.conftest import HEADERS

MODEL = "figure_fixture_v1"
TYPES = ("roc", "pr", "confusion", "calibration", "effort", "feat_importance")


def test_figures_hides_missing_files_and_reports_them(client, tmp_path, monkeypatch):
    monkeypatch.setattr(config, "FIGURES_DIR", tmp_path / "static" / "figures")
    on_disk = config.FIGURES_DIR / "expert" / MODEL / "roc.png"
    on_disk.parent.mkdir(parents=True)
    on_disk.write_bytes(b"png")

    with SessionLocal() as session:
        session.add(Model(model_name=MODEL, line="expert"))
        session.add_all(
            ModelFigure(
                model_name=MODEL,
                figure_type=figure_type,
                title=figure_type,
                file_path=f"/static/figures/expert/{MODEL}/{figure_type}.png",
                generated_at=datetime(2026, 11, 1, 8, 0, 0),
            )
            for figure_type in TYPES
        )
        session.commit()

    body = client.get("/api/figures", params={"model_name": MODEL}, headers=HEADERS).json()
    data = body["data"]
    assert [item["figure_type"] for item in data["figures"]] == ["roc"]
    assert len(data["missing"]) == len(TYPES) - 1
    assert f"/static/figures/expert/{MODEL}/pr.png" in data["missing"]


def test_figures_unknown_model_is_40400(client):
    resp = client.get("/api/figures", params={"model_name": "no_such_model"}, headers=HEADERS)
    assert resp.status_code == 404
    assert resp.json()["code"] == 40400


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
