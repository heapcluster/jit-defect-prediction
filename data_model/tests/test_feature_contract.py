"""契约二（14 项特征列）与实现 / 交付清单的一致性测试（T-MO-01）。

课程把「规格与代码不一致」列为一票否决缺陷。本测试把四处来源钉在同一份**有序**清单上：

  1. 契约文档  ``docs/model/feature-columns.md`` 第三节（权威，v1.2 冻结）
  2. 特征实现  ``data_model/preparation/03_extract_features.py`` 的 ``FEATURE_FIELDS``
  3. 后端装配  ``backend/app/config.py`` 的 ``FEATURE_COLUMNS``（模型输入向量顺序）
  4. 交付清单  ``data_model/pipelines/expert/models/feature_order.txt`` 的 ``[feature_order]``

任何一处列名改动 / 顺序漂移 / 漏项，本测试即红 —— 在合入前暴露，而不是等联调时解释条静默空白。

跑法：``cd data_model && python -m pytest -q``
"""

from __future__ import annotations

import ast
import re
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
EXTRACT_FEATURES = REPO_ROOT / "data_model" / "preparation" / "03_extract_features.py"
BACKEND_CONFIG = REPO_ROOT / "backend" / "app" / "config.py"
FEATURE_ORDER_TXT = REPO_ROOT / "data_model" / "pipelines" / "expert" / "models" / "feature_order.txt"
CONTRACT_MD = REPO_ROOT / "docs" / "model" / "feature-columns.md"
MODEL_DIR = REPO_ROOT / "data_model" / "pipelines" / "expert" / "models"

# 契约二第三节：14 项，顺序即契约出现顺序（五维度分组）
EXPECTED_14 = [
    "ns", "nd", "nf", "entropy",  # 代码分布 Diffusion
    "la", "ld", "lt",  # 规模 Size
    "fix",  # 目的 Purpose
    "ndev", "age", "nuc",  # 历史 History
    "exp", "rexp", "sexp",  # 开发者经验 Experience
]

# 交付边界（specs/model-coverage R6）：8 个模型全部为评估用，
# [models] 段只登记交给后端加载的三个
DELIVERED_MODELS = ["lr_v1.pkl", "rf_v1.pkl", "xgb_v1.pkl"]


def _literal(path: Path, name: str):
    """用 ast 取模块级字面量（列表/元组/字符串），避免 import 触发重依赖。"""
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    for node in tree.body:
        if not isinstance(node, ast.Assign):
            continue
        if not any(isinstance(t, ast.Name) and t.id == name for t in node.targets):
            continue
        value = node.value
        if isinstance(value, (ast.List, ast.Tuple)):
            return [elt.value for elt in value.elts]
        if isinstance(value, ast.Constant):
            return value.value
    raise AssertionError(f"{path.name} 中未找到模块级 {name}")


def _section(path: Path, header: str, next_header: str) -> str:
    text = path.read_text(encoding="utf-8")
    start = text.index(header)
    end = text.index(next_header, start)
    return text[start:end]


def _contract_columns() -> list[str]:
    section = _section(CONTRACT_MD, "## 三、14 项特征列", "## 四、")
    return re.findall(r"^\|\s*`([a-z_]+)`\s*\|", section, re.M)


def _manifest_columns() -> list[str]:
    text = FEATURE_ORDER_TXT.read_text(encoding="utf-8")
    match = re.search(r"\[feature_order\](.*?)(?:\n\[|\Z)", text, re.S)
    assert match, "feature_order.txt 缺少 [feature_order] 段"
    return re.findall(r"^\s*\d+\.\s*([A-Za-z_]+)", match.group(1), re.M)


def _manifest_models() -> list[str]:
    text = FEATURE_ORDER_TXT.read_text(encoding="utf-8")
    match = re.search(r"\[models\](.*?)(?:\n\[|\Z)", text, re.S)
    assert match, "feature_order.txt 缺少 [models] 段"
    return re.findall(r"^\s*([A-Za-z0-9_.]+\.pkl)", match.group(1), re.M)


@pytest.mark.parametrize(
    "source",
    [
        pytest.param(_contract_columns, id="契约文档-第三节"),
        pytest.param(lambda: _literal(EXTRACT_FEATURES, "FEATURE_FIELDS"), id="实现-FEATURE_FIELDS"),
        pytest.param(lambda: _literal(BACKEND_CONFIG, "FEATURE_COLUMNS"), id="后端-FEATURE_COLUMNS"),
        pytest.param(_manifest_columns, id="交付清单-feature_order"),
    ],
)
def test_fourteen_columns_same_order(source):
    """四处来源必须是同一份有序清单（列名 + 顺序都不能漂移）。"""
    assert source() == EXPECTED_14


def test_feature_version_is_v1():
    """契约冻结对应 feature_version = v1；口径一改必须升 v2，不覆盖 v1。"""
    assert _literal(EXTRACT_FEATURES, "FEATURE_VERSION") == "v1"


def test_delivered_models_are_exactly_three():
    """交付边界：只有三个模型进 [models] 段，其余五个仅作评估。"""
    assert _manifest_models() == DELIVERED_MODELS


def test_manifest_models_exist_on_disk():
    """清单里登记的 .pkl 必须真实存在。

    `.pkl` 被 `.gitignore` 排除（走打包交付），干净 clone 里没有 —— 这种环境
    下**跳过**而不是失败：本用例验的是「清单与磁盘一致」，不是「仓库必须带模型」。
    要跑这条，先按 `model/data-pipeline.md` 训练产出模型。
    """
    if not any(MODEL_DIR.glob("*.pkl")):
        pytest.skip(f"{MODEL_DIR} 内无 .pkl（.gitignore 排除，干净 clone 跳过本用例）")
    missing = [m for m in _manifest_models() if not (MODEL_DIR / m).exists()]
    assert not missing, f"清单登记但文件缺失：{missing}"


def test_contract_has_no_unknown_column():
    """反向：契约里不得出现 14 项之外的列名（防私自加派生特征）。"""
    extra = [c for c in _contract_columns() if c not in EXPECTED_14]
    assert not extra, f"契约出现 14 项之外的列名：{extra}"
