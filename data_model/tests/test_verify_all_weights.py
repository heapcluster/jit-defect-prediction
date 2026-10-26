"""权重清单脚本的守门测试（`pipelines/verify_all_weights.py`）。

背景是 2026-10-24 的一次真实分叉：同一个 `tabnet_v1.pkl` 在两台机器上类路径不同
（`pipelines.expert.model` vs `__main__`），而 `#98` 写过「本地已验证 8/8 全过」。
因此这里钉住三件事：清单能往返、md5 漂移必被拦、`__main__` 类路径必被判失败。
"""

from __future__ import annotations

import hashlib
import pickle
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from pipelines import verify_all_weights as vw


def _fake_weight(path: Path, payload: dict | None = None) -> Path:
    with path.open("wb") as fh:
        pickle.dump(payload or {"stub": True}, fh)
    return path


def _record(**kwargs) -> vw.WeightRecord:
    base = {
        "file": "x_v1.pkl",
        "md5": "0" * 32,
        "size": 1,
        "module": "sklearn.linear_model._base.LinearRegression",
        "n_features": 14,
        "loaded": True,
        "error": "",
    }
    base.update(kwargs)
    return vw.WeightRecord(**base)


def test_md5_of_matches_hashlib(tmp_path):
    target = _fake_weight(tmp_path / "a.pkl")
    assert vw.md5_of(target) == hashlib.md5(target.read_bytes()).hexdigest()


def test_manifest_render_parse_roundtrip(tmp_path):
    records = [_record(file="lr_v1.pkl"), _record(file="xgb_v1.pkl", module="xgboost.core.Booster")]
    text = vw.render_manifest(records, "expert", "2026-10-24T00:00:00Z")
    assert text.startswith("#")
    rows = vw.parse_manifest(text)
    assert rows == vw._rows(records)
    assert len(rows) == 2


def test_manifest_rejects_bad_column_count():
    with pytest.raises(ValueError):
        vw.parse_manifest("md5  size  module\n")


def test_main_module_is_never_importable():
    assert vw.is_importable_module("__main__") is False
    assert vw.is_importable_module("json") is True


def test_verdict_flags_main_module_class_path():
    problems = vw.verdict([_record(module="__main__.TabNetWithEarlyStop")], expect_width=0)
    assert len(problems) == 1
    assert "__main__" in problems[0]


def test_nested_modules_reads_pipeline_steps():
    """tabnet 的顶层对象是 Pipeline，`__main__` 藏在 `steps` 里 —— 必须能取到内层。"""
    inner = type("FakeTabNet", (), {"__module__": "__main__"})()
    pipe = SimpleNamespace(steps=[("tabnet", inner)])
    assert vw.nested_modules(pipe) == ["__main__.FakeTabNet"]
    assert vw.nested_modules(object()) == []


def test_verdict_flags_main_module_inside_pipeline():
    rec = _record(module="sklearn.pipeline.Pipeline", inner=["__main__.TabNetWithEarlyStop"])
    problems = vw.verdict([rec], expect_width=0)
    assert len(problems) == 1
    assert "TabNetWithEarlyStop" in problems[0]


def test_verdict_flags_width_mismatch():
    problems = vw.verdict([_record(n_features=782)], expect_width=14)
    assert len(problems) == 1
    assert "782" in problems[0]


def test_verdict_allows_unknown_width():
    """预测器没有 `n_features_in_` 时不判失败（不能把「测不到」当「错了」）。"""
    assert vw.verdict([_record(n_features=None)], expect_width=14) == []


def test_write_manifest_then_check_passes(tmp_path, capsys):
    _fake_weight(tmp_path / "lr_v1.pkl")
    _fake_weight(tmp_path / "rf_v1.pkl", {"stub": 2})
    args = ["--models-dir", str(tmp_path), "--expect-width", "0"]

    assert vw.main(args + ["--write-manifest"]) == 0
    assert (tmp_path / vw.MANIFEST_NAME).is_file()
    assert vw.main(args + ["--check"]) == 0
    assert "清单一致" in capsys.readouterr().out


def test_check_fails_after_weight_replaced(tmp_path):
    target = _fake_weight(tmp_path / "lr_v1.pkl")
    args = ["--models-dir", str(tmp_path), "--expect-width", "0"]
    assert vw.main(args + ["--write-manifest"]) == 0

    _fake_weight(target, {"stub": "re-exported"})  # 重新导出 → md5 变
    assert vw.main(args + ["--check"]) == 2


def test_check_without_manifest_exits_2(tmp_path):
    _fake_weight(tmp_path / "lr_v1.pkl")
    assert vw.main(["--models-dir", str(tmp_path), "--check"]) == 2


def test_missing_dir_exits_2(tmp_path):
    assert vw.main(["--models-dir", str(tmp_path / "nope")]) == 2


def test_empty_dir_exits_2(tmp_path):
    assert vw.main(["--models-dir", str(tmp_path)]) == 2


def test_no_load_skips_module_column_and_passes(tmp_path, capsys):
    """无 torch 的环境也能算 md5 清单：`--no-load` 不判类路径。"""
    _fake_weight(tmp_path / "lr_v1.pkl")
    assert vw.main(["--models-dir", str(tmp_path), "--no-load"]) == 0
    assert "已跳过回读" in capsys.readouterr().out
