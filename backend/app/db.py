"""建库与连接：python -m app.db init 一条命令建好表（design D1），并应用最小 BCNF 迁移。

BCNF 迁移（change startup-baseline-sync，幂等、可重复执行）：
1. 确保 `model` 表存在；
2. 为四表补 `updated_at` 审计列（已存在则跳过）；
3. 从 `prediction` 去重回填 `model` 表缺失的模型名；
4. 为 `prediction.model_name` / 三表的 `commit_hash` 补外键（已存在则跳过）。
全新库由 `create_all` 直接建成新形态，迁移步骤因「已存在」自动跳过。
"""

from __future__ import annotations

import sys
from datetime import datetime, timezone

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
    _apply_bcnf_migration(engine)


def _apply_bcnf_migration(engine: Engine) -> None:
    inspector = inspect(engine)
    # 1. model 表（全新库 create_all 已建，这里兜底历史库）
    if "model" not in inspector.get_table_names():
        with engine.begin() as conn:
            conn.execute(
                text(
                    """CREATE TABLE IF NOT EXISTS `model` (
                        `model_name` VARCHAR(64) NOT NULL,
                        `version_key` VARCHAR(64) NOT NULL DEFAULT '',
                        `trained_at` DATETIME NULL,
                        `algo` VARCHAR(64) NULL,
                        `feature_version` VARCHAR(32) NULL,
                        `updated_at` DATETIME NOT NULL,
                        PRIMARY KEY (`model_name`)
                    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4"""
                )
            )

    # 2. 四表补 updated_at（MySQL 用 CURRENT_TIMESTAMP 默认值，历史行自动填）
    for table in ("commit", "commit_label", "commit_feature", "prediction"):
        cols = {c["name"] for c in inspector.get_columns(table)}
        if "updated_at" not in cols:
            with engine.begin() as conn:
                conn.execute(
                    text(
                        f"ALTER TABLE `{table}` ADD COLUMN `updated_at` "
                        "DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP"
                    )
                )

    # 3. 从 prediction 去重回填 model 表（仅补缺失的 model_name）
    # 时间函数方言适配：MySQL 用 NOW()，SQLite（仅 preflight 校验用）用 CURRENT_TIMESTAMP
    now_fn = "NOW()" if engine.dialect.name == "mysql" else "CURRENT_TIMESTAMP"
    with engine.begin() as conn:
        conn.execute(
            text(
                f"""INSERT INTO `model` (`model_name`, `version_key`, `trained_at`, `algo`, `feature_version`, `updated_at`)
                   SELECT DISTINCT p.model_name, '', NULL, NULL, NULL, {now_fn}
                   FROM prediction p LEFT JOIN `model` m ON m.model_name = p.model_name
                   WHERE m.model_name IS NULL"""
            )
        )

    # 4. 外键（referenced 列分别为 model PK / commit unique(commit_hash)）
    _add_fk(engine, "prediction", "fk_prediction_model", "model_name", "model", "model_name")
    _add_fk(engine, "prediction", "fk_prediction_commit", "commit_hash", "commit", "commit_hash")
    _add_fk(engine, "commit_feature", "fk_commit_feature_commit", "commit_hash", "commit", "commit_hash")
    _add_fk(engine, "commit_label", "fk_commit_label_commit", "commit_hash", "commit", "commit_hash")


def _add_fk(
    engine: Engine,
    table: str,
    fk_name: str,
    col: str,
    ref_table: str,
    ref_col: str,
) -> None:
    # 仅 MySQL：SQLite 不支持 ALTER ADD FOREIGN KEY，且默认不强制外键
    # （SQLite 的 FK 由 create_all 内联生成，已满足结构要求）
    if engine.dialect.name != "mysql":
        return
    exists = inspect(engine).get_foreign_keys(table)
    if any(fk.get("name") == fk_name for fk in exists):
        return
    with engine.begin() as conn:
        conn.execute(
            text(
                f"ALTER TABLE `{table}` ADD CONSTRAINT `{fk_name}` "
                f"FOREIGN KEY (`{col}`) REFERENCES `{ref_table}` (`{ref_col}`)"
            )
        )


def ensure_model_rows(entries: list[dict]) -> None:
    """load_models 后把当前已加载模型元数据 upsert 进 `model` 表（供 FK 与查询）。

    `entries` 元素形如 {"model_name", "version_key", "algo", "feature_version", "trained_at"}。
    空库首启时 prediction 为空、迁移无法回填，故由启动时显式补齐，保证 FK 不空。
    """
    if not entries:
        return
    engine = get_engine()
    now = datetime.now(timezone.utc).replace(tzinfo=None)
    with engine.begin() as conn:
        for e in entries:
            conn.execute(
                text(
                    """INSERT INTO `model` (`model_name`, `version_key`, `algo`, `feature_version`, `trained_at`, `updated_at`)
                       VALUES (:name, :vk, :algo, :fv, :trained, :now)
                       ON DUPLICATE KEY UPDATE `version_key`=VALUES(`version_key`),
                         `algo`=VALUES(`algo`), `feature_version`=VALUES(`feature_version`),
                         `trained_at`=VALUES(`trained_at`), `updated_at`=VALUES(`updated_at`)"""
                ),
                {
                    "name": e["model_name"],
                    "vk": e.get("version_key") or "",
                    "algo": e.get("algo"),
                    "fv": e.get("feature_version"),
                    "trained": e.get("trained_at"),
                    "now": now,
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
        if not any(cols == tuple(columns) and uniq is must_unique for cols, uniq in entries):
            raise RuntimeError(f"索引自检失败：{table} {list(columns)} unique={must_unique} 未满足")


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
    print("表建表完成：commit / commit_label / commit_feature / prediction / model")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
