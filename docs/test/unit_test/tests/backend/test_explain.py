# [AI生成] 本文件用例由 AI 编写，核心断言经人工复核。
"""解释因子标签的三例单元测试（app/explain.py）。

`explain_label` / `with_labels` 是详情 / 预测 / PR 理由共用的中文名映射入口，
此前只在 API 层间接覆盖，缺函数级三例（尤其「未知因子回退原名、不报错」）。
"""

from __future__ import annotations

from app.explain import explain_label, with_labels


def test_explain_label_known_feature_returns_chinese():
    assert explain_label("ns") == "变更子系统多"
    assert explain_label("fix") == "历史修复标记"


def test_explain_label_unknown_feature_falls_back_to_name():
    """边界：未知因子回退为原名，MUST NOT 报错或返回空。"""
    assert explain_label("not_a_feature") == "not_a_feature"
    assert explain_label("") == ""


def test_with_labels_appends_label_to_each_item():
    rows = with_labels(
        [
            {"feature": "ns", "contribution": 0.5},
            {"feature": "lt", "contribution": -0.3},
        ]
    )
    assert rows[0]["label"] == "变更子系统多"
    assert rows[1]["label"] == "测试改动少"


def test_with_labels_empty_list():
    assert with_labels([]) == []


def test_with_labels_missing_feature_key_gets_empty_label():
    assert with_labels([{"contribution": 0.1}]) == [{"contribution": 0.1, "label": ""}]


def test_with_labels_does_not_mutate_input():
    """返回新列表，不改原对象。"""
    item = {"feature": "ns", "contribution": 0.5}
    with_labels([item])
    assert item == {"feature": "ns", "contribution": 0.5}
