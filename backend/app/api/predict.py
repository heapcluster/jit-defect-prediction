"""模型预测与预测详情接口。"""

from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, Depends, File, Form, Query, UploadFile
from fastapi.responses import Response
from sqlalchemy.orm import Session

from app.api.deps import current_user, export_filename
from app.constants import EXPERT_FEATURES, SEMANTIC_FEATURES
from app.db import get_db
from app.errors import AppError, ok
from app.models import User
from app.schemas import (
    PredictExplainRequest,
    PredictLocalizeRequest,
    PredictPrecheckRequest,
    PredictRunRequest,
    PredictSaveModelRequest,
    PredictSaveRequest,
)
from app.services import artifacts, datasets, explain, jobs, localization, predict, uploads
from data_model import ml

router = APIRouter(prefix="/predict", tags=["predict"])


@router.post("/import")
async def import_file(file: UploadFile = File(...), user: User = Depends(current_user)) -> dict:
    payload = await file.read()
    result = uploads.save_data_upload(
        user.user_id, file.filename or "", payload, "predict",
        allow_missing_bug=True, require_unique=True,
    )
    rows = result["rows"]
    has_label = "bug" in result["columns"]
    pos = sum(1 for row in rows if str(row.get("bug")) == "1") if has_label else None
    neg = sum(1 for row in rows if str(row.get("bug")) == "0") if has_label else None
    return ok({
        "file_id": result["meta"]["file_id"],
        "line": result["meta"]["line"],
        "has_label": has_label,
        "columns": result["columns"],
        "sample_count": len(rows),
        "pos": pos,
        "neg": neg,
    })


@router.post("/precheck")
def precheck(
    payload: PredictPrecheckRequest,
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
) -> dict:
    return ok(predict.precheck(user, payload.dataset_id, db))


@router.post("/import-model")
async def import_model(
    file: UploadFile = File(...),
    line: str = Form(...),
    user: User = Depends(current_user),
) -> dict:
    if line not in ("expert", "semantic"):
        raise AppError(40001, "模型线非法")
    payload = await file.read()
    result = uploads.save_model_upload(user.user_id, file.filename or "", payload, line)
    path = result["path"]
    try:
        model = ml.load_model(path)
    except Exception as exc:  # noqa: BLE001
        raise AppError(42201, f"无法加载模型：{exc}") from exc
    if isinstance(model, ml.TorchModel):
        if model.line and model.line != line:
            raise AppError(42201, "模型文件声明的模型线与请求不一致")
        expected = len(EXPERT_FEATURES if line == "expert" else SEMANTIC_FEATURES)
        if model.input_dim != expected:
            raise AppError(42201, "模型特征数与声明线不符")
        framework, fmt, n_features = "pytorch", "pt", model.input_dim
    else:
        n_features = getattr(model, "n_features_in_", None)
        expected = len(EXPERT_FEATURES if line == "expert" else SEMANTIC_FEATURES)
        if n_features is not None and n_features != expected:
            raise AppError(42201, "模型特征数与声明线不符")
        framework, fmt = "sklearn", "pkl"
    return ok({
        "model_ref": result["model_ref"],
        "label": Path(file.filename or "model").stem,
        "line": line,
        "n_features": n_features,
        "framework": framework,
        "format": fmt,
    })


@router.post("/save-model")
def save_model(
    payload: PredictSaveModelRequest,
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
) -> dict:
    model_name = predict.save_model(db, user, payload.model_ref, payload.name)
    return ok({"model_name": model_name})


@router.post("/run", status_code=202)
def run(payload: PredictRunRequest, user: User = Depends(current_user), db: Session = Depends(get_db)) -> dict:
    total = predict.preflight(db, user, payload.model_dump())
    job = jobs.manager.create(db, user, "predict", payload.model_dump(), total=total)
    jobs.manager.start(job.job_id, predict.run_predict)
    return ok({"job_id": job.job_id, "total": total})


@router.get("/results/{job_id}/rows")
def rows(
    job_id: str,
    page: int = 1,
    page_size: int = 20,
    result: str = "all",
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
) -> dict:
    page = max(page, 1)
    page_size = min(max(page_size, 1), 100)
    _, all_rows, _ = predict.resolve_rows(db, user, job_id)
    if result == "defect":
        filtered = [row for row in all_rows if str(row.get("predicted_label")) == "1"]
    elif result == "normal":
        filtered = [row for row in all_rows if str(row.get("predicted_label")) == "0"]
    elif result == "all":
        filtered = all_rows
    else:
        raise AppError(40001, "结果筛选取值非法")
    start = (page - 1) * page_size
    items = [predict.public_row(row) for row in filtered[start : start + page_size]]
    return ok({"items": items, "total": len(filtered), "page": page, "page_size": page_size})


@router.get("/results/{job_id}/export")
def export(
    job_id: str,
    filename: str = Query(...),
    format: str = "csv",
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
) -> Response:
    columns, rows, ref = predict.resolve_rows(db, user, job_id)
    if not ref.get("has_label"):
        columns = [name for name in columns if name != "bug"]
    name = export_filename(filename, f"predict-{job_id[4:12]}")
    if format not in ("csv", "excel"):
        raise AppError(40001, "导出格式非法")
    from urllib.parse import quote

    if format == "excel":
        return Response(
            content=artifacts.table_bytes(columns, rows, "excel"),
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers={"Content-Disposition": f"attachment; filename*=UTF-8''{quote(name, safe='')}.xlsx"},
        )
    return Response(
        content=artifacts.table_bytes(columns, rows, "csv"),
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": f"attachment; filename*=UTF-8''{quote(name, safe='')}.csv"},
    )


@router.post("/save")
def save(payload: PredictSaveRequest, user: User = Depends(current_user), db: Session = Depends(get_db)) -> dict:
    dataset = datasets.save_prediction(db, user, payload.job_id, payload.name)
    return ok({"dataset_id": dataset.dataset_id})


@router.get("/results/{job_id}/commits/{commit_hash}")
def detail(
    job_id: str, commit_hash: str,
    user: User = Depends(current_user), db: Session = Depends(get_db),
) -> dict:
    return ok(predict.detail(db, user, job_id, commit_hash))


@router.post("/explain")
def explain_result(
    payload: PredictExplainRequest,
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
) -> dict:
    return ok(explain.explain(db, user, payload.job_id, payload.commit_hash, payload.technique))


@router.post("/localize")
def localize_result(
    payload: PredictLocalizeRequest,
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
) -> dict:
    return ok(localization.localize(db, user, payload.job_id, payload.commit_hash))
