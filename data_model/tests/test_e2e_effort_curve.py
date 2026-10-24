"""e2e 线 effort 曲线：`cumulative_curve` 必须存在且与 fused 线同口径。

背景（#88 复审）：`e2e/report.py` 从 `.metrics` 导入 `cumulative_curve`，但
`e2e/metrics.py` 里没有该函数 —— `python -m pipelines.e2e.train` 一启动就
ImportError，且发生在模型训练之前。本用例钉住：函数存在、曲线端点与单调性正确、
与 fused 线逐点一致（两条线的 effort 曲线必须可直接比较）。

不需要 GPU / torch / 真实模型，只依赖 numpy 与 sklearn。
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from pipelines.e2e.metrics import cumulative_curve as e2e_curve
from pipelines.fused.metrics import cumulative_curve as fused_curve

Y = np.array([0, 1, 1, 0, 1, 0, 0, 1], dtype=float)
EFFORT = np.array([3, 1, 2, 5, 4, 1, 1, 2], dtype=float)
PROBA = np.array([0.1, 0.9, 0.8, 0.2, 0.7, 0.3, 0.4, 0.6])


def _orders() -> dict:
    return {
        "model": np.argsort(-PROBA, kind="stable"),
        "density": np.argsort(-(PROBA / EFFORT), kind="stable"),
        "optimal": np.argsort(-(Y / EFFORT), kind="stable"),
        "random": np.random.default_rng(0).permutation(len(Y)),
    }


def test_curve_shape_endpoints_and_monotonic():
    for name, order in _orders().items():
        xs, ys = e2e_curve(order, EFFORT, Y)
        assert len(xs) == len(ys) == len(Y) + 1, name
        assert (xs[0], ys[0]) == (0.0, 0.0), name
        assert xs[-1] == 1.0 and ys[-1] == 1.0, name
        assert np.all(np.diff(xs) >= 0) and np.all(np.diff(ys) >= 0), name


def test_matches_fused_line_pointwise():
    order = _orders()["model"]
    xs_e, ys_e = e2e_curve(order, EFFORT, Y)
    xs_f, ys_f = fused_curve(order, EFFORT, Y)
    assert np.array_equal(xs_e, xs_f)
    assert np.array_equal(ys_e, ys_f)
