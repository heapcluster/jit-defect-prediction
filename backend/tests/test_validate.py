"""commit_hash 归一化的三例单元测试（app/validate.py）。

此前该函数只在 API 层被间接覆盖（test_security_boundaries.py），缺函数级
「正常/边界/异常」三例：这里锁死「大写放行但查库用小写」口径（D-09）与
统一错误码 40001。
"""

from __future__ import annotations

import pytest
from app.errors import AppError
from app.validate import normalize_commit_hash

LOWER = "a" * 40


def test_normalize_lowercase_hex_is_identity():
    """正常：40 位小写十六进制原样返回。"""
    assert normalize_commit_hash(LOWER) == LOWER


def test_normalize_uppercase_hex_lowers_for_lookup():
    """边界：大写/混合大小写放行，但返回小写（调用方必须用返回值查库，D-09）。"""
    assert normalize_commit_hash(LOWER.upper()) == LOWER
    assert normalize_commit_hash(LOWER.title()) == LOWER


@pytest.mark.parametrize(
    "bad",
    [
        None,
        "",
        "a" * 39,
        "a" * 41,
        "g" * 40,
        "z" * 40,
        LOWER + "!",
    ],
)
def test_normalize_rejects_non_40_hex(bad):
    """异常：空值、长度不符、非十六进制字符一律 40001。"""
    with pytest.raises(AppError) as exc:
        normalize_commit_hash(bad)
    assert exc.value.code == 40001
