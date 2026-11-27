# === AI 辅助说明 ===
# 本文件为测试夹具配置，不产生测试用例
# [AI生成]：0 条
# [AI生成-人工修改]：0 条（夹具逻辑由 AI 生成骨架、人工调整）
# [手写]：0 条
# 使用工具：原始生成记录未归档（标注依据代码特征判断，作者于 2026-11-17 确认）
# 提示词见：docs/README.md

"""测试公共夹具：本机 MySQL 测试库 jit_test + fixture 决策树模型（design D9）。

所有测试依赖本机 MySQL：连接由 `backend/.env` 的分字段（DB_HOST / DB_USER / DB_PASSWORD …）
或整段 `DATABASE_URL` 提供；库名由 `config.test_database_url()` 自动换成 `DB_TEST_NAME`（默认
jit_test，由仓库 `infra/setup_mysql.py` 一键建好）。
"""

from __future__ import annotations

import os
import pickle
import tempfile
from datetime import datetime
from pathlib import Path

# CLI 子进程与进程内 mock 共用同一确定性抽取器，避免 parity 测试漂移。
_FIXTURES = Path(__file__).parent / "fixtures"
FAKE_EXTRACTOR = _FIXTURES / "fake_feature_extractor.py"
import sys as _sys

if str(_FIXTURES) not in _sys.path:
    _sys.path.insert(0, str(_FIXTURES))

import numpy as np
import pytest
from fake_feature_extractor import _fake_features  # noqa: E402
from sklearn.tree import DecisionTreeClassifier

MODEL_DIR = Path(tempfile.mkdtemp(prefix="jit-models-"))
os.environ["API_TOKEN"] = "test-token"
os.environ["MODEL_DIR"] = str(MODEL_DIR)
# 训练/预测从"绑定仓库"现算特征；测试用假仓库路径，实际抽取被全局 mock 覆盖。
TEST_REPO = Path(tempfile.mkdtemp(prefix="jit-repo-"))
os.environ["SOURCE_REPO"] = str(TEST_REPO)
# 连接不在此写死：由 backend/.env 的分字段或 DATABASE_URL 提供，库名自动切到 DB_TEST_NAME。
# 跑 pytest 前请确保测试库已建好（见 infra/setup_mysql.py）。

from app import config, model_registry
from app.db import Base, configure_engine
from app.main import create_app
from app.models import Commit, CommitFeature, Model, Prediction
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text

HEADERS = {"X-API-Key": "test-token"}

C1 = "a" * 40
C2 = "b" * 40
C3 = "c" * 40
UNKNOWN = "d" * 40

FEATURE_VALUES = {
    "ns": 1.0986,
    "nd": 1.6094,
    "nf": 1.9459,
    "entropy": 1.42,
    "la": -4.2720,
    "ld": -5.2753,
    "lt": 7.1136,
    "fix": 1,
    "ndev": 1.3863,
    "age": 2.5257,
    "nuc": 0.2513,
    "exp": 5.7683,
    "rexp": 3.8114,
    "sexp": 2.8904,
}


def _make_pickle(name: str) -> None:
    rng = np.random.RandomState(7)
    X = rng.rand(60, 14)
    y = (X[:, 3] > 0.5).astype(int)
    model = DecisionTreeClassifier(max_depth=3, random_state=7).fit(X, y)
    with open(MODEL_DIR / f"{name}.pkl", "wb") as fh:
        pickle.dump(model, fh)


_make_pickle("fixture_v1")
_make_pickle("fixture_v2")
(MODEL_DIR / "feature_order.txt").write_text(
    "[models]\nfixture_v1.pkl\nfixture_v2.pkl\n[feature_order]\n"
    + "\n".join(f"{i}. {name}" for i, name in enumerate(FEATURE_VALUES, 1))
    + "\n",
    encoding="utf-8",
)
# 钉死 mtime 顺序：「默认最新模型」必须确定为 fixture_v2，不依赖文件系统时间精度
os.utime(MODEL_DIR / "fixture_v1.pkl", (1_000_000, 1_000_000))
os.utime(MODEL_DIR / "fixture_v2.pkl", (2_000_000, 2_000_000))


@pytest.fixture(autouse=True)
def _mock_feature_extraction(request, monkeypatch):
    """测试用假提交无法现算真实特征，统一 mock 为按 hash 派生的确定性 14 维。

    测试模块可用 `@pytest.mark.no_feature_mock` 关闭（用于 feature_source 自身单测）。
    """
    if "no_feature_mock" in request.keywords:
        return
    from app import feature_source

    def fake_extract(commit_hash, repo=None):
        values = _fake_features(commit_hash)
        return {
            "commit_hash": commit_hash,
            "repo_name": "fixture",
            "author_name": "jdoe",
            "author_email": "",
            "committed_at": "2026-01-01T00:00:00Z",
            "message": "fixture",
            "parent_hash": None,
            "feature_version": "v1",
            "features": values,
            "vector": [values[name] for name in FEATURE_VALUES],
        }

    def fake_extract_many(commit_hashes, repo=None):
        return [{"commit_hash": h, **_fake_features(h)} for h in commit_hashes]

    monkeypatch.setattr(feature_source, "extract", fake_extract)
    monkeypatch.setattr(feature_source, "extract_many", fake_extract_many)


@pytest.fixture(scope="session")
def engine():
    # 库名由 config.test_database_url() 决定：分字段配置下自动用 DB_TEST_NAME，
    # 不必手工把 .env 改成 jit_test（改错就会把演示库当测试库清空）。
    url = config.test_database_url()
    if not url:
        pytest.fail(
            "未配置数据库连接：请在 backend/.env 填 DB_HOST / DB_USER / DB_PASSWORD"
            "（或整段写 DATABASE_URL），再跑 infra/setup_mysql.py",
            pytrace=False,
        )
    eng = create_engine(url, pool_pre_ping=True)
    # 重建表以匹配当前 models.py（schema 随模型演进；jit_test 为专用测试库，可安全重建）。
    # 先落旧版遗留表（commit_label / runtime_setting 已随口径下线），否则 drop_all 被其外键卡住。
    with eng.begin() as conn:
        conn.execute(text("SET FOREIGN_KEY_CHECKS=0"))
        conn.execute(text("DROP TABLE IF EXISTS commit_label, runtime_setting"))
        Base.metadata.drop_all(eng)
        Base.metadata.create_all(eng)
        conn.execute(text("SET FOREIGN_KEY_CHECKS=1"))
    configure_engine(eng)
    return eng


@pytest.fixture()
def client(engine):
    from app.db import SessionLocal

    with SessionLocal() as session:
        for table in reversed(Base.metadata.sorted_tables):
            session.execute(table.delete())
        session.add_all(
            [
                Model(model_name="fixture_v1", line="expert"),
                Model(model_name="fixture_v2", line="expert"),
            ]
        )
        session.add_all(
            [
                Commit(
                    commit_hash=C1,
                    repo_name="camel",
                    author_name="jdoe",
                    committed_at=datetime(2026, 7, 20, 9, 0, 0),
                    message="CAMEL-1 fix",
                    parent_hash=None,
                ),
                Commit(
                    commit_hash=C2,
                    repo_name="camel",
                    author_name="jdoe",
                    committed_at=datetime(2026, 8, 3, 9, 0, 0),
                    message="CAMEL-2 fix",
                    parent_hash=None,
                ),
                Commit(
                    commit_hash=C3,
                    repo_name="camel",
                    author_name="jdoe",
                    committed_at=datetime(2026, 8, 10, 9, 0, 0),
                    message="CAMEL-3 fix",
                    parent_hash=None,
                ),
            ]
        )
        for hash_ in (C1, C2):
            session.add(
                CommitFeature(
                    commit_hash=hash_,
                    feature_version="v1",
                    is_test=1,
                    is_bug_inducing=1 if hash_ == C1 else 0,
                    **FEATURE_VALUES,
                )
            )
        session.add(
            Prediction(
                commit_hash=C1,
                model_name="fixture_v2",
                risk_score=0.87320,
                predicted_at=datetime(2026, 9, 1, 8, 0, 0),
            )
        )
        session.add(
            Prediction(
                commit_hash=C2,
                model_name="fixture_v2",
                risk_score=0.21000,
                predicted_at=datetime(2026, 9, 1, 8, 0, 0),
            )
        )
        session.commit()
    model_registry.load_models()
    with TestClient(create_app()) as test_client:
        yield test_client


_DB_FIXTURES = {"client", "engine", "integration_db", "populated_api"}


def pytest_collection_modifyitems(config, items):
    """按是否请求 DB 夹具自动分层：unit 不连库，integration 连 jit_test。

    课程口径要求「纯函数测试不依赖数据库」；显式写 300 条 marker 易漏，按夹具自动判定。
    直接连库、不走夹具的模块（如 test_db.py）在文件内自行 `pytestmark` 声明。
    """
    for item in items:
        if item.get_closest_marker("integration") is not None:
            continue
        if _DB_FIXTURES.intersection(getattr(item, "fixturenames", ())):
            item.add_marker(pytest.mark.integration)
        else:
            item.add_marker(pytest.mark.unit)
