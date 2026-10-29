"""建库与连接：python -m app.db init 一条命令建好表（design D1），并应用最小 BCNF 迁移。

BCNF 迁移（change startup-baseline-sync，幂等、可重复执行）：
1. 确保 `model` 表存在；
2. 为四表补 `updated_at` 审计列（已存在则跳过）；
3. 从 `prediction` 去重回填 `model` 表缺失的模型名；
4. 为 `prediction.model_name` / 三表的 `commit_hash` 补外键（已存在则跳过）。
全新库由 `create_all` 直接建成新形态，迁移步骤因「已存在」自动跳过。
"""

from __future__ import annotations

import logging
import sys
from datetime import UTC, datetime

from sqlalchemy import create_engine, inspect, text
from sqlalchemy.engine import Engine
from sqlalchemy.exc import IntegrityError, OperationalError
from sqlalchemy.orm import sessionmaker

from app import config
from app.errors import AppError
from app.models import Base, Model

_engine: Engine | None = None
SessionLocal = sessionmaker(autocommit=False, autoflush=False)
logger = logging.getLogger("backend.db")


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


def _rebuild_table_for_updated_at(engine: Engine, table_name: str) -> None:
    """非 MySQL 方言补 `updated_at`：按 ORM DDL 重建表，让列默认值与 models.py 一致。

    SQLite 不能修改已存在列的默认值，`ADD COLUMN` 又只接受常量默认值 —— 用常量
    （如 `'1970-01-01 00:00:00'`）建列的话，迁移后新写入的行只要没显式赋值就会落成
    1970，与 `server_default=CURRENT_TIMESTAMP` 的口径不一致。这里走 SQLite 官方推荐的
    重建流程：删旧索引 → 按 ORM DDL 建临时表 → 拷共有列（`updated_at` 由新表默认值填）
    → 删旧表 → 改名。SQLite 的 DDL 是事务性的，整段在一个事务里，失败即整体回滚。

    只在「旧表列是 ORM 列的子集」时重建：出现 ORM 不认识的列就说明这不是本项目的
    历史库形态，宁可不动也不静默丢列。
    """
    from sqlalchemy import MetaData

    table = Base.metadata.tables[table_name]
    legacy = [c["name"] for c in inspect(engine).get_columns(table_name)]
    orm_cols = [c.name for c in table.columns]
    unknown = [c for c in legacy if c not in orm_cols]
    if unknown:
        # 出现 ORM 不认识的列 = 不是本项目的历史库形态：宁可保留旧表也不静默丢列。
        # 退回「常量默认值 + 整表回填」，并如实记下残留（该库上未显式赋值的新行
        # 仍会拿到常量默认值，与 models.py 的 CURRENT_TIMESTAMP 口径不一致）。
        logger.warning(
            "表 %s 含 ORM 未定义的列 %s，跳过重建；改用常量默认值补 updated_at",
            table_name,
            unknown,
        )
        with engine.begin() as conn:
            conn.execute(
                text(
                    f'ALTER TABLE "{table_name}" ADD COLUMN "updated_at" '
                    "DATETIME NOT NULL DEFAULT '1970-01-01 00:00:00'"
                )
            )
            conn.execute(text(f'UPDATE "{table_name}" SET "updated_at" = CURRENT_TIMESTAMP'))
        return
    shared = [c for c in orm_cols if c in legacy]
    cols = ", ".join(f'"{c}"' for c in shared)
    tmp_name = f"{table_name}__mig"
    # 外键目标表必须在同一个 MetaData 里才能解析，故先把全部表复制过去，
    # 再只对目标表改名（不污染 Base.metadata，避免别处 create_all 建出临时表）。
    tmp_meta = MetaData()
    for existing in Base.metadata.sorted_tables:
        existing.to_metadata(tmp_meta)
    tmp = Base.metadata.tables[table_name].to_metadata(tmp_meta, name=tmp_name)
    try:
        with engine.begin() as conn:
            # 旧表索引名与 ORM 规范名相同，先删，否则建临时表时撞名
            for idx in inspect(engine).get_indexes(table_name):
                if idx.get("name"):
                    conn.execute(text(f'DROP INDEX IF EXISTS "{idx["name"]}"'))
            tmp.create(bind=conn)
            conn.execute(
                text(f'INSERT INTO "{tmp_name}" ({cols}) SELECT {cols} FROM "{table_name}"')
            )
            conn.execute(text(f'DROP TABLE "{table_name}"'))
            conn.execute(text(f'ALTER TABLE "{tmp_name}" RENAME TO "{table_name}"'))
    except (IntegrityError, OperationalError) as exc:
        # 旧数据违反当前 ORM 约束（例如某列后来改成 NOT NULL）时不硬失败：
        # 事务已整体回滚（SQLite 的 DDL 是事务性的，索引也随之恢复），
        # 退回「常量默认值 + 整表回填」，并如实记下残留口径差异。
        logger.warning(
            "表 %s 重建失败（%s），退回常量默认值补 updated_at；"
            "该库上未显式赋值的新行会拿到常量默认值",
            table_name,
            exc.__class__.__name__,
        )
        with engine.begin() as conn:
            conn.execute(
                text(
                    f'ALTER TABLE "{table_name}" ADD COLUMN "updated_at" '
                    "DATETIME NOT NULL DEFAULT '1970-01-01 00:00:00'"
                )
            )
            conn.execute(text(f'UPDATE "{table_name}" SET "updated_at" = CURRENT_TIMESTAMP'))


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
    # SQLite 既不接受 ADD COLUMN 带非确定默认值（OperationalError: Cannot add a column
    # with non-constant default），也不能事后修改列默认值 —— 用常量默认值建列的话，
    # 迁移后任何未显式赋该列的新行都会落成 1970-01-01，与 models.py 的
    # server_default=CURRENT_TIMESTAMP 不一致。故 SQLite 走「按 ORM DDL 重建表」。
    for table in ("commit", "commit_label", "commit_feature", "prediction"):
        cols = {c["name"] for c in inspector.get_columns(table)}
        if "updated_at" in cols:
            continue
        if engine.dialect.name == "mysql":
            with engine.begin() as conn:
                conn.execute(
                    text(
                        f"ALTER TABLE `{table}` ADD COLUMN `updated_at` "
                        "DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP"
                    )
                )
        else:
            _rebuild_table_for_updated_at(engine, table)
        inspector = inspect(engine)

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
