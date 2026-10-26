"""连接配置的拼装契约：分字段 → DSN、显式覆盖、缺字段、测试库切换。

本文件**不连库**，只锁「字段怎么变成 DSN」这一段；真连库的用例在 `test_db.py` /
`test_integration_api.py`（依赖本机 MySQL 测试库）。
"""

from __future__ import annotations

import pytest
from app import config


@pytest.fixture()
def fields(monkeypatch):
    """把连接配置固定成一组已知值，并清掉可能从环境/CI 继承的整段 DSN。"""
    monkeypatch.delenv("DATABASE_URL", raising=False)
    monkeypatch.delenv("TEST_DATABASE_URL", raising=False)
    monkeypatch.setattr(config, "DB_HOST", "127.0.0.1")
    monkeypatch.setattr(config, "DB_PORT", "3306")
    monkeypatch.setattr(config, "DB_USER", "jit")
    monkeypatch.setattr(config, "DB_PASSWORD", "plain")
    monkeypatch.setattr(config, "DB_NAME", "jit_demo")
    monkeypatch.setattr(config, "DB_TEST_NAME", "jit_test")
    monkeypatch.setattr(config, "DB_CHARSET", "utf8mb4")


def test_fields_build_expected_dsn(fields):
    """五项字段拼出的就是可直接给 SQLAlchemy 的 DSN。"""
    assert config.build_database_url() == (
        "mysql+pymysql://jit:plain@127.0.0.1:3306/jit_demo?charset=utf8mb4"
    )


def test_password_with_reserved_chars_is_percent_encoded(fields, monkeypatch):
    """口令里的 @ : / # ? 必须被编码，否则会拼出「连到别的库」的 DSN（这是分字段的核心理由）。"""
    monkeypatch.setattr(config, "DB_PASSWORD", "p@ss:w/rd#1?x")
    assert config.build_database_url() == (
        "mysql+pymysql://jit:p%40ss%3Aw%2Frd%231%3Fx@127.0.0.1:3306/jit_demo?charset=utf8mb4"
    )


def test_user_with_reserved_chars_is_percent_encoded(fields, monkeypatch):
    monkeypatch.setattr(config, "DB_USER", "dev@corp")
    assert "dev%40corp" in config.build_database_url()


def test_empty_password_omits_the_colon(fields, monkeypatch):
    """空口令不写成 `jit:@host`（那是「显式空口令」，部分驱动会拒）。"""
    monkeypatch.setattr(config, "DB_PASSWORD", "")
    assert (
        config.build_database_url() == "mysql+pymysql://jit@127.0.0.1:3306/jit_demo?charset=utf8mb4"
    )


def test_missing_host_or_user_yields_empty(fields, monkeypatch):
    """缺字段返回空串 → 由 `get_engine()` 抛 50000，不猜一个默认账号去连。"""
    monkeypatch.setattr(config, "DB_HOST", "")
    assert config.build_database_url() == ""
    monkeypatch.setattr(config, "DB_HOST", "127.0.0.1")
    monkeypatch.setattr(config, "DB_USER", "")
    assert config.build_database_url() == ""


def test_explicit_database_url_wins_over_fields(fields, monkeypatch):
    """显式 DSN 优先：CI / 容器只注入一行 DATABASE_URL 时，字段被忽略。"""
    monkeypatch.setenv("DATABASE_URL", "mysql+pymysql://root:root@mysql:3307/ci_db?charset=utf8mb4")
    assert config.build_database_url() == (
        "mysql+pymysql://root:root@mysql:3307/ci_db?charset=utf8mb4"
    )


def test_database_name_argument_overrides_default(fields):
    assert config.build_database_url("jit_test").endswith("/jit_test?charset=utf8mb4")


def test_test_database_url_switches_to_test_db(fields):
    """pytest 不再要求手工把 .env 改成 jit_test —— 库名在这里被换掉。"""
    assert config.test_database_url() == (
        "mysql+pymysql://jit:plain@127.0.0.1:3306/jit_test?charset=utf8mb4"
    )


def test_test_database_url_rewrites_explicit_dsn_and_keeps_password(fields, monkeypatch):
    """显式 DSN 模式下只换库名，口令（含编码后的字符）原样保留。"""
    monkeypatch.setenv(
        "DATABASE_URL",
        "mysql+pymysql://jit:s3cr%40t@127.0.0.1:3306/jit_demo?charset=utf8mb4",
    )
    url = config.test_database_url()
    assert url.endswith("/jit_test?charset=utf8mb4")
    assert "s3cr%40t" in url, "口令不能被 render_as_string 打码成 ***"


def test_test_database_url_honours_explicit_test_url(fields, monkeypatch):
    monkeypatch.setenv(
        "TEST_DATABASE_URL", "mysql+pymysql://u:p@127.0.0.1:3306/other?charset=utf8mb4"
    )
    assert config.test_database_url() == (
        "mysql+pymysql://u:p@127.0.0.1:3306/other?charset=utf8mb4"
    )
