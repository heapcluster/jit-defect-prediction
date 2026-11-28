"""数据存储页：资产列表、模型删除、算法清单与用户配置。"""

from __future__ import annotations

import shutil

from sqlalchemy import select
from sqlalchemy.orm import Session

from app import config
from app.errors import AppError
from app.models import Algorithm, Dataset, Model, ModelArtifact, User, UserConfig
from app.services import artifacts
from app.utils import iso, loads, now

CONFIG_DEFAULTS = {"estimate_warn_minutes": 10, "estimate_danger_minutes": 30}


def config_values(db: Session, user: User) -> dict:
    rows = db.scalars(select(UserConfig).where(UserConfig.user_id == user.user_id)).all()
    values = {row.config_key: loads(row.value_json, None) for row in rows}
    updated = max((row.updated_at for row in rows), default=None)
    return {"items": values, "updated_at": iso(updated)}


def effective_config(db: Session, user: User) -> dict:
    values = dict(CONFIG_DEFAULTS)
    values.update(config_values(db, user)["items"])
    return values


def save_config(db: Session, user: User, items: dict) -> dict:
    unknown = set(items) - set(CONFIG_DEFAULTS)
    if unknown:
        raise AppError(40001, f"未知配置键：{sorted(unknown)[0]}")
    merged = effective_config(db, user)
    for key, value in items.items():
        if not isinstance(value, int) or isinstance(value, bool) or value <= 0:
            raise AppError(40001, f"配置值必须为正整数：{key}")
        merged[key] = value
    if merged["estimate_warn_minutes"] >= merged["estimate_danger_minutes"]:
        raise AppError(40001, "黄色阈值必须小于红色阈值")
    for key, value in items.items():
        row = db.get(UserConfig, (user.user_id, key))
        if row is None:
            db.add(UserConfig(user_id=user.user_id, config_key=key, value_json=str(value), updated_at=now()))
        else:
            row.value_json = str(value)
            row.updated_at = now()
    db.commit()
    return config_values(db, user)


def algorithms(db: Session, line: str | None, q: str | None) -> dict:
    query = select(Algorithm).where(Algorithm.enabled == 1)
    if line:
        query = query.where(Algorithm.line == line)
    rows = db.scalars(query.order_by(Algorithm.line, Algorithm.algo)).all()
    items = []
    for row in rows:
        payload = loads(row.hyperparams_json, {}) or {}
        name = row.description or row.algo
        if q and q.lower() not in name.lower() and q.lower() not in row.algo.lower():
            continue
        items.append({
            "line": row.line, "algo": row.algo, "family": row.family, "enabled": bool(row.enabled),
            "description": row.description, "defaults": payload.get("defaults") or {},
        })
    return {"items": items}


def list_files(db: Session, user: User, args: dict) -> dict:
    type_filter = args.get("type")
    source_type = args.get("source_type")
    line = args.get("line")
    status = args.get("status")
    q = (args.get("q") or "").lower()
    page = max(int(args.get("page") or 1), 1)
    page_size = min(max(int(args.get("page_size") or 20), 1), 100)
    items = []
    if type_filter in (None, "", "dataset"):
        query = select(Dataset).where(Dataset.owner_user_id == user.user_id)
        if source_type:
            query = query.where(Dataset.source_type == source_type)
        if line:
            query = query.where(Dataset.line == line)
        if status:
            query = query.where(Dataset.status == status)
        for row in db.scalars(query).all():
            if q and q not in row.name.lower() and q not in (row.job_id or "").lower():
                continue
            items.append({
                "id": row.dataset_id, "type": "dataset", "name": row.name, "badge": row.source_type,
                "source_job_id": row.job_id, "created_at": iso(row.created_at), "status": row.status,
                "line": row.line, "sample_count": row.sample_count, "pos_count": row.pos_count,
                "neg_count": row.neg_count, "repo_url": row.repo_url, "branch": row.branch,
            })
    if type_filter in (None, "", "model"):
        query = select(Model).where(Model.owner_user_id == user.user_id)
        if line:
            query = query.where(Model.line == line)
        for row in db.scalars(query).all():
            artifact = db.scalar(select(ModelArtifact).where(ModelArtifact.model_name == row.model_name))
            state = artifact.status if artifact else "missing"
            if status and state != status:
                continue
            if q and q not in row.model_name.lower():
                continue
            items.append({
                "id": row.model_name, "type": "model", "name": row.model_name, "badge": row.line,
                "source_job_id": artifact.train_job_id if artifact else None,
                "created_at": iso(artifact.created_at if artifact else row.trained_at), "status": state,
                "algo": row.algo, "metrics": loads(row.metrics_json, {}) or {},
                "format": artifact.format if artifact else None,
                "size_bytes": artifact.size_bytes if artifact else None,
                "framework": artifact.framework if artifact else None,
            })
    items.sort(key=lambda item: item["created_at"] or "", reverse=True)
    total = len(items)
    start = (page - 1) * page_size
    return {"items": items[start : start + page_size], "total": total, "page": page, "page_size": page_size}


def delete_model(db: Session, user: User, model_name: str) -> None:
    model = db.get(Model, model_name)
    if model is None or model.owner_user_id != user.user_id:
        raise AppError(40401, "模型不存在")
    artifact = db.scalar(select(ModelArtifact).where(ModelArtifact.model_name == model_name))
    weight_path = artifacts.resolve(artifact.weight_path) if artifact else None
    try:
        if artifact is not None:
            db.delete(artifact)
            db.flush()
        db.delete(model)
        db.commit()
    except Exception:
        db.rollback()
        raise
    if weight_path is not None:
        try:
            weight_path.unlink(missing_ok=True)
        except OSError:
            pass
    shutil.rmtree(config.MODELS_DIR / user.user_id / model_name, ignore_errors=True)


def dataset_asset(db: Session, user: User, dataset_id: str) -> tuple[list[str], list[dict], str]:
    from app.services import datasets

    dataset = datasets.owned(db, user, dataset_id)
    columns, rows = datasets.export_rows(db, dataset)
    return columns, rows, dataset.name
