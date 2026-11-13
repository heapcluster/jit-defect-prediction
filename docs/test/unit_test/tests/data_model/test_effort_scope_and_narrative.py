"""评审意见 #2 / #4 的回归测试。

#2 预算感知的评审下限必须按口径走：LOC 口径是"行"，nf 口径是"文件"；
   早期实现把 `MIN_REVIEW_LOC=10` 同时套在两个口径上（"至少 10 个文件"）。
#4 报告的结论段必须由本轮结果算出来：`--models` 支持子集、P_norm 也可能非负，
   硬编码"全为负 / 最低出自 svm / 两万多条"在子集与非负结果下会说谎。
"""

from __future__ import annotations

import sys
from pathlib import Path
from types import SimpleNamespace

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from pipelines.expert import config, report
from pipelines.expert.metrics import budget_order, effort_aware_metrics

LOC = "LOC（改动行数 la+ld）"
NF = "改动文件数 nf"


def test_metrics_skip_budget_when_no_floor():
    proba = np.array([0.9, 0.8, 0.2])
    y = np.array([1, 0, 0])
    effort = np.array([5.0, 100.0, 20.0])
    out = effort_aware_metrics(proba, y, effort, review_floor=None)
    assert "budget" not in out
    assert {"model", "density", "optimal", "random"} <= set(out)


def test_floor_unit_follows_effort_unit():
    """同一个 floor=10：LOC 口径只挡掉 <10 行的提交，nf 口径是按文件数挡。"""
    proba = np.array([0.9, 0.95, 0.1])
    loc = np.array([4.0, 12.0, 30.0])
    files = np.array([1.0, 5.0, 3.0])

    loc_order = budget_order(proba, loc, config.MIN_REVIEW_LOC)
    assert loc_order[-1] == 0, "4 行的提交应被排到队尾"

    nf_order = budget_order(proba, files, config.MIN_REVIEW_FILES)
    assert nf_order[-1] == 0, "1 个文件的提交应被排到队尾"
    # 若误用 10 个文件做阈值，所有提交都会被判为"太小"，顺序退化成按分数
    wrong = budget_order(proba, files, 10)
    assert wrong.tolist() == [1, 0, 2]


def _effort_block(p_norm: float, n20: int, recall20: float) -> dict:
    row = {
        "area": 0.3,
        "p_norm": p_norm,
        "popt": p_norm,
        "recall@20": recall20,
        "recall@50": recall20,
        "ce20": recall20,
        "n_commits@20": n20,
    }
    return {
        "model": dict(row),
        "density": dict(row),
        "optimal": dict(row),
        "random": {
            "area": 0.2,
            "area_std": 0.01,
            "p_norm": 0.0,
            "repeats": 200,
            "recall@20": 0.2,
            "recall@50": float("nan"),
        },
        "confound": {"spearman_risk_log_effort": 0.85, "median_effort": 8.0},
    }


def _results(p_norm_by_model: dict, with_budget: bool = True) -> dict:
    out = {}
    for name, pn in p_norm_by_model.items():
        block = _effort_block(pn, 100, 0.2)
        if with_budget:
            block["budget"] = dict(block["model"])
        out[name] = {
            "model_name": f"{name}_v1",
            "label": name,
            "auc": 0.8,
            "f1": 0.4,
            "precision": 0.4,
            "recall": 0.4,
            "accuracy": 0.8,
            "effort": {LOC: block},
        }
    return out


def _args() -> SimpleNamespace:
    return SimpleNamespace(
        train=Path("split_szz_train.csv"),
        test=Path("split_szz_test.csv"),
        seed=42,
        from_saved=False,
    )


def _frame(n: int) -> pd.DataFrame:
    return pd.DataFrame(
        {
            config.LABEL_COL: [0] * (n - 1) + [1],
            "committed_at": pd.date_range("2024-01-01", periods=n, freq="D").astype(str),
        }
    )


def test_narrative_does_not_claim_all_negative_when_results_are_positive():
    text = report.render(_args(), _frame(10), _frame(10), _results({"lr": 0.12, "xgb": 0.30}))
    assert "全为负" not in text
    assert "svm" not in text, "结论里的模型名必须来自结果，不能写死"
    assert "2/2" in text or "0/2" in text


def test_narrative_scales_to_model_subset():
    text = report.render(
        _args(), _frame(10), _frame(10), _results({"lr": -0.2, "rf": -0.3, "xgb": -0.1})
    )
    assert "3/3" in text
    assert "全为负" in text


def test_report_without_budget_column_still_renders():
    text = report.render(_args(), _frame(10), _frame(10), _results({"lr": -0.2}, with_budget=False))
    assert "预算感知" not in text.split("## 三")[0] or "未启用" in text
    assert True  # 表头存在与否不作断言，只要不抛异常
