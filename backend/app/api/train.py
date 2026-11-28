"""模型训练页接口。"""

from __future__ import annotations

from fastapi import APIRouter, Depends, File, Query, UploadFile
from fastapi.responses import Response
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import current_user, export_filename
from app.db import get_db
from app.errors import AppError, ok
from app.models import Job, Model, ModelArtifact, User
from app.schemas import TrainPrecheckRequest, TrainRunRequest, TrainSaveRequest
from app.services import artifacts, datasets, jobs, train, uploads
from app.utils import dumps, iso, loads, new_id, now, valid_name

router = APIRouter(prefix="/train", tags=["train"])


@router.post("/import")
async def import_file(file: UploadFile = File(...), user: User = Depends(current_user)) -> dict:
    payload = await file.read()
    result = uploads.save_data_upload(user.user_id, file.filename or "", payload, "train", require_unique=True)
    rows = result["rows"]
    pos = sum(1 for row in rows if str(row.get("bug")) == "1")
    times = sorted(str(row.get("commit_time") or "") for row in rows if str(row.get("commit_time") or ""))
    return ok({
        "file_id": result["meta"]["file_id"],
        "line": result["meta"]["line"],
        "columns": result["columns"],
        "sample_count": len(rows),
        "pos": pos,
        "neg": len(rows) - pos,
        "time_start": times[0] if times else None,
        "time_end": times[-1] if times else None,
    })


@router.post("/precheck")
def precheck(
    payload: TrainPrecheckRequest,
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
) -> dict:
    return ok(train.precheck(user, payload.dataset_id, db))


@router.post("/run", status_code=202)
def run(payload: TrainRunRequest, user: User = Depends(current_user), db: Session = Depends(get_db)) -> dict:
    algorithms = train._validate_algorithms(payload.algorithms)
    train.validate_split(payload.split)
    if (payload.source.kind == "dataset" and not payload.source.id) or (payload.source.kind == "file" and not payload.source.id):
        raise AppError(40001, "数据源不能为空")
    job = jobs.manager.create(db, user, "train", payload.model_dump(), total=len(algorithms))
    jobs.manager.start(job.job_id, train.run_train)
    return ok({"job_id": job.job_id, "total": len(algorithms)})


def _ref(db: Session, user: User, job_id: str) -> dict:
    job = db.get(Job, job_id)
    if job is None or job.owner_user_id != user.user_id:
        raise AppError(40401, "任务不存在")
    if job.kind != "train":
        raise AppError(40001, "任务类型不匹配")
    if job.status != "success":
        raise AppError(40901, "训练任务尚未成功结束")
    ref = loads(job.output_ref_json, {}) or {}
    if not ref.get("models"):
        raise AppError(40901, "训练结果已失效")
    return ref


@router.get("/results/{job_id}")
def result(job_id: str, user: User = Depends(current_user), db: Session = Depends(get_db)) -> dict:
    return ok(train.public_result(_ref(db, user, job_id)))


@router.get("/outputs/{job_id}/{name}")
def download_output(
    job_id: str, name: str,
    user: User = Depends(current_user), db: Session = Depends(get_db),
) -> Response:
    ref = _ref(db, user, job_id)
    item = None
    for model in ref.get("models") or []:
        if name in (model.get("model_name"), model.get("file", {}).get("name")):
            item = model
            break
    if item is None:
        raise AppError(40401, "模型文件不存在")
    path = artifacts.resolve(item["file"]["path"])
    if not path.is_file():
        raise AppError(40901, "模型文件已失效")
    extension = ".pt" if item.get("format") == "pt" else ".pkl"
    from urllib.parse import quote

    filename = quote(item["model_name"], safe="")
    return Response(
        content=path.read_bytes(),
        media_type="application/octet-stream",
        headers={"Content-Disposition": f"attachment; filename*=UTF-8''{filename}{extension}"},
    )


@router.get("/results/{job_id}/test-set/export")
def export_test_set(
    job_id: str, filename: str = Query(...), format: str = "csv",
    user: User = Depends(current_user), db: Session = Depends(get_db),
) -> Response:
    ref = _ref(db, user, job_id)
    test = ref.get("test_set") or {}
    if not test.get("path"):
        raise AppError(40901, "未生成测试集")
    columns, rows = artifacts.read_table(artifacts.resolve(test["path"]))
    name = export_filename(filename, test.get("name") or f"test-{job_id[4:12]}")
    from urllib.parse import quote

    if format not in ("csv", "excel"):
        raise AppError(40001, "导出格式非法")
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
def save(payload: TrainSaveRequest, user: User = Depends(current_user), db: Session = Depends(get_db)) -> dict:
    ref = _ref(db, user, payload.job_id)
    if not payload.model_names and not payload.save_test:
        raise AppError(40001, "请选择模型或测试集")
    if payload.save_test and not valid_name(payload.test_name or ""):
        raise AppError(40001, "测试集名称非法")
    available = {item["model_name"]: item for item in ref.get("models") or []}
    unknown = [name for name in payload.model_names if name not in available]
    if unknown:
        raise AppError(40401, "模型不存在")
    saved = []
    test_dataset_id = None
    try:
        if payload.save_test:
            test_dataset = datasets.save_split(
                db, user, db.get(Job, payload.job_id), ref, payload.test_name or "", ref.get("parent_dataset_id")
            )
            test_dataset_id = test_dataset.dataset_id
        for model_name in payload.model_names:
            existing = db.get(Model, model_name)
            if existing is not None:
                if existing.owner_user_id != user.user_id:
                    raise AppError(40901, "模型名称冲突")
                saved.append(model_name)
                continue
            item = available[model_name]
            source = artifacts.resolve(item["file"]["path"])
            if not source.is_file():
                raise AppError(40901, "模型文件已失效")
            target_dir = artifacts.model_dir(user.user_id, model_name)
            target = target_dir / f"{model_name}.{'pt' if item['format'] == 'pt' else 'pkl'}"
            artifacts.copy_asset(source, target)
            trained_at = now()
            db.add(Model(
                model_name=model_name, owner_user_id=user.user_id, line=ref.get("line"),
                algo=item.get("algo"), version_key=payload.job_id, trained_at=trained_at,
                feature_version=ref.get("feature_version"), train_dataset_id=ref.get("parent_dataset_id"),
                test_dataset_id=test_dataset_id, params_json=dumps(item.get("params") or {}),
                metrics_json=dumps(item.get("metrics") or {}),
            ))
            db.add(ModelArtifact(
                artifact_id=new_id("artifact"), model_name=model_name, line=ref.get("line"),
                algo=item.get("algo"), framework=item.get("framework") or "sklearn",
                format=item.get("format") or "pkl", version_key=payload.job_id,
                weight_path=artifacts.rel(target), checksum_sha256=artifacts.file_sha256(target),
                size_bytes=target.stat().st_size, feature_version=ref.get("feature_version"),
                train_job_id=payload.job_id, status="available", trained_at=trained_at, created_at=now(),
            ))
            saved.append(model_name)
        if test_dataset_id:
            for model_name in saved:
                model = db.get(Model, model_name)
                if model is not None:
                    model.test_dataset_id = test_dataset_id
        db.commit()
    except Exception:
        db.rollback()
        raise
    return ok({"saved_models": saved, "test_dataset_id": test_dataset_id})
