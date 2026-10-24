"""三线共用的「提交变更文本」口径：占位串、来源分类、行装配与登记统计。

放在 `pipelines/` 顶层（与 `verify_all_weights.py` 同级）供 semantic 与 e2e 共同 import。
**为什么不做成各包一份**：同一口径出现两份实现必然分叉 —— 交付包里的 `tabnet_v1.pkl`
就是因为两处导出上下文不同而分叉（#88 / Issue #103），`e2e/metrics.py` 缺
`cumulative_curve` 也是同一类问题。文本口径直接决定样本集合，分叉会让三线对比失效。

三类来源（`text_source` 列的取值，只做统计与登记，**不进特征、不进模型输入**）：

| 取值 | 判定条件 | 写入的 text |
|---|---|---|
| `diff` | 提交可读取，且第一父提交的 diff 有文本内容 | 真实 diff 文本（按 `max_chars` 截断） |
| `no_text_change` | 提交可读取、**有父提交**、diff 条目为 0 或装配后为空 | `[no-text-change]` |
| `root_commit` | 提交可读取、**没有父提交**（无「引入的 diff」可言） | `[root-commit]` |

提交在克隆仓库里**取不到**（`BadName` / `BadObject` 等）不属于以上任何一类：仍然跳过并
单独计数，绝不用占位串掩盖 —— 那意味着切分文件与克隆版本不一致，是真缺陷。

`no_text_change` 的现实来源：SVN 迁移进来的 `svn:ignore` / 属性类提交，Git 侧没有任何
文件内容变更。具体条数不在代码里写死 —— 以每次运行报告「文本来源与覆盖率」段的实测
登记为准（占位合计 / 全量 / 其中正样本），避免代码里的旧数字与新一轮切分对不上。
"""

from __future__ import annotations

from collections import Counter
from pathlib import Path

import numpy as np
import pandas as pd

SOURCE_DIFF = "diff"
SOURCE_NO_TEXT_CHANGE = "no_text_change"
SOURCE_ROOT_COMMIT = "root_commit"

# 占位串必须一眼能与真实 diff 区分（真实文本一律以 "diff --git " 开头），
# 且不能被 pandas 读成 NaN —— 空串会被 read_csv 当缺失值，随后被 dropna 丢掉，
# 覆盖率就又缺回去了。
PLACEHOLDER = {
    SOURCE_NO_TEXT_CHANGE: "[no-text-change]",
    SOURCE_ROOT_COMMIT: "[root-commit]",
}

SOURCES = (SOURCE_DIFF, SOURCE_NO_TEXT_CHANGE, SOURCE_ROOT_COMMIT)

# commit_text.csv 的列顺序（契约：`config-and-output-spec.md` §1.3）
TEXT_COLUMNS = ["commit_hash", "text", "label", "feature_version", "text_source"]

# 单文件 patch 超过该行数上限即截断（与各线原有口径一致，不随本模块改变）
PER_FILE_LIMIT = 1500


def assemble(diffs, max_chars: int,
             per_file_limit: int = PER_FILE_LIMIT) -> tuple[str, bool]:
    """把 GitPython 的 diff 列表装配成一段文本 → `(text, has_content)`。

    口径：每个改动文件 = 文件头（a/b 路径）+ patch；单文件超 `per_file_limit` 截断；
    总长超 `max_chars` 截断。合并提交由调用方按第一父提交取 diff。

    `has_content` 表示**是否含真实 patch 正文**：文件头是装配时自己加的，只有文件头
    而没有任何正文（模式变更、属性类变更等）不算「有文本变更」，否则模型会拿到一段
    只含路径的伪文本，还会被登记成 `diff` 而逃过占位统计。
    """
    parts: list[str] = []
    total = 0
    has_content = False
    for d in diffs:
        a_path = d.a_path or ""
        b_path = d.b_path or a_path
        header = f"diff --git a/{a_path} b/{b_path}\n"
        parts.append(header)
        total += len(header)
        patch = d.diff
        if patch:
            text = patch.decode("utf-8", "replace") if isinstance(patch, bytes) else str(patch)
            if text.strip():
                has_content = True
            if len(text) > per_file_limit:
                text = text[:per_file_limit] + "\n... [truncated]\n"
            parts.append(text)
            total += len(text)
        if total >= max_chars:
            break
    return "".join(parts)[:max_chars], has_content


def classify(has_parents: bool, assembled: str, has_content: bool) -> tuple[str, str]:
    """由「有没有父提交」与「有没有真实 patch 正文」定 (text, text_source)。"""
    if not has_parents:
        return PLACEHOLDER[SOURCE_ROOT_COMMIT], SOURCE_ROOT_COMMIT
    if has_content and assembled.strip():
        return assembled, SOURCE_DIFF
    return PLACEHOLDER[SOURCE_NO_TEXT_CHANGE], SOURCE_NO_TEXT_CHANGE


def make_row(commit_hash: str, text: str, source: str, label: int, feature_version: str) -> dict:
    return {"commit_hash": str(commit_hash), "text": text, "label": int(label),
            "feature_version": str(feature_version), "text_source": source}


def summarize(sources) -> dict:
    """按来源计数，键固定为 SOURCES 顺序，缺失的补 0（报告里不缺行）。"""
    counts = Counter(sources)
    return {name: int(counts.get(name, 0)) for name in SOURCES}


def sources_of(df: pd.DataFrame) -> pd.Series:
    """取每行的 `text_source`；老文件没这一列时一律按 `diff` 记（不静默改变样本集合）。"""
    if "text_source" in df.columns:
        return df["text_source"].astype(str)
    return pd.Series(SOURCE_DIFF, index=df.index, dtype=object)


def stats_of(sources, labels=None) -> tuple[dict, dict | None]:
    """→ (按来源计数, 按来源正样本数)；`labels` 为 None 时第二项为 None，报告写 `—` 不编数。"""
    counts = summarize(sources)
    if labels is None:
        return counts, None
    labels = np.asarray(labels).astype(int)
    sources = np.asarray([str(s) for s in sources])
    return counts, {name: int(((sources == name) & (labels == 1)).sum()) for name in SOURCES}


def as_str_array(values) -> np.ndarray:
    """定宽 Unicode 数组，而不是 object 数组。

    ``np.savez`` 把 object 数组存成 pickle，而 semantic 与 fused 两个 loader 都用
    ``allow_pickle=False`` 读 —— 存成 object 就等于让缓存对消费方不可读。
    """
    arr = np.asarray([str(v) for v in values], dtype=object)
    if arr.size == 0:
        return np.empty(0, dtype="U1")
    return arr.astype(f"U{max(1, max(len(s) for s in arr))}")


NPZ_KEY = "text_source"


def load_sources(npz_path) -> list[str] | None:
    """从编码缓存读 `text_source`；旧缓存没有该键时返回 None，调用方必须如实写「未登记」。"""
    path = Path(npz_path)
    if not path.is_file():
        return None
    with np.load(path, allow_pickle=False) as z:
        if NPZ_KEY not in z:
            return None
        return [str(v) for v in z[NPZ_KEY]]


def load_sources_with_hashes(npz_path) -> tuple[list[str], list[str]] | None:
    """同上，但连 `commit_hash` 一起返回，便于按哈希对齐到切分文件。

    两个键长度不一致时返回 None（缓存被写坏了，宁可报「未登记」也不静默错位对齐）。
    """
    path = Path(npz_path)
    if not path.is_file():
        return None
    with np.load(path, allow_pickle=False) as z:
        if NPZ_KEY not in z or "commit_hash" not in z:
            return None
        hashes = [str(h) for h in z["commit_hash"]]
        sources = [str(v) for v in z[NPZ_KEY]]
    if len(hashes) != len(sources):
        return None
    return hashes, sources


def robustness(probas: dict, y, keep, metric_fn, keys=("auc", "f1")) -> dict:
    """剔除占位行后重算指标，返回各指标跨模型的最大绝对变化。

    **模型不重训** —— 这是对检验集口径的敏感性检查，不是「重训后指标不变」。
    `metric_fn(y, proba) -> dict`，与各线 `metrics.effort_unaware` 同签名，
    所以三条线共用这一份实现，不各写一遍。
    """
    keep = np.asarray(keep, dtype=bool)
    dropped = int((~keep).sum())
    if not dropped or not probas:
        return {}
    worst: dict[str, float] = {}
    y = np.asarray(y)
    for proba in probas.values():
        proba = np.asarray(proba)
        base = metric_fn(y, proba)
        sub = metric_fn(y[keep], proba[keep])
        for key in keys:
            if key in base and key in sub:
                delta = abs(float(sub[key]) - float(base[key]))
                label = key.upper()
                worst[label] = max(worst.get(label, 0.0), delta)
    return worst


def registration(counts: dict, positives: dict | None, n_total: int, test_sources,
                 y_test, probas: dict, metric_fn, retrained: bool = False) -> dict:
    """组装报告登记段需要的全部数字（三条线共用这一份，不各写一遍）。

    `metric_fn(y, proba) -> dict` 即各线的 `metrics.effort_unaware`；`retrained` 只有
    真的按剔除后样本重训过才能传 True，否则稳健性附注会写明「模型未重训」。
    """
    test_sources = [str(s) for s in test_sources]
    keep = [s == SOURCE_DIFF for s in test_sources]
    return {"counts": counts, "positives": positives, "n_total": n_total,
            "test_counts": stats_of(test_sources)[0],
            "kept": int(sum(keep)), "dropped": int(len(keep) - sum(keep)),
            "deltas": robustness(probas, y_test, keep, metric_fn),
            "retrained": retrained}


def registration_from_cache(npz_path, test_hashes, y_test, probas: dict, metric_fn) -> dict | None:
    """从编码缓存（semantic 产出、fused 消费）取来源并登记；旧缓存无该键 → None。

    检验侧哈希在缓存里查不到时按 `diff` 计入（保守：不让敏感性检查静默少算行）；
    全量登记段仍以缓存实有行为准，两处口径在报告里各自成表，不互相顶替。
    """
    loaded = load_sources_with_hashes(npz_path)
    if loaded is None:
        return None
    hashes, sources = loaded
    labels = None
    with np.load(npz_path, allow_pickle=False) as z:
        if "labels" in z and z["labels"].size == len(sources):
            labels = z["labels"]
    counts, positives = stats_of(sources, labels)
    src_by_hash = dict(zip(hashes, sources))
    test_sources = [src_by_hash.get(h, SOURCE_DIFF) for h in test_hashes]
    return registration(counts, positives, len(hashes), test_sources, y_test, probas, metric_fn)


def registration_from_frame(df: pd.DataFrame, test_hashes, y_test, probas: dict,
                            metric_fn) -> dict | None:
    """从文本数据集（e2e 直接吃 CSV）取来源并登记；没有 `text_source` 列 → None。

    检验侧哈希在 CSV 里查不到时按 `diff` 计入，口径同 `registration_from_cache`。
    """
    if "text_source" not in df.columns or "commit_hash" not in df.columns:
        return None
    sources = sources_of(df)
    labels = df["label"].to_numpy() if "label" in df.columns else None
    counts, positives = stats_of(sources, labels)
    src_by_hash = dict(zip(df["commit_hash"].astype(str), sources.astype(str)))
    test_sources = [src_by_hash.get(str(h), SOURCE_DIFF) for h in test_hashes]
    return registration(counts, positives, len(df), test_sources, y_test, probas, metric_fn)


def registration_lines(stats: dict, n_total: int, positives_by_source: dict | None = None) -> list[str]:
    """报告里的「文本来源与覆盖率」登记段（markdown 行）。

    只登记实测数字：条数、占全量比例、其中正样本数、正样本占该来源比例。
    `positives_by_source` 缺省时正样本两列写 `—`，不编数。
    """
    lines = ["## 文本来源与覆盖率\n",
             "| 来源 | 条数 | 占全量 | 其中正样本 | 正样本占该来源 |\n",
             "|---|---|---|---|---|\n"]
    for name in SOURCES:
        count = stats.get(name, 0)
        share = f"{100.0 * count / n_total:.2f}%" if n_total else "—"
        if positives_by_source is None:
            pos_text, pos_share = "—", "—"
        else:
            pos = positives_by_source.get(name, 0)
            pos_text = str(pos)
            pos_share = f"{100.0 * pos / count:.2f}%" if count else "—"
        lines.append(f"| `{name}` | {count} | {share} | {pos_text} | {pos_share} |\n")

    if positives_by_source is None or not n_total:
        total_pos, total_pos_share = "—", "—"
    else:
        positives = sum(positives_by_source.values())
        total_pos = str(positives)
        total_pos_share = f"{100.0 * positives / n_total:.2f}%"
    lines.append(f"| **合计** | {n_total} | 100.00% | {total_pos} | {total_pos_share} |\n")

    placeholder = sum(stats.get(name, 0) for name in (SOURCE_NO_TEXT_CHANGE, SOURCE_ROOT_COMMIT))
    share = f"{100.0 * placeholder / n_total:.2f}%" if n_total else "—"
    lines.append(f"\n> 占位（`no_text_change` + `root_commit`）合计 {placeholder} 条 = {share}"
                 f"（全量 {n_total} 条）。占位串只是「该提交没有可取的文本变更」这一事实的"
                 "显式登记，不是伪造的 diff；`text_source` 列不进特征、不进模型输入，"
                 "只用于本段登记与下面的稳健性附注。\n")
    return lines


def robustness_lines(kept: int, dropped: int, deltas: dict | None, retrained: bool) -> list[str]:
    """稳健性附注：剔除非 `diff` 来源的检验行后指标怎么变。

    `deltas` 形如 `{"AUC": 0.0012, "F1": 0.0034}`（各模型绝对变化的最大值）。
    `retrained=False` 时必须写明「模型未重训，这是对检验集口径的敏感性检查」，
    不能让人读成「重训后指标不变」。
    """
    lines = ["### 稳健性附注（剔除占位样本）\n"]
    scope = "已按剔除后样本重训" if retrained else "**模型未重训**，仅把占位行从检验集中剔除后重算指标（敏感性检查）"
    lines.append(f"- 检验集保留 {kept} 条、剔除 {dropped} 条（`text_source != diff`）；{scope}。\n")
    if deltas:
        items = "、".join(f"{k} 最大绝对变化 {v:.4f}" for k, v in sorted(deltas.items()))
        lines.append(f"- {items}。\n")
    else:
        lines.append("- 未重算指标（本线口径见上），不以「影响可忽略」代替实测。\n")
    return lines
