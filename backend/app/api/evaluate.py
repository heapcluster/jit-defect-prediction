"""预测性能评估接口。"""

from __future__ import annotations

from fastapi import APIRouter, Depends, File, Form, Query, UploadFile
from fastapi.responses import FileResponse, Response
from sqlalchemy.orm import Session

from app.api.deps import current_user, export_filename, pagination
from app.db import get_db
from app.errors import AppError, ok
from app.models import User
from app.schemas import EvaluatePrecheckRequest, EvaluateRunRequest, EvaluateSaveRequest
from app.services import artifacts, evaluate, jobs
from app.utils import loads

router = APIRouter(prefix="/evaluate", tags=["evaluate"])


@router.post("/import")
async def import_file(
    file: UploadFile = File(...),
    label: str | None = Form(None),
    user: User = Depends(current_user),
) -> dict:
    payload = await file.read()
    return ok(evaluate.import_file(user, file.filename or "", payload, label))


@router.post("/precheck")
def precheck(
    payload: EvaluatePrecheckRequest,
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
) -> dict:
    return ok(evaluate.precheck_dataset(db, user, payload.dataset_id))


@router.post("/run", status_code=202)
def run(payload: EvaluateRunRequest, user: User = Depends(current_user), db: Session = Depends(get_db)) -> dict:
    evaluate._validate_request(payload.metrics, payload.threshold)
    figures = evaluate.planned_figures(payload.metrics)
    job = jobs.manager.create(db, user, "evaluate", payload.model_dump(), total=len(figures))
    jobs.manager.start(job.job_id, evaluate.run_evaluate)
    return ok({"job_id": job.job_id, "total_figures": len(figures)})


def _ref(db: Session, user: User, job_id: str) -> dict:
    return evaluate._job_ref(db, user, job_id)


@router.get("/results/{job_id}")
def result(job_id: str, user: User = Depends(current_user), db: Session = Depends(get_db)) -> dict:
    return ok(evaluate.result_payload(_ref(db, user, job_id), job_id))


@router.get("/results/{job_id}/export")
def export(
    job_id: str, filename: str = Query(...), format: str = "csv",
    user: User = Depends(current_user), db: Session = Depends(get_db),
) -> Response:
    ref = _ref(db, user, job_id)
    columns, rows = evaluate.export_table(ref)
    return _table_response(columns, rows, filename, format, f"evaluate-{job_id[4:12]}")


@router.get("/results/{job_id}/figures/{figure_type}")
def figure(
    job_id: str, figure_type: str,
    user: User = Depends(current_user), db: Session = Depends(get_db),
) -> FileResponse:
    ref = _ref(db, user, job_id)
    path = (ref.get("figure_paths") or {}).get(figure_type)
    if not path:
        raise AppError(40901, "图表不存在")
    target = artifacts.resolve(path)
    if not target.is_file():
        raise AppError(40901, "图表文件缺失")
    return FileResponse(target, media_type="image/png", filename=f"{figure_type}.png")


@router.post("/save")
def save(payload: EvaluateSaveRequest, user: User = Depends(current_user), db: Session = Depends(get_db)) -> dict:
    evaluation_id = evaluate.save_evaluation(db, user, payload.job_id, payload.name)
    return ok({"evaluation_id": evaluation_id})


@router.get("/history")
def history(
    q: str | None = None,
    page: int = 1,
    page_size: int = 20,
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
) -> dict:
    page, page_size = pagination(page, page_size)
    return ok(evaluate.history(db, user, q, page, page_size))


@router.get("/history/{evaluation_id}")
def history_detail(
    evaluation_id: str,
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
) -> dict:
    return ok(evaluate.evaluation_detail(db, user, evaluation_id))


@router.get("/history/{evaluation_id}/figures/{figure_type}")
def history_figure(
    evaluation_id: str, figure_type: str,
    user: User = Depends(current_user), db: Session = Depends(get_db),
) -> FileResponse:
    path = evaluate.evaluation_figure_path(db, user, evaluation_id, figure_type)
    target = artifacts.resolve(path)
    return FileResponse(target, media_type="image/png", filename=f"{figure_type}.png")


@router.get("/history/{evaluation_id}/export")
def history_export(
    evaluation_id: str, filename: str = Query(...), format: str = "csv",
    user: User = Depends(current_user), db: Session = Depends(get_db),
) -> Response:
    row = evaluate._owned_evaluation(db, user, evaluation_id)
    payload = row.metrics_json or {}
    ref = {
        "metrics": payload.get("metrics") or {},
        "metric_names": payload.get("metric_names") or list((payload.get("metrics") or {}).keys()),
        "threshold": float(row.threshold),
    }
    columns, rows = evaluate.export_table(ref)
    return _table_response(columns, rows, filename, format, row.name)


@router.delete("/history/{evaluation_id}")
def delete_history(
    evaluation_id: str,
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
) -> dict:
    evaluate.delete_evaluation(db, user, evaluation_id)
    return ok({"deleted": True})


def _table_response(columns: list[str], rows: list[dict], filename: str, fmt: str, default: str) -> Response:
    name = export_filename(filename, default)
    if fmt not in ("csv", "excel"):
        raise AppError(40001, "导出格式非法")
    from urllib.parse import quote

    if fmt == "excel":
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
