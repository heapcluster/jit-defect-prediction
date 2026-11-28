"""GitHub / Gitee 公开接口：分支与缺陷 issue。"""

from __future__ import annotations

import json
import urllib.error
import urllib.parse
import urllib.request

from app import config


def _get(url: str, token: str = "") -> tuple[int, object]:
    request = urllib.request.Request(url, headers={"Accept": "application/vnd.github+json", "User-Agent": "jit-defect-prediction"})
    if token:
        if "gitee.com" in url:
            request.add_header("Authorization", f"token {token}")
        else:
            request.add_header("Authorization", f"Bearer {token}")
    try:
        with urllib.request.urlopen(request, timeout=20) as response:
            return response.status, json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        if exc.code == 404:
            return 404, None
        if exc.code in (403, 429):
            raise RuntimeError("平台接口限流，请稍后重试（仅支持公开仓库）") from exc
        raise RuntimeError(f"平台接口不可用（HTTP {exc.code}）") from exc
    except (urllib.error.URLError, TimeoutError) as exc:
        raise RuntimeError("平台接口不可用") from exc


def branches(info: dict) -> tuple[str, list[str]]:
    if info["platform"] == "github":
        status, repo = _get(f"https://api.github.com/repos/{info['owner']}/{info['repo']}", config.GITHUB_TOKEN)
        if status == 404:
            raise LookupError("仓库不存在或非公开")
        default = (repo or {}).get("default_branch", "main")
        status, data = _get(
            f"https://api.github.com/repos/{info['owner']}/{info['repo']}/branches?per_page=100",
            config.GITHUB_TOKEN,
        )
        if status == 404:
            raise LookupError("仓库不存在或非公开")
        names = [item["name"] for item in (data or [])]
        return default, sorted(set(names) | {default})
    status, data = _get(
        f"https://gitee.com/api/v5/repos/{info['owner']}/{info['repo']}/branches?per_page=100",
        config.GITEE_TOKEN,
    )
    if status == 404:
        raise LookupError("仓库不存在或非公开")
    names = [item["name"] for item in (data or [])]
    default = names[0] if names else "master"
    return default, sorted(names)


def bug_issues(info: dict, limit: int = 200) -> list[dict]:
    """返回缺陷 issue 列表：[{number, title, fix_hashes[]}]。"""
    if info["platform"] == "github":
        url = (
            f"https://api.github.com/repos/{info['owner']}/{info['repo']}"
            f"/issues?state=all&labels=bug&per_page=100"
        )
        status, data = _get(url, config.GITHUB_TOKEN)
        if status == 404:
            raise LookupError("仓库不存在或非公开")
        issues = []
        for item in (data or [])[:limit]:
            if "pull_request" in item:
                continue
            issues.append({"number": item["number"], "title": item.get("title", ""), "fix_hashes": []})
        return issues
    url = (
        f"https://gitee.com/api/v5/repos/{info['owner']}/{info['repo']}"
        f"/issues?state=all&per_page=100"
    )
    status, data = _get(url, config.GITEE_TOKEN)
    if status == 404:
        raise LookupError("仓库不存在或非公开")
    issues = []
    for item in (data or [])[:limit]:
        if str(item.get("issue_type", "bug")) != "bug":
            continue
        issues.append({"number": item["number"], "title": item.get("title", ""), "fix_hashes": []})
    return issues


def fill_fix_hashes(info: dict, issues: list[dict], commit_hashes: list[str], message_by_hash: dict[str, str]) -> int:
    """用 issue 事件与提交说明两路结果补充修复提交，返回关联成功的 issue 数。"""
    import re

    by_number = {str(item["number"]): item for item in issues}
    pattern = re.compile(r"(?:fix|fixes|fixed|close|closes|closed|resolve|resolves|resolved)\s+#(\d+)", re.IGNORECASE)
    for commit_hash, message in message_by_hash.items():
        for number in pattern.findall(message or ""):
            item = by_number.get(number)
            if item is not None and commit_hash not in item["fix_hashes"]:
                item["fix_hashes"].append(commit_hash)
    if info["platform"] == "github":
        token = config.GITHUB_TOKEN
        for item in issues[:50]:
            if item["fix_hashes"]:
                continue
            url = (
                f"https://api.github.com/repos/{info['owner']}/{info['repo']}"
                f"/issues/{item['number']}/events?per_page=100"
            )
            try:
                _, events = _get(url, token)
            except RuntimeError:
                continue
            for event in events or []:
                commit_id = event.get("commit_id")
                if commit_id and commit_id in commit_hashes and commit_id not in item["fix_hashes"]:
                    item["fix_hashes"].append(commit_id)
    return sum(1 for item in issues if item["fix_hashes"])
