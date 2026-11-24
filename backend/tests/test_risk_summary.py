# === AI 辅助说明 ===
# 本文件共 5 条测试用例
# [AI生成]：0 条
# [AI生成-人工修改]：5 条（AI 生成骨架，人工补充核心断言）
# [手写]：0 条
# 使用工具：原始生成记录未归档（标注依据代码特征判断，作者于 2026-11-17 确认）
# 提示词见：docs/test/unit_test/prompts/README.md

from app.services import risk_summary


def test_template_uses_top_factors_and_top_file():
    text = risk_summary.template_summary(
        model_name="xgb_v1",
        model_line="expert",
        risk_score=0.82,
        features={"nf": 2.0, "la": 5.0},
        explanation=[
            {"feature": "nf", "label": "改动文件多", "direction": "increase", "contribution": 0.4},
            {
                "feature": "la",
                "label": "代码改动量大",
                "direction": "increase",
                "contribution": 0.3,
            },
            {
                "feature": "sexp",
                "label": "作者近期经验低",
                "direction": "decrease",
                "contribution": 0.2,
            },
        ],
        localization={"files": [{"path": "core/A.java"}]},
    )
    assert "高风险" in text
    assert "改动文件多" in text and "代码改动量大" in text
    assert "core/A.java" in text


def test_template_without_explanation_uses_feature_thresholds():
    text = risk_summary.template_summary(
        model_name="xgb_semantic_v1",
        model_line="semantic",
        risk_score=0.35,
        features={"nf": 2.0, "ld": 3.5},
        explanation=[],
        localization=None,
    )
    assert "中风险" in text
    assert "改动文件较多" in text and "删除代码较多" in text


def test_summary_returns_none_without_prediction():
    assert (
        risk_summary.summary_for(
            commit_hash="a" * 40,
            model_name=None,
            model_line=None,
            risk_score=None,
            features=None,
            explanation=None,
        )
        is None
    )


def test_summary_falls_back_to_template_without_llm_config(monkeypatch):
    monkeypatch.setattr(risk_summary.config, "LLM_BASE_URL", "")
    risk_summary._cache.clear()
    text = risk_summary.summary_for(
        commit_hash="b" * 40,
        model_name="xgb_semantic_v1",
        model_line="semantic",
        risk_score=0.12,
        features={"nf": 1.0},
        explanation=[],
    )
    assert "语义模型判为低风险" in text


def test_llm_result_is_used_when_available(monkeypatch):
    risk_summary._cache.clear()
    monkeypatch.setattr(risk_summary, "_llm_summary", lambda facts: "LLM 生成的一句话。")
    text = risk_summary.summary_for(
        commit_hash="c" * 40,
        model_name="xgb_semantic_v1",
        model_line="semantic",
        risk_score=0.6,
        features={},
        explanation=[],
    )
    assert text == "LLM 生成的一句话。"
