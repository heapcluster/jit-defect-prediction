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
from datetime import UTC, datetime

from sqlalchemy import create_engine, inspect, text
from sqlalchemy.engine import Engine
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import sessionmaker

from app import config
from app.errors import AppError
from app.models import Base, Model

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
    _ensure_prediction_index(engine)


def _ensure_prediction_index(engine: Engine) -> None:
    """历史库补 `(model_name, risk_score)` 复合索引。

    `create_all` 只建表不 ALTER，已存在的库不会自动获得新索引；没有它时
    列表/趋势的「某模型 + 风险排序」是全表扫 + filesort（838 万行量级明显）。
    """
    inspector = inspect(engine)
    if "prediction" not in inspector.get_table_names():
        return
    if any(
        idx.get("name") == "ix_prediction_model_risk" for idx in inspector.get_indexes("prediction")
    ):
        return
    ddl = "CREATE INDEX ix_prediction_model_risk ON prediction (model_name, risk_score)"
    if engine.dialect.name != "mysql":
        ddl = "CREATE INDEX IF NOT EXISTS ix_prediction_model_risk ON prediction (model_name, risk_score)"
    with engine.begin() as conn:
        conn.execute(text(ddl))


def _apply_bcnf_migration(engine: Engine) -> None:
    inspector = inspect(engine)
    # 1. model 表（全新库 create_all 已建，这里兜底历史库）
    if "model" not in inspector.get_table_names():
        if engine.dialect.name == "mysql":
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
        else:
            # 兜底 DDL 带 ENGINE/CHARSET 是 MySQL 专有，SQLite 会语法错。
            # 非 MySQL 直接用 ORM 生成的建表语句，保证与 models.py 单一定义一致。
            Model.__table__.create(bind=engine)
        inspector = inspect(engine)

    # 2. 四表补 updated_at（MySQL 用 CURRENT_TIMESTAMP 默认值，历史行自动填）
    # SQLite 不接受 ADD COLUMN 带非确定默认值（OperationalError: Cannot add a column
    # with non-constant default），所以那里改成「常量默认值建列 + 整表回填」两步。
    # 标识符引用也按方言分：MySQL 用反引号，SQLite 用双引号（`commit` 在 SQLite 是保留字）。
    for table in ("commit", "commit_label", "commit_feature", "prediction"):
        cols = {c["name"] for c in inspector.get_columns(table)}
        if "updated_at" in cols:
            continue
        ident = f"`{table}`" if engine.dialect.name == "mysql" else f'"{table}"'
        with engine.begin() as conn:
            if engine.dialect.name == "mysql":
                conn.execute(
                    text(
                        f"ALTER TABLE {ident} ADD COLUMN `updated_at` "
                        "DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP"
                    )
                )
            else:
                conn.execute(
                    text(
                        f"ALTER TABLE {ident} ADD COLUMN \"updated_at\" "
                        "DATETIME NOT NULL DEFAULT '1970-01-01 00:00:00'"
                    )
                )
                conn.execute(text(f'UPDATE {ident} SET "updated_at" = CURRENT_TIMESTAMP'))

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
    _add_fk(
        engine, "commit_feature", "fk_commit_feature_commit", "commit_hash", "commit", "commit_hash"
    )
    _add_fk(
        engine, "commit_label", "fk_commit_label_commit", "commit_hash", "commit", "commit_hash"
    )


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
    now = datetime.now(UTC).replace(tzinfo=None)
    # 启动期自检式补表：`model` 表原本只由 init/迁移创建，没跑过 init 的库会让下面的
    # 写入整批失败、又被调用方吞成一行日志（半套元数据、无人察觉）。checkfirst 幂等。
    Model.__table__.create(bind=engine, checkfirst=True)
    # 不用 `ON DUPLICATE KEY UPDATE`：那是 MySQL 专有语法，SQLite 直接
    # 「near "DUPLICATE": syntax error」，而调用方（main 启动）把异常吞成一行日志，
    # 结果是「应用照启、model 表只有迁移回填的那几行」，本地 SQLite 用户无声拿到半套元数据。
    # UPDATE→无行则 INSERT 两种方言都成立；并发撞主键时回落为 UPDATE，保证幂等而非 50000。
    update_sql = text(
        "UPDATE `model` SET `version_key`=:vk, `algo`=:algo, "
        "`feature_version`=:fv, `trained_at`=:trained, `updated_at`=:now "
        "WHERE `model_name`=:name"
    )
    insert_sql = text(
        "INSERT INTO `model` (`model_name`, `version_key`, `algo`, `feature_version`, "
        "`trained_at`, `updated_at`) VALUES (:name, :vk, :algo, :fv, :trained, :now)"
    )
    for e in entries:
        params = {
            "name": e["model_name"],
            "vk": e.get("version_key") or "",
            "algo": e.get("algo"),
            "fv": e.get("feature_version"),
            "trained": e.get("trained_at"),
            "now": now,
        }
        try:
            with engine.begin() as conn:
                if conn.execute(update_sql, params).rowcount == 0:
                    conn.execute(insert_sql, params)
        except IntegrityError:
            with engine.begin() as conn:
                conn.execute(update_sql, params)


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
    print("表建表完成：commit / commit_label / commit_feature / prediction / model")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
