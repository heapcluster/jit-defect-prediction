"""批量同步最新提交并在线预测（POST /api/sync，change realtime-commit-sync）。

职责：对配置的 SOURCE_REPO 执行一次「fetch → 挑新哈希 → 逐条现算特征并预测入库」。
预测本身复用 POST /api/predict 的单条路径（同一条 extract→upsert→幂等 prediction 链），
本模块只负责批量编排，不另立预测口径、不直接写表。

边界：不从请求接收仓库路径；不做 PR open/merged/closed 状态清理（归 change 后续任务）；
全量历史扫描的时延由 SOURCE_REPO 仓库自身规模决定，MUST NOT 宣称 500ms 靶子适用于本接口。
"""

from __future__ import annotations

import logging
import subprocess
import threading

from fastapi import APIRouter, Depends, Query

from app import config, feature_source
from app.api.predict import PredictRequest, predict
from app.auth import require_api_key
from app.db import SessionLocal
from app.errors import AppError
from app.models import Commit

router = APIRouter(dependencies=[Depends(require_api_key)])

_GIT_TIMEOUT = 180
_sync_lock = threading.Lock()
logger = logging.getLogger("backend.sync")

MAX_LIMIT = 50


def _run_git(repo: str, *args: str) -> str:
    """执行只读 git 命令；代理经命令行参数禁用，不读全局配置。"""
    cmd = ["git", "-C", repo, "-c", "http.proxy=", "-c", "https.proxy=", *args]
    try:
        proc = subprocess.run(
            cmd, capture_output=True, text=True, timeout=_GIT_TIMEOUT, check=True
        )
    except subprocess.TimeoutExpired as exc:
        raise RuntimeError("git fetch timed out") from exc
    except subprocess.CalledProcessError as exc:
        raise RuntimeError("git command failed") from exc
    return proc.stdout


def build_fetch_args() -> list[str]:
    """fetch 命令参数（纯函数，供测试断言禁代理与超时口径）。"""
    return ["fetch", "origin"]


def pick_new_hashes(hashes: list[str], existing: set[str]) -> list[str]:
    """按最新在前挑出库中尚不存在的哈希（纯函数，供测试）。"""
    return [h for h in hashes if h not in existing]


def fetch_latest_tip(repo: str) -> str:
    """fetch 远端并返回最新 tip 哈希（FETCH_HEAD 首个条目）。"""
    _run_git(repo, *build_fetch_args())
    tip = _run_git(repo, "rev-parse", "FETCH_HEAD").strip()
    if len(tip) != 40:
        raise RuntimeError("unexpected fetch head")
    return tip


def ensure_reachable(repo: str, tip: str) -> None:
    """提取器只认 HEAD 可达提交：tip 不是 HEAD 祖先时，detach 到 tip。"""
    check = subprocess.run(
        ["git", "-C", repo, "merge-base", "--is-ancestor", tip, "HEAD"],
        capture_output=True, timeout=_GIT_TIMEOUT, check=False,
    )
    # merge-base --is-ancestor 以退出码表达结果：0=是祖先，1=不是
    if check.returncode != 0:
        _run_git(repo, "checkout", "--detach", "-q", tip)


def list_recent_hashes(repo: str, limit: int) -> list[str]:
    out = _run_git(repo, "log", "--format=%H", f"-n{limit}", "FETCH_HEAD")
    return [line.strip() for line in out.splitlines() if line.strip()]


def sync_recent(limit: int = 10) -> dict:
    """同步入口：fetch → 挑新 → 逐条走单条预测链。任一条失败不中断整批。"""
    if not (1 <= limit <= MAX_LIMIT):
        raise AppError(40001, f"参数非法：limit 需在 1..{MAX_LIMIT}")
    if not _sync_lock.acquire(blocking=False):
        raise AppError(50000, "sync already in progress")
    try:
        repo = config.SOURCE_REPO
        if repo is None or not (repo / ".git").exists():
            raise AppError(40400, "sync source repository unavailable")

        tip = fetch_latest_tip(str(repo))
        ensure_reachable(str(repo), tip)
        hashes = list_recent_hashes(str(repo), limit)

        with SessionLocal() as session:
            rows = session.query(Commit.commit_hash).filter(Commit.commit_hash.in_(hashes)).all()
            existing = {r[0] for r in rows}
        new_hashes = pick_new_hashes(hashes, existing)

        predicted: list[dict] = []
        skipped: list[dict] = []
        for h in new_hashes:
            try:
                result = predict(PredictRequest(commit_hash=h))
                predicted.append(
                    {
                        "commit_hash": h,
                        "model_name": result["data"]["model_name"],
                        "risk_score": result["data"]["risk_score"],
                    }
                )
            except AppError as exc:
                skipped.append({"commit_hash": h, "code": exc.code, "message": exc.message})
        logger.info("sync done: scanned=%s new=%s predicted=%s skipped=%s",
                    len(hashes), len(new_hashes), len(predicted), len(skipped))
        return {
            "tip": tip,
            "scanned": len(hashes),
            "new": len(new_hashes),
            "predicted": predicted,
            "skipped": skipped,
        }
    finally:
        _sync_lock.release()


@router.post("/api/sync")
def sync_endpoint(limit: int = Query(default=10, ge=1, le=MAX_LIMIT)) -> dict:
    """拉取 SOURCE_REPO 最新提交并逐条现算预测入库；无新提交时幂等返回 0。"""
    data = sync_recent(limit)
    return {"code": 0, "message": "ok", "data": data}


__all__ = ["build_fetch_args", "feature_source", "pick_new_hashes", "router", "sync_recent"]
