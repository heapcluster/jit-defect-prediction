"""静态比对 `infra/schema.sql` 与 SQLAlchemy `Base.metadata`。

`infra/schema.sql` 是建表唯一真源（docker compose 首次启动与 CI 实际执行它），
本测试守住三件事，防止 ORM 与建表脚本漂移：

1. 表集合一致；
2. 每张表的列名集合一致；
3. 每张表的主键列一致（含联合主键顺序）。

重建说明：原 `test_schema_sql.py` 在 2026-11 文档重组中丢失，本版按当前
`infra/schema.sql` 与 `app.models` 重新实现，聚焦上述三类不变量；
openspec 中记录的历史 25 条用例（含 8 条漂移负例、11 条额外操作负例）尚未全部恢复。
"""

from __future__ import annotations

import re
from pathlib import Path

from app.models import Base

SCHEMA_SQL = Path(__file__).resolve().parents[2] / "infra" / "schema.sql"

_TABLE_RE = re.compile(r"^CREATE TABLE IF NOT EXISTS `?(\w+)`?\s*\($", re.IGNORECASE)
_PK_RE = re.compile(r"^PRIMARY KEY\s*\(([^)]+)\)", re.IGNORECASE)
_COLUMN_RE = re.compile(r"^`?(\w+)`?\s+[A-Za-z]")
_NON_COLUMN_PREFIX = re.compile(
    r"^(PRIMARY|UNIQUE|INDEX|KEY|FOREIGN|CONSTRAINT)\b", re.IGNORECASE
)


def parse_schema(sql: str) -> dict[str, dict[str, list[str]]]:
    """解析建表脚本，返回 {表名: {"columns": [...], "pk": [...]}}。"""
    tables: dict[str, dict[str, list[str]]] = {}
    current: str | None = None

    for raw in sql.splitlines():
        line = raw.strip()
        match = _TABLE_RE.match(line)
        if match:
            current = match.group(1).lower()
            tables[current] = {"columns": [], "pk": []}
            continue
        if current is None:
            continue
        if line.startswith(")"):
            current = None
            continue

        pk = _PK_RE.match(line)
        if pk:
            tables[current]["pk"] = [
                part.strip().strip("`").lower() for part in pk.group(1).split(",")
            ]
            continue
        if _NON_COLUMN_PREFIX.match(line):
            continue

        column = _COLUMN_RE.match(line)
        if column:
            tables[current]["columns"].append(column.group(1).lower())

    return tables


def test_schema_sql_exists() -> None:
    assert SCHEMA_SQL.is_file(), f"建表真源缺失：{SCHEMA_SQL}"


def test_parser_detects_unknown_table() -> None:
    """负例：解析器应能读出一张 metadata 里不存在的表，证明比对不是恒真。"""
    parsed = parse_schema(
        "CREATE TABLE IF NOT EXISTS ghost (\n\tid INT NOT NULL,\n\tPRIMARY KEY (id)\n);\n"
    )
    assert "ghost" in parsed
    assert "ghost" not in Base.metadata.tables


def test_table_set_matches_metadata() -> None:
    parsed = parse_schema(SCHEMA_SQL.read_text(encoding="utf-8"))
    assert set(parsed) == set(Base.metadata.tables), (
        f"表集合不一致：schema.sql={sorted(parsed)} metadata={sorted(Base.metadata.tables)}"
    )


def test_columns_match_metadata() -> None:
    parsed = parse_schema(SCHEMA_SQL.read_text(encoding="utf-8"))
    for name, table in Base.metadata.tables.items():
        assert name in parsed, f"metadata 表 {name} 未在 schema.sql 中建表"
        assert set(parsed[name]["columns"]) == set(table.columns.keys()), (
            f"{name} 列集合不一致：schema.sql={sorted(parsed[name]['columns'])} "
            f"metadata={sorted(table.columns.keys())}"
        )


def test_primary_keys_match_metadata() -> None:
    parsed = parse_schema(SCHEMA_SQL.read_text(encoding="utf-8"))
    for name, table in Base.metadata.tables.items():
        expected = [column.name for column in table.primary_key.columns]
        assert parsed[name]["pk"] == expected, (
            f"{name} 主键不一致：schema.sql={parsed[name]['pk']} metadata={expected}"
        )
