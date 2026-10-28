"""历史 SQLite 库的迁移回归（改动前必崩，且崩得无声）。

`test_db.py` 把**应用级夹具**统一到 MySQL（jit_test），但本机排障与 `demo_preflight`
仍会用 SQLite 文件（`tests/test_demo_preflight.py:912` 就直接对 SQLite 调 `init_database`）。
`db.py` 里保留的 `dialect.name != "mysql"` 分支也说明 SQLite 并未被宣布不支持。

两处硬错只在「历史库 + SQLite」这个组合下暴露，所以 CI 一直全绿：

1. `ALTER TABLE … ADD COLUMN updated_at … DEFAULT CURRENT_TIMESTAMP` —— SQLite 拒绝
   非确定默认值（`Cannot add a column with non-constant default`），`app.db init` 直接崩；
2. `ensure_model_rows` 的 `ON DUPLICATE KEY UPDATE` —— SQLite 语法错，而调用方
   （`main.py` 启动）把它吞成一行 ERROR 日志 → 应用照启、`model` 表只剩迁移回填的
   那几行，**元数据半套且无人察觉**。

全新库不会碰到它们：`create_all` 直接建成当前形态，第 1 步因列已存在而跳过。
"""

from __future__ import annotations

import pytest
from app import db
from app.db import Base, _apply_bcnf_migration, ensure_model_rows
from sqlalchemy import create_engine, inspect, text

# 只建到「迁移前」的形态：四表在、无 updated_at、无 model 表。
# 表名一律加双引号：`commit` 在 SQLite 是保留字（不加引号直接 syntax error）。
LEGACY_DDL = {
    "commit": """CREATE TABLE "commit" (
        id INTEGER PRIMARY KEY AUTOINCREMENT, commit_hash CHAR(40) NOT NULL UNIQUE,
        repo_name VARCHAR(64), author_name VARCHAR(128), author_email VARCHAR(254),
        message TEXT, committed_at DATETIME, parent_hash VARCHAR(255))""",
    "commit_label": """CREATE TABLE "commit_label" (
        id INTEGER PRIMARY KEY AUTOINCREMENT, commit_hash CHAR(40) NOT NULL,
        is_bug_inducing BOOLEAN, label_method VARCHAR(32), bug_fix_hash CHAR(40),
        labeled_at DATETIME, UNIQUE (commit_hash, label_method))""",
    "commit_feature": """CREATE TABLE "commit_feature" (
        commit_hash CHAR(40) PRIMARY KEY, committed_at DATETIME,
        feature_version VARCHAR(32), ns DECIMAL(20,10))""",
    "prediction": """CREATE TABLE "prediction" (
        id INTEGER PRIMARY KEY AUTOINCREMENT, commit_hash CHAR(40) NOT NULL,
        risk_score DECIMAL(6,5), model_name VARCHAR(64) NOT NULL,
        predicted_at DATETIME, feature_version VARCHAR(32),
        UNIQUE (commit_hash, model_name))""",
}


@pytest.fixture
def legacy_sqlite_engine(tmp_path):
    """一个「跑过老版本、现在要迁移」的 SQLite 库。

    注入引擎要同时还原 `_engine` 与 `SessionLocal` 的 bind —— 只还原前者会把坏 bind
    留给后面的测试文件（本项目为此踩过一次 78 errors 的整片失败）。
    """
    eng = create_engine(f"sqlite:///{(tmp_path / 'legacy.db').as_posix()}")
    with eng.begin() as conn:
        for ddl in LEGACY_DDL.values():
            conn.execute(text(ddl))
        conn.execute(text('INSERT INTO "commit" (commit_hash, committed_at) '
                          "VALUES (:h, '2020-01-01')"), {"h": "a" * 40})
        for name in ("xgb_v1", "lr_v1"):
            conn.execute(text('INSERT INTO "prediction" (commit_hash, model_name, risk_score) '
                              "VALUES (:h, :m, 0.5)"),
                         {"h": "a" * 40, "m": name})

    original = db._engine
    eng_ = eng
    db._engine = eng_
    db.SessionLocal.configure(bind=eng_)
    try:
        yield eng_
    finally:
        db._engine = original
        if original is not None:
            db.SessionLocal.configure(bind=original)
        else:
            db.SessionLocal.kw.pop("bind", None)
        eng_.dispose()


def _columns(eng, table):
    return {c["name"] for c in inspect(eng).get_columns(table)}


def test_legacy_sqlite_db_migrates_without_raising(legacy_sqlite_engine):
    """改动前这里直接抛 OperationalError（ADD COLUMN 的非确定默认值）。"""
    _apply_bcnf_migration(legacy_sqlite_engine)

    for table in LEGACY_DDL:
        assert "updated_at" in _columns(legacy_sqlite_engine, table), table
        # 回填过的历史行不能是常量占位值（那是「没填」的伪装）
        with legacy_sqlite_engine.begin() as conn:
            n_null = conn.execute(text(
                f'SELECT COUNT(*) FROM "{table}" WHERE updated_at IS NULL')).scalar()
        assert n_null == 0, f"{table}.updated_at 出现 NULL：历史行没被回填"


def test_migration_backfills_model_table_from_prediction(legacy_sqlite_engine):
    _apply_bcnf_migration(legacy_sqlite_engine)
    with legacy_sqlite_engine.begin() as conn:
        names = {r[0] for r in conn.execute(text("SELECT model_name FROM `model`"))}
    assert names == {"xgb_v1", "lr_v1"}


def test_ensure_model_rows_is_portable_and_idempotent(legacy_sqlite_engine):
    """改动前这里抛 `near "DUPLICATE": syntax error`；且启动期从不检查它成没成。"""
    entries = [{"model_name": f"m{i}_v1", "version_key": "m", "algo": "Pipeline",
                "feature_version": "v1", "trained_at": None} for i in range(8)]
    ensure_model_rows(entries)
    with legacy_sqlite_engine.begin() as conn:
        assert conn.execute(text("SELECT COUNT(*) FROM `model`")).scalar() == 8

    # 再跑一次（模拟重启）：仍是 8 行，且元数据被更新而不是插出第二行
    ensure_model_rows([{**e, "algo": "Changed"} for e in entries])
    with legacy_sqlite_engine.begin() as conn:
        rows = conn.execute(text("SELECT model_name, algo FROM `model` ORDER BY model_name")).fetchall()
    assert len(rows) == 8, f"重复启动插出多余行：{len(rows)}"
    assert {r[1] for r in rows} == {"Changed"}


def test_fresh_sqlite_db_still_needs_no_migration_steps(tmp_path):
    """全新库走 create_all：迁移必须整体 no-op（这条守住「幂等、可重复执行」的承诺）。"""
    eng = create_engine(f"sqlite:///{(tmp_path / 'fresh.db').as_posix()}")
    Base.metadata.create_all(eng)
    before = {t: sorted(_columns(eng, t)) for t in inspect(eng).get_table_names()}
    _apply_bcnf_migration(eng)
    after = {t: sorted(_columns(eng, t)) for t in inspect(eng).get_table_names()}
    assert before == after, "全新库上迁移改动了结构，说明不幂等"
