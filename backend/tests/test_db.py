"""建表索引自检测试（Issue #73 缺口二：`_assert_indexes` 此前零覆盖）。

`_assert_indexes` 是「建表即校验唯一索引」的唯一防线：`prediction(commit_hash,
model_name)` 的唯一性是 `POST /api/predict` 幂等回落（`IntegrityError` → update）
的前提，自检失守会让幂等静默变成双插。
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import pytest
from sqlalchemy import (
    CHAR,
    Column,
    MetaData,
    String,
    Table,
    UniqueConstraint,
    create_engine,
    text,
)
from sqlalchemy.pool import StaticPool

from app.db import Base, _assert_indexes
from app.errors import AppError
from app.models import Commit


def _new_engine():
    return create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )


def test_index_assertions_pass_on_fresh_schema():
    eng = _new_engine()
    Base.metadata.create_all(eng)
    _assert_indexes(eng)  # 不抛即通过：四条断言（含两条唯一性）全部满足
    # 蒋励 #79 建议：正例也要有可读判据，不只靠「不抛」
    from sqlalchemy import inspect

    insp = inspect(eng)
    # SQLite 方言：唯一约束经 get_unique_constraints 报告（条目无 unique 键，唯一性由约束本身保证）；
    # 普通索引经 get_indexes 报告
    assert ("commit_hash", "model_name") in {
        tuple(c["column_names"]) for c in insp.get_unique_constraints("prediction")
    }
    assert ("commit_hash",) in {tuple(i["column_names"]) for i in insp.get_indexes("prediction")}


def test_index_assertions_raise_when_unique_pair_missing():
    """prediction 缺 (commit_hash, model_name) 唯一约束 → 必须 RuntimeError 且点名该表。"""
    eng = _new_engine()
    Base.metadata.create_all(eng, tables=[Commit.__table__])
    stand_in = MetaData()
    Table(
        "prediction",
        stand_in,
        Column("commit_hash", CHAR(40)),
        Column("model_name", String(64)),
        UniqueConstraint("commit_hash", name="uq_only_hash"),  # 唯一性给错了列组合
    )
    stand_in.create_all(eng)
    with pytest.raises(RuntimeError) as exc:
        _assert_indexes(eng)
    assert "prediction" in str(exc.value)


def test_index_assertions_raise_when_non_unique_index_dropped():
    """prediction(commit_hash) 的普通索引被drop → 第二条断言（must_unique=False）失守。"""
    eng = _new_engine()
    Base.metadata.create_all(eng)
    with eng.begin() as conn:
        conn.execute(text("DROP INDEX ix_prediction_commit_hash"))
    with pytest.raises(RuntimeError) as exc:
        _assert_indexes(eng)
    assert "prediction" in str(exc.value)


# ── 以下补 Sprint 2 报告 §6 第 5 项：`get_engine()` 懒建分支 + CLI `main()` + `__main__` 守卫 ──


def test_get_engine_lazily_builds_from_database_url(tmp_path, monkeypatch, engine):
    """未预配置时 `get_engine()` 按 `DATABASE_URL` 懒建、绑 `SessionLocal`，且只建一次。"""
    from app import db

    original = db._engine
    monkeypatch.setattr(db, "_engine", None)
    monkeypatch.setattr(db.config, "DATABASE_URL", f"sqlite:///{(tmp_path / 'lazy.db').as_posix()}")
    built = None
    try:
        built = db.get_engine()
        assert built is not original
        assert db.get_engine() is built  # 第二次命中缓存，不再新建
        assert db.SessionLocal.kw["bind"] is built
        db.init_db()  # 懒建这条路真能建四张表并过索引自检
        assert (tmp_path / "lazy.db").is_file()
    finally:
        if built is not None:
            built.dispose()
        db.configure_engine(original)  # `_engine` 与 `SessionLocal` 一起还原，不污染后续用例


def test_get_engine_without_database_url_raises_50000(monkeypatch, engine):
    """`DATABASE_URL` 为空 → 50000 且消息是固定文案（fail closed，不回显配置细节）。"""
    from app import db

    original = db._engine
    monkeypatch.setattr(db, "_engine", None)
    monkeypatch.setattr(db.config, "DATABASE_URL", "")
    try:
        with pytest.raises(AppError) as exc:
            db.get_engine()
    finally:
        db.configure_engine(original)
    assert exc.value.code == 50000
    assert exc.value.message == "internal error"


def test_db_cli_covers_usage_config_error_and_success(tmp_path, monkeypatch, engine, capsys):
    """`python -m app.db` 的三条出口：用法错 rc=2、配置错 rc=1、成功 rc=0。"""
    from app import db

    original = db._engine
    try:
        assert db.main(["app.db"]) == 2
        assert "用法：python -m app.db init" in capsys.readouterr().err

        monkeypatch.setattr(db, "_engine", None)
        monkeypatch.setattr(db.config, "DATABASE_URL", "")
        assert db.main(["app.db", "init"]) == 1
        err = capsys.readouterr().err
        assert "DATABASE_URL" in err  # 指路配置项
        assert "internal error" not in err  # 但不把内部消息吐给用户

        monkeypatch.setattr(db, "_engine", None)
        monkeypatch.setattr(db.config, "DATABASE_URL", f"sqlite:///{(tmp_path / 'cli.db').as_posix()}")
        assert db.main(["app.db", "init"]) == 0
        assert "四张表建表完成" in capsys.readouterr().out
        assert (tmp_path / "cli.db").is_file()
    finally:
        db.configure_engine(original)


@pytest.mark.parametrize("module", ["app.db", "app.ingest"])
def test_module_guard_exits_with_usage(module):
    """`python -m <module>`（无参）真走 `__main__` 守卫：退出码 2 + stderr 是用法行。"""
    backend = Path(__file__).resolve().parents[1]
    env = dict(os.environ, PYTHONUTF8="1", DATABASE_URL="sqlite://", API_TOKEN="test-token")
    env.pop("PYTHONPATH", None)
    assert Path(sys.executable).is_file(), f"解释器不可用：{sys.executable}"
    proc = subprocess.run(
        [sys.executable, "-m", module],
        cwd=str(backend), env=env, capture_output=True, text=True, timeout=180, check=False,
    )
    assert proc.returncode == 2, proc.stderr
    assert "用法：" in proc.stderr
