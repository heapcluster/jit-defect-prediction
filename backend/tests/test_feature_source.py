"""`app/feature_source.py` 的抽取器不可用分支（Sprint 2 报告 §6 第 7 项）。

`_extractor()` 是 #97「新提交现算 14 维特征」的入口：抽取脚本缺失或不可加载时必须
明确抛 `RuntimeError`，而不是把 `None` 当模块继续用 —— 后者会变成请求期的
`AttributeError`，被兜底处理器吞成一句没有解释的 50000。
"""

from __future__ import annotations

import importlib.util

import pytest

from app import feature_source


@pytest.fixture(autouse=True)
def _clear_extractor_cache():
    """`_extractor` 带 `lru_cache`：每条用例前后都清空，避免上一条的结果被下一条继承。"""
    feature_source._extractor.cache_clear()
    yield
    feature_source._extractor.cache_clear()


@pytest.mark.parametrize("broken", ["spec_none", "loader_none"])
def test_extractor_raises_when_script_unimportable(monkeypatch, broken):
    """`spec is None` 与 `spec.loader is None` 两个分支都要抛固定文案的 RuntimeError。"""
    if broken == "spec_none":
        monkeypatch.setattr(importlib.util, "spec_from_file_location", lambda *a, **k: None)
    else:
        monkeypatch.setattr(
            importlib.util,
            "spec_from_file_location",
            lambda *a, **k: importlib.util.spec_from_loader("jit_extract_features", None),
        )

    with pytest.raises(RuntimeError, match="feature extractor unavailable"):
        feature_source._extractor()
