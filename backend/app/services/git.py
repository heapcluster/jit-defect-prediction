"""Git 操作共享服务（供 sync / prs 等模块复用）。

此前 `_run_git` / `fetch_latest_tip` / `ensure_extractable` 等散落在
`app.api.sync`，`prs.py` 通过 `sync._run_git` 跨路由私有调用，层次被破坏。
本模块统一为唯一定义点，对外行为与原实现一字不变。
"""

from __future__ import annotations

import logging
import os
import re
import shutil
import subprocess
import tempfile
import time
from collections.abc import Callable
from pathlib import Path

from app.errors import INTERNAL_ERROR_MESSAGE, AppError

logger = logging.getLogger("backend.git")

_GIT_TIMEOUT = 180
# 可重试的失败特征：只对「网络抖动」重试；仓库不存在 / 权限 / 参数错重试没有意义
_NETWORK_HINTS = (
    "could not resolve host",
    "connection timed out",
    "connection reset",
    "failed to connect",
    "early eof",
    "rpc failed",
    "the remote end hung up",
    "ssl",
    "tls",
    "timeout",
)
# 日志里的 URL 可能含 `https://token@host`，脱敏后再落盘
_CREDENTIAL = re.compile(r"://[^/@\s]+@")


class GitError(AppError):
    """git 子进程失败的统一异常（沿用契约错误码 50000）。

    `retryable` 区分「网络抖动（值得重试）」与「配置/仓库错误（立即失败）」——
    前者重试 3 次、每次 5s 等待，后者直接把失败抛给调用方。
    """

    def __init__(self, *, retryable: bool) -> None:
        super().__init__(50000, INTERNAL_ERROR_MESSAGE)
        self.retryable = retryable


def _redact(text: str) -> str:
    """抹掉 URL 里的凭据片段，避免 token 落进日志。"""
    return _CREDENTIAL.sub("://***@", text)


def _looks_like_network(stderr: str) -> bool:
    lowered = stderr.lower()
    return any(hint in lowered for hint in _NETWORK_HINTS)


def run_git(repo: str, *args: str) -> str:
    """执行 git 命令；代理只认 `GIT_PROXY`（其次 `HTTPS_PROXY`）。

    `encoding="utf-8"` 显式指定：Windows 默认按 locale（cp936）解码，Camel 的
    中文提交信息会乱码并最终写进 `commit.message`。
    """
    cmd = ["git", "-C", repo]
    proxy = os.getenv("GIT_PROXY", "").strip() or os.getenv("HTTPS_PROXY", "").strip()
    if proxy:
        cmd += ["-c", f"http.proxy={proxy}", "-c", f"https.proxy={proxy}"]
    else:
        cmd += ["-c", "http.proxy=", "-c", "https.proxy="]
    cmd += [*args]
    try:
        proc = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=_GIT_TIMEOUT,
            check=True,
        )
    except subprocess.TimeoutExpired as exc:
        logger.warning("git 超时（%ss）：%s", _GIT_TIMEOUT, args[:2])
        raise GitError(retryable=True) from exc
    except subprocess.CalledProcessError as exc:
        # 失败原因几乎全在 stderr 里；只记 args 会让线上「同步全挂」无从下手
        stderr = _redact((exc.stderr or "").strip())
        logger.warning("git 失败（%s）：%s", args[:2], stderr[:500])
        raise GitError(retryable=_looks_like_network(stderr)) from exc
    except OSError as exc:
        # git 未安装 / 不可执行：重试也没用
        logger.warning("git 无法执行（%s）：%s", args[:2], exc)
        raise GitError(retryable=False) from exc
    return proc.stdout


def build_fetch_args() -> list[str]:
    """fetch 命令参数：取远端默认分支（HEAD），纯函数，供测试。"""
    return ["fetch", "origin", "HEAD"]


def fetch_latest_tip(repo: str, retries: int = 3) -> str:
    """fetch 远端并返回最新 tip 哈希（FETCH_HEAD 首个条目）；仅网络类失败重试。"""
    last: Exception | None = None
    for attempt in range(1, retries + 1):
        try:
            run_git(repo, *build_fetch_args())
            break
        except GitError as exc:
            if not exc.retryable:
                raise
            last = exc
            if attempt < retries:
                time.sleep(5)
    else:
        raise AppError(50000, INTERNAL_ERROR_MESSAGE) from last
    tip = run_git(repo, "rev-parse", "FETCH_HEAD").strip()
    if len(tip) != 40:
        raise AppError(50000, INTERNAL_ERROR_MESSAGE)
    return tip


def is_ancestor(repo: str, commit: str, base: str = "HEAD") -> bool:
    """判断 commit 是否为 base 的祖先（纯函数，供测试）。"""
    check = subprocess.run(
        ["git", "-C", repo, "merge-base", "--is-ancestor", commit, base],
        capture_output=True,
        encoding="utf-8",
        errors="replace",
        timeout=_GIT_TIMEOUT,
        check=False,
    )
    return check.returncode == 0


def ensure_extractable(repo: str, tip: str) -> tuple[Path | str, Callable[[], None]]:
    """返回 (特征提取用仓库路径, 释放函数)。

    tip 已从 HEAD 可达直接用 SOURCE_REPO；否则建临时 worktree，用后即焚。
    绝不改动 SOURCE_REPO 的检出状态。
    """
    if is_ancestor(repo, tip):
        return Path(repo), lambda: None

    tmp = Path(tempfile.mkdtemp(prefix="jit-sync-"))
    try:
        run_git(repo, "worktree", "add", "--detach", "--no-checkout", str(tmp), tip)
    except AppError:
        shutil.rmtree(tmp, ignore_errors=True)
        raise

    def _release() -> None:
        try:
            run_git(repo, "worktree", "remove", "--force", str(tmp))
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

    return str(tmp), _release


def pick_hashes_to_predict(hashes: list[str], predicted: set[str]) -> list[str]:
    """按最新在前挑出尚无 prediction 行的哈希（纯函数，供测试）。"""
    return [h for h in hashes if h not in predicted]


def list_recent_hashes(repo: str, limit: int, ref: str = "FETCH_HEAD") -> list[str]:
    """取 ref 最近 limit 条哈希（时间倒序）。"""
    out = run_git(repo, "log", f"-n{limit}", "--format=%H", ref)
    return [line.strip() for line in out.splitlines() if line.strip()]


def list_all_hashes(repo: str, ref: str = "FETCH_HEAD") -> list[str]:
    """取 ref 历史全部哈希（时间倒序），用于 catchup 补齐 DB→HEAD 缺口。"""
    out = run_git(repo, "log", "--format=%H", ref)
    return [line.strip() for line in out.splitlines() if line.strip()]
