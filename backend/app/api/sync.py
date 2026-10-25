"""批量同步最新提交并在线预测（POST /api/sync，change realtime-commit-sync）。

职责：对配置的 SOURCE_REPO 执行一次「fetch → 挑待预测哈希 → 逐条现算特征并预测入库」。
预测本身复用 POST /api/predict 的单条路径（同一条 extract→upsert→幂等 prediction 链），
本模块只负责批量编排，不另立预测口径、不直接写表。

三条边界（2026-10-25 审阅后固化）：
1. **绝不改动 SOURCE_REPO 的检出状态**：远端 tip 不是本地 HEAD 祖先时，建一个专用临时
   工作树（--no-checkout）做特征提取，用后即焚；用户正在用的分支/工作区不受影响。
2. 「待预测」按**默认模型是否已有 prediction 行**判断（commit 表存在 ≠ 已预测）。
3. 不从请求接收仓库路径；不做 PR open/merged/closed 状态清理（归 change 后续任务）；
   MUST NOT 宣称 500ms 靶子适用于本接口（时延取决于 SOURCE_REPO 历史规模）。
"""

from __future__ import annotations

import logging
import shutil
import subprocess
import tempfile
import threading
import time
from collections.abc import Callable
from pathlib import Path

from fastapi import APIRouter, Depends, Query

from app import config, model_registry
from app.api.predict import PredictRequest, predict_commit
from app.auth import require_api_key
from app.db import SessionLocal
from app.errors import INTERNAL_ERROR_MESSAGE, AppError
from app.models import Prediction

router = APIRouter(dependencies=[Depends(require_api_key)])

_GIT_TIMEOUT = 180
_sync_lock = threading.Lock()
logger = logging.getLogger("backend.sync")

MAX_LIMIT = 50


def _run_git(repo: str, *args: str) -> str:
    """执行 git 命令；代理经命令行参数禁用，不读全局配置。

    `encoding="utf-8"` 显式指定：Windows 默认按 locale（cp936）解码，Camel 的
    中文提交信息会乱码并最终写进 `commit.message`。
    失败一律映射为契约内 50000 + `internal error`（细节只进 logger，不回显调用方）。
    """
    cmd = ["git", "-C", repo, "-c", "http.proxy=", "-c", "https.proxy=", *args]
    try:
        proc = subprocess.run(
            cmd, capture_output=True, text=True, encoding="utf-8", errors="replace",
            timeout=_GIT_TIMEOUT, check=True,
        )
    except subprocess.TimeoutExpired as exc:
        logger.exception("sync git timeout: %s", args[:2])
        raise AppError(50000, INTERNAL_ERROR_MESSAGE) from exc
    except (subprocess.CalledProcessError, OSError) as exc:
        logger.exception("sync git failed: %s", args[:2])
        raise AppError(50000, INTERNAL_ERROR_MESSAGE) from exc
    return proc.stdout


def build_fetch_args() -> list[str]:
    """fetch 命令参数：取远端默认分支（HEAD），经命令行禁代理（纯函数，供测试）。"""
    return ["fetch", "origin", "HEAD"]


def fetch_latest_tip(repo: str, retries: int = 3) -> str:
    """fetch 远端并返回最新 tip 哈希（FETCH_HEAD 首个条目）；网络抖动时重试。"""
    last: Exception | None = None
    for attempt in range(1, retries + 1):
        try:
            _run_git(repo, *build_fetch_args())
            break
        except AppError as exc:
            last = exc
            if attempt < retries:
                time.sleep(5)
    else:
        raise AppError(50000, "sync git operation failed") from last
    tip = _run_git(repo, "rev-parse", "FETCH_HEAD").strip()
    if len(tip) != 40:
        raise AppError(50000, INTERNAL_ERROR_MESSAGE)
    return tip


def _is_ancestor(repo: str, commit: str, base: str = "HEAD") -> bool:
    check = subprocess.run(
        ["git", "-C", repo, "merge-base", "--is-ancestor", commit, base],
        capture_output=True, encoding="utf-8", errors="replace",
        timeout=_GIT_TIMEOUT, check=False,
    )
    return check.returncode == 0


def ensure_extractable(repo: str, tip: str) -> tuple[str, Callable[[], None]]:
    """返回 (特征提取用仓库路径, 释放函数)。

    tip 已从 HEAD 可达：直接用 SOURCE_REPO 本身，释放为空操作；
    否则建专用临时工作树（detached @ tip，--no-checkout 不落工作区文件），
    绝不 checkout / reset 用户的检出状态。释放函数负责 worktree remove + 目录清理。

    自救：进程被硬杀（Ctrl-C）时 `<repo>/.git/worktrees/` 可能留残留条目，
    之后 `git worktree` 命令会警告 —— 在 SOURCE_REPO 里跑一次 `git worktree prune` 即可。
    """
    if _is_ancestor(repo, tip):
        return repo, lambda: None

    tmp = Path(tempfile.mkdtemp(prefix="jit-sync-"))
    try:
        _run_git(repo, "worktree", "add", "--detach", "--no-checkout", str(tmp), tip)
    except AppError:
        shutil.rmtree(tmp, ignore_errors=True)
        raise

    def _release() -> None:
        try:
            _run_git(repo, "worktree", "remove", "--force", str(tmp))
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

    return str(tmp), _release


def pick_hashes_to_predict(hashes: list[str], predicted: set[str]) -> list[str]:
    """按最新在前挑出**默认模型尚无 prediction 行**的哈希（纯函数，供测试）。

    判据是 prediction 而非 commit：灌数允许 commit 多于 prediction，
    已存在但未预测的提交必须能被同步补上。
    """
    return [h for h in hashes if h not in predicted]


def list_recent_hashes(repo: str, limit: int) -> list[str]:
    out = _run_git(repo, "log", "--format=%H", f"-n{limit}", "FETCH_HEAD")
    return [line.strip() for line in out.splitlines() if line.strip()]


def sync_recent(limit: int = 10) -> dict:
    """同步入口：fetch → 挑待预测 → 逐条走单条预测链。任一条失败不中断整批。"""
    if not (1 <= limit <= MAX_LIMIT):
        raise AppError(40001, f"参数非法：limit 需在 1..{MAX_LIMIT}")
    if not _sync_lock.acquire(blocking=False):
        # 冻结错误码集合内无 429；并发重入统一按 50000 + internal error 处理
        raise AppError(50000, INTERNAL_ERROR_MESSAGE)
    try:
        repo = config.SOURCE_REPO
        if repo is None or not (repo / ".git").exists():
            raise AppError(40400, "sync source repository unavailable")

        tip = fetch_latest_tip(str(repo))
        hashes = list_recent_hashes(str(repo), limit)

        default_model = model_registry.default_model()
        default_name = default_model.name if default_model else None
        with SessionLocal() as session:
            if default_name is not None:
                rows = (
                    session.query(Prediction.commit_hash)
                    .filter(
                        Prediction.commit_hash.in_(hashes),
                        Prediction.model_name == default_name,
                    )
                    .all()
                )
                predicted = {r[0] for r in rows}
            else:
                predicted = set()
        pending = pick_hashes_to_predict(hashes, predicted)

        extract_repo, release = ensure_extractable(str(repo), tip)
        try:
            results: list[dict] = []
            skipped: list[dict] = []
            for h in pending:
                try:
                    result = predict_commit(PredictRequest(commit_hash=h), repo=extract_repo)
                    results.append(
                        {
                            "commit_hash": h,
                            "model_name": result["data"]["model_name"],
                            "risk_score": result["data"]["risk_score"],
                        }
                    )
                except AppError as exc:
                    skipped.append({"commit_hash": h, "code": exc.code, "message": exc.message})
        finally:
            release()

        logger.info(
            "sync done: tip=%s scanned=%s pending=%s predicted=%s skipped=%s",
            tip[:10], len(hashes), len(pending), len(results), len(skipped),
        )
        return {
            "tip": tip,
            "scanned": len(hashes),
            "new": len(pending),
            "predicted": results,
            "skipped": skipped,
        }
    finally:
        _sync_lock.release()


@router.post("/api/sync")
def sync_endpoint(limit: int = Query(default=10, ge=1, le=MAX_LIMIT)) -> dict:
    """拉取 SOURCE_REPO 最新提交并逐条现算预测入库；无待预测提交时幂等返回 0。"""
    data = sync_recent(limit)
    return {"code": 0, "message": "ok", "data": data}


__all__ = [
    "MAX_LIMIT",
    "build_fetch_args",
    "ensure_extractable",
    "fetch_latest_tip",
    "list_recent_hashes",
    "pick_hashes_to_predict",
    "router",
    "sync_recent",
]
