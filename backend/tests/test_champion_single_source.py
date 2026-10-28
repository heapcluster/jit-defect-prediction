"""「默认模型」只有一个入口（契约三 §17）—— 用临时 SQLite 文件跑，不依赖 MySQL 测试库。

钉三件事：

1. `services.champion.resolve()` 的三步解析（冠军有行 → 冠军；冠军无行 → 表内有行的最新模型；
   表内一行都没有 → 注册表冠军）。
2. 单条预测的默认模型与列表同源：`resolve_model_name(None)` 必须走同一个 `champion.resolve`，
   不得自己再读一遍注册表（否则冠军还没补齐数据时，列表按 A 模型排、predict 按 B 模型打分）。
3. `sync` 的「待预测」判据必须带 `model_name`：只要某提交被**任意**模型预测过就跳过，
   会让其余在线模型永远补不上，与 change `realtime-commit-sync` 的「全模型落库」相反。
"""

from __future__ import annotations

from datetime import UTC, datetime

import pytest
from app import db, model_registry
from app.api import sync as sync_api
from app.models import Prediction
from app.services import champion
from app.services.predict import resolve_model_name
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

H1 = "1" * 40
H2 = "2" * 40
H3 = "3" * 40


def _row(commit_hash: str, model_name: str, risk: float = 0.6) -> Prediction:
    """构造一行 prediction；`predicted_at`/`feature_version` 是 NOT NULL，必须显式给。"""
    return Prediction(
        commit_hash=commit_hash,
        model_name=model_name,
        risk_score=risk,
        predicted_at=datetime.now(UTC).replace(tzinfo=None),
        feature_version="v1",
    )


@pytest.fixture
def session(tmp_path):
    eng = create_engine(f"sqlite:///{(tmp_path / 'champ.db').as_posix()}")
    db.Base.metadata.drop_all(eng)
    db.Base.metadata.create_all(eng)
    original = db._engine
    db.configure_engine(eng)
    local = sessionmaker(bind=eng)
    with local() as s:
        s.add(_row(H1, "lr_v1"))
        s.add(_row(H2, "xgb_v1"))
        s.commit()
        yield s
    db._engine = original
    if original is not None:
        db.SessionLocal.configure(bind=original)
    else:
        db.SessionLocal.kw.pop("bind", None)
    eng.dispose()


def _as_champion(monkeypatch, name):
    """把注册表冠军钉成某个名字（resolve 只认 `champion().name`）。"""
    monkeypatch.setattr(model_registry, "champion", lambda: type("E", (), {"name": name})())


def test_champion_with_rows_wins(session, monkeypatch):
    _as_champion(monkeypatch, "xgb_v1")
    assert champion.resolve(session) == "xgb_v1"


def test_champion_without_rows_degrades_to_model_with_rows(session, monkeypatch):
    """冠军切到 lr_v1 时 H2 看得见；切到从没预测过的 et_v1 时按 version_key 取有行模型。"""
    _as_champion(monkeypatch, "et_v1")
    assert champion.resolve(session) == "xgb_v1", "降级要按 version_key 降序取有行的模型"


def test_empty_table_returns_none_and_predict_falls_back_to_registry(session, monkeypatch):
    """表内一行都没有：读路径不加过滤（None），predict 侧才回退注册表冠军。"""
    session.query(Prediction).delete()
    session.commit()
    _as_champion(monkeypatch, "rf_v1")
    assert champion.resolve(session) is None
    assert resolve_model_name(None) == "rf_v1"


def test_predict_default_is_same_source_as_list(session, monkeypatch):
    """resolve_model_name(None) 必须复用 champion.resolve，而不是各读一遍注册表。"""
    calls: list = []

    def fake_resolve(_session):
        calls.append("hit")
        return "lgbm_v1"

    monkeypatch.setattr(champion, "resolve", fake_resolve)
    assert resolve_model_name(None) == "lgbm_v1"
    assert calls == ["hit"]


def test_predict_default_falls_back_when_no_rows_anywhere(session, monkeypatch):
    monkeypatch.setattr(champion, "resolve", lambda _s: None)
    _as_champion(monkeypatch, "svm_v1")
    assert resolve_model_name(None) == "svm_v1"


def test_explicit_model_name_is_still_validated(session, monkeypatch):
    monkeypatch.setattr(model_registry, "has", lambda name: False)
    with pytest.raises(Exception) as exc:
        resolve_model_name("nope_v9")
    assert getattr(exc.value, "code", None) == 40001


def test_sync_pending_is_model_aware(session, monkeypatch):
    """H1 只有 lr_v1 行、H2 只有 xgb_v1 行：默认模型=lr_v1 时，H2 必须仍算待预测。

    改动前判据不带 model_name（`SELECT commit_hash … distinct`），H2 会被当成已完成，
    于是「先被某个模型预测过的提交」永远不会被补齐到默认模型 —— 全模型落库形同虚设。
    """
    _as_champion(monkeypatch, "lr_v1")
    with db.SessionLocal() as s:
        s.add(_row(H3, "lr_v1", 0.7))
        s.commit()
    pending, truncated = sync_api._unpredicted([H1, H2, H3])
    assert pending == [H2], "只有默认模型无行的提交才该进待预测队列"
    assert truncated is False


def test_sync_pending_explicit_none_keeps_legacy_any_model_semantics(session):
    """传 None = 显式要「任意模型有行即算完成」，与 AUTO 区分开，别把两种语义混掉。"""
    pending, _ = sync_api._unpredicted([H1, H2, H3], model_name=None)
    assert pending == [H3]


def test_sync_pending_limit_truncates_and_reports_more(session):
    """三条都没有 tabnet_v1 行 → 全是待预测；limit 截断时要如实置 truncated。"""
    pending, truncated = sync_api._unpredicted([H1, H2, H3], limit=2, model_name="tabnet_v1")
    assert pending == [H1, H2]
    assert truncated is True, "还有剩余时必须报 truncated，否则「补齐到最新」会静默少补"
