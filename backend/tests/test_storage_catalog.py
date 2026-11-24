# 来源：[AI生成]；尚未人工审核，不作为课程审核完成证据。

import importlib
import importlib.util

from app.errors import register_error_handlers
from app.models import Base
from fastapi import FastAPI
from fastapi.testclient import TestClient

from tests.conftest import HEADERS


def catalog_client():
    assert importlib.util.find_spec("app.api.storage_catalog") is not None, "Storage table catalog is missing"
    app = FastAPI()
    register_error_handlers(app)
    app.include_router(importlib.import_module("app.api.storage_catalog").router)
    return TestClient(app)


def test_catalog_is_the_twelve_real_tables_and_columns():
    with catalog_client() as client:
        response = client.get("/api/storage/tables", headers=HEADERS)
    assert response.status_code == 200
    items = response.json()["data"]["items"]
    assert [item["name"] for item in items] == sorted(Base.metadata.tables)
    assert len(items) == 12
    assert all(item["columns"] == list(Base.metadata.tables[item["name"]].columns.keys()) for item in items)
    commit = next(item for item in items if item["name"] == "commit")
    assert set(commit["filters"]) == {"dataset_id", "start_time", "end_time", "limit"}


def test_catalog_requires_auth():
    with catalog_client() as client:
        response = client.get("/api/storage/tables")
    assert response.status_code == 401
    assert response.json()["code"] == 40100
