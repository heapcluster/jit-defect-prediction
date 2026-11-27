"""建库与连接：python -m app.db init 一条命令建好表（design D1）。

12 张表（docs/database/）：任务、数据集、模型、预测与评估图等，直接 `create_all`
建成；已有库的可空列、`job` 链路索引与 `model_figure` 批次主键由幂等升级函数补齐。
"""

from __future__ import annotations

import sys
from datetime import datetime

from sqlalchemy import create_engine, inspect, select, text
from sqlalchemy.engine import Engine
from sqlalchemy.orm import sessionmaker

from app import config
from app.errors import AppError
from app.models import Base, ModelArtifact, ModelFigure

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


_JOB_CHAIN_COLUMNS = (
    ("chain_id", "VARCHAR(36) NOT NULL DEFAULT ''"),
    ("parent_job_ids", "TEXT"),
)

_DATASET_COLUMNS = (
    ("label_source", "VARCHAR(32) NOT NULL DEFAULT 'git_szz'"),
    ("szz_method", "VARCHAR(32)"),
    ("license", "VARCHAR(128)"),
    ("source_note", "TEXT"),
    ("unlabeled_count", "INT NOT NULL DEFAULT 0"),
    ("summary_path", "VARCHAR(512)"),
    ("manifest_path", "VARCHAR(512)"),
    ("quality_report_path", "VARCHAR(512)"),
)


def init_db() -> None:
    engine = get_engine()
    Base.metadata.create_all(engine)
    _ensure_prediction_index(engine)
    _ensure_schema_upgrades(engine)
    _ensure_model_figure_batches(engine)


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


def _ensure_schema_upgrades(engine: Engine) -> None:
    """已存在的库不会随 create_all 获得新列；这里只做幂等的可空列与索引补齐。"""
    inspector = inspect(engine)
    tables = set(inspector.get_table_names())
    if "job" in tables:
        columns = {column["name"] for column in inspector.get_columns("job")}
        with engine.begin() as conn:
            for name, ddl in _JOB_CHAIN_COLUMNS:
                if name not in columns:
                    conn.execute(text(f"ALTER TABLE job ADD COLUMN {name} {ddl}"))
            if "ix_job_chain" not in {index["name"] for index in inspector.get_indexes("job")}:
                conn.execute(text("CREATE INDEX ix_job_chain ON job (chain_id)"))
            conn.execute(text("UPDATE job SET chain_id = job_id WHERE chain_id IS NULL OR chain_id = ''"))
    if "dataset" in tables:
        columns = {column["name"] for column in inspector.get_columns("dataset")}
        with engine.begin() as conn:
            for name, ddl in _DATASET_COLUMNS:
                if name not in columns:
                    conn.execute(text(f"ALTER TABLE dataset ADD COLUMN {name} {ddl}"))


def _ensure_model_figure_batches(engine: Engine) -> None:
    """旧 `(model_name, figure_type)` 主键无法按批次保留图，重建为新主键。"""
    inspector = inspect(engine)
    if "model_figure" not in inspector.get_table_names():
        return
    columns = {column["name"] for column in inspector.get_columns("model_figure")}
    primary = inspector.get_pk_constraint("model_figure").get("constrained_columns") or []
    if {"job_id", "figure_name"} <= columns and "job_id" in primary:
        return
    with engine.begin() as conn:
        rows = conn.execute(text(
            "SELECT model_name, figure_type, title, file_path, generated_at FROM model_figure"
        )).mappings().all()
        if engine.dialect.name == "sqlite":
            conn.execute(text("ALTER TABLE model_figure RENAME TO model_figure_legacy"))
        else:
            conn.execute(text("RENAME TABLE model_figure TO model_figure_legacy"))
        ModelFigure.__table__.create(bind=conn)
        if rows:
            entries = []
            for row in rows:
                generated = row["generated_at"]
                if isinstance(generated, str):
                    generated = datetime.fromisoformat(generated)
                entries.append({
                    "job_id": "",
                    "model_name": row["model_name"],
                    "figure_type": row["figure_type"],
                    "figure_name": f"{row['model_name']}_{row['figure_type']}.png"[:128],
                    "title": row["title"],
                    "file_path": row["file_path"],
                    "testset_ref": None,
                    "generated_at": generated,
                })
            conn.execute(ModelFigure.__table__.insert(), entries)
        conn.execute(text("DROP TABLE model_figure_legacy"))


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
            registered = conn.execute(select(ModelArtifact.artifact_id).where(
                ModelArtifact.model_name == e["model_name"]).with_for_update()).first()
            if registered:
                continue
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
    print("表建表完成：commit / commit_feature / prediction / model / model_figure / job / dataset 等 12 张表")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
