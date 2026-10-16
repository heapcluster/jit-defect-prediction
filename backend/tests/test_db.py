"""建表索引自检测试（Issue #73 缺口二：`_assert_indexes` 此前零覆盖）。

`_assert_indexes` 是「建表即校验唯一索引」的唯一防线：`prediction(commit_hash,
model_name)` 的唯一性是 `POST /api/predict` 幂等回落（`IntegrityError` → update）
的前提，自检失守会让幂等静默变成双插。
"""

from __future__ import annotations

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
