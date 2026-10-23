"""fused 语义覆盖率：内连接保留比例 + 写入 Markdown 报告。

背景（#86 复审）：`fused/train.py` 把覆盖率算好后经 `report.render(coverage=...)`
写进「数据与参数」，此前只有控制台警告，报告里查不到。这里用合成数据覆盖
100% 与 99.5% 两种输入，断言保留行数与报告中的训练/检验数值。

不需要真实模型、不需要 GPU、也不需要 matplotlib（绘图依赖已延迟到 `make_charts`），
只依赖 numpy / pandas / pytest。
"""

from __future__ import annotations

import sys
from pathlib import Path
from types import SimpleNamespace

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from pipelines.fused import data as fused_data
from pipelines.fused import report as fused_report

N = 200
DIM_KAMEI = 14


def _make_case(covered: int):
    """构造 covered/N 条带语义向量的合成切分。"""
    hashes = [f"h{i:03d}" for i in range(N)]
    df = pd.DataFrame({
        "commit_hash": hashes,
        "is_bug_inducing": [0, 1] * (N // 2),
    })
    X = np.random.RandomState(0).rand(N, DIM_KAMEI).astype(np.float32)
    emb = np.random.RandomState(1).rand(covered, 768).astype(np.float32)
    index = {h: i for i, h in enumerate(hashes[:covered])}
    return df, X, index, emb


def _coverage(kept: int) -> dict[str, float]:
    """与 fused/train.py 相同的口径：内连接后保留条数 / 原始条数。"""
    return {"train": 100.0 * kept / N, "test": 100.0 * kept / N}


def _fake_results() -> dict:
    """render() 需要的最小结果结构（只用于拼 Markdown，不训练）。"""
    eff = {
        "model": {"area": 0.1, "p_norm": 0.2, "recall@20": 0.3, "recall@50": 0.4},
        "density": {"area": 0.1, "p_norm": 0.2, "recall@20": 0.3, "recall@50": 0.4},
        "optimal": {"area": 0.5, "p_norm": 0.6, "recall@20": 0.7, "recall@50": 0.8},
        "random": {"repeats": 200, "area": 0.05, "area_std": 0.01, "p_norm": 0.1},
    }
    return {"lr": {"model_name": "lr_fused_v1", "label": "逻辑回归", "auc": 0.5,
                   "f1": 0.5, "precision": 0.5, "recall": 0.5, "accuracy": 0.5,
                   "effort": {"LOC（改动行数 la+ld）": eff}}}


def _render(coverage: dict[str, float], kept: int) -> str:
    y = np.array([0, 1] * (kept // 2)) if kept % 2 == 0 else np.zeros(kept, dtype=int)
    return fused_report.render(SimpleNamespace(seed=42), _fake_results(),
                               kept, kept, y, coverage=coverage)


def test_coverage_100_percent_keeps_all_rows_and_reports_it():
    df, X, index, emb = _make_case(covered=N)

    kept_df, X_fused, _ = fused_data.fuse(df, X, index, emb)
    coverage = _coverage(len(kept_df))

    assert len(kept_df) == N, "语义全覆盖时不应丢行"
    assert X_fused.shape[1] == 782

    text = _render(coverage, len(kept_df))
    assert "| 语义覆盖率 | 训练 100.00% / 检验 100.00%" in text


def test_coverage_99_5_percent_drops_missing_row_and_reports_both_splits():
    df, X, index, emb = _make_case(covered=N - 1)

    kept_df, X_fused, _ = fused_data.fuse(df, X, index, emb)
    coverage = _coverage(len(kept_df))

    assert len(kept_df) == N - 1, "缺 1 条语义向量时应丢 1 行"
    assert X_fused.shape[1] == 782

    text = _render(coverage, len(kept_df))
    assert "| 语义覆盖率 | 训练 99.50% / 检验 99.50%" in text
    assert "低于 100% 需说明缺失原因" in text


def test_report_title_states_trained_classifier_count():
    """标题里的分类器数量必须等于本次实际训练的模型数（曾写死 12，与默认 8 漂移）。"""
    df, X, index, emb = _make_case(covered=N)
    kept_df, _, _ = fused_data.fuse(df, X, index, emb)

    text = _render(_coverage(len(kept_df)), len(kept_df))
    assert "→ %d 分类器" % len(_fake_results()) in text, "标题须与本次训练的模型数一致"
