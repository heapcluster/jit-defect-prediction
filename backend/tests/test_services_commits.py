# === AI 辅助说明 ===
# 本文件共 14 条测试用例
# [AI生成]：12 条（经人工审核修改后采纳）
# [AI生成-人工修改]：0 条
# [手写]：0 条
# 使用工具：原始生成记录未归档（标注依据代码特征判断，作者于 2026-11-17 确认）
# 提示词见：docs/test/unit_test/prompts/README.md

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


def test_localization_top_k_zero_gives_empty_highlights():
    """边界：top_k=0 时高亮为空，level 与提示仍完整。"""
    explanation = [
        {"feature": "a", "label": "A", "contribution": 0.4, "direction": "increase"},
    ]
    loc = localization_for(explanation, top_k=0)
    assert loc["level"] == "commit"
    assert loc["highlights"] == []
    assert "暂无定位" in loc["notice"]


def test_localization_top_k_exceeds_length_returns_all():
    """边界：top_k 大于归因条数时返回全部，不补空位。"""
    explanation = [
        {"feature": "a", "label": "A", "contribution": 0.2, "direction": "increase"},
        {"feature": "b", "label": "B", "contribution": -0.6, "direction": "decrease"},
    ]
    loc = localization_for(explanation, top_k=10)
    assert [h["feature"] for h in loc["highlights"]] == ["b", "a"]


def test_file_score_prefers_modified_source_over_test_or_generated():
    """启发式排序：修改既有源码 > 纯新增源码 > 测试/生成物。"""
    from app.services.commits import _file_raw_score

    modified_source = {
        "path": "core/src/main/java/A.java",
        "added_lines": [{"number": 1, "content": "x"}],
        "deleted_count": 5,
        "hunks": [{"added_lines": [{"number": 1, "content": "x"}], "deleted_count": 5}],
    }
    new_source = {
        "path": "core/src/main/java/B.java",
        "added_lines": [{"number": 1, "content": "x"}] * 6,
        "deleted_count": 0,
        "hunks": [{"added_lines": [{"number": 1, "content": "x"}] * 6, "deleted_count": 0}],
    }
    test_file = {
        "path": "core/src/test/java/ATest.java",
        "added_lines": [{"number": 1, "content": "x"}],
        "deleted_count": 5,
        "hunks": [{"added_lines": [{"number": 1, "content": "x"}], "deleted_count": 5}],
    }
    assert _file_raw_score(modified_source)[0] > _file_raw_score(new_source)[0]
    assert _file_raw_score(modified_source)[0] > _file_raw_score(test_file)[0]


def test_line_suspicion_penalizes_comments_and_boosts_control_flow():
    from app.services.commits import _line_suspicion

    flow = _line_suspicion(
        {"content": "if (source == null) throw new IllegalArgumentException();"},
        risk_score=0.8,
        file_score=1.0,
        hunk_norm=1.0,
        path="core/A.java",
    )
    comment = _line_suspicion(
        {"content": "// explain the branch"},
        risk_score=0.8,
        file_score=1.0,
        hunk_norm=1.0,
        path="core/A.java",
    )
    test_line = _line_suspicion(
        {"content": "if (source == null) throw new IllegalArgumentException();"},
        risk_score=0.8,
        file_score=1.0,
        hunk_norm=1.0,
        path="core/src/test/java/ATest.java",
    )
    assert flow > comment
    assert flow > test_line
    assert 0 <= comment <= 1 and 0 <= flow <= 1


def test_source_tier_is_above_generated_and_docs():
    """生成物/文档行数再多，也不能压过源码文件（排序第一优先级是类型层级）。"""
    from app.services.commits import _FILE_TIER, _file_weight

    assert _file_weight("core/src/main/java/A.java")[1] == "源码文件"
    assert _file_weight("dsl/generated/A.java")[1] == "生成物"
    assert _FILE_TIER["源码文件"] > _FILE_TIER["文档/配置"]
    assert _FILE_TIER["源码文件"] > _FILE_TIER["生成物"]
