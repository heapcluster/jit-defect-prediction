"""Conservative PR review prototype. No model API is called by this module.

The default workflow is read-only. A future provider may write a JSON decision
file; publication still requires explicit config and a separate --publish flag.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

API = "https://api.github.com"
MARKER = "<!-- pr-auto-review:{sha} -->"


def api_request(path: str, token: str, method: str = "GET", data: dict | None = None):
    body = json.dumps(data).encode("utf-8") if data is not None else None
    request = urllib.request.Request(
        API + path,
        data=body,
        method=method,
        headers={
            "Accept": "application/vnd.github+json",
            "Authorization": "Bearer " + token,
            "Content-Type": "application/json",
            "User-Agent": "jit-pr-review-prototype",
            "X-GitHub-Api-Version": "2022-11-28",
        },
    )
    with urllib.request.urlopen(request, timeout=20) as response:
        return json.load(response)


def list_pages(path: str, token: str, max_pages: int = 31) -> list[dict]:
    """Read at most GitHub's 3000-file PR limit; fail closed at the boundary."""
    rows: list[dict] = []
    for page in range(1, max_pages + 1):
        separator = "&" if "?" in path else "?"
        batch = api_request(f"{path}{separator}per_page=100&page={page}", token)
        if not isinstance(batch, list):
            raise TypeError("GitHub API did not return a list")
        rows.extend(batch)
        if len(batch) < 100:
            return rows
    raise ValueError("PR file pagination exceeded the safe limit")


def inspect_files(files: list[dict], config: dict) -> tuple[bool, str]:
    if not files:
        return False, "PR has no changed files"
    if len(files) > config["max_files"]:
        return False, "PR has too many files for complete review"
    if any("patch" not in f for f in files):
        return False, "A changed file has no textual patch"
    for f in files:
        lines = f["patch"].splitlines()
        added = sum(line.startswith("+") for line in lines)
        deleted = sum(line.startswith("-") for line in lines)
        if added != f.get("additions") or deleted != f.get("deletions"):
            return False, "A file patch is incomplete or truncated"
    size = sum(len(f["patch"].encode("utf-8")) for f in files)
    if size > config["max_patch_bytes"]:
        return False, "PR patch exceeds review size limit"
    return True, "complete"


def choose_action(
    decision: dict | None,
    files: list[dict],
    config: dict,
    check_conclusions: dict[str, str],
    head_sha: str,
) -> tuple[str, str]:
    """Return (APPROVE|REQUEST_CHANGES|SKIP, reason); never infer an approval."""
    if not config.get("enabled", False):
        return "SKIP", "prototype disabled"
    complete, reason = inspect_files(files, config)
    if not complete:
        return "SKIP", reason
    if not decision:
        return "SKIP", "no model decision; provider API is disabled"
    if decision.get("head_sha") != head_sha:
        return "SKIP", "model decision is for another commit"
    action = decision.get("action")
    findings = decision.get("findings")
    if not isinstance(findings, list):
        return "SKIP", "decision findings must be a list"
    if action not in ("APPROVE", "REQUEST_CHANGES"):
        return "SKIP", "unsupported decision action"
    changed = {f["filename"] for f in files}
    if len(findings) > 10:
        return "SKIP", "too many findings for a single review"
    for finding in findings:
        if not isinstance(finding, dict) or finding.get("path") not in changed:
            return "SKIP", "finding does not point to a changed file"
        if not isinstance(finding.get("reason"), str) or not finding["reason"].strip():
            return "SKIP", "finding has no explanation"
        patch = next(f["patch"] for f in files if f["filename"] == finding["path"])
        evidence = finding.get("evidence")
        if not isinstance(evidence, str) or not evidence.strip() or evidence not in patch:
            return "SKIP", "finding evidence does not occur in the changed patch"
    if action == "REQUEST_CHANGES":
        if not findings:
            return "SKIP", "request changes needs an actionable finding"
        return action, "validated findings"
    if findings:
        return "SKIP", "approval conflicts with findings"
    for check in config["required_checks"]:
        if check_conclusions.get(check) != "success":
            return "SKIP", f"required check {check!r} is not successful"
    return action, "all approval gates passed"


def review_body(action: str, reason: str, decision: dict, head_sha: str) -> str:
    lines = [MARKER.format(sha=head_sha), "自动审阅（原型）：" + reason]
    if action == "REQUEST_CHANGES":
        for finding in decision["findings"]:
            lines.append(
                f"- `{finding['path']}`：{finding['reason']}（差异证据：`{finding['evidence']}`）"
            )
    else:
        lines.append("已覆盖完整文本差异，模型无阻断项，且必需检查通过。")
    return "\n\n".join(lines)


def run(args: argparse.Namespace) -> int:
    config = json.loads(args.config.read_text(encoding="utf-8"))
    event = json.loads(args.event.read_text(encoding="utf-8"))
    pr_event = event.get("pull_request") or {}
    number = pr_event.get("number") or event.get("number")
    repo = (event.get("repository") or {}).get("full_name")
    if not isinstance(number, int) or not repo or "/" not in repo:
        print("SKIP: event has no valid PR number or repository")
        return 0
    if not config.get("enabled", False):
        print(f"SKIP: prototype disabled for {repo}#{number}; no model API or review write")
        return 0
    token = os.environ.get("GITHUB_TOKEN", "")
    if not token:
        print("SKIP: GITHUB_TOKEN is absent")
        return 0
    repo_path = "/repos/" + urllib.parse.quote(repo, safe="/")
    pr_path = f"{repo_path}/pulls/{number}"
    pr = api_request(pr_path, token)
    if pr.get("state") != "open" or pr.get("draft"):
        print("SKIP: PR is not open and ready")
        return 0
    head_sha = pr["head"]["sha"]
    if pr_event.get("head", {}).get("sha") not in (None, head_sha):
        print("SKIP: event head is stale")
        return 0
    files = list_pages(pr_path + "/files", token)
    decision = (
        json.loads(args.decision_file.read_text(encoding="utf-8")) if args.decision_file else None
    )
    checks = {}
    if decision and decision.get("action") == "APPROVE":
        response = api_request(f"{repo_path}/commits/{head_sha}/check-runs?per_page=100", token)
        checks = {row["name"]: row["conclusion"] for row in response.get("check_runs", [])}
    action, reason = choose_action(decision, files, config, checks, head_sha)
    print(f"{action}: {reason}; {len(files)} changed file(s); head {head_sha}")
    if action == "SKIP" or not args.publish:
        return 0
    if not config.get("publish", False):
        print("SKIP: publication is disabled by config")
        return 0
    latest = api_request(pr_path, token)
    if latest["head"]["sha"] != head_sha:
        print("SKIP: PR head changed before publication")
        return 0
    previous = list_pages(pr_path + "/reviews", token)
    marker = MARKER.format(sha=head_sha)
    if any(marker in (review.get("body") or "") for review in previous):
        print("SKIP: already reviewed this commit")
        return 0
    payload = {
        "commit_id": head_sha,
        "event": action,
        "body": review_body(action, reason, decision, head_sha),
    }
    api_request(pr_path + "/reviews", token, method="POST", data=payload)
    print("Published " + action)
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--event", type=Path, required=True)
    parser.add_argument(
        "--config", type=Path, default=Path(__file__).with_name("pr_review_config.json")
    )
    parser.add_argument(
        "--decision-file", type=Path, help="offline provider JSON; no API provider is built in"
    )
    parser.add_argument("--publish", action="store_true", help="also requires config.publish=true")
    args = parser.parse_args()
    try:
        return run(args)
    except (OSError, TypeError, ValueError, KeyError, urllib.error.HTTPError) as exc:
        print(f"SKIP: review failed closed: {type(exc).__name__}: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
