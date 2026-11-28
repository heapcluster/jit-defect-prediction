"""数据集列表、详情、保存与删除。"""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.api.deps import current_user, pagination
from app.constants import PREDICTION_VIEW_COLUMNS
from app.db import get_db
from app.errors import AppError, ok
from app.models import Dataset, User
from app.schemas import DatasetSaveRequest
from app.services import artifacts, datasets
from app.utils import iso

router = APIRouter(tags=["datasets"])


def _summary(dataset: Dataset) -> dict:
    return {
        "dataset_id": dataset.dataset_id,
        "name": dataset.name,
        "line": dataset.line,
        "source_type": dataset.source_type,
        "parent_dataset_id": dataset.parent_dataset_id,
        "sample_count": dataset.sample_count,
        "pos_count": dataset.pos_count,
        "neg_count": dataset.neg_count,
        "status": dataset.status,
        "created_at": iso(dataset.created_at),
    }


@router.get("/datasets")
def list_datasets(
    scope: str = Query("mine"),
    q: str | None = None,
    page: int = 1,
    page_size: int = 20,
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
) -> dict:
    page, page_size = pagination(page, page_size)
    query = select(Dataset).where(Dataset.owner_user_id == user.user_id)
    count_query = select(func.count()).select_from(Dataset).where(Dataset.owner_user_id == user.user_id)
    if q:
        query = query.where(Dataset.name.like(f"%{q}%"))
        count_query = count_query.where(Dataset.name.like(f"%{q}%"))
    total = db.scalar(count_query) or 0
    rows = db.scalars(
        query.order_by(Dataset.created_at.desc(), Dataset.dataset_id.asc())
        .offset(page_size * (page - 1)).limit(page_size)
    ).all()
    return ok({"items": [_summary(row) for row in rows], "total": total, "page": page, "page_size": page_size})


@router.get("/datasets/{dataset_id}")
def dataset_detail(
    dataset_id: str,
    page: int = 1,
    page_size: int = 20,
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
) -> dict:
    page, page_size = pagination(page, page_size)
    dataset = datasets.owned(db, user, dataset_id)
    if dataset.source_type == "prediction":
        columns = list(PREDICTION_VIEW_COLUMNS)
    elif dataset.manifest_path:
        columns = artifacts.read_json(artifacts.resolve(dataset.manifest_path)).get("columns") or []
    else:
        from app.services.validation import expected_columns

        columns = expected_columns(dataset.line or "expert")
    members = datasets.member_page(db, dataset, page, page_size)
    return ok({
        **_summary(dataset),
        "repo_url": dataset.repo_url,
        "branch": dataset.branch,
        "head_hash": dataset.head_hash,
        "feature_version": dataset.feature_version,
        "job_id": dataset.job_id,
        "columns": columns,
        "members": members,
    })


@router.post("/datasets")
def save_dataset(
    payload: DatasetSaveRequest,
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
) -> dict:
    dataset = datasets.save_from_job(db, user, payload.job_id, payload.name)
    return ok({"dataset_id": dataset.dataset_id})


@router.delete("/datasets/{dataset_id}")
def delete_dataset(dataset_id: str, user: User = Depends(current_user), db: Session = Depends(get_db)) -> dict:
    dataset = datasets.owned(db, user, dataset_id)
    datasets.delete_dataset(db, dataset)
    return ok(None)
