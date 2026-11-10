"""四线在线接入的单测：语义 embedding 查表、按线向量组装、四线目录懒加载。

[AI生成] 本例由 AI 生成，核心断言（维度/落表一致性）经人工复核。
"""

from __future__ import annotations

import numpy as np
import pytest
from app import config, model_registry, semantic_source
from app.errors import AppError
from app.services.predict import _vector_for_line

DIM = 768
HIT = "a" * 40
MISS = "c" * 40


@pytest.fixture()
def tiny_npz(tmp_path, monkeypatch):
    """造一张最小语义 embedding 表（2 条提交 × 768 维）。"""
    path = tmp_path / "emb.npz"
    hashes = np.array([HIT, "b" * 40], dtype="<U40")
    emb = np.zeros((2, DIM), dtype=np.float32)
    emb[0, 0] = 1.0
    emb[1, 0] = 2.0
    np.savez_compressed(path, commit_hash=hashes, embeddings=emb)
    monkeypatch.setattr(config, "SEMANTIC_EMBEDDINGS", path)
    semantic_source._table.cache_clear()
    yield path
    semantic_source._table.cache_clear()


class _Feature:
    def __init__(self) -> None:
        for i, name in enumerate(config.FEATURE_COLUMNS):
            setattr(self, name, float(i))


def test_embedding_lookup_hit_returns_768(tiny_npz):
    vec = semantic_source.embedding_for(HIT)
    assert vec is not None and vec.shape == (DIM,) and vec[0] == 1.0


def test_embedding_lookup_miss_returns_none(tiny_npz):
    assert semantic_source.embedding_for(MISS) is None


def test_embedding_unavailable_returns_none(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "SEMANTIC_EMBEDDINGS", tmp_path / "missing.npz")
    semantic_source._table.cache_clear()
    assert semantic_source.embedding_for(HIT) is None
    semantic_source._table.cache_clear()


def test_vector_expert_is_14():
    assert len(_vector_for_line("expert", HIT, _Feature())) == 14


def test_vector_semantic_is_768(tiny_npz):
    assert len(_vector_for_line("semantic", HIT, _Feature())) == DIM


def test_vector_fused_is_14_plus_768(tiny_npz):
    assert len(_vector_for_line("fused", HIT, _Feature())) == 14 + DIM


def test_vector_semantic_missing_embedding_raises_40001(tiny_npz):
    with pytest.raises(AppError) as exc:
        _vector_for_line("semantic", MISS, _Feature())
    assert exc.value.code == 40001


def test_catalog_scans_semantic_line_and_lazy_loads(tmp_path, monkeypatch):
    """四线清单登记：catalog 认识 semantic 模型名，get_model 才真正读权重。"""
    import joblib
    from sklearn.linear_model import LogisticRegression

    models_dir = tmp_path / "pipelines" / "semantic" / "models"
    models_dir.mkdir(parents=True)
    clf = LogisticRegression(max_iter=50).fit(np.zeros((4, DIM)), [0, 0, 1, 1])
    joblib.dump(clf, models_dir / "lr_semantic_v1.pkl")
    (models_dir / "load_manifest.txt").write_text(
        "[models]\nlr_semantic_v1.pkl\t逻辑回归\n", encoding="utf-8"
    )
    # 保存并恢复全局注册表，避免污染其它用例（pytest 单进程共享模块）
    saved = (dict(model_registry._REGISTRY), dict(model_registry._CATALOG))
    saved_line = dict(model_registry._LINE_OF)
    try:
        monkeypatch.setattr(config, "PIPELINES_DIR", tmp_path / "pipelines")
        model_registry.load_models()
        assert model_registry.has("lr_semantic_v1")
        assert model_registry.line_of("lr_semantic_v1") == "semantic"
        entry = model_registry.get_model("lr_semantic_v1")
        assert entry.line == "semantic" and entry.model is not None
    finally:
        model_registry._REGISTRY.clear()
        model_registry._REGISTRY.update(saved[0])
        model_registry._CATALOG.clear()
        model_registry._CATALOG.update(saved[1])
        model_registry._LINE_OF.clear()
        model_registry._LINE_OF.update(saved_line)


def test_e2e_text_lookup_and_missing(tmp_path, monkeypatch):
    """e2e 读提交文本：命中返回文本，未命中 predict 返回 None（不编造）。"""
    from app import e2e_source

    data = tmp_path / "e2e" / "data"
    data.mkdir(parents=True)
    (data / "commit_text.csv").write_text(
        "commit_hash,text,label,feature_version,text_source\n"
        f"{HIT},diff --git a/x b/x +1,0,v1,diff\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(config, "PIPELINES_DIR", tmp_path)
    e2e_source._texts.cache_clear()
    e2e_source._runtime.cache_clear()
    try:
        assert e2e_source._texts()[HIT] == "diff --git a/x b/x +1"
        # 文本未命中 → None（不进入模型）
        assert e2e_source.predict_proba(MISS) is None
    finally:
        e2e_source._texts.cache_clear()
        e2e_source._runtime.cache_clear()


def test_e2e_unavailable_returns_none(tmp_path, monkeypatch):
    """无文本表 / 无编码器 → predict 返回 None，由上层给明确提示。"""
    from app import e2e_source

    monkeypatch.setattr(config, "PIPELINES_DIR", tmp_path)
    e2e_source._texts.cache_clear()
    e2e_source._runtime.cache_clear()
    try:
        assert e2e_source.predict_proba(HIT) is None
        assert e2e_source.available() is False
    finally:
        e2e_source._texts.cache_clear()
        e2e_source._runtime.cache_clear()
