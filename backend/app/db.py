"""建库与连接：python -m app.db init 一条命令建好表（design D1）。

5 张表（docs/overview.md「数据库口径」）：`model` / `commit` / `commit_feature` /
`prediction` / `model_figure`，直接 `create_all` 建成；历史库的 7 表 → 5 表迁移
不由本模块承担（数据口径以 docs 为准，现库由仓库根 `infra/schema.sql` 建表、
`data_model/evaluation/out/data_init.sql` 灌入测试数据）。
"""

from __future__ import annotations

import sys

from sqlalchemy import create_engine, inspect, text
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
        url = config.DATABASE_URL
        if not url:
            raise AppError(50000, "internal error")
        _engine = create_engine(url, pool_pre_ping=True)
        SessionLocal.configure(bind=_engine)
    return _engine


def configure_engine(engine: Engine) -> None:
    """测试用：注入自定义 engine（如 MySQL 测试库 jit_test）。"""
    global _engine
    _engine = engine
    SessionLocal.configure(bind=engine)


def init_db() -> None:
    engine = get_engine()
    Base.metadata.create_all(engine)
    _ensure_prediction_index(engine)


def _ensure_prediction_index(engine: Engine) -> None:
    """历史库补 `(model_name, risk_score)` 复合索引。

    `create_all` 只建表不 ALTER，已存在的库不会自动获得新索引；没有它时
    列表/趋势的「某模型 + 风险排序」是全表扫 + filesort。
    """
    inspector = inspect(engine)
    if "prediction" not in inspector.get_table_names():
        return
    if any(
        idx.get("name") == "ix_prediction_model_risk" for idx in inspector.get_indexes("prediction")
    ):
        return
    with engine.begin() as conn:
        conn.execute(
            text("CREATE INDEX ix_prediction_model_risk ON prediction (model_name, risk_score)")
        )


def ensure_model_rows(entries: list[dict]) -> None:
    """load_models 后把当前已加载模型元数据 upsert 进 `model` 表（供 FK 与查询）。

    `entries` 元素形如 {"model_name", "line", "version_key", "algo", "feature_version",
    "trained_at"}。空库首启时 prediction 为空，故由启动时显式补齐，保证 FK 不空。
    """
    if not entries:
        return
    engine = get_engine()
    with engine.begin() as conn:
        for e in entries:
            conn.execute(
                text(
                    """INSERT INTO `model` (`model_name`, `line`, `algo`, `version_key`, `feature_version`, `trained_at`)
                       VALUES (:name, :line, :algo, :vk, :fv, :trained)
                       ON DUPLICATE KEY UPDATE `line`=VALUES(`line`),
                         `algo`=VALUES(`algo`), `version_key`=VALUES(`version_key`),
                         `feature_version`=VALUES(`feature_version`),
                         `trained_at`=VALUES(`trained_at`)"""
                ),
                {
                    "name": e["model_name"],
                    "line": e.get("line") or "expert",
                    "algo": e.get("algo"),
                    "vk": e.get("version_key") or "",
                    "fv": e.get("feature_version"),
                    "trained": e.get("trained_at"),
                },
            )


def _assert_indexes(engine: Engine) -> None:
    from app.models import INDEX_ASSERTIONS

    inspector = inspect(engine)
    for table, columns, must_unique in INDEX_ASSERTIONS:
        entries: list[tuple[tuple[str, ...], bool]] = []
        for idx in inspector.get_indexes(table):
            entries.append((tuple(idx["column_names"]), bool(idx.get("unique"))))
        for uc in inspector.get_unique_constraints(table):
            entries.append((tuple(uc["column_names"]), True))
        # 主键（单列或联合）由 get_pk_constraint 报告，get_indexes 不含它
        pk = inspector.get_pk_constraint(table)
        if pk and pk.get("constrained_columns"):
            entries.append((tuple(pk["constrained_columns"]), True))
        if not any(cols == tuple(columns) and uniq is must_unique for cols, uniq in entries):
            raise RuntimeError(f"索引自检失败：{table} {list(columns)} unique={must_unique} 未满足")


def get_db():
    """FastAPI 依赖注入：每次请求创建新 Session，请求结束时自动关闭。"""
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()


def main(argv: list[str]) -> int:
    if len(argv) != 2 or argv[1] != "init":
        print("用法：python -m app.db init", file=sys.stderr)
        return 2
    try:
        init_db()
    except AppError:
        # 连接配置错误：指出配置项名，不回显密码明文
        print(
            "建库失败：请检查 backend/.env 的数据库连接配置"
            "（DB_HOST / DB_USER / DB_PASSWORD / DB_NAME，或整段 DATABASE_URL）",
            file=sys.stderr,
        )
        return 1
    print("表建表完成：commit / commit_feature / prediction / model / model_figure")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
