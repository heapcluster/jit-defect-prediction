"""测试公共夹具：本机 MySQL 测试库 jit_test + fixture 决策树模型（design D9）。

所有测试依赖本机 MySQL：连接由 `backend/.env` 的分字段（DB_HOST / DB_USER / DB_PASSWORD …）
或整段 `DATABASE_URL` 提供；库名由 `config.test_database_url()` 自动换成 `DB_TEST_NAME`（默认
jit_test，由仓库 `infra/setup_mysql.py` 一键建好）。代码里不再写死 SQLite 内存库。
"""

from __future__ import annotations

import os
import pickle
import tempfile
from datetime import datetime
from pathlib import Path

import numpy as np
import pytest
from sklearn.tree import DecisionTreeClassifier

MODEL_DIR = Path(tempfile.mkdtemp(prefix="jit-models-"))
os.environ["API_TOKEN"] = "test-token"
os.environ["MODEL_DIR"] = str(MODEL_DIR)
# 连接不在此写死：由 backend/.env 的分字段或 DATABASE_URL 提供，库名自动切到 DB_TEST_NAME。
# 跑 pytest 前请确保测试库已建好（见 infra/setup_mysql.py）。

from app import config, model_registry
from app.db import Base, configure_engine
from app.main import create_app
from app.models import Commit, CommitFeature, CommitLabel, Prediction, RuntimeSetting
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


@pytest.fixture(scope="session")
def engine():
    # 库名由 config.test_database_url() 决定：分字段配置下自动用 DB_TEST_NAME，
    # 不必手工把 .env 改成 jit_test（改错就会把演示库当测试库清空）。
    url = config.test_database_url()
    if not url:
        pytest.fail(
            "未配置数据库连接：请在 backend/.env 填 DB_HOST / DB_USER / DB_PASSWORD"
            "（或整段写 DATABASE_URL），再跑 infra/setup_mysql.py；"
            "见 docs/backend/mysql-setup.md",
            pytrace=False,
        )
    eng = create_engine(url, pool_pre_ping=True)
    # 重建表以匹配当前 models.py（schema 随模型演进；jit_test 为专用测试库，可安全重建）
    with eng.begin() as conn:
        conn.execute(text("SET FOREIGN_KEY_CHECKS=0"))
        Base.metadata.drop_all(eng)
        Base.metadata.create_all(eng)
        conn.execute(text("SET FOREIGN_KEY_CHECKS=1"))
    configure_engine(eng)
    return eng


@pytest.fixture()
def client(engine):
    from app.db import SessionLocal
    from app.services import settings as runtime_settings

    with SessionLocal() as session:
        # BCNF 迁移后四表之间存在外键，需先删子表（prediction/feature/label）再删父表（commit）；
        # runtime_setting 无外键，一并清空，避免上一条用例校准出的阈值串到下一条
        for table in (Prediction, CommitFeature, CommitLabel, Commit, RuntimeSetting):
            session.query(table).delete()
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
                    committed_at=datetime(2026, 8, 3, 9, 0, 0),
                    feature_version="v1",
                    **FEATURE_VALUES,
                )
            )
        session.add(
            Prediction(
                commit_hash=C1,
                model_name="xgb_v1",
                risk_score=0.87320,
                predicted_at=datetime(2026, 9, 1, 8, 0, 0),
                feature_version="v1",
            )
        )
        session.add(
            Prediction(
                commit_hash=C2,
                model_name="xgb_v1",
                risk_score=0.21000,
                predicted_at=datetime(2026, 9, 1, 8, 0, 0),
                feature_version="v1",
            )
        )
        session.commit()
    runtime_settings.reset_cache()
    model_registry.load_models()
    with TestClient(create_app()) as test_client:
        yield test_client
