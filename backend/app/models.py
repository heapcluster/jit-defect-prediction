"""SQLAlchemy 模型：逐字对齐契约一 v2 与契约二 §2/§3，并补齐最小 BCNF 化（change startup-baseline-sync）。

BCNF 化要点：
- 新增 `model` 表承载模型元数据（model_name PK），`prediction.model_name` 改为引用它的外键；
- `prediction` / `commit_feature` / `commit_label` 的 `commit_hash` 改为引用 `commit.commit_hash` 的外键；
- 各表统一加 `updated_at` 审计列。
- 测试集评估看板：`model.line`、`commit_feature.is_test`、新增 `model_figure`（change 见 docs/database）。
"""

from __future__ import annotations

from sqlalchemy import (
    CHAR,
    DATETIME,
    DECIMAL,
    BigInteger,
    ForeignKey,
    Index,
    String,
    Text,
    UniqueConstraint,
    event,
    text,
)
from sqlalchemy.dialects.mysql import TINYINT
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

# 本项目只支持 MySQL 8.0：TINYINT(1) / BIGINT 直接使用，不再做方言变体
TINYINT1 = TINYINT(1)
# MySQL 自增主键用 BIGINT（契约要求）
ID_TYPE = BigInteger


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
    line: Mapped[str] = mapped_column(
        String(16), nullable=False, default="expert", server_default=text("'expert'"), index=True
    )
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
    __table_args__ = (
        UniqueConstraint("commit_hash", "label_method", name="uq_label_hash_method"),
        # 质量视图按标签口径过滤（manual / szz），没有这条索引时每次都全表扫；
        # 唯一约束前缀是 commit_hash，帮不到「只按 label_method 筛」的查询
        Index("ix_commit_label_label_method", "label_method"),
    )

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
    is_test: Mapped[int] = mapped_column(
        TINYINT1, nullable=False, default=0, server_default=text("0"), index=True
    )
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


class ModelFigure(Base):
    """模型性能图索引：后端据它列出某模型有哪些图，前端拿 file_path 渲染。"""

    __tablename__ = "model_figure"
    __table_args__ = (UniqueConstraint("model_name", "figure_type", name="uq_model_figure"),)

    id: Mapped[int] = mapped_column(ID_TYPE, primary_key=True, autoincrement=True)
    model_name: Mapped[str] = mapped_column(
        String(64), ForeignKey("model.model_name"), index=True
    )
    figure_type: Mapped[str] = mapped_column(String(32))
    title: Mapped[str] = mapped_column(String(128))
    file_path: Mapped[str] = mapped_column(String(255))
    generated_at: Mapped[object] = mapped_column(DATETIME)
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
    # 测试集评估看板：检验集筛选 + 四线分组 + 图索引
    ("commit_feature", ("is_test",), False),
    ("model", ("line",), False),
    ("model_figure", ("model_name",), False),
    ("model_figure", ("model_name", "figure_type"), True),
)


# BCNF 外键完整性兜底：预测落库前确保 `model` 表存在对应 model_name 行。
# 生产由 db.ensure_model_rows 启动时预注册（此处 INSERT IGNORE 幂等 no-op）；
# 测试或历史数据直接写 prediction 时也能保持外键成立，不必逐条手工补 model 行。
@event.listens_for(Prediction, "before_insert")
def _ensure_model_row(mapper, connection, target) -> None:
    connection.execute(
        text(
            "INSERT IGNORE INTO `model` (`model_name`, `version_key`, `updated_at`) "
            "VALUES (:n, '', NOW())"
        ),
        {"n": target.model_name},
    )
