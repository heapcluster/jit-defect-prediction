"""文本来源口径（`pipelines/text_source.py`）与两个构建器的回归测试。

钉住的四件事：
1. 三类来源的判定边界（有父+空 diff / 根提交 / 仓库里取不到），取不到**不许**落占位串；
2. 占位串是非空字符串 —— 空串会被 `pandas.read_csv` 读成 NaN，再被 `dropna` 丢掉，
   覆盖率就静默缺回去（这正是本口径要修的原缺陷）；
3. `text_source` 只作登记，列顺序固定，且不进模型输入；
4. 旧编码缓存没有 `text_source` 键时读方拿到 None（报告写「未登记」），不按 `diff` 冒充。
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest
from git.exc import BadName

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from data_model.pipelines import text_source
from data_model.pipelines.e2e.build_text_dataset import commit_text
from data_model.pipelines.semantic.data import load_embeddings, save_embeddings

HASH = "a" * 40


class _FakeDiff:
    def __init__(self, path: str, patch: bytes | None):
        self.a_path = path
        self.b_path = path
        self.diff = patch


class _FakeCommit:
    def __init__(self, n_parents: int, diffs):
        self.parents = [object()] * n_parents
        self._diffs = diffs

    def diff(self, parent, create_patch=True, R=True):
        return self._diffs


class _FakeRepo:
    """只实现 commit_text 用到的那一点接口；哈希不在表里就抛 BadName。"""

    def __init__(self, mapping):
        self.mapping = mapping

    def commit(self, commit_hash):
        if commit_hash not in self.mapping:
            raise BadName(commit_hash)
        return self.mapping[commit_hash]


def _repo():
    return _FakeRepo(
        {
            "diff": _FakeCommit(1, [_FakeDiff("src/A.java", b"+int a = 1;\n")]),
            "empty": _FakeCommit(1, []),
            "blank": _FakeCommit(1, [_FakeDiff("src/B.java", b"   \n")]),
            "root": _FakeCommit(0, []),
        }
    )


# ────────────────────── 1. 三类来源的判定边界 ──────────────────────


def test_real_diff_keeps_text_and_source():
    text, source = commit_text(_repo(), "diff", 4000)
    assert source == text_source.SOURCE_DIFF
    assert text.startswith("diff --git a/src/A.java b/src/A.java\n")
    assert "+int a = 1;" in text


def test_parent_but_empty_diff_becomes_no_text_change():
    text, source = commit_text(_repo(), "empty", 4000)
    assert source == text_source.SOURCE_NO_TEXT_CHANGE
    assert text == text_source.PLACEHOLDER[text_source.SOURCE_NO_TEXT_CHANGE]


def test_whitespace_body_stays_diff_per_ruling():
    """空白正文的 diff 仍记 `diff`：装配结果非空，与补丁前旧管线逐哈希一致（裁定第 ③ 条）。"""
    text, source = commit_text(_repo(), "blank", 4000)
    assert source == text_source.SOURCE_DIFF
    assert text.startswith("diff --git a/src/B.java")


def test_root_commit_is_its_own_source():
    text, source = commit_text(_repo(), "root", 4000)
    assert source == text_source.SOURCE_ROOT_COMMIT
    assert text == text_source.PLACEHOLDER[text_source.SOURCE_ROOT_COMMIT]
    # 根提交不能和属性类提交混成一个来源（蒋励 2026-10-24 裁定第 1 条）
    assert text != text_source.PLACEHOLDER[text_source.SOURCE_NO_TEXT_CHANGE]


def test_unreachable_commit_returns_none_not_placeholder():
    # 取不到 = 切分与克隆版本可能不一致，是真缺陷；占位串会把它伪装成「无文本变更」
    assert commit_text(_repo(), "f" * 40, 4000) is None


# ────────────────────── 2. 截断口径未被本补丁改动 ──────────────────────


def test_assemble_truncates_per_file_and_total():
    long_patch = b"x" * 5000
    diffs = [_FakeDiff(f"f{i}.java", long_patch) for i in range(5)]
    text = text_source.assemble(diffs, max_chars=4000)
    assert len(text) == 4000
    assert "... [truncated]" in text
    assert text_source.assemble([], 4000) == ""


def test_header_only_diff_stays_diff_per_ruling():
    """只有文件头、没有 patch 正文（模式/属性类变更）仍记 `diff`（蒋励 2026-10-24 裁定口径）。

    占位只认「diff 为空」（零条目 → 装配结果为空串）。若把「仅文件头」也算无内容，
    实测会把 82 条旧 `diff` 行改判占位，破坏裁定第 ③ 条「原 83,674 行逐哈希不变」。
    """
    text = text_source.assemble([_FakeDiff("src/C.java", None)], 4000)
    assert text.startswith("diff --git a/src/C.java")
    assert text_source.classify(True, text)[1] == text_source.SOURCE_DIFF
    assert text_source.classify(True, "")[1] == text_source.SOURCE_NO_TEXT_CHANGE
    assert text_source.classify(False, "")[1] == text_source.SOURCE_ROOT_COMMIT


# ────────────────────── 3. 占位串不会被 pandas 读成 NaN ──────────────────────


def test_placeholder_survives_csv_roundtrip(tmp_path):
    rows = [
        text_source.make_row(
            HASH,
            text_source.PLACEHOLDER[text_source.SOURCE_NO_TEXT_CHANGE],
            text_source.SOURCE_NO_TEXT_CHANGE,
            0,
            "v1",
        )
    ]
    path = tmp_path / "commit_text.csv"
    pd.DataFrame(rows, columns=text_source.TEXT_COLUMNS).to_csv(path, index=False, quoting=1)
    back = pd.read_csv(path)
    assert list(back.columns) == text_source.TEXT_COLUMNS
    assert back["text"].notna().all(), "占位串被读成 NaN 就会在 dropna 后静默丢行"
    assert back["text"].iloc[0] == text_source.PLACEHOLDER[text_source.SOURCE_NO_TEXT_CHANGE]
    # 空串对照：同样写法下会被读成 NaN —— 这就是为什么占位串必须非空
    empty = tmp_path / "empty.csv"
    pd.DataFrame(
        [{"commit_hash": HASH, "text": ""}],
    ).to_csv(empty, index=False, quoting=1)
    assert pd.read_csv(empty)["text"].isna().all()


def test_text_source_is_not_a_model_input_column():
    # text_source 只做登记：不在特征列里，也不参与 TextDataset 的输入构造
    assert "text_source" not in ("commit_hash", "text", "label", "feature_version")
    assert text_source.TEXT_COLUMNS[-1] == "text_source"
    assert text_source.SOURCES == (
        text_source.SOURCE_DIFF,
        text_source.SOURCE_NO_TEXT_CHANGE,
        text_source.SOURCE_ROOT_COMMIT,
    )


def test_sources_of_falls_back_to_diff_for_old_files():
    old = pd.DataFrame({"commit_hash": [HASH], "text": ["diff --git a/a b/a"]})
    assert list(text_source.sources_of(old)) == [text_source.SOURCE_DIFF]
    new = old.assign(text_source=[text_source.SOURCE_ROOT_COMMIT])
    assert list(text_source.sources_of(new)) == [text_source.SOURCE_ROOT_COMMIT]


# ────────────────────── 4. 登记与稳健性附注 ──────────────────────


def test_stats_and_registration_numbers():
    sources = (
        [text_source.SOURCE_DIFF] * 10
        + [text_source.SOURCE_NO_TEXT_CHANGE] * 3
        + [text_source.SOURCE_ROOT_COMMIT] * 2
    )
    labels = np.array([1, 0, 0, 0, 0, 0, 0, 0, 0, 0] + [0] * 3 + [1, 0])
    counts, positives = text_source.stats_of(sources, labels)
    assert counts == {"diff": 10, "no_text_change": 3, "root_commit": 2}
    assert positives == {"diff": 1, "no_text_change": 0, "root_commit": 1}

    y = np.array([1, 0, 0, 0, 0])
    probas = {"m": np.array([0.9, 0.4, 0.3, 0.2, 0.1])}

    def metric_fn(yy, pp):  # 与 effort_unaware 同签名的假指标
        return {"auc": float(np.mean(pp)), "f1": float(np.max(pp))}

    keep = [True, True, True, False, False]  # 后两条是占位行
    reg = text_source.registration(
        counts,
        positives,
        15,
        [text_source.SOURCE_DIFF] * 3 + ["no_text_change"] * 2,
        y,
        probas,
        metric_fn,
    )
    assert reg["kept"] == 3 and reg["dropped"] == 2 and reg["retrained"] is False
    base, sub = metric_fn(y, probas["m"]), metric_fn(y[keep], probas["m"][keep])
    assert reg["deltas"]["AUC"] == pytest.approx(abs(sub["auc"] - base["auc"]))


def test_registration_lines_state_that_models_were_not_retrained():
    lines = text_source.robustness_lines(
        kept=25123, dropped=60, deltas={"AUC": 0.0012, "F1": 0.0034}, retrained=False
    )
    joined = "".join(lines)
    assert "模型未重训" in joined and "敏感性检查" in joined
    assert "0.0012" in joined and "0.0034" in joined
    # 不写「影响可忽略」这类没有实测支撑的结论
    assert "可忽略" not in joined


def test_registration_lines_do_not_invent_positives():
    lines = "".join(text_source.registration_lines({"diff": 5}, 5, None))
    assert "| `diff` | 5 | 100.00% | — | — |" in lines


# ────────────────────── 5. 编码缓存携带 text_source，旧缓存返回 None ──────────────────────


def test_embedding_cache_roundtrips_text_source(tmp_path):
    df = pd.DataFrame(
        {
            "commit_hash": [HASH, "b" * 40],
            "label": [1, 0],
            "feature_version": ["v1", "v1"],
            "text_source": [text_source.SOURCE_DIFF, text_source.SOURCE_ROOT_COMMIT],
        }
    )
    path = tmp_path / "semantic_embeddings.npz"
    save_embeddings(path, df, np.zeros((2, 768), dtype=np.float32))

    hashes, sources = text_source.load_sources_with_hashes(path)
    assert hashes == [HASH, "b" * 40]
    assert sources == [text_source.SOURCE_DIFF, text_source.SOURCE_ROOT_COMMIT]
    # 缓存仍必须能被 allow_pickle=False 读回（既有契约，别被新键破坏）
    assert load_embeddings(path)[0] == hashes


def test_old_cache_without_key_reports_unregistered(tmp_path):
    path = tmp_path / "old.npz"
    np.savez_compressed(
        path,
        commit_hash=text_source.as_str_array([HASH]),
        embeddings=np.zeros((1, 768), dtype=np.float32),
        labels=np.array([1]),
        feature_version=text_source.as_str_array(["v1"]),
    )
    assert text_source.load_sources(path) is None
    assert text_source.load_sources_with_hashes(path) is None
    assert text_source.load_sources(tmp_path / "missing.npz") is None
