"""数据库引擎与会话。"""

from __future__ import annotations

from collections.abc import Iterator
from datetime import datetime

from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

from app import config

_engine: Engine | None = None
SessionLocal = sessionmaker(autocommit=False, autoflush=False, expire_on_commit=False)


def get_engine() -> Engine:
    global _engine
    if _engine is None:
        url = config.DATABASE_URL
        if not url:
            raise RuntimeError("数据库连接未配置")
        _engine = create_engine(url, pool_pre_ping=True, pool_recycle=1800)
        SessionLocal.configure(bind=_engine)
    return _engine


def configure_engine(engine: Engine) -> None:
    global _engine
    _engine = engine
    SessionLocal.configure(bind=engine)


def init_db() -> None:
    from app.models import Base

    Base.metadata.create_all(get_engine())


def get_db() -> Iterator[Session]:
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()


def naive(value: datetime | None) -> datetime | None:
    if value is None:
        return None
    return value.replace(tzinfo=None) if value.tzinfo else value
