# [AI生成-人工修改] 一句话总结：模板事实句 + LLM 不可用时回退。
from app.services import risk_summary


def test_template_uses_top_factors_and_top_file():
    text = risk_summary.template_summary(
        model_name="xgb_v1",
        model_line="expert",
        risk_score=0.82,
        features={"nf": 2.0, "la": 5.0},
        explanation=[
            {"feature": "nf", "label": "改动文件多", "direction": "increase", "contribution": 0.4},
            {"feature": "la", "label": "代码改动量大", "direction": "increase", "contribution": 0.3},
            {"feature": "sexp", "label": "作者近期经验低", "direction": "decrease", "contribution": 0.2},
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
        model_name="codebert_e2e_v1",
        model_line="e2e",
        risk_score=0.12,
        features={"nf": 1.0},
        explanation=[],
    )
    assert "端到端模型判为低风险" in text


def test_llm_result_is_used_when_available(monkeypatch):
    risk_summary._cache.clear()
    monkeypatch.setattr(risk_summary, "_llm_summary", lambda facts: "LLM 生成的一句话。")
    text = risk_summary.summary_for(
        commit_hash="c" * 40,
        model_name="xgb_fused_v1",
        model_line="fused",
        risk_score=0.6,
        features={},
        explanation=[],
    )
    assert text == "LLM 生成的一句话。"
