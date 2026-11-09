"""提交查询的共享组装逻辑（供 commits 路由与其它服务复用）。

只放「纯组装 / 查询片段」，不放 HTTP 相关东西；对外行为（字段、错误码）以
docs/api/commits.md 为准。
"""

from __future__ import annotations

from pathlib import Path

from sqlalchemy import select
from sqlalchemy.orm import Session

from app import config, model_registry
from app.diff import parse_unified_diff
from app.explain import with_labels
from app.models import Commit, CommitFeature
from app.services.git import GitError, show_unified_diff
from app.timeutil import iso_z


def default_model_in_table(session: Session | None = None) -> str | None:
    """「默认模型」= 已加载模型中 `version_key` 最大者（docs/database/model.md）。

    与列表 / 详情 / 趋势 / predict / sync 共用 `model_registry.default_model()` 一处实现，
    避免同一提交在多处拿到不同模型的不同分。
    """
    entry = model_registry.default_model()
    return entry.name if entry is not None else None


def feature_dict(feature: CommitFeature | None) -> dict | None:
    """14 项特征 → dict（fix 为整型，其余浮点）。"""
    if feature is None:
        return None
    out: dict = {}
    for name in config.FEATURE_COLUMNS:
        value = getattr(feature, name)
        out[name] = int(value) if name == "fix" else float(value)
    return out


def explanation_for(model_name: str | None, feature: CommitFeature | None) -> list[dict]:
    """SHAP 解释项（附中文因子名）；模型未注册或缺特征时返回空列表。"""
    if not model_name or feature is None or not model_registry.has(model_name):
        return []
    vector = [float(getattr(feature, name)) for name in config.FEATURE_COLUMNS]
    return with_labels(model_registry.explain(model_registry.get_model(model_name), vector))


def localization_for(explanation: list[dict], top_k: int = 5) -> dict:
    """缺陷可视化定位（G1-1）：无文件/行级差异数据，降级到提交级特征归因。

    高亮项 = 按 |SHAP contribution| 降序的前 `top_k` 个特征；归因为空（核/深度模型
    设计内降级）时如实返回空，MUST NOT 编造行级数据。
    """
    highlights = sorted(explanation, key=lambda item: abs(item["contribution"]), reverse=True)[
        :top_k
    ]
    notice = (
        "未采集文件/行级差异数据，已降级到提交级特征定位（按 SHAP 归因高亮可疑特征）"
        if highlights
        else "该模型未提供特征归因，暂无定位信息"
    )
    return {"level": "commit", "notice": notice, "highlights": highlights}


def diff_localization_for(
    repo: str | Path | None, commit_hash: str, max_files: int = 5, max_lines: int = 30
) -> dict | None:
    """行级缺陷定位（G1-1）：取提交 diff 的新增行，按文件聚合并截断。

    repo 未配置 / 提交不可达 → None（调用方降级到提交级）。只返回真实 diff 数据，
    MUST NOT 编造行级概率。
    """
    if repo is None or not (Path(repo) / ".git").exists():
        return None
    try:
        text = show_unified_diff(str(repo), commit_hash)
    except GitError:
        return None
    files = parse_unified_diff(text)
    if not files:
        return None
    truncated = False
    files.sort(key=lambda f: len(f["added_lines"]), reverse=True)
    if len(files) > max_files:
        files = files[:max_files]
        truncated = True
    for f in files:
        if len(f["added_lines"]) > max_lines:
            f["added_lines"] = f["added_lines"][:max_lines]
            truncated = True
    return {"files": files, "truncated": truncated}


def fix_references_for(session: Session, repo_name: str, exclude_hash: str, top_k: int = 5) -> dict:
    """高质量修复参考（G1-2）：同仓库历史修复提交（commit_feature.fix=1），按时间倒序。

    只返回真实存在的历史修复提交；无依据时 items 为空，MUST NOT 编造建议。
    """
    rows = session.execute(
        select(Commit.commit_hash, Commit.message, Commit.committed_at)
        .join(CommitFeature, CommitFeature.commit_hash == Commit.commit_hash)
        .where(
            Commit.repo_name == repo_name,
            CommitFeature.fix == 1,
            Commit.commit_hash != exclude_hash,
        )
        .order_by(Commit.committed_at.desc())
        .limit(top_k)
    ).all()
    items = [
        {"commit_hash": hash_, "message": message, "committed_at": iso_z(committed_at)}
        for hash_, message, committed_at in rows
    ]
    return {
        "basis": "同仓库历史修复提交（commit_feature.fix=1），按提交时间倒序",
        "items": items,
    }
