# === AI 辅助说明 ===
# 本文件共 8 条测试用例
# [AI生成]：6 条（经人工审核修改后采纳）
# [AI生成-人工修改]：0 条
# [手写]：0 条
# 使用工具：原始生成记录未归档（标注依据代码特征判断，作者于 2026-11-17 确认）
# 提示词见：docs/README.md

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


def test_explain_label_covers_all_fourteen_features():
    """边界：14 项特征全部有中文名；新增特征漏配标签时这条先失败。"""
    from app import config

    for name in config.FEATURE_COLUMNS:
        assert explain_label(name) != name, f"{name} 缺少中文名"


def test_explain_label_is_case_sensitive():
    """异常：大写输入不做小写匹配，按未知因子原样返回。"""
    assert explain_label("NS") == "NS"
    assert explain_label("Entropy") == "Entropy"


def test_with_labels_appends_label_to_each_item():
    rows = with_labels(
        [
            {"feature": "ns", "contribution": 0.5},
            {"feature": "lt", "contribution": -0.3},
        ]
    )
    assert rows[0]["label"] == "变更子系统多"
    assert rows[1]["label"] == "变更前文件代码规模"


def test_with_labels_empty_list():
    assert with_labels([]) == []


def test_with_labels_missing_feature_key_gets_empty_label():
    assert with_labels([{"contribution": 0.1}]) == [{"contribution": 0.1, "label": ""}]


def test_with_labels_does_not_mutate_input():
    """返回新列表，不改原对象。"""
    item = {"feature": "ns", "contribution": 0.5}
    with_labels([item])
    assert item == {"feature": "ns", "contribution": 0.5}
