"""GitHub REST 客户端：拉取 Camel 公开仓库的 open PR 与提交清单（只读）。

纯标准库 urllib 实现，不引入新依赖（与 infra/pr_auto_review.py 同源风格）。
职责边界：本模块**只负责获知哪些 PR 是 open 及其 head/commits**（数据是实时的），
特征计算与预测仍走本地 blobless 历史索引（config.SOURCE_REPO）+ 现有预测链。
"""

from __future__ import annotations

import json
import os
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass

from app import config

API = "https://api.github.com"


@dataclass
class PullRequest:
    number: int
    title: str
    author: str
    state: str
    head_sha: str
    html_url: str
    updated_at: str


def _headers() -> dict[str, str]:
    headers = {
        "Accept": "application/vnd.github+json",
        "User-Agent": "jit-defect-prediction",
        "X-GitHub-Api-Version": "2022-11-28",
    }
    token = os.getenv("GITHUB_TOKEN") or config.GITHUB_TOKEN
    if token:
        headers["Authorization"] = "Bearer " + token
    return headers


def _get(path: str, params: dict | None = None) -> list | dict:
    url = API + path
    if params:
        url += "?" + urllib.parse.urlencode(params)
    req = urllib.request.Request(url, headers=_headers())
    try:
        with urllib.request.urlopen(req, timeout=20) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:  # 403/404 等：细节只进日志，调用方按内部错误处理
        raise RuntimeError(f"github api {exc.code}: {url}") from exc
    except urllib.error.URLError as exc:
        raise RuntimeError(f"github api unreachable: {url}") from exc


def list_open_prs(limit: int = 20, repo: str | None = None) -> list[PullRequest]:
    """按最近更新排序取 open PR（封顶 limit 条）。"""
    repo = repo or config.GITHUB_REPO
    if not repo:
        raise RuntimeError("GITHUB_REPO not configured")
    prs: list[PullRequest] = []
    for page in range(1, 4):  # 最多 3 页 = 300 个 PR
        batch = _get(
            f"/repos/{repo}/pulls",
            {"state": "open", "sort": "updated", "direction": "desc", "per_page": 100, "page": page},
        )
        if not isinstance(batch, list):
            break
        for item in batch:
            prs.append(
                PullRequest(
                    number=item["number"],
                    title=item.get("title", ""),
                    author=(item.get("user") or {}).get("login", ""),
                    state=item.get("state", ""),
                    head_sha=item["head"]["sha"],
                    html_url=item.get("html_url", ""),
                    updated_at=item.get("updated_at", ""),
                )
            )
            if len(prs) >= limit:
                return prs
        if len(batch) < 100:
            break
    return prs[:limit]


def get_pr(pr_number: int, repo: str | None = None) -> PullRequest:
    repo = repo or config.GITHUB_REPO
    item = _get(f"/repos/{repo}/pulls/{pr_number}")
    return PullRequest(
        number=item["number"],
        title=item.get("title", ""),
        author=(item.get("user") or {}).get("login", ""),
        state=item.get("state", ""),
        head_sha=item["head"]["sha"],
        html_url=item.get("html_url", ""),
        updated_at=item.get("updated_at", ""),
    )


def list_pr_commit_shas(pr_number: int, repo: str | None = None) -> list[str]:
    """PR 内全部提交哈希（按时间正序）。封顶 1000 条以防异常大 PR。"""
    repo = repo or config.GITHUB_REPO
    shas: list[str] = []
    for page in range(1, 11):
        batch = _get(f"/repos/{repo}/pulls/{pr_number}/commits", {"per_page": 100, "page": page})
        if not isinstance(batch, list):
            break
        for item in batch:
            shas.append(item["sha"])
        if len(batch) < 100:
            break
    return shas
