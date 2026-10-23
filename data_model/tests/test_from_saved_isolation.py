"""PR #88 复审阻断项 2 的回归测试：``--from-saved`` 的图表不得落进权威 ``reports/figs/``。

重训产出的 ``figs/`` 三张图是权威产物；``--from-saved`` 用旧权重复算，属探索性结果，
报告已隔离到 ``model_metrics_from_saved.md``，图表同理必须隔离到 ``figs_from_saved/``。
"""

from __future__ import annotations

import sys
from pathlib import Path
from types import SimpleNamespace

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from pipelines.expert import config, train as expert_train  # noqa: E402

LOC = "LOC（改动行数 la+ld）"
NF = "改动文件数 nf"


class _FakeModel:
    """替身模型：proba 直接取特征第一列，避免真实训练。"""

    def predict_proba(self, X):
        p = np.clip(X[:, 0], 0.0, 1.0)
        return np.column_stack([1 - p, p])


def test_from_saved_charts_isolated_from_authoritative_figs(tmp_path, monkeypatch):
    captured: dict = {}
    monkeypatch.setattr(
        expert_train.report, "make_charts",
        lambda results, probas, y, effort_loc, out_dir:
            captured.update(out_dir=Path(out_dir)) or [])

    # joblib.load 返回替身模型，隔离测试不依赖真实 .pkl
    monkeypatch.setattr(expert_train.joblib, "load", lambda path: _FakeModel())

    model_dir = tmp_path / "models"
    model_dir.mkdir()
    (model_dir / "lr_v1.pkl").write_bytes(b"fake")

    report_path = tmp_path / "reports" / "model_metrics_from_saved.md"
    authoritative = report_path.parent / "figs"
    authoritative.mkdir(parents=True)
    sentinel = authoritative / "roc_curves.png"
    sentinel.write_bytes(b"authoritative")

    args = SimpleNamespace(
        train=Path("train.csv"), test=Path("test.csv"), seed=42,
        report=report_path, model_dir=model_dir,
        no_charts=False, from_saved=True)

    n = 8
    X_test = np.linspace(0.1, 0.9, n).reshape(-1, 1)
    y_test = np.array([0, 1, 0, 0, 1, 0, 0, 1])
    train_df = pd.DataFrame({config.LABEL_COL: [0, 1],
                             "committed_at": ["2024-01-01", "2024-01-02"]})
    test_df = pd.DataFrame({config.LABEL_COL: [0, 1],
                            "committed_at": ["2024-02-01", "2024-02-02"]})
    effort_sets = {LOC: np.full(n, 20.0), NF: np.full(n, 3.0)}

    rc = expert_train.from_saved(args, train_df, test_df, X_test, y_test,
                                 effort_sets, np.full(n, 20.0), ["lr"])

    assert rc == 0
    # 图表落 figs_from_saved/，权威 figs/ 一个字节都不动
    assert captured["out_dir"] == report_path.parent / "figs_from_saved"
    assert sentinel.read_bytes() == b"authoritative"
    assert report_path.is_file()


def test_retrain_path_keeps_authoritative_figs_dir(tmp_path):
    """正常重训（from_saved=False）仍写 ``figs/``：权威目录只属于重训产物。"""
    args = SimpleNamespace(
        train=Path("train.csv"), test=Path("test.csv"), seed=42,
        report=tmp_path / "reports" / "model_metrics.md", from_saved=False)
    assert expert_train.fig_dir_for(args) == args.report.parent / "figs"
