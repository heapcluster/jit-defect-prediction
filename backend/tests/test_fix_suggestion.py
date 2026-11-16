# [AI生成-人工修改] 修复建议：模板回退 + LLM 结果优先。
from app.services import fix_suggestion


def test_template_suggestions_reference_top_file_and_line():
    suggestions = fix_suggestion.suggestions_for(
        commit_message="fix null pointer",
        risk_score=0.8,
        model_line="expert",
        features={"nf": 2.0},
        explanation=[],
        localization={
            "files": [
                {
                    "path": "core/A.java",
                    "lines": [{"number": 120, "content": "if (source == null) {"}],
                }
            ]
        },
        historical_fixes=[],
    )
    assert suggestions
    assert "core/A.java" in suggestions[0]
    assert "120" in suggestions[0]


def test_template_suggestions_without_localization_are_generic():
    suggestions = fix_suggestion.suggestions_for(
        commit_message="change",
        risk_score=0.3,
        model_line="semantic",
        features={},
        explanation=[],
        localization=None,
    )
    assert suggestions
    assert all(isinstance(item, str) and item for item in suggestions)


def test_llm_suggestions_take_precedence(monkeypatch):
    monkeypatch.setattr(
        fix_suggestion, "_llm_suggestions", lambda facts: ["先修这里。", "再补测试。"]
    )
    assert fix_suggestion.suggestions_for(
        commit_message="x",
        risk_score=0.5,
        model_line="fused",
        features={},
        explanation=[],
        localization=None,
    ) == ["先修这里。", "再补测试。"]
