# [AI生成] 本文件用例由 AI 编写，核心断言经人工复核。
"""提交组装纯函数的三例单元测试（app/services/commits.py）。

`feature_dict` / `explanation_for` 是详情接口的字段组装入口，此前只在 API 层
间接覆盖；这里补函数级三例（fix 整型 vs 其余浮点、缺模型/缺特征空列表）。
"""

from __future__ import annotations

import pytest
from app import config, model_registry
from app.models import CommitFeature
from app.services.commits import explanation_for, feature_dict, localization_for

FEATURE_VALUES = {
    "ns": 1.0986,
    "nd": 1.6094,
    "nf": 1.9459,
    "entropy": 1.42,
    "la": -4.2720,
    "ld": -5.2753,
    "lt": 7.1136,
    "fix": 1,
    "ndev": 1.3863,
    "age": 2.5257,
    "nuc": 0.2513,
    "exp": 5.7683,
    "rexp": 3.8114,
    "sexp": 2.8904,
}


def _feature() -> CommitFeature:
    return CommitFeature(commit_hash="a" * 40, feature_version="v1", **FEATURE_VALUES)


def test_feature_dict_returns_14_features_in_contract_order():
    out = feature_dict(_feature())
    assert list(out.keys()) == list(config.FEATURE_COLUMNS)
    assert len(out) == 14


def test_feature_dict_fix_is_int_others_float():
    out = feature_dict(_feature())
    assert isinstance(out["fix"], int) and out["fix"] == 1
    assert isinstance(out["ns"], float)
    assert isinstance(out["sexp"], float)


def test_feature_dict_none_returns_none():
    assert feature_dict(None) is None


def test_explanation_for_returns_labeled_rows(monkeypatch):
    """正常：已注册模型返回 SHAP 项并补中文因子名。"""
    feat = _feature()
    monkeypatch.setattr(model_registry, "has", lambda name: name == "m_v1")
    monkeypatch.setattr(model_registry, "get_model", lambda name: object())
    monkeypatch.setattr(
        model_registry,
        "explain",
        lambda model, vector: [{"feature": "ns", "contribution": 0.5, "direction": "increase"}],
    )
    assert explanation_for("m_v1", feat) == [
        {"feature": "ns", "contribution": 0.5, "direction": "increase", "label": "变更子系统多"}
    ]


@pytest.mark.parametrize(
    ("model_name", "has_feature"),
    [
        (None, True),
        ("m_v1", False),
    ],
)
def test_explanation_for_empty_when_model_or_feature_missing(model_name, has_feature):
    """边界：模型名缺失 / 特征缺失 → 空列表，不报错。"""
    feature = _feature() if has_feature else None
    assert explanation_for(model_name, feature) == []


def test_explanation_for_empty_when_model_not_registered():
    """边界：模型在交付清单但未加载 → 空列表。"""
    assert explanation_for("not_loaded_v1", _feature()) == []


def test_localization_sorts_by_abs_contribution_and_truncates():
    """正常：高亮项按 |contribution| 降序，top_k 截断，level 恒为 commit。"""
    explanation = [
        {"feature": "a", "label": "A", "contribution": 0.1, "direction": "increase"},
        {"feature": "b", "label": "B", "contribution": -0.5, "direction": "decrease"},
        {"feature": "c", "label": "C", "contribution": 0.3, "direction": "increase"},
    ]
    loc = localization_for(explanation, top_k=2)
    assert loc["level"] == "commit"
    assert [h["feature"] for h in loc["highlights"]] == ["b", "c"]
    assert "降级到提交级" in loc["notice"]


def test_localization_empty_explanation_gives_empty_highlights():
    """边界：归因为空（核/深度模型设计内降级）→ 空高亮 + 明确提示，不编造。"""
    loc = localization_for([])
    assert loc["level"] == "commit"
    assert loc["highlights"] == []
    assert "暂无定位" in loc["notice"]
