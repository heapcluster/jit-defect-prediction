"""入参校验：40 位十六进制 commit_hash 的归一化。

此前 `predict` / `commits` / `feedback` 三个路由各写一份（名字还不一样：
`_normalize_hash` / `_check_hash` / `normalize_hash`），同一条校验规则散落三处。
集中一处，保证「大写放行但查库用小写」（D-09）口径唯一。
"""

from __future__ import annotations

from app.errors import AppError

HASH_HEX = "0123456789abcdef"


def normalize_commit_hash(commit_hash: str | None) -> str:
    """校验并归一化为小写；非法 → 40001。调用方**必须**用返回值查库。"""
    if (
        not commit_hash
        or len(commit_hash) != 40
        or any(c not in HASH_HEX for c in commit_hash.lower())
    ):
        raise AppError(40001, "参数非法：commit_hash 需为 40 位十六进制")
    return commit_hash.lower()
