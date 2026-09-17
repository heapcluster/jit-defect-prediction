"""测试公共夹具：SQLite 内存库 + fixture 决策树模型（design D9）。"""

from __future__ import annotations

import os
import pickle
import tempfile
from datetime import datetime
from pathlib import Path

import numpy as np
import pytest
from sklearn.tree import DecisionTreeClassifier
from sqlalchemy import create_engine
from sqlalchemy.pool import StaticPool

MODEL_DIR = Path(tempfile.mkdtemp(prefix="jit-models-"))
os.environ["API_TOKEN"] = "test-token"
os.environ["DATABASE_URL"] = "sqlite://"
os.environ["MODEL_DIR"] = str(MODEL_DIR)

from fastapi.testclient import TestClient

from app import model_registry
from app.db import Base, configure_engine
from app.main import create_app
from app.models import Commit, CommitFeature, Prediction

HEADERS = {"X-API-Key": "test-token"}

C1 = "a" * 40
C2 = "b" * 40
C3 = "c" * 40
UNKNOWN = "d" * 40

FEATURE_VALUES = {
    "ns": 1.0986, "nd": 1.6094, "nf": 1.9459, "entropy": 1.42,
    "la": -4.2720, "ld": -5.2753, "lt": 7.1136,
    "fix": 1,
    "ndev": 1.3863, "age": 2.5257, "nuc": 0.2513,
    "exp": 5.7683, "rexp": 3.8114, "sexp": 2.8904,
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
# 钉死 mtime 顺序：「默认最新模型」必须确定为 fixture_v2，不依赖文件系统时间精度
os.utime(MODEL_DIR / "fixture_v1.pkl", (1_000_000, 1_000_000))
os.utime(MODEL_DIR / "fixture_v2.pkl", (2_000_000, 2_000_000))


@pytest.fixture(scope="session")
def engine():
    eng = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(eng)
    configure_engine(eng)
    return eng


@pytest.fixture()
def client(engine):
    from app.db import SessionLocal

    with SessionLocal() as session:
        for table in (Prediction, CommitFeature, Commit):
            session.query(table).delete()
        session.add_all(
            [
                Commit(commit_hash=C1, repo_name="activemq", author_name="jdoe",
                       committed_at=datetime(2026, 7, 20, 9, 0, 0), message="AMQ-1 fix", parent_hash=None),
                Commit(commit_hash=C2, repo_name="activemq", author_name="jdoe",
                       committed_at=datetime(2026, 8, 3, 9, 0, 0), message="AMQ-2 fix", parent_hash=None),
                Commit(commit_hash=C3, repo_name="activemq", author_name="jdoe",
                       committed_at=datetime(2026, 8, 10, 9, 0, 0), message="AMQ-3 fix", parent_hash=None),
            ]
        )
        for hash_ in (C1, C2):
            session.add(CommitFeature(commit_hash=hash_, committed_at=datetime(2026, 8, 3, 9, 0, 0),
                                      feature_version="v1", **FEATURE_VALUES))
        session.add(Prediction(commit_hash=C1, model_name="xgb_v1", risk_score=0.87320,
                               predicted_at=datetime(2026, 9, 1, 8, 0, 0), feature_version="v1"))
        session.add(Prediction(commit_hash=C2, model_name="xgb_v1", risk_score=0.21000,
                               predicted_at=datetime(2026, 9, 1, 8, 0, 0), feature_version="v1"))
        session.commit()
    model_registry.load_models()
    with TestClient(create_app()) as test_client:
        yield test_client
