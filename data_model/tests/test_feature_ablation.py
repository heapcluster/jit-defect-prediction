"""消融脚本（`15_feature_ablation.py`）的守门测试。

钉住四件事：
1. 留一法的符号约定 —— 删掉有用特征后 AUC **下降**，`delta_auc` 为负；
2. 置换重要性对强预测列给出**正的**下降量（打乱就打不准）；
3. 两口径的名次排序与「分歧」判定是纯函数、可复算；
4. 报告必须把负贡献与分歧如实写出，不允许只挑顺眼的一口径。

脚本名以数字开头，不能按模块名 import，故用 `importlib` 按路径装载。
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import numpy as np

DATA_MODEL_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(DATA_MODEL_DIR))

from pipelines.expert import config


def _load_module():
    path = DATA_MODEL_DIR / "15_feature_ablation.py"
    spec = importlib.util.spec_from_file_location("feature_ablation_mod", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


ab = _load_module()


def _toy(n=400, seed=0, informative=(0, 1, 2)):
    """三列强信号 + 其余噪声；标签由信号列决定，保证 LOO 有可测的下降。"""
    rng = np.random.default_rng(seed)
    X = rng.normal(size=(n, 14))
    signal = X[:, list(informative)].sum(axis=1)
    y = (signal > 0).astype(int)
    return X, y


def test_fit_eval_returns_bounded_metrics():
    X, y = _toy()
    m = ab._fit_eval("lr", 42, X[:300], y[:300], X[300:], y[300:])
    assert 0.0 <= m["auc"] <= 1.0
    assert 0.0 <= m["f1"] <= 1.0


def test_leave_one_out_covers_all_features():
    X, y = _toy()
    base, rows = ab.leave_one_out(
        "lr", 42, X[:300], y[:300], X[300:], y[300:], config.FEATURE_FIELDS
    )
    assert len(rows) == len(config.FEATURE_FIELDS)
    assert {r["feature"] for r in rows} == set(config.FEATURE_FIELDS)
    assert 0.0 <= base["auc"] <= 1.0


def test_leave_one_out_dropping_signal_hurts_auc():
    """删掉信号列 → AUC 下降（delta 为负）。这是留一法唯一的语义约定。"""
    X, y = _toy()
    _, rows = ab.leave_one_out("lr", 42, X[:300], y[:300], X[300:], y[300:], config.FEATURE_FIELDS)
    by = {r["feature"]: r for r in rows}
    for name in ("ns", "nd", "nf"):  # 前 3 列被构造成信号列
        assert by[name]["delta_auc"] < 0, f"{name} 删掉后 AUC 未下降，符号约定被破坏"


def test_leave_one_out_noise_feature_does_not_crash():
    X, y = _toy()
    _, rows = ab.leave_one_out("lr", 42, X[:300], y[:300], X[300:], y[300:], config.FEATURE_FIELDS)
    noise = [r for r in rows if r["feature"] in ("sexp", "nuc", "age")]
    assert len(noise) == 3
    assert all(np.isfinite(r["delta_auc"]) for r in noise)


def test_permutation_importance_positive_for_signal():
    X, y = _toy()
    model = ab.build_model("lr", 42)
    model.fit(X[:300], y[:300])
    base_auc, rows = ab.permutation_importance(model, X[300:], y[300:], config.FEATURE_FIELDS, 3, 0)
    by = {r["feature"]: r for r in rows}
    assert by["ns"]["drop_mean"] > 0, "打乱信号列后 AUC 未下降"
    assert base_auc > 0.5


def test_permutation_importance_std_nonnegative():
    X, y = _toy()
    model = ab.build_model("lr", 42)
    model.fit(X[:300], y[:300])
    _, rows = ab.permutation_importance(model, X[300:], y[300:], config.FEATURE_FIELDS, 3, 0)
    assert all(r["drop_std"] >= 0 for r in rows)


def test_rank_orders_by_key_desc():
    rows = [{"feature": "a", "v": 0.1}, {"feature": "b", "v": 0.3}, {"feature": "c", "v": 0.2}]
    assert ab._rank(rows, "v") == {"b": 1, "c": 2, "a": 3}
    assert ab._rank(rows, "v", reverse=False) == {"a": 1, "c": 2, "b": 3}


def _synthetic(base_auc=0.80):
    loo = [
        {"feature": f, "auc_without": base_auc, "delta_auc": -0.01, "delta_f1": -0.01}
        for f in config.FEATURE_FIELDS
    ]
    perm = [{"feature": f, "drop_mean": 0.01, "drop_std": 0.002} for f in config.FEATURE_FIELDS]
    return {"auc": base_auc, "f1": 0.4}, loo, perm


def test_render_report_has_required_sections():
    base, loo, perm = _synthetic()
    text = ab.render_report(base, loo, perm, 0.80, "xgb", 42, 1.0, 0)
    for token in (
        "# Kamei 14 项特征消融",
        "## 1. 基线",
        "## 2. 两口径交叉排序",
        "## 3. 结论",
        "## 4. 口径与边界",
        "## 5. 复现",
    ):
        assert token in text
    assert text.count("| `") == len(config.FEATURE_FIELDS), "交叉表应恰好 14 行"


def test_render_report_flags_negative_contribution():
    base, loo, perm = _synthetic()
    loo[0]["delta_auc"] = +0.004  # 删掉反而更好
    text = ab.render_report(base, loo, perm, 0.80, "xgb", 42, 1.0, 0)
    assert "负贡献" in text
    assert config.FEATURE_FIELDS[0] in text


def test_render_report_reports_metric_disagreement():
    base, loo, perm = _synthetic()
    # 让第 1 列在留一法里最重要、在置换里最不重要，名次差 ≥6
    loo[0]["delta_auc"] = -0.5
    perm[0]["drop_mean"] = -0.5
    text = ab.render_report(base, loo, perm, 0.80, "xgb", 42, 1.0, 0)
    assert "两口径分歧" in text


def test_render_report_marks_smoke_mode():
    base, loo, perm = _synthetic()
    text = ab.render_report(base, loo, perm, 0.80, "lr", 42, 1.0, limit=2000)
    assert "冒烟模式" in text
