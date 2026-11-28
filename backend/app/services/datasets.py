"""数据集保存、覆盖、成员读取与删除。"""

from __future__ import annotations

import shutil
from datetime import datetime

from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session

from app import config
from app.constants import EXPERT_FEATURES, PREDICTION_VIEW_COLUMNS, SEMANTIC_FEATURES
from app.errors import AppError
from app.models import Commit, Dataset, DatasetCommit, Job, Prediction, User
from app.services import artifacts
from app.services.validation import expected_columns, parse_time
from app.utils import is_commit_hash, iso, loads, new_id, now, valid_name

LINE_FEATURES = {"expert": EXPERT_FEATURES, "semantic": SEMANTIC_FEATURES}


def ensure_commit(db: Session, repo_name: str, row: dict, commit_hash: str) -> str:
    """按 (repo_name, commit_hash) 幂等补齐全局提交表。"""
    repo_name = (repo_name or row.get("project") or "unknown").strip()
    existing = db.scalar(
        select(Commit).where(Commit.repo_name == repo_name, Commit.commit_hash == commit_hash)
    )
    if existing is not None:
        return existing.commit_id
    commit = Commit(
        commit_id=new_id("commit"),
        commit_hash=commit_hash,
        repo_name=repo_name,
        author_name=str(row.get("author_name") or ""),
        author_email=str(row.get("author_email") or "") or None,
        committed_at=parse_time(row.get("commit_time")) or now(),
        message=str(row.get("commit_message") or ""),
        parent_hash=str(row.get("parent_hash") or "") or None,
    )
    db.add(commit)
    db.flush()
    return commit.commit_id


def owned(db: Session, user: User, dataset_id: str) -> Dataset:
    dataset = db.get(Dataset, dataset_id)
    if dataset is None or dataset.owner_user_id != user.user_id:
        raise AppError(40401, "数据集不存在")
    return dataset


def _feature_list(row: dict, line: str) -> list[float]:
    return [float(row.get(name, 0) or 0) for name in LINE_FEATURES[line]]


def _stats(rows: list[dict], line: str, store_features: bool = True):
    pos = sum(1 for row in rows if str(row.get("bug", "")) == "1")
    times = [parse_time(row.get("commit_time")) for row in rows]
    times = [item for item in times if item is not None]
    return pos, len(rows) - pos if store_features else 0, (min(times) if times else None), (max(times) if times else None)


def _load_job_output(db: Session, user: User, job_id: str, kinds: tuple[str, ...]) -> tuple[Job, dict]:
    job = db.get(Job, job_id)
    if job is None or job.owner_user_id != user.user_id:
        raise AppError(40401, "任务不存在")
    if job.kind not in kinds:
        raise AppError(40001, "任务类型不支持保存为数据集")
    if job.status != "success":
        raise AppError(40001, "任务尚未成功结束")
    ref = loads(job.output_ref_json, {}) or {}
    return job, ref


def _repo_info(ref: dict) -> dict:
    return ref.get("repo") or {}


def _inherited(dataset: Dataset, repo: dict) -> None:
    dataset.repo_url = repo.get("repo_url")
    dataset.repo_name = repo.get("repo_name")
    dataset.platform = repo.get("platform")
    dataset.branch = repo.get("branch")
    dataset.head_hash = repo.get("head_hash")


def _write_dataset_asset(dataset_id: str, data_path: str, manifest: dict) -> str:
    target = artifacts.dataset_dir(dataset_id)
    source = artifacts.resolve(data_path)
    shutil.copy2(source, target / "data.csv")
    artifacts.write_json(target / "manifest.json", manifest)
    return artifacts.rel(target / "manifest.json")


def _insert_members(db: Session, dataset: Dataset, rows: list[dict], line: str) -> None:
    repo_name = dataset.repo_name or (rows[0].get("project") if rows else None)
    if not repo_name:
        raise AppError(40001, "结果缺少 project")
    seen: set[str] = set()
    for index, row in enumerate(rows):
        commit_hash = str(row.get("commit_id", "")).strip().lower()
        if not is_commit_hash(commit_hash):
            raise AppError(42201, "提交哈希非法", {"invalid_rows": [index + 1]})
        if commit_hash in seen:
            raise AppError(40901, "结果存在重复 commit_hash，请先去重")
        seen.add(commit_hash)
        commit_id = ensure_commit(db, repo_name, row, commit_hash)
        db.add(
            DatasetCommit(
                dataset_id=dataset.dataset_id,
                commit_id=commit_id,
                commit_hash=commit_hash,
                repo_url=dataset.repo_url,
                branch=dataset.branch,
                author_name=str(row.get("author_name") or "") or None,
                author_email=str(row.get("author_email") or "") or None,
                committed_at=parse_time(row.get("commit_time")),
                message=str(row.get("commit_message") or "") or None,
                parent_hash=str(row.get("parent_hash") or "") or None,
                is_bug_inducing=int(str(row.get("bug"))) if str(row.get("bug")) in ("0", "1") else None,
                label_method=row.get("label_method") or "szz",
                fix_commit_hash=row.get("fix_commit_hash") or None,
                feature_json=_feature_list(row, line),
                row_no=index,
            )
        )


def save_from_job(db: Session, user: User, job_id: str, name: str) -> Dataset:
    if not valid_name(name):
        raise AppError(40001, "数据集名称非法")
    job, ref = _load_job_output(db, user, job_id, ("collect", "clean"))
    rows = artifacts.read_table(artifacts.resolve(ref["data_path"]))[1]
    if not rows:
        raise AppError(40901, "结果为空，无法保存")
    hashes = [str(row.get("commit_id", "")).lower() for row in rows]
    if len(set(hashes)) != len(hashes):
        raise AppError(40901, "结果存在重复 commit_hash，请先按提交哈希去重")
    if len({str(row.get("project", "")) for row in rows}) > 1:
        raise AppError(40901, "同一数据集只允许一个 project")
    pos = sum(1 for row in rows if str(row.get("bug", "")) == "1")
    if pos == 0:
        raise AppError(40901, "结果正样本为 0，不可保存为可训练数据集")

    line = ref.get("line") or "expert"
    source_type = ref.get("source_type") or ("git_repo" if job.kind == "collect" else "upload")
    repo = _repo_info(ref)
    if not repo.get("repo_name") and rows:
        repo = {**repo, "repo_name": str(rows[0].get("project") or "") or None}
    parent_id = ref.get("parent_dataset_id")
    if source_type in ("clean", "split", "prediction") and parent_id:
        parent = db.get(Dataset, parent_id)
        if parent is None or parent.owner_user_id != user.user_id:
            raise AppError(40401, "来源数据集不存在")
    key = None
    if source_type == "git_repo":
        key = artifacts.dedupe_key(
            f"collect|{(repo.get('repo_name') or '').lower()}|{repo.get('branch') or ''}|{line}"
        )
    elif source_type == "clean":
        key = artifacts.dedupe_key(f"clean|{parent_id}|{ref.get('ops_hash')}")
    elif source_type == "upload":
        key = artifacts.dedupe_key(f"upload|{ref.get('file_sha256')}|{ref.get('ops_hash')}")

    existing = None
    if key:
        existing = db.scalar(
            select(Dataset).where(Dataset.owner_user_id == user.user_id, Dataset.dedupe_key == key)
        )
    dataset = existing or Dataset(dataset_id=new_id("dataset"), owner_user_id=user.user_id, created_at=now())
    dataset.name = name
    dataset.line = line
    dataset.source_type = source_type
    dataset.parent_dataset_id = parent_id
    dataset.feature_version = ref.get("feature_version")
    dataset.sample_count = len(rows)
    dataset.pos_count = pos
    dataset.neg_count = len(rows) - pos
    dataset.time_start = min(filter(None, (parse_time(r.get("commit_time")) for r in rows)), default=None)
    dataset.time_end = max(filter(None, (parse_time(r.get("commit_time")) for r in rows)), default=None)
    dataset.status = "ready"
    dataset.job_id = job_id
    dataset.dedupe_key = key
    _inherited(dataset, repo)

    try:
        if existing is not None:
            db.execute(delete(DatasetCommit).where(DatasetCommit.dataset_id == dataset.dataset_id))
        else:
            db.add(dataset)
        db.flush()
        dataset.manifest_path = _write_dataset_asset(dataset.dataset_id, ref["data_path"], ref.get("manifest") or {"columns": expected_columns(line), "row_count": len(rows)})
        _insert_members(db, dataset, rows, line)
        db.commit()
    except Exception:
        db.rollback()
        raise
    db.refresh(dataset)
    return dataset


def save_prediction(db: Session, user: User, job_id: str, name: str) -> Dataset:
    if not valid_name(name):
        raise AppError(40001, "预测数据集名称非法")
    job, ref = _load_job_output(db, user, job_id, ("predict",))
    rows = artifacts.read_table(artifacts.resolve(ref["rows_path"]))[1]
    if not rows:
        raise AppError(40901, "预测结果为空，无法保存")
    line = ref.get("line") or "expert"
    dataset = Dataset(
        dataset_id=new_id("dataset"),
        owner_user_id=user.user_id,
        name=name,
        line=line,
        source_type="prediction",
        parent_dataset_id=ref.get("parent_dataset_id"),
        sample_count=len(rows),
        pos_count=sum(1 for row in rows if str(row.get("predicted_label")) == "1"),
        neg_count=sum(1 for row in rows if str(row.get("predicted_label")) == "0"),
        feature_version=ref.get("feature_version"),
        dedupe_key=None,
        status="ready",
        job_id=job_id,
        created_at=now(),
    )
    dataset.time_start = min(filter(None, (parse_time(r.get("commit_time")) for r in rows)), default=None)
    dataset.time_end = max(filter(None, (parse_time(r.get("commit_time")) for r in rows)), default=None)
    _inherited(dataset, _repo_info(ref))
    if not dataset.repo_name and rows:
        dataset.repo_name = str(rows[0].get("project") or "") or None
    try:
        db.add(dataset)
        db.flush()
        dataset.manifest_path = _write_dataset_asset(dataset.dataset_id, ref["rows_path"], {"columns": ref.get("columns") or [], "row_count": len(rows)})
        repo_name = dataset.repo_name or (rows[0].get("project") if rows else "unknown")
        for row in rows:
            commit_hash = str(row.get("commit_id", "")).lower()
            commit_id = ensure_commit(db, repo_name, row, commit_hash)
            db.add(
                Prediction(
                    dataset_id=dataset.dataset_id,
                    commit_hash=commit_hash,
                    commit_id=commit_id,
                    model_name=ref.get("model_name"),
                    model_label=ref.get("model_label"),
                    risk_score=float(row.get("risk_score", 0) or 0),
                    predicted_label=int(float(row.get("predicted_label", 0) or 0)),
                    threshold=float(row.get("threshold", ref.get("threshold", 0.5)) or 0.5),
                    actual_label=int(str(row.get("bug"))) if str(row.get("bug")) in ("0", "1") else None,
                    feature_version=ref.get("feature_version"),
                    predicted_at=now(),
                )
            )
        db.commit()
    except Exception:
        db.rollback()
        raise
    db.refresh(dataset)
    return dataset


def save_split(db: Session, user: User, job: Job, ref: dict, name: str, parent_id: str) -> Dataset:
    if not valid_name(name):
        raise AppError(40001, "测试集名称非法")
    test = ref.get("test_set") or {}
    if not test.get("path"):
        raise AppError(40901, "测试集不存在")
    rows = artifacts.read_table(artifacts.resolve(test["path"]))[1]
    line = ref.get("line") or "expert"
    parent = db.get(Dataset, parent_id)
    fallback_project = (parent.repo_name or parent.name) if parent else None
    for row in rows:
        if not row.get("project"):
            row["project"] = fallback_project or "unknown"
    dataset = Dataset(
        dataset_id=new_id("dataset"), owner_user_id=user.user_id, name=name, line=line,
        source_type="split", parent_dataset_id=parent_id, feature_version=ref.get("feature_version"),
        sample_count=len(rows), status="ready", job_id=job.job_id, created_at=now(),
    )
    dataset.repo_url = parent.repo_url if parent else None
    dataset.repo_name = parent.repo_name if parent else None
    if not dataset.repo_name and rows:
        dataset.repo_name = str(rows[0].get("project") or "") or None
    dataset.platform = parent.platform if parent else None
    dataset.branch = parent.branch if parent else None
    dataset.head_hash = parent.head_hash if parent else None
    pos = sum(1 for row in rows if str(row.get("bug")) == "1")
    dataset.pos_count = pos
    dataset.neg_count = len(rows) - pos
    dataset.time_start = min(filter(None, (parse_time(r.get("commit_time")) for r in rows)), default=None)
    dataset.time_end = max(filter(None, (parse_time(r.get("commit_time")) for r in rows)), default=None)
    try:
        db.add(dataset)
        db.flush()
        dataset.manifest_path = _write_dataset_asset(dataset.dataset_id, test["path"], {"columns": test.get("columns") or expected_columns(line), "row_count": len(rows)})
        _insert_members(db, dataset, rows, line)
        db.commit()
    except Exception:
        db.rollback()
        raise
    db.refresh(dataset)
    return dataset


def delete_dataset(db: Session, dataset: Dataset) -> None:
    dataset_id = dataset.dataset_id
    try:
        db.execute(delete(Prediction).where(Prediction.dataset_id == dataset_id))
        db.execute(delete(DatasetCommit).where(DatasetCommit.dataset_id == dataset_id))
        db.delete(dataset)
        db.commit()
    except Exception:
        db.rollback()
        raise
    shutil.rmtree(config.DATASETS_DIR / dataset_id, ignore_errors=True)


def member_page(db: Session, dataset: Dataset, page: int, page_size: int) -> dict:
    if dataset.source_type == "prediction":
        rows = db.scalars(select(Prediction).where(Prediction.dataset_id == dataset.dataset_id).order_by(Prediction.commit_hash)).all()
        items = []
        commits = {p.commit_hash: p for p in rows}

        commit_rows = {}
        if rows:
            ids = [p.commit_id for p in rows if p.commit_id]
            if ids:
                for commit in db.scalars(select(Commit).where(Commit.commit_id.in_(ids))).all():
                    commit_rows[commit.commit_id] = commit
        for item in rows[page_size * (page - 1) : page_size * page]:
            commit = commit_rows.get(item.commit_id)
            items.append({
                "commit_hash": item.commit_hash,
                "commit_message": commit.message if commit else "",
                "author_name": commit.author_name if commit else "",
                "commit_time": iso(commit.committed_at) if commit else None,
                "bug": item.actual_label,
                "risk_score": float(item.risk_score),
                "predicted_label": item.predicted_label,
            })
        return {"items": items, "total": len(rows), "page": page, "page_size": page_size}

    total = db.scalar(
        select(func.count()).select_from(DatasetCommit).where(DatasetCommit.dataset_id == dataset.dataset_id)
    ) or 0
    members = db.scalars(
        select(DatasetCommit).where(DatasetCommit.dataset_id == dataset.dataset_id)
        .order_by(DatasetCommit.row_no).offset(page_size * (page - 1)).limit(page_size)
    ).all()
    features = LINE_FEATURES[dataset.line or "expert"]
    items = []
    for member in members:
        row = {
            "project": dataset.repo_name or "",
            "commit_id": member.commit_hash,
            "commit_time": iso(member.committed_at),
            "author_name": member.author_name or "",
            "author_email": member.author_email or "",
            "commit_message": member.message or "",
            "bug": member.is_bug_inducing,
        }
        values = member.feature_json or []
        for index, name in enumerate(features):
            row[name] = values[index] if index < len(values) else 0
        items.append(row)
    return {"items": items, "total": total, "page": page, "page_size": page_size}


def export_rows(db: Session, dataset: Dataset) -> tuple[list[str], list[dict]]:
    if dataset.source_type == "prediction":
        columns = expected_columns(dataset.line or "expert") + ["risk_score", "predicted_label", "threshold"]
        predictions = db.scalars(select(Prediction).where(Prediction.dataset_id == dataset.dataset_id).order_by(Prediction.commit_hash)).all()

        commit_rows = {}
        ids = [p.commit_id for p in predictions if p.commit_id]
        if ids:
            for commit in db.scalars(select(Commit).where(Commit.commit_id.in_(ids))).all():
                commit_rows[commit.commit_id] = commit
        rows = []
        for item in predictions:
            commit = commit_rows.get(item.commit_id)
            base = expected_columns(dataset.line or "expert")
            row = {name: "" for name in base}
            row.update({
                "project": dataset.repo_name or "",
                "commit_id": item.commit_hash,
                "commit_time": iso(commit.committed_at) if commit else "",
                "author_name": commit.author_name if commit else "",
                "author_email": commit.author_email if commit else "",
                "commit_message": commit.message if commit else "",
                "bug": item.actual_label if item.actual_label is not None else "",
                "risk_score": float(item.risk_score),
                "predicted_label": item.predicted_label,
                "threshold": float(item.threshold),
            })
            rows.append(row)
        return columns, rows
    columns = expected_columns(dataset.line or "expert")
    rows = member_page(db, dataset, 1, max(dataset.sample_count, 1))["items"]
    return columns, rows
