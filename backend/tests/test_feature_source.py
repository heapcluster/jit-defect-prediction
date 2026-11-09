"""`app/feature_source.py` 的抽取器不可用分支（Sprint 2 报告 §6 第 7 项）。

`_extractor()` 是 #97「新提交现算 14 维特征」的入口：抽取脚本缺失或不可加载时必须
明确抛 `RuntimeError`，而不是把 `None` 当模块继续用 —— 后者会变成请求期的
`AttributeError`，被兜底处理器吞成一句没有解释的 50000。
"""

from __future__ import annotations

import importlib.util

import pytest
from app import config, feature_source


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


def test_extract_raises_when_source_repo_missing(monkeypatch):
    """SOURCE_REPO 未配置 → RuntimeError，而不是把 None 当路径继续用。"""
    monkeypatch.setattr(config, "SOURCE_REPO", None)
    with pytest.raises(RuntimeError, match="source repository unavailable"):
        feature_source.extract("a" * 40)


def test_extract_rejects_unreachable_commit_before_scan(tmp_path, monkeypatch):
    """不可达提交在调用抽取器之前就被拒，避免先扫全量历史再判「HEAD 可达」。"""
    repo = tmp_path / "repo"
    (repo / ".git").mkdir(parents=True)
    monkeypatch.setattr(config, "SOURCE_REPO", repo)
    monkeypatch.setattr(feature_source, "is_ancestor", lambda _repo, _commit: False)

    def _stub_extractor():
        raise AssertionError("不可达提交不得触发特征抽取")

    _stub_extractor.cache_clear = lambda: None  # 兼容 autouse 夹具的 lru_cache 清理
    monkeypatch.setattr(feature_source, "_extractor", _stub_extractor)

    with pytest.raises(ValueError, match="HEAD 可达"):
        feature_source.extract("a" * 40)


def test_extract_calls_extractor_with_source_and_hash(tmp_path, monkeypatch):
    repo = tmp_path / "repo"
    (repo / ".git").mkdir(parents=True)
    monkeypatch.setattr(config, "SOURCE_REPO", repo)
    monkeypatch.setattr(feature_source, "is_ancestor", lambda _repo, _commit: True)

    calls = []

    def _stub_extractor():
        def _inner(repo_dir, commit_hash):
            calls.append((repo_dir, commit_hash))
            return {"ok": True}

        return _inner

    _stub_extractor.cache_clear = lambda: None  # 兼容 autouse 夹具的 lru_cache 清理
    monkeypatch.setattr(feature_source, "_extractor", _stub_extractor)

    assert feature_source.extract("a" * 40) == {"ok": True}
    assert calls == [(repo, "a" * 40)]


def test_extractor_uses_custom_script_when_configured(tmp_path, monkeypatch):
    """插件化：FEATURE_EXTRACTOR_SCRIPT 覆盖默认抽取器，零核心改动。"""
    script = tmp_path / "custom_extractor.py"
    script.write_text(
        "def extract_single_commit(repo_dir, commit_hash):\n"
        "    return {'commit_hash': commit_hash}\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(config, "FEATURE_EXTRACTOR_SCRIPT", str(script))
    feature_source._extractor.cache_clear()
    fn = feature_source._extractor()
    assert fn(None, "a" * 40) == {"commit_hash": "a" * 40}
