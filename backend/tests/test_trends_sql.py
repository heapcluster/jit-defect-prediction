# === AI 辅助说明 ===
# 本文件共 3 条测试用例
# [AI生成]：0 条
# [AI生成-人工修改]：3 条（AI 生成骨架，人工补充核心断言）
# [手写]：0 条
# 使用工具：原始生成记录未归档（标注依据代码特征判断，作者于 2026-11-17 确认）
# 提示词见：docs/test/unit_test/prompts/README.md

"""趋势接口的 MySQL 聚合分支：用 MySQL 方言编译后断言 SQL 结构。

做法：把聚合语句抽成纯函数 `build_aggregate_stmt`，用 MySQL 方言编译后断言结构。
这样「分桶 / 计数 / 均值 / 高风险计数是否真下推到 SQL」在 CI 里也有判据，
不必等真库跑起来才发现 `date_format` 或 GROUP BY 写错。
"""

from __future__ import annotations

import pytest
from app.api.trends import build_aggregate_stmt
from app.models import Commit, Prediction
from sqlalchemy import select
from sqlalchemy.dialects import mysql


def _base():
    return select(Prediction.risk_score, Commit.committed_at).join(
        Commit, Commit.commit_hash == Prediction.commit_hash
    )


@pytest.mark.parametrize(("granularity", "fmt"), [("week", "%x-W%v"), ("month", "%Y-%m")])
def test_aggregation_is_pushed_down_to_sql(granularity: str, fmt: str):
    sql = str(
        build_aggregate_stmt(_base(), granularity, 0.5).compile(
            dialect=mysql.dialect(), compile_kwargs={"literal_binds": True}
        )
    ).lower()
    assert "date_format" in sql, "分桶必须下推到 SQL，否则整表会被搬进 Python"
    # pymysql 风格的参数转义会把字面量里的 `%` 写成 `%%`
    assert fmt.lower().replace("%", "%%") in sql
    assert "group by" in sql and "order by" in sql
    assert "count(" in sql and "avg(" in sql
    assert "case when" in sql, "高风险计数必须是条件聚合，不能回 Python 再数"


def test_aggregation_has_no_derived_table():
    """直接 GROUP BY 表达式即可；套一层子查询会让 MySQL 多一次派生表物化。"""
    sql = str(build_aggregate_stmt(_base(), "week", 0.5).compile(dialect=mysql.dialect())).lower()
    assert "from (select" not in sql
