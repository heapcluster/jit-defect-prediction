"""静态检查 MySQL DDL 快照；只编译元数据，不连接 MySQL 或用 SQLite 执行 SQL。"""

from __future__ import annotations

from pathlib import Path

import pytest
from app.models import INDEX_ASSERTIONS, Base
from sqlalchemy import MetaData, UniqueConstraint
from sqlalchemy.dialects import mysql
from sqlalchemy.schema import CreateIndex, CreateTable

SCHEMA_SQL = Path(__file__).resolve().parents[2] / "infra" / "schema.sql"


def _mysql_statements(metadata: MetaData) -> dict[str, str]:
    """按稳定顺序编译四表；索引内联，避免重跑独立 CREATE INDEX。"""
    dialect = mysql.dialect()
    statements = {}
    for table in metadata.sorted_tables:
        ddl = str(CreateTable(table, if_not_exists=True).compile(dialect=dialect)).strip()
        indexes = []
        for index in sorted(table.indexes, key=lambda item: item.name):
            index_sql = str(CreateIndex(index).compile(dialect=dialect))
            # 保留方言生成的索引名、唯一性和列顺序，只移除独立语句的外壳。
            indexes.append(
                index_sql.removeprefix("CREATE ").replace(
                    f" ON {dialect.identifier_preparer.format_table(table)}", "", 1
                )
            )
        if indexes:
            body, closing, options = ddl.rpartition("\n)")
            assert closing, f"unexpected CREATE TABLE format: {table.name}"
            ddl = body + ",\n\t" + ",\n\t".join(indexes) + closing + options
        statements[table.name] = ddl
    return statements


def _normalize_sql(sql: str) -> str:
    return " ".join(sql.split())


def _assert_schema_matches_metadata(sql: str) -> None:
    # 仅忽略普通整行注释与排版；不忽略 MySQL 可执行注释或任何额外语句。
    sql = "\n".join(line for line in sql.splitlines() if not line.lstrip().startswith("-- "))
    statements = [_normalize_sql(part) for part in sql.split(";") if part.strip()]
    expected = _mysql_statements(Base.metadata)
    assert len(statements) == len(expected), "CREATE TABLE statements count mismatch"
    for statement, (table_name, ddl) in zip(statements, expected.items(), strict=True):
        assert statement == _normalize_sql(ddl), f"metadata drift: {table_name}"


def test_schema_sql_matches_complete_mysql_metadata():
    assert set(Base.metadata.tables) == {
        "commit",
        "commit_label",
        "commit_feature",
        "prediction",
        "model",
        "runtime_setting",
    }
    _assert_schema_matches_metadata(SCHEMA_SQL.read_text(encoding="utf-8"))


@pytest.mark.parametrize(
    ("table_name", "definitions"),
    [
        (
            "commit",
            (
                "PRIMARY KEY (id)",
                "UNIQUE (commit_hash)",
                "INDEX ix_commit_committed_at (committed_at)",
            ),
        ),
        ("commit_feature", ("PRIMARY KEY (commit_hash)",)),
        (
            "commit_label",
            (
                "PRIMARY KEY (id)",
                "CONSTRAINT uq_label_hash_method UNIQUE (commit_hash, label_method)",
                "INDEX ix_commit_label_commit_hash (commit_hash)",
            ),
        ),
        (
            "prediction",
            (
                "PRIMARY KEY (id)",
                "CONSTRAINT uq_prediction_hash_model UNIQUE (commit_hash, model_name)",
                "INDEX ix_prediction_commit_hash (commit_hash)",
            ),
        ),
    ],
)
def test_primary_unique_and_normal_indexes_are_inline(table_name, definitions):
    sql = SCHEMA_SQL.read_text(encoding="utf-8")
    _assert_schema_matches_metadata(sql)
    quoted_name = mysql.dialect().identifier_preparer.quote(table_name)
    statement = next(part for part in sql.split(";") if f"EXISTS {quoted_name} (" in part)
    for definition in definitions:
        assert definition in _normalize_sql(statement)


def test_metadata_covers_runtime_assertions_and_label_keys():
    keys = set()
    for table in Base.metadata.sorted_tables:
        for constraint in table.constraints:
            if isinstance(constraint, UniqueConstraint):
                keys.add((table.name, tuple(column.name for column in constraint.columns), True))
        for index in table.indexes:
            keys.add(
                (table.name, tuple(column.name for column in index.columns), bool(index.unique))
            )
    # 标签表两项不在 INDEX_ASSERTIONS 中，不能把运行时自检当完整元数据比对。
    required = (
        *INDEX_ASSERTIONS,
        ("commit_label", ("commit_hash", "label_method"), True),
        ("commit_label", ("commit_hash",), False),
    )
    assert set(required) <= keys


@pytest.mark.parametrize(
    ("original", "replacement", "table_name"),
    [
        (
            ", CONSTRAINT uq_prediction_hash_model UNIQUE (commit_hash, model_name)",
            "",
            "prediction",
        ),
        (
            ", CONSTRAINT uq_label_hash_method UNIQUE (commit_hash, label_method)",
            "",
            "commit_label",
        ),
        (", INDEX ix_commit_label_commit_hash (commit_hash)", "", "commit_label"),
        ("is_bug_inducing TINYINT(1)", "is_bug_inducing SMALLINT", "commit_label"),
        ("repo_name VARCHAR(64) NOT NULL", "repo_name VARCHAR(64)", "commit"),
        ("id BIGINT NOT NULL AUTO_INCREMENT", "id BIGINT NOT NULL", "commit"),
        ("UNIQUE (commit_hash, model_name)", "UNIQUE (model_name, commit_hash)", "prediction"),
        ("CREATE TABLE IF NOT EXISTS", "CREATE TABLE", "commit"),
    ],
    ids=[
        "missing-prediction-unique",
        "missing-label-unique",
        "missing-label-index",
        "wrong-type",
        "wrong-nullability",
        "missing-autoincrement",
        "wrong-key-order",
        "missing-if-not-exists",
    ],
)
def test_drift_check_rejects_mutated_schema(original, replacement, table_name):
    sql = SCHEMA_SQL.read_text(encoding="utf-8")
    _assert_schema_matches_metadata(sql)
    sql = _normalize_sql(sql)
    assert original in sql
    mutated = sql.replace(original, replacement, 1)
    with pytest.raises(AssertionError, match=f"metadata drift: {table_name}"):
        _assert_schema_matches_metadata(mutated)


@pytest.mark.parametrize(
    "extra_statement",
    [
        "INSERT INTO prediction (commit_hash) VALUES ('test')",
        "UPDATE prediction SET risk_score = 0",
        "DELETE FROM prediction",
        "DROP TABLE prediction",
        "ALTER TABLE prediction ADD extra INT",
        "TRUNCATE TABLE prediction",
        "GRANT SELECT ON prediction TO 'example'@'localhost'",
        "REVOKE SELECT ON prediction FROM 'example'@'localhost'",
        "CREATE DATABASE example",
        "CREATE USER 'example'@'localhost'",
        "CREATE INDEX ix_extra ON prediction (model_name)",
    ],
)
def test_rejects_data_permissions_destructive_and_standalone_index_statements(extra_statement):
    sql = SCHEMA_SQL.read_text(encoding="utf-8")
    _assert_schema_matches_metadata(sql)
    with pytest.raises(AssertionError, match="CREATE TABLE statements"):
        _assert_schema_matches_metadata(sql + "\n" + extra_statement + ";\n")
