"""数据收集：平台接口、SZZ 打标、专家 / 语义特征与产物。"""

from __future__ import annotations

import math
from datetime import datetime

from git import Repo

from app import config
from app.constants import EXPERT_COLUMNS, EXPERT_FEATURES, FEATURE_VERSION, SEMANTIC_COLUMNS, SEMANTIC_FEATURES
from app.errors import AppError
from app.services import artifacts, platform
from app.services.jobs import JobContext
from app.utils import iso
from data_model import features as feature_lib
from data_model import gitops, semantic, szz


def parse_repo(repo_url: str) -> dict:
    try:
        return gitops.parse_repo_url(repo_url)
    except ValueError as exc:
        raise AppError(40001, str(exc)) from exc


def branch_list(repo_url: str) -> dict:
    info = parse_repo(repo_url)
    try:
        default, branches = platform.branches(info)
    except LookupError as exc:
        raise AppError(40401, str(exc)) from exc
    except RuntimeError as exc:
        raise AppError(50301, str(exc)) from exc
    return {"platform": info["platform"], "default_branch": default, "branches": branches}


def precheck(repo_url: str, branch: str, mode: str, warn_minutes: int, danger_minutes: int) -> dict:
    info = parse_repo(repo_url)
    if mode not in ("expert", "semantic"):
        raise AppError(40001, "解析方式非法")
    try:
        repo = gitops.ensure_repo(info)
        commits = gitops.iter_commits(repo, branch)
        issues = platform.bug_issues(info)
    except LookupError as exc:
        raise AppError(40401, str(exc)) from exc
    except RuntimeError as exc:
        raise AppError(50301, str(exc)) from exc
    except Exception as exc:  # noqa: BLE001
        raise AppError(50301, f"仓库拉取失败：{exc}") from exc
    estimate = 30 + len(issues) * 0.05 + len(commits) * (0.3 if mode == "expert" else 1.0)
    minutes = math.ceil(estimate / 60)
    level = "red" if minutes >= danger_minutes else "yellow" if minutes >= warn_minutes else "none"
    return {
        "platform": info["platform"],
        "commit_count": len(commits),
        "issue_count": len(issues),
        "estimate_seconds": int(math.ceil(estimate)),
        "warn_level": level,
    }


def _patch_text(commit) -> str:
    if not commit.parents:
        return ""
    try:
        diff = commit.parents[0].diff(commit, create_patch=True)
    except Exception:  # noqa: BLE001
        return ""
    parts = []
    for item in diff:
        path = item.b_path or item.a_path
        patch = item.diff.decode("utf-8", errors="replace") if isinstance(item.diff, bytes) else (item.diff or "")
        parts.append(f"--- {path}\n{patch}")
    return "\n".join(parts)


def run_collect(ctx: JobContext) -> None:
    params = ctx.params
    info = parse_repo(params.get("repo_url", ""))
    branch = params.get("branch")
    mode = params.get("mode", "expert")
    if not branch:
        raise AppError(40001, "分支不能为空")

    ctx.set_stage("克隆仓库")
    try:
        repo = gitops.ensure_repo(info)
        commits = gitops.iter_commits(repo, branch)
    except Exception as exc:  # noqa: BLE001
        raise AppError(50301, f"仓库拉取失败：{exc}") from exc
    if not commits:
        raise AppError(40901, "该分支没有可收集的提交")
    ctx.set_total(len(commits))
    ctx.update(force=True)

    ctx.set_stage("拉取 issue")
    try:
        issues = platform.bug_issues(info)
    except LookupError as exc:
        raise AppError(40401, str(exc)) from exc
    except RuntimeError as exc:
        raise AppError(50301, str(exc)) from exc
    if not issues:
        raise AppError(40901, "该仓库无可用的缺陷 issue 数据")

    ctx.set_stage("SZZ 回溯")
    message_by_hash = {commit.hexsha: commit.message for commit in commits}
    associated = platform.fill_fix_hashes(info, issues, list(message_by_hash), message_by_hash)
    fix_hashes: list[str] = []
    for issue in issues:
        for item in issue["fix_hashes"]:
            if item not in fix_hashes:
                fix_hashes.append(item)
    if not fix_hashes:
        raise AppError(40901, "全部缺陷 issue 均未关联到修复提交")
    labels = szz.label_commits(repo, list(message_by_hash), fix_hashes)
    ctx.advance(len(commits) // 3, "SZZ 回溯")

    ctx.set_stage("特征计算")
    feature_map: dict[str, list[float]] = {}
    if mode == "expert":
        computed = feature_lib.compute_features_batch(repo, commits)
        for commit in commits:
            feature_map[commit.hexsha] = [float(computed[commit.hexsha][name]) for name in EXPERT_FEATURES]
        columns = EXPERT_COLUMNS
    else:
        texts = [semantic.compose_text(commit.message, _patch_text(commit)) for commit in commits]
        vectors = semantic.encode_texts(texts, config.SEMANTIC_TEXT_MODEL, config.SEMANTIC_MAX_LEN)
        for index, commit in enumerate(commits):
            feature_map[commit.hexsha] = [float(value) for value in vectors[index].tolist()]
        columns = SEMANTIC_COLUMNS
    ctx.advance(len(commits) // 3, "特征计算")

    rows = []
    for commit in commits:
        meta = gitops.commit_meta(commit)
        label = labels.get(commit.hexsha, {"is_bug_inducing": 0, "fix_commit_hash": None})
        row = {
            "project": info["repo_name"],
            "commit_id": commit.hexsha,
            "commit_time": iso(meta["committed_at"]),
            "author_name": meta["author_name"],
            "author_email": meta["author_email"],
            "commit_message": meta["message"],
            "bug": label["is_bug_inducing"],
            "label_method": "szz",
            "fix_commit_hash": label["fix_commit_hash"] or "",
            "parent_hash": meta["parent_hash"] or "",
        }
        for name, value in zip(EXPERT_FEATURES if mode == "expert" else SEMANTIC_FEATURES, feature_map[commit.hexsha]):
            row[name] = value
        rows.append(row)
    pos = sum(1 for row in rows if row["bug"] == 1)
    if pos == 0:
        raise AppError(40901, "SZZ 未标记出任何缺陷提交，无法产出可训练数据集")

    out_dir = artifacts.output_dir(ctx.user_id, ctx.job_id)
    data_path = out_dir / "data.csv"
    artifacts.write_csv(data_path, columns, rows)
    manifest = {
        "job_id": ctx.job_id,
        "kind": "collect",
        "user_id": ctx.user_id,
        "created_at": iso(datetime.now()),
        "line": mode,
        "columns": columns,
        "row_count": len(rows),
        "files": [{"name": "data.csv", "size": data_path.stat().st_size, "sha256": artifacts.file_sha256(data_path)}],
        "repo": {
            "repo_url": info["repo_url"],
            "repo_name": info["repo_name"],
            "platform": info["platform"],
            "branch": branch,
            "head_hash": commits[-1].hexsha if commits else None,
        },
    }
    artifacts.write_manifest(out_dir / "manifest.json", manifest)
    artifacts.write_json(
        out_dir / "steps.json",
        {"issues": len(issues), "associated_issues": associated, "fix_commits": len(fix_hashes), "sample": len(rows)},
    )
    ctx.advance(len(commits), "完成")
    ctx.set_output({
        "data_path": artifacts.rel(data_path),
        "manifest_path": artifacts.rel(out_dir / "manifest.json"),
        "columns": columns,
        "row_count": len(rows),
        "line": mode,
        "feature_version": FEATURE_VERSION[mode],
        "source_type": "git_repo",
        "summary": {"total": len(rows), "pos": pos, "neg": len(rows) - pos},
        "repo": manifest["repo"],
        "manifest": manifest,
    })


def preview(job_output: dict) -> dict:
    ref = job_output
    columns, rows = artifacts.read_table(artifacts.resolve(ref["data_path"]))
    core = ["commit_id", "commit_time", "author_name", "bug"]
    features = [name for name in columns if name not in ("project", "commit_id", "commit_time", "author_name", "author_email", "commit_message", "bug")]
    core_features = features[:6]
    return {"columns": core + core_features, "rows": rows, "all_columns": columns}
