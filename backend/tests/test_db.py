"""建表索引自检测试（Issue #73 缺口二：`_assert_indexes` 此前零覆盖）。

`_assert_indexes` 是「建表即校验唯一索引」的唯一防线：`prediction(commit_hash,
model_name)` 的唯一性是 `POST /api/predict` 幂等回落（`IntegrityError` → update）
的前提，自检失守会让幂等静默变成双插。

本文件依赖本机 MySQL 测试库 jit_test（由仓库 infra/setup_mysql.py 建好）：
`_new_engine()` 直接读 config.DATABASE_URL，并在每个用例前 drop/create 表做隔离。
全项目统一 MySQL。
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import pytest
from app import config, db
from app.db import Base, _assert_indexes
from app.errors import AppError
from app.models import Prediction
from sqlalchemy import (
    CHAR,
    Column,
    MetaData,
    String,
    Table,
    UniqueConstraint,
    create_engine,
    inspect,
    text,
)


def _new_engine():
    # 只连本机 MySQL 测试库 jit_test（MUST NOT 碰 jit_demo 演示库）
    url = config.test_database_url()
    if not url:
        pytest.fail("未配置测试数据库连接（config.test_database_url 为空）", pytrace=False)
    eng = create_engine(url, pool_pre_ping=True)
    # 测试隔离：每个用例从干净表开始；先落旧版遗留表，避免 drop_all 被其外键卡住
    with eng.begin() as conn:
        conn.execute(text("SET FOREIGN_KEY_CHECKS=0"))
        conn.execute(text("DROP TABLE IF EXISTS commit_label, runtime_setting"))
        Base.metadata.drop_all(eng)
        Base.metadata.create_all(eng)
        conn.execute(text("SET FOREIGN_KEY_CHECKS=1"))
    return eng


def test_index_assertions_pass_on_fresh_schema():
    eng = _new_engine()
    _assert_indexes(eng)  # 不抛即通过：七条断言（含三条唯一性）全部满足
    # 蒋励 #79 建议：正例也要有可读判据，不只靠「不抛」
    insp = inspect(eng)
    # 联合主键 (commit_hash, model_name) 经 get_pk_constraint 报告；普通索引经 get_indexes 报告
    assert tuple(insp.get_pk_constraint("prediction")["constrained_columns"]) == (
        "commit_hash",
        "model_name",
    )
    indexes = {tuple(i["column_names"]): bool(i.get("unique")) for i in insp.get_indexes("prediction")}
    assert indexes[("model_name", "risk_score")] is False


def test_index_assertions_raise_when_unique_pair_missing():
    """prediction 缺 (commit_hash, model_name) 唯一约束 → 必须 RuntimeError 且点名该表。"""
    eng = _new_engine()
    # 重建一个约束错误的 prediction 表覆盖正确的那张
    Prediction.__table__.drop(eng)
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
    # 还原正确表：必须先 drop 替身表再 create_all —— 表已存在时 create_all 会跳过，
    # 只调 create_all 会把两列的替身表留给后面的用例（曾污染共享 MySQL 测试库，
    # 让 test_integration_api / test_predict_api 整片报索引自检失败）。
    Prediction.__table__.drop(eng, checkfirst=True)
    Base.metadata.create_all(eng)
    _assert_indexes(eng)  # 还原后必须立刻自证，别把坏状态留给下一个用例


def test_index_assertions_raise_when_non_unique_index_dropped():
    """commit(committed_at) 的普通索引被 drop → 断言（must_unique=False）失守。

    不用 prediction 的 ix_prediction_model_risk 测：它同时是 model_name 外键的支撑索引，
    MySQL 不许 drop（1553 needed in a foreign key constraint）。
    """
    eng = _new_engine()
    Base.metadata.create_all(eng)
    with eng.begin() as conn:
        conn.execute(text("DROP INDEX ix_commit_committed_at ON commit"))
    with pytest.raises(RuntimeError) as exc:
        _assert_indexes(eng)
    assert "commit" in str(exc.value)
    # 还原：补回索引并自证，别把缺索引的表留给后续用例
    with eng.begin() as conn:
        conn.execute(text("CREATE INDEX ix_commit_committed_at ON commit (committed_at)"))
    _assert_indexes(eng)


# ── 以下补 Sprint 2 报告 §6 第 5 项：`get_engine()` 懒建分支 + CLI `main()` + `__main__` 守卫 ──


def test_get_engine_lazily_builds_from_database_url(tmp_path, monkeypatch, engine):
    """未预配置时 `get_engine()` 按 `DATABASE_URL` 懒建、绑 `SessionLocal`，且只建一次。"""
    original = db._engine
    monkeypatch.setattr(db, "_engine", None)
    monkeypatch.setattr(db.config, "DATABASE_URL", config.test_database_url())
    built = None
    try:
        built = db.get_engine()
        assert built is not original
        assert db.get_engine() is built  # 第二次命中缓存，不再新建
        assert db.SessionLocal.kw["bind"] is built
        db.init_db()  # 懒建这条路真能建四张表并过索引自检
    finally:
        if built is not None:
            built.dispose()
        db.configure_engine(original)  # `_engine` 与 `SessionLocal` 一起还原，不污染后续用例


def test_get_engine_without_database_url_raises_50000(monkeypatch, engine):
    """`DATABASE_URL` 为空 → 50000 且消息是固定文案（fail closed，不回显配置细节）。"""
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
    original = db._engine
    original_url = config.test_database_url()  # 先存原值：下面两次 monkeypatch 会把它改成 ""
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
        monkeypatch.setattr(db.config, "DATABASE_URL", original_url)
        assert db.main(["app.db", "init"]) == 0
        assert "表建表完成" in capsys.readouterr().out
    finally:
        db.configure_engine(original)


@pytest.mark.parametrize("module", ["app.db"])
def test_module_guard_exits_with_usage(module):
    """`python -m <module>`（无参）真走 `__main__` 守卫：退出码 2 + stderr 是用法行。"""
    backend = Path(__file__).resolve().parents[1]
    env = dict(
        os.environ, PYTHONUTF8="1", DATABASE_URL=db.config.DATABASE_URL, API_TOKEN="test-token"
    )
    env.pop("PYTHONPATH", None)
    assert Path(sys.executable).is_file(), f"解释器不可用：{sys.executable}"
    proc = subprocess.run(
        [sys.executable, "-m", module],
        cwd=str(backend),
        env=env,
        capture_output=True,
        text=True,
        encoding="utf-8",
        timeout=180,
        check=False,
    )
    assert proc.returncode == 2, proc.stderr
    assert "用法：" in proc.stderr
