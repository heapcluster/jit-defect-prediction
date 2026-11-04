"""SQLAlchemy 模型：逐字对齐 docs/database（5 张表）与 data_model/evaluation/out/schema.sql。

口径（docs/overview.md「数据库口径（5 张表）」）：
- `commit_label` 并入 `commit_feature.is_bug_inducing`（可空）+ `labeled_at`（审计，不对外）；
- `runtime_setting` 删除：阈值写死 `.env`，默认模型统一 `version_key` 最大者；
- 删除 `commit` / `prediction` / `model_figure` 的自增 `id`，改 `commit_hash` / 联合主键；
- 各表不再保留 `updated_at` 审计列。
"""

from __future__ import annotations

from sqlalchemy import (
    CHAR,
    DATETIME,
    DECIMAL,
    ForeignKey,
    Index,
    String,
    Text,
)
from sqlalchemy.dialects.mysql import TINYINT
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

# 本项目只支持 MySQL 8.0：TINYINT(1) 直接使用，不做方言变体
TINYINT1 = TINYINT(1)


class Base(DeclarativeBase):
    pass


class Model(Base):
    """模型注册表：`model_name` 主键，`line` 分组（架构 → 模型级联选择器数据源）。"""

    __tablename__ = "model"

    model_name: Mapped[str] = mapped_column(String(64), primary_key=True)
    line: Mapped[str] = mapped_column(String(16), nullable=False, default="expert", index=True)
    algo: Mapped[str | None] = mapped_column(String(64), nullable=True)
    version_key: Mapped[str] = mapped_column(String(64), nullable=False, default="")
    trained_at: Mapped[object | None] = mapped_column(DATETIME, nullable=True)
    feature_version: Mapped[str | None] = mapped_column(String(32), nullable=True)


class Commit(Base):
    __tablename__ = "commit"

    commit_hash: Mapped[str] = mapped_column(CHAR(40), primary_key=True)
    repo_name: Mapped[str] = mapped_column(String(64))
    author_name: Mapped[str] = mapped_column(String(128))
    author_email: Mapped[str | None] = mapped_column(String(128), nullable=True)
    committed_at: Mapped[object] = mapped_column(DATETIME, index=True)
    message: Mapped[str] = mapped_column(Text)
    parent_hash: Mapped[str | None] = mapped_column(CHAR(40), nullable=True)


class CommitFeature(Base):
    __tablename__ = "commit_feature"

    commit_hash: Mapped[str] = mapped_column(
        CHAR(40), ForeignKey("commit.commit_hash"), primary_key=True
    )
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
    is_test: Mapped[int] = mapped_column(TINYINT1, nullable=False, default=0, index=True)
    # SZZ 真标签：1 = 引入缺陷 / 0 = 非缺陷 / NULL = 未打标（库内外同名）
    is_bug_inducing: Mapped[int | None] = mapped_column(TINYINT1, nullable=True)
    labeled_at: Mapped[object | None] = mapped_column(DATETIME, nullable=True)


class Prediction(Base):
    __tablename__ = "prediction"
    __table_args__ = (
        # 列表/趋势按「某模型 + 风险排序」取数；没有这条复合索引时是全表扫 + filesort
        Index("ix_prediction_model_risk", "model_name", "risk_score"),
    )

    commit_hash: Mapped[str] = mapped_column(
        CHAR(40), ForeignKey("commit.commit_hash"), primary_key=True
    )
    model_name: Mapped[str] = mapped_column(
        String(64), ForeignKey("model.model_name"), primary_key=True
    )
    risk_score: Mapped[float] = mapped_column(DECIMAL(6, 5))
    predicted_at: Mapped[object] = mapped_column(DATETIME)


class ModelFigure(Base):
    """模型性能图索引：`(model_name, figure_type)` 联合主键。"""

    __tablename__ = "model_figure"

    model_name: Mapped[str] = mapped_column(
        String(64), ForeignKey("model.model_name"), primary_key=True
    )
    figure_type: Mapped[str] = mapped_column(String(32), primary_key=True)
    title: Mapped[str] = mapped_column(String(128))
    file_path: Mapped[str] = mapped_column(String(255))
    generated_at: Mapped[object] = mapped_column(DATETIME)


INDEX_ASSERTIONS = (
    ("commit", ("commit_hash",), True),
    ("commit", ("committed_at",), False),
    ("prediction", ("commit_hash", "model_name"), True),
    # 列表/趋势的取数路径：模型 + 风险分
    ("prediction", ("model_name", "risk_score"), False),
    # 测试集评估看板：检验集筛选 + 四线分组 + 图索引
    ("commit_feature", ("is_test",), False),
    ("model", ("line",), False),
    ("model_figure", ("model_name", "figure_type"), True),
)
