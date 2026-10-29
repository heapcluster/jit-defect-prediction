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

from datetime import datetime

import pytest
from app import db
from app.config import FEATURE_COLUMNS
from app.db import Base, _apply_bcnf_migration, ensure_model_rows
from sqlalchemy import create_engine, inspect, text

# 「迁移前」的库形态：与 ORM 同列同可空性，只少 `updated_at`（也没有 `model` 表）。
# 必须照着 ORM 的真实约束写 —— 重建路径会把旧数据拷进当前 ORM DDL，
# 夹具若比真旧库松（例如漏了 NOT NULL），测的就不是真实迁移。
# 表名一律加双引号：`commit` 在 SQLite 是保留字（不加引号直接 syntax error）。
_FEATURE_COLS = ",\n        ".join(
    f'"{name}" {"SMALLINT" if name == "fix" else "DECIMAL(20, 10)"} NOT NULL'
    for name in FEATURE_COLUMNS
)
LEGACY_DDL = {
    "commit": """CREATE TABLE "commit" (
        id INTEGER NOT NULL PRIMARY KEY,
        repo_name VARCHAR(64) NOT NULL,
        commit_hash CHAR(40) NOT NULL,
        author_name VARCHAR(128) NOT NULL,
        author_email VARCHAR(128),
        committed_at DATETIME NOT NULL,
        message TEXT NOT NULL,
        parent_hash CHAR(40),
        UNIQUE (commit_hash))""",
    "commit_label": """CREATE TABLE "commit_label" (
        id INTEGER NOT NULL PRIMARY KEY,
        commit_hash CHAR(40) NOT NULL,
        is_bug_inducing SMALLINT NOT NULL,
        label_method VARCHAR(32) NOT NULL,
        bug_fix_hash CHAR(40),
        labeled_at DATETIME NOT NULL,
        CONSTRAINT uq_label_hash_method UNIQUE (commit_hash, label_method))""",
    "commit_feature": f"""CREATE TABLE "commit_feature" (
        commit_hash CHAR(40) NOT NULL PRIMARY KEY,
        committed_at DATETIME NOT NULL,
        feature_version VARCHAR(32) NOT NULL,
        {_FEATURE_COLS})""",
    "prediction": """CREATE TABLE "prediction" (
        id INTEGER NOT NULL PRIMARY KEY,
        commit_hash CHAR(40) NOT NULL,
        model_name VARCHAR(64) NOT NULL,
        risk_score DECIMAL(6, 5) NOT NULL,
        predicted_at DATETIME NOT NULL,
        feature_version VARCHAR(32) NOT NULL,
        CONSTRAINT uq_prediction_hash_model UNIQUE (commit_hash, model_name))""",
}
# 旧库上已有的索引（重建时会先删掉再按 ORM 规范名重建，用来验证这条路径）
LEGACY_INDEXES = [
    'CREATE INDEX ix_commit_committed_at ON "commit" (committed_at)',
    "CREATE INDEX ix_prediction_commit_hash ON prediction (commit_hash)",
]


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
        for ddl in LEGACY_INDEXES:
            conn.execute(text(ddl))
        conn.execute(
            text(
                'INSERT INTO "commit" (id, repo_name, commit_hash, author_name, committed_at, '
                "message) VALUES (1, 'camel', :h, 'jdoe', '2020-01-01 00:00:00', 'CAMEL-1 fix')"
            ),
            {"h": "a" * 40},
        )
        for name in ("xgb_v1", "lr_v1"):
            conn.execute(
                text(
                    'INSERT INTO "prediction" (commit_hash, model_name, risk_score, '
                    "predicted_at, feature_version) VALUES (:h, :m, 0.5, '2026-01-01 00:00:00', 'v1')"
                ),
                {"h": "a" * 40, "m": name},
            )

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
            n_null = conn.execute(
                text(f'SELECT COUNT(*) FROM "{table}" WHERE updated_at IS NULL')
            ).scalar()
        assert n_null == 0, f"{table}.updated_at 出现 NULL：历史行没被回填"


def test_migration_backfills_model_table_from_prediction(legacy_sqlite_engine):
    _apply_bcnf_migration(legacy_sqlite_engine)
    with legacy_sqlite_engine.begin() as conn:
        names = {r[0] for r in conn.execute(text("SELECT model_name FROM `model`"))}
    assert names == {"xgb_v1", "lr_v1"}


def test_ensure_model_rows_is_portable_and_idempotent(legacy_sqlite_engine):
    """改动前这里抛 `near "DUPLICATE": syntax error`；且启动期从不检查它成没成。"""
    entries = [
        {
            "model_name": f"m{i}_v1",
            "version_key": "m",
            "algo": "Pipeline",
            "feature_version": "v1",
            "trained_at": None,
        }
        for i in range(8)
    ]
    ensure_model_rows(entries)
    with legacy_sqlite_engine.begin() as conn:
        assert conn.execute(text("SELECT COUNT(*) FROM `model`")).scalar() == 8

    # 再跑一次（模拟重启）：仍是 8 行，且元数据被更新而不是插出第二行
    ensure_model_rows([{**e, "algo": "Changed"} for e in entries])
    with legacy_sqlite_engine.begin() as conn:
        rows = conn.execute(
            text("SELECT model_name, algo FROM `model` ORDER BY model_name")
        ).fetchall()
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


def test_migrated_column_default_matches_orm(legacy_sqlite_engine):
    """评审要求：迁移后列默认值必须与 models.py 的 CURRENT_TIMESTAMP 一致。

    SQLite 不能改已有列的默认值，所以这里走「按 ORM DDL 重建表」；
    用常量默认值建列的话，之后任何未显式赋值的新行都会落成 1970-01-01。
    """
    _apply_bcnf_migration(legacy_sqlite_engine)
    with legacy_sqlite_engine.begin() as conn:
        for table in LEGACY_DDL:
            dflt = conn.execute(
                text(
                    'SELECT dflt_value FROM pragma_table_info(:t) WHERE name="updated_at"'
                ).bindparams(t=table)
            ).scalar()
            assert "CURRENT_TIMESTAMP" in (dflt or "").upper(), (
                f"{table}.updated_at 的列默认值是 {dflt!r}，与 ORM 的 server_default 不一致"
            )


def test_insert_after_migration_gets_current_time_not_epoch(legacy_sqlite_engine):
    """评审要求的 INSERT 回归：迁移后新写入行拿到当前时间，而不是 1970 常量。"""
    _apply_bcnf_migration(legacy_sqlite_engine)
    stamp = "e" * 40
    with legacy_sqlite_engine.begin() as conn:
        conn.execute(
            text(
                'INSERT INTO "prediction" (commit_hash, model_name, risk_score, '
                "predicted_at, feature_version) VALUES (:h, :m, 0.5, :p, :v)"
            ),
            {"h": stamp, "m": "xgb_v1", "p": "2026-01-01 00:00:00", "v": "v1"},
        )
        got = str(
            conn.execute(
                text('SELECT updated_at FROM "prediction" WHERE commit_hash = :h'),
                {"h": stamp},
            ).scalar()
        )
    year = datetime.now().year
    assert got.startswith(str(year)), f"新行 updated_at={got}，仍是常量默认值而不是当前时间"
    assert "1970" not in got


def test_rebuild_preserves_rows_and_unique_constraint(legacy_sqlite_engine):
    """重建表不能丢数据、也不能丢唯一约束（prediction 的幂等靠它）。"""
    with legacy_sqlite_engine.begin() as conn:
        before = conn.execute(text('SELECT COUNT(*) FROM "prediction"')).scalar()
    _apply_bcnf_migration(legacy_sqlite_engine)
    with legacy_sqlite_engine.begin() as conn:
        after = conn.execute(text('SELECT COUNT(*) FROM "prediction"')).scalar()
        assert after == before == 2, "重建后行数变了"
        assert (
            conn.execute(
                text('SELECT COUNT(*) FROM "commit" WHERE commit_hash = :h'), {"h": "a" * 40}
            ).scalar()
            == 1
        )
    # 唯一约束仍在：同 (commit_hash, model_name) 再插一行必须被拒
    with pytest.raises(Exception) as exc:
        with legacy_sqlite_engine.begin() as conn:
            conn.execute(
                text(
                    'INSERT INTO "prediction" (commit_hash, model_name, risk_score, '
                    "predicted_at, feature_version) VALUES (:h, :m, 0.5, :p, :v)"
                ),
                {"h": "a" * 40, "m": "xgb_v1", "p": "2026-01-01", "v": "v1"},
            )
    assert "UNIQUE" in str(exc.value).upper(), f"唯一约束在重建后丢失：{exc.value}"
