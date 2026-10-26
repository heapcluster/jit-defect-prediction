"""PR 实时预测与查询（change realtime-pr-prediction）。

数据来源：GitHub REST API 拉 Camel 的 open PR 清单与提交（app.github）；
特征计算：复用现有 feature_source（需本地 blobless 历史索引 = config.SOURCE_REPO）；
预测与入库：复用 POST /api/predict 的单条链（predict_commit_all_models 一次现算、逐模型打分）。

边界（沿用 realtime-commit-sync 的纪律）：
1. 绝不改动 SOURCE_REPO 的检出状态：拉 PR head 仅用 `git fetch origin pull/<n>/head` 取对象，不 checkout。
2. 不从请求接收仓库路径；不做 PR open/merged/closed 状态清理。
3. 复用冻结错误码集合（0/40001/40400/50000）。
"""

from __future__ import annotations

import logging
from pathlib import Path

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select

from app import config, github, model_registry, schemas
from app.api import sync
from app.api.commits import _iso_z
from app.api.predict import predict_commit_all_models
from app.auth import require_api_key
from app.db import SessionLocal
from app.errors import INTERNAL_ERROR_MESSAGE, AppError, ok
from app.models import Commit, Prediction

router = APIRouter(dependencies=[Depends(require_api_key)])
logger = logging.getLogger("backend.prs")

MAX_LIMIT = 50
MAX_COMMITS_PER_PR = 50


def _repo_path() -> Path:
    repo = config.SOURCE_REPO
    if repo is None or not (repo / ".git").exists():
        raise AppError(
            40400, "history index repository unavailable (set SOURCE_REPO to a blobless clone)"
        )
    return repo


def _resolve_model(model_name: str | None) -> str:
    if model_name and not model_registry.has(model_name):
        raise AppError(40001, "参数非法：model_name 不在已加载模型清单")
    if model_name:
        return model_name
    default = model_registry.default_model()
    if default is None:
        raise AppError(50000, INTERNAL_ERROR_MESSAGE)
    return default.name


def fetch_pr_ref(repo: Path, pr_number: int) -> str:
    """把 PR 的 head ref 拉进本地历史索引（仅取对象，不 checkout），返回 head sha。"""
    sync._run_git(str(repo), "fetch", "origin", f"pull/{pr_number}/head")
    return sync._run_git(str(repo), "rev-parse", "FETCH_HEAD").strip()


def sync_prs(limit: int = 10) -> dict:
    """拉取 open PR → 逐 PR 取其提交 → 现算特征并逐模型预测入库。任一条失败不中断整批。"""
    if not (1 <= limit <= MAX_LIMIT):
        raise AppError(40001, f"参数非法：limit 需在 1..{MAX_LIMIT}")
    repo = _repo_path()
    prs = github.list_open_prs(limit=limit)
    pr_results: list[dict] = []
    skipped: list[dict] = []
    commits_predicted = 0
    for pr in prs:
        try:
            fetch_pr_ref(repo, pr.number)
        except AppError as exc:
            skipped.append({"pr": pr.number, "reason": f"fetch failed: {exc.message}"})
            continue
        shas = github.list_pr_commit_shas(pr.number)[:MAX_COMMITS_PER_PR]
        done = 0
        for sha in shas:
            try:
                predict_commit_all_models(sha, repo=str(repo))
                done += 1
                commits_predicted += 1
            except AppError as exc:
                skipped.append(
                    {"pr": pr.number, "commit": sha, "code": exc.code, "message": exc.message}
                )
        pr_results.append({"pr": pr.number, "title": pr.title, "commits_predicted": done})
    return {
        "prs_scanned": len(prs),
        "commits_predicted": commits_predicted,
        "prs": pr_results,
        "skipped": skipped,
    }


def _pr_risk(pr_number: int, model_name: str) -> tuple[int, int, float | None, object | None]:
    """返回 (commit_count, predicted_count, max_risk, latest_predicted_at)。"""
    shas = github.list_pr_commit_shas(pr_number)
    with SessionLocal() as session:
        rows = (
            session.execute(
                select(Prediction).where(
                    Prediction.commit_hash.in_(shas), Prediction.model_name == model_name
                )
            )
            .scalars()
            .all()
        )
    risks = [p.risk_score for p in rows if p.risk_score is not None]
    times = [p.predicted_at for p in rows if p.predicted_at is not None]
    return len(shas), len(risks), (max(risks) if risks else None), (max(times) if times else None)


@router.post("/api/sync-prs", response_model=schemas.SyncPrsResponse)
def sync_prs_endpoint(limit: int = Query(default=10, ge=1, le=MAX_LIMIT)) -> dict:
    """实时拉取 Camel 最新 open PR 并逐条现算预测入库；无待预测时幂等返回 0。"""
    data = sync_prs(limit)
    return ok(data)


@router.get("/api/prs", response_model=schemas.PrsResponse)
def list_prs(
    limit: int = Query(default=20, ge=1, le=MAX_LIMIT),
    model_name: str | None = Query(default=None),
) -> dict:
    """列出 open PR 及其聚合风险（取该 PR 各提交在指定模型下的最高风险分）。"""
    model = _resolve_model(model_name)
    # 只读查询：数据来自 GitHub API + 本地 prediction 表，不依赖 SOURCE_REPO 历史索引，
    # 故不调用 _repo_path() —— 未配历史索引时这两个查询端点不该 40400。
    prs = github.list_open_prs(limit=limit)
    items = []
    skipped = 0
    for pr in prs:
        # 逐 PR 隔离：GitHub 没有「批量取多个 PR 的提交清单」的端点，每个 PR 一次
        # list_pr_commit_shas 是 API 形态决定的（limit≤50 → 最多 50 次调用）；
        # 未带 token 时 60 req/h 限额下单个 PR 失败不该让整端 50000。
        try:
            commit_count, predicted_count, risk, predicted_at = _pr_risk(pr.number, model)
        except RuntimeError as exc:
            logger.warning("pr %s 风险聚合失败，跳过该 PR：%s", pr.number, exc)
            skipped += 1
            continue
        items.append(
            {
                "number": pr.number,
                "title": pr.title,
                "author": pr.author,
                "state": pr.state,
                "html_url": pr.html_url,
                "updated_at": pr.updated_at,
                "risk_score": risk,
                "commit_count": commit_count,
                "predicted_count": predicted_count,
                "predicted_at": _iso_z(predicted_at) if predicted_at else None,
            }
        )
    return ok({"items": items, "model_name": model, "skipped": skipped})


@router.get("/api/prs/{number}", response_model=schemas.PrDetailResponse)
def pr_detail(number: int, model_name: str | None = Query(default=None)) -> dict:
    """单个 PR 的元信息与其各提交的风险分（指定模型）。"""
    model = _resolve_model(model_name)
    # 同 list_prs：纯读端点，不依赖 SOURCE_REPO（见上）
    pr = github.get_pr(number)
    shas = github.list_pr_commit_shas(number)
    with SessionLocal() as session:
        preds = (
            session.execute(
                select(Prediction).where(
                    Prediction.commit_hash.in_(shas), Prediction.model_name == model
                )
            )
            .scalars()
            .all()
        )
        commits = (
            session.execute(select(Commit).where(Commit.commit_hash.in_(shas))).scalars().all()
        )
    by_sha = {p.commit_hash: p for p in preds}
    meta = {c.commit_hash: c for c in commits}
    commit_rows = []
    for sha in shas:
        pred = by_sha.get(sha)
        commit_rows.append(
            {
                "sha": sha,
                "message": (meta[sha].message if sha in meta else "")[:200],
                "author": meta[sha].author_name if sha in meta else "",
                "risk_score": float(pred.risk_score)
                if pred and pred.risk_score is not None
                else None,
                "predicted_at": _iso_z(pred.predicted_at) if pred and pred.predicted_at else None,
            }
        )
    return ok(
        {
            "number": pr.number,
            "title": pr.title,
            "author": pr.author,
            "state": pr.state,
            "html_url": pr.html_url,
            "updated_at": pr.updated_at,
            "model_name": model,
            "commits": commit_rows,
        }
    )


__all__ = ["MAX_LIMIT", "fetch_pr_ref", "router", "sync_prs"]
