"""pytest 公共夹具：使用本机 MySQL 的 jit_test 库。"""

from __future__ import annotations

import os
from pathlib import Path

import pytest

from app import config

config.DATABASE_URL = config.test_database_url()

from app import db as db_module  # noqa: E402
from app.cli import seed_algorithms  # noqa: E402
from app.db import SessionLocal  # noqa: E402
from app.main import app  # noqa: E402
from app.models import Base, User  # noqa: E402
from app.utils import new_id, now  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

TABLES = [
    "prediction", "evaluation_figure", "evaluation", "dataset_commit", "dataset",
    "model_artifact", "model", "job", "commit_feature", "commit",
    "user_page_state", "user_config", "user_session", "user", "algorithm",
]


def _truncate() -> None:
    engine = db_module.get_engine()
    with engine.begin() as connection:
        connection.exec_driver_sql("SET FOREIGN_KEY_CHECKS=0")
        for table in TABLES:
            connection.exec_driver_sql(f"TRUNCATE TABLE `{table}`")
        connection.exec_driver_sql("SET FOREIGN_KEY_CHECKS=1")


@pytest.fixture(scope="session", autouse=True)
def prepare_database():
    engine = db_module.get_engine()
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    with SessionLocal() as session:
        session.commit()
    seed_algorithms()
    yield
    engine.dispose()


@pytest.fixture()
def client():
    _truncate()
    with SessionLocal() as session:
        session.commit()
    seed_algorithms()
    with TestClient(app) as test_client:
        yield test_client


def create_account(username: str, password: str = "pass123", display: str | None = None) -> str:
    with SessionLocal() as session:
        user = User(
            user_id=new_id("user"), username=username, password=password,
            display_name=display or username, status="active", created_at=now(),
        )
        session.add(user)
        session.commit()
        return user.user_id


def login(client: TestClient, username: str, password: str = "pass123") -> None:
    response = client.post("/api/auth/login", json={"username": username, "password": password})
    assert response.status_code == 200, response.text


@pytest.fixture()
def user_client(client):
    create_account("alice", "pass123", "Alice")
    login(client, "alice")
    return client


@pytest.fixture()
def other_client(client):
    create_account("bob", "pass123", "Bob")
    second = TestClient(app)
    login(second, "bob")
    return second
