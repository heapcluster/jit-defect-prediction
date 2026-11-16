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
    """SHAP 解释项（附中文因子名）；模型未注册、缺特征或非 expert 线时返回空。

    semantic/fused/e2e 的输入不是 14 维特征，强行算 SHAP 会加载错模型/维度不符；
    与 predict_single 同口径，只对 expert 线提供逐因子解释。
    """
    if not model_name or feature is None or not model_registry.has(model_name):
        return []
    if model_registry.line_of(model_name) != "expert":
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


_SOURCE_SUFFIXES = (
    ".java",
    ".kt",
    ".py",
    ".ts",
    ".tsx",
    ".js",
    ".jsx",
    ".go",
    ".rs",
    ".c",
    ".cc",
    ".cpp",
    ".h",
    ".cs",
)
_DOC_SUFFIXES = (".md", ".adoc", ".txt", ".rst", ".json", ".yml", ".yaml", ".xml", ".properties")
_TEST_MARKERS = ("/test/", "/tests/", "src/test", "test_", "_test.", ".test.", ".spec.")
_GENERATED_MARKERS = ("/generated/", "/target/", "/dist/", "/build/", "node_modules/")


def _file_weight(path: str) -> tuple[float, str]:
    """启发式文件类型权重：源码 > 普通文件 > 配置/文档 > 测试/生成物。"""
    low = path.lower()
    if any(marker in low for marker in _GENERATED_MARKERS):
        return 0.1, "生成物"
    if any(marker in low for marker in _TEST_MARKERS):
        return 0.35, "测试文件"
    if low.endswith(_SOURCE_SUFFIXES):
        return 1.0, "源码文件"
    if low.endswith(_DOC_SUFFIXES):
        return 0.4, "文档/配置"
    return 0.6, "普通文件"


_FILE_TIER = {"源码文件": 3, "普通文件": 2, "文档/配置": 1, "测试文件": 1, "生成物": 0}
_LINE_PATH_FACTOR = {"源码文件": 1.0, "普通文件": 0.9, "文档/配置": 0.55, "测试文件": 0.6, "生成物": 0.35}


def _file_raw_score(file: dict) -> tuple[float, list[str]]:
    added = len(file.get("added_lines") or [])
    deleted = int(file.get("deleted_count") or 0)
    hunks = file.get("hunks") or []
    weight, kind = _file_weight(file["path"])
    modified = bool(added and deleted)
    # 修改既有逻辑（有增有删）比纯新增文件更值得先看；hunk 越多说明改动越分散
    raw = (added + 2 * deleted) * (1.5 if modified else 1.0) * weight
    raw *= 1 + 0.15 * max(0, min(len(hunks) - 1, 4))
    reasons = [kind]
    if modified:
        reasons.append("修改既有代码")
    if len(hunks) > 1:
        reasons.append(f"{len(hunks)} 个 hunk")
    return raw, reasons


def _hunk_raw_score(hunk: dict) -> int:
    added = len(hunk.get("added_lines") or [])
    deleted = int(hunk.get("deleted_count") or 0)
    return added + 2 * deleted + (1 if added and deleted else 0)


_SUSPICIOUS_KEYWORDS = (
    "if ",
    "else",
    "throw",
    "catch",
    "return",
    "null",
    "none",
    "optional",
    "todo",
    "fixme",
    "lock",
    "close",
    "url",
    "path",
    "glob",
    "security",
    "auth",
    "password",
    "token",
    "assert",
    "while",
    "for ",
    "switch",
    "case",
    "synchronized",
    "try",
)


def _line_suspicion(
    line: dict, *, risk_score: float | None, file_score: float, hunk_norm: float, path: str
) -> float:
    """启发式逐行可疑度：提交风险 × 文件/hunk 权重 × 行内容信号（不是训练出的行级概率）。"""
    text = (line.get("content") or "").strip()
    if not text:
        factor = 0.35
    elif text.startswith(("//", "/*", "*", "#", "<!--")):
        factor = 0.45
    elif text.startswith(("import ", "package ", "from ", "using ")):
        factor = 0.55
    else:
        low = text.lower()
        factor = 1.25 if any(keyword in low for keyword in _SUSPICIOUS_KEYWORDS) else 1.0
    _, kind = _file_weight(path)
    factor *= _LINE_PATH_FACTOR.get(kind, 0.9)
    base = risk_score if risk_score is not None else 0.5
    score = base * (0.45 + 0.35 * file_score + 0.20 * hunk_norm) * factor
    return round(max(0.02, min(score, 0.99)), 3)


def diff_localization_for(
    repo: str | Path | None,
    commit_hash: str,
    max_files: int = 5,
    max_lines: int = 30,
    risk_score: float | None = None,
) -> dict | None:
    """启发式行级缺陷定位（G1-1）：按文件/hunk 可疑度排序后展示新增行。

    repo 未配置 / 提交不可达 → None（调用方降级到提交级）。只返回真实 diff 数据；
    行内概率仍是提交级概率，不编造独立行级模型输出。
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

    scored = [(raw, f, reasons) for f in files for raw, reasons in [_file_raw_score(f)]]
    max_raw = max((raw for raw, _, _ in scored), default=0.0)
    for raw, f, reasons in scored:
        f["score"] = round(raw / max_raw, 3) if max_raw else 0.0
        f["reasons"] = reasons
        f["added_count"] = len(f.get("added_lines") or [])
        f["deleted_count"] = int(f.get("deleted_count") or 0)
    # 先按文件类型层级（源码 > 普通 > 文档/测试 > 生成物），再按可疑度与规模排序：
    # 生成物/文档即使行数再多，也不能压过源码文件。
    scored.sort(
        key=lambda item: (
            _FILE_TIER.get(item[2][0], 1),
            item[1]["score"],
            item[1]["added_count"],
        ),
        reverse=True,
    )

    truncated = False
    if len(scored) > max_files:
        scored = scored[:max_files]
        truncated = True

    for _, f, _ in scored:
        hunks = sorted(f.get("hunks") or [], key=_hunk_raw_score, reverse=True)
        if not hunks:
            if len(f["added_lines"]) > max_lines:
                f["added_lines"] = f["added_lines"][:max_lines]
                truncated = True
            for line in f["added_lines"]:
                line["score"] = _line_suspicion(
                    line,
                    risk_score=risk_score,
                    file_score=f["score"],
                    hunk_norm=0.5,
                    path=f["path"],
                )
            continue
        max_hunk = max((_hunk_raw_score(hunk) for hunk in hunks), default=1) or 1
        selected: list[dict] = []
        for hunk in hunks:
            if len(selected) >= max_lines:
                truncated = True
                break
            take = hunk["added_lines"][: max_lines - len(selected)]
            if len(take) < len(hunk["added_lines"]):
                truncated = True
            hunk_norm = _hunk_raw_score(hunk) / max_hunk
            for line in take:
                line["score"] = _line_suspicion(
                    line,
                    risk_score=risk_score,
                    file_score=f["score"],
                    hunk_norm=hunk_norm,
                    path=f["path"],
                )
            selected.extend(take)
        # 行号回序展示，避免按 hunk 分数跳来跳去
        f["added_lines"] = sorted(selected, key=lambda line: line["number"])
        f.pop("hunks", None)

    return {
        "files": [f for _, f, _ in scored],
        "truncated": truncated,
        "notice": (
            "启发式行级定位：文件按类型/修改方式/规模/hunk 排序；"
            "行级可疑度 = 提交风险 × 文件/hunk 权重 × 行内容信号，"
            "不是训练出的独立行级概率"
        ),
    }


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
