"""SQLAlchemy 模型：四张表逐字对齐契约一 v2 与契约二 §2/§3，并补齐最小 BCNF 化（change startup-baseline-sync）。

BCNF 化要点：
- 新增 `model` 表承载模型元数据（model_name PK），`prediction.model_name` 改为引用它的外键；
- `prediction` / `commit_feature` / `commit_label` 的 `commit_hash` 改为引用 `commit.commit_hash` 的外键；
- 四表统一加 `updated_at` 审计列。
"""

from __future__ import annotations

from sqlalchemy import (
    CHAR,
    DATETIME,
    DECIMAL,
    BigInteger,
    ForeignKey,
    Index,
    Integer,
    SmallInteger,
    String,
    Text,
    UniqueConstraint,
    event,
    text,
)
from sqlalchemy.dialects.mysql import TINYINT
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

# 契约一/二要求 MySQL TINYINT(1)；用 with_variant 在 MySQL 方言下映射为 TINYINT(1)
TINYINT1 = SmallInteger().with_variant(TINYINT(1), "mysql")
# MySQL 自增主键用 BIGINT（契约要求）
ID_TYPE = Integer().with_variant(BigInteger, "mysql")


class Base(DeclarativeBase):
    pass


class Model(Base):
    """模型元数据表（BCNF 化）：prediction.model_name 的外键目标。

    feature_version 与 commit_feature.feature_version 同源；algo / trained_at
    由交付清单/模型文件元信息填充，缺失可为空（不影响预测落库）。
    """

    __tablename__ = "model"

    model_name: Mapped[str] = mapped_column(String(64), primary_key=True)
    version_key: Mapped[str] = mapped_column(String(64), default="")
    trained_at: Mapped[object | None] = mapped_column(DATETIME, nullable=True)
    algo: Mapped[str | None] = mapped_column(String(64), nullable=True)
    feature_version: Mapped[str | None] = mapped_column(String(32), nullable=True)
    updated_at: Mapped[object] = mapped_column(
        DATETIME, nullable=False, server_default=text("CURRENT_TIMESTAMP")
    )


class RuntimeSetting(Base):
    """运行时配置表（change quality-loop）：阈值等「运营参数」，改完即时生效。

    为什么入库而不是留在 `.env`：阈值需要由质量看板按人工标签校准后热更新，
    `.env` 改一次要重启一次，校准就失去意义。
    """

    __tablename__ = "runtime_setting"

    key: Mapped[str] = mapped_column(String(64), primary_key=True)
    value: Mapped[str] = mapped_column(String(255))
    updated_at: Mapped[object] = mapped_column(
        DATETIME, nullable=False, server_default=text("CURRENT_TIMESTAMP")
    )


class Commit(Base):
    __tablename__ = "commit"

    id: Mapped[int] = mapped_column(ID_TYPE, primary_key=True, autoincrement=True)
    repo_name: Mapped[str] = mapped_column(String(64))
    commit_hash: Mapped[str] = mapped_column(CHAR(40), unique=True, index=False)
    author_name: Mapped[str] = mapped_column(String(128))
    author_email: Mapped[str | None] = mapped_column(String(128), nullable=True)
    committed_at: Mapped[object] = mapped_column(DATETIME, index=True)
    message: Mapped[str] = mapped_column(Text)
    parent_hash: Mapped[str | None] = mapped_column(CHAR(40), nullable=True)
    updated_at: Mapped[object] = mapped_column(
        DATETIME, nullable=False, server_default=text("CURRENT_TIMESTAMP")
    )


class CommitLabel(Base):
    __tablename__ = "commit_label"
    __table_args__ = (UniqueConstraint("commit_hash", "label_method", name="uq_label_hash_method"),)

    id: Mapped[int] = mapped_column(ID_TYPE, primary_key=True, autoincrement=True)
    commit_hash: Mapped[str] = mapped_column(CHAR(40), ForeignKey("commit.commit_hash"), index=True)
    is_bug_inducing: Mapped[int] = mapped_column(TINYINT1)
    label_method: Mapped[str] = mapped_column(String(32))
    bug_fix_hash: Mapped[str | None] = mapped_column(CHAR(40), nullable=True)
    labeled_at: Mapped[object] = mapped_column(DATETIME)
    updated_at: Mapped[object] = mapped_column(
        DATETIME, nullable=False, server_default=text("CURRENT_TIMESTAMP")
    )


class CommitFeature(Base):
    __tablename__ = "commit_feature"

    commit_hash: Mapped[str] = mapped_column(
        CHAR(40), ForeignKey("commit.commit_hash"), primary_key=True
    )
    committed_at: Mapped[object] = mapped_column(DATETIME)
    feature_version: Mapped[str] = mapped_column(String(32))
    ns: Mapped[float] = mapped_column(DECIMAL(20, 10))
    nd: Mapped[float] = mapped_column(DECIMAL(20, 10))
    nf: Mapped[float] = mapped_column(DECIMAL(20, 10))
    entropy: Mapped[float] = mapped_column(DECIMAL(20, 10))
    la: Mapped[float] = mapped_column(DECIMAL(20, 10))
    ld: Mapped[float] = mapped_column(DECIMAL(20, 10))
    lt: Mapped[float] = mapped_column(DECIMAL(20, 10))
    fix: Mapped[int] = mapped_column(TINYINT1)
    ndev: Mapped[float] = mapped_column(DECIMAL(20, 10))
    age: Mapped[float] = mapped_column(DECIMAL(20, 10))
    nuc: Mapped[float] = mapped_column(DECIMAL(20, 10))
    exp: Mapped[float] = mapped_column(DECIMAL(20, 10))
    rexp: Mapped[float] = mapped_column(DECIMAL(20, 10))
    sexp: Mapped[float] = mapped_column(DECIMAL(20, 10))
    updated_at: Mapped[object] = mapped_column(
        DATETIME, nullable=False, server_default=text("CURRENT_TIMESTAMP")
    )


class Prediction(Base):
    __tablename__ = "prediction"
    # design D7：predict 幂等「库里只保留最新一行」落进 schema；契约一允许后端自属冗余索引
    __table_args__ = (
        UniqueConstraint("commit_hash", "model_name", name="uq_prediction_hash_model"),
        # 列表/趋势按「某模型 + 风险排序」取数；没有这条复合索引时是全表扫 + filesort
        Index("ix_prediction_model_risk", "model_name", "risk_score"),
    )

    id: Mapped[int] = mapped_column(ID_TYPE, primary_key=True, autoincrement=True)
    commit_hash: Mapped[str] = mapped_column(CHAR(40), ForeignKey("commit.commit_hash"), index=True)
    model_name: Mapped[str] = mapped_column(String(64), ForeignKey("model.model_name"))
    risk_score: Mapped[float] = mapped_column(DECIMAL(6, 5))
    predicted_at: Mapped[object] = mapped_column(DATETIME)
    feature_version: Mapped[str] = mapped_column(String(32))
    updated_at: Mapped[object] = mapped_column(
        DATETIME, nullable=False, server_default=text("CURRENT_TIMESTAMP")
    )


INDEX_ASSERTIONS = (
    ("commit", ("commit_hash",), True),
    ("commit", ("committed_at",), False),
    ("prediction", ("commit_hash", "model_name"), True),
    ("prediction", ("commit_hash",), False),
    # 列表/趋势的取数路径：模型 + 风险分（复核 D7）
    ("prediction", ("model_name", "risk_score"), False),
)


# BCNF 外键完整性兜底：预测落库前确保 `model` 表存在对应 model_name 行。
# 生产由 db.ensure_model_rows 启动时预注册（此处 INSERT IGNORE 幂等 no-op）；
# 测试或历史数据直接写 prediction 时也能保持外键成立，不必逐条手工补 model 行。
# 方言适配：MySQL 用 INSERT IGNORE/NOW()；SQLite（仅单测、默认不强制外键）用 OR IGNORE/CURRENT_TIMESTAMP。
@event.listens_for(Prediction, "before_insert")
def _ensure_model_row(mapper, connection, target) -> None:
    dialect = connection.dialect.name
    if dialect == "mysql":
        connection.execute(
            text(
                "INSERT IGNORE INTO `model` (`model_name`, `version_key`, `updated_at`) "
                "VALUES (:n, '', NOW())"
            ),
            {"n": target.model_name},
        )
    elif dialect == "sqlite":
        connection.execute(
            text(
                "INSERT OR IGNORE INTO `model` (`model_name`, `version_key`, `updated_at`) "
                "VALUES (:n, '', CURRENT_TIMESTAMP)"
            ),
            {"n": target.model_name},
        )
