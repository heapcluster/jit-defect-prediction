"""建库与连接：python -m app.db init 一条命令建好四张表（design D1）。"""

from __future__ import annotations

import sys

from sqlalchemy import create_engine, inspect
from sqlalchemy.engine import Engine
from sqlalchemy.orm import sessionmaker

from app import config
from app.errors import AppError
from app.models import Base

_engine: Engine | None = None
SessionLocal = sessionmaker(autocommit=False, autoflush=False)


def get_engine() -> Engine:
    global _engine
    if _engine is None:
        if not config.DATABASE_URL:
            raise AppError(50000, "internal error")
        _engine = create_engine(config.DATABASE_URL, pool_pre_ping=True)
        SessionLocal.configure(bind=_engine)
    return _engine


def configure_engine(engine: Engine) -> None:
    """测试用：注入自定义 engine（SQLite 内存库）。"""
    global _engine
    _engine = engine
    SessionLocal.configure(bind=engine)


def init_db() -> None:
    engine = get_engine()
    Base.metadata.create_all(engine)
    _assert_indexes(engine)


def _assert_indexes(engine: Engine) -> None:
    inspector = inspect(engine)
    checks = (
        ("commit", "commit_hash", True),
        ("commit", "committed_at", False),
    )
    for table, column, must_unique in checks:
        matched = [
            idx
            for idx in inspector.get_indexes(table) + _unique_constraints_as_indexes(inspector, table)
            if column in idx["column_names"] and (idx.get("unique", False) is must_unique or not must_unique)
        ]
        if must_unique and not any(idx.get("unique") for idx in matched):
            raise RuntimeError(f"索引自检失败：{table}.{column} 缺少唯一索引")
        if not must_unique and not matched:
            raise RuntimeError(f"索引自检失败：{table}.{column} 缺少普通索引")


def _unique_constraints_as_indexes(inspector, table: str):
    return [
        {"column_names": list(uc["column_names"]), "unique": True, "name": uc["name"]}
        for uc in inspector.get_unique_constraints(table)
    ]


def main(argv: list[str]) -> int:
    if len(argv) != 2 or argv[1] != "init":
        print("用法：python -m app.db init", file=sys.stderr)
        return 2
    try:
        init_db()
    except AppError:
        # 连接配置错误：指出配置项名，不回显密码明文
        print("建库失败：请检查 .env 中的 DATABASE_URL 配置", file=sys.stderr)
        return 1
    print("四张表建表完成：commit / commit_label / commit_feature / prediction")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
