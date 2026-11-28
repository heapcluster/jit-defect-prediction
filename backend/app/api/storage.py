"""数据存储页：资产、算法与配置。"""

from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, Depends, Query, Request
from fastapi.responses import Response
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import current_user, export_filename
from app.db import get_db
from app.errors import AppError, ok
from app.models import Dataset, ModelArtifact, User
from app.schemas import ConfigSaveRequest
from app.services import artifacts, datasets, storage

router = APIRouter(tags=["storage"])


@router.get("/storage/files")
def list_files(
    request: Request,
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
) -> dict:
    args = dict(request.query_params)
    return ok(storage.list_files(db, user, args))


@router.get("/storage/files/{asset_id}/download")
def download_asset(
    asset_id: str,
    filename: str | None = None,
    format: str = "csv",
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
) -> Response:
    dataset = db.get(Dataset, asset_id)
    if dataset is not None:
        if dataset.owner_user_id != user.user_id:
            raise AppError(40401, "数据集不存在")
        name = export_filename(filename, dataset.name)
        columns, rows = datasets.export_rows(db, dataset)
        if format not in ("csv", "excel"):
            raise AppError(40001, "导出格式非法")
        if format == "excel":
            return Response(
                content=artifacts.table_bytes(columns, rows, "excel"),
                media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                headers={"Content-Disposition": f"attachment; filename*=UTF-8''{_quote(name)}.xlsx"},
            )
        return Response(
            content=artifacts.table_bytes(columns, rows, "csv"),
            media_type="text/csv; charset=utf-8",
            headers={"Content-Disposition": f"attachment; filename*=UTF-8''{_quote(name)}.csv"},
        )
    artifact = db.scalar(select(ModelArtifact).where(ModelArtifact.model_name == asset_id))
    if artifact is None:
        raise AppError(40401, "资产不存在")
    from app.models import Model

    model = db.get(Model, asset_id)
    if model is None or model.owner_user_id != user.user_id:
        raise AppError(40401, "模型不存在")
    if artifact.status != "available":
        raise AppError(40901, "模型文件缺失")
    path = artifacts.resolve(artifact.weight_path)
    if not path.is_file():
        artifact.status = "missing"
        db.commit()
        raise AppError(40901, "模型文件缺失")
    name = export_filename(filename, asset_id)
    extension = ".pt" if artifact.format == "pt" else ".pkl"
    return Response(
        content=path.read_bytes(),
        media_type="application/octet-stream",
        headers={"Content-Disposition": f"attachment; filename*=UTF-8''{_quote(name)}{extension}"},
    )


def _quote(name: str) -> str:
    from urllib.parse import quote

    return quote(name, safe="")


@router.get("/algorithms")
def algorithms(
    line: str | None = None,
    q: str | None = None,
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
) -> dict:
    return ok(storage.algorithms(db, line, q))


@router.get("/config")
def get_config(user: User = Depends(current_user), db: Session = Depends(get_db)) -> dict:
    return ok(storage.config_values(db, user))


@router.put("/config")
def put_config(
    payload: ConfigSaveRequest,
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
) -> dict:
    return ok(storage.save_config(db, user, payload.items))


@router.delete("/models/{model_name}")
def delete_model(model_name: str, user: User = Depends(current_user), db: Session = Depends(get_db)) -> dict:
    storage.delete_model(db, user, model_name)
    return ok({"deleted": True})
