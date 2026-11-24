"""SQLAlchemy 模型：逐字对齐 docs/database（12 张表）与仓库根 infra/schema.sql。

口径（docs/database/README.md §0 表清单）：
- 现有 5 表：`commit_label` 并入 `commit_feature.is_bug_inducing`（可空）+ `labeled_at`（审计，不对外）；
- 重构新增 7 表：`user` / `user_config` / `job` / `algorithm` / `model_artifact` / `dataset` / `dataset_commit`，
  契约见 docs/database/ 同名文档；本轮只落表定义，业务服务押代码波次；
- `runtime_setting` 删除的历史口径由 `user_config` 取代：阈值/默认模型权威落库，`.env` 仅出厂默认；
- 删除 `commit` / `prediction` / `model_figure` 的自增 `id`，改 `commit_hash` / 联合主键；
- 各表不再保留 `updated_at` 审计列（`user_config.updated_at` 为配置语义必需，例外）。
"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import (
    BIGINT,
    CHAR,
    DATETIME,
    DECIMAL,
    ForeignKey,
    Index,
    Integer,
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
    model_version: Mapped[str | None] = mapped_column(String(64), nullable=True)
    feature_version: Mapped[str | None] = mapped_column(String(32), nullable=True)


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


class User(Base):
    """系统用户（非提交作者）；预置 global 行作为无登录上下文的配置归属。"""

    __tablename__ = "user"

    user_id: Mapped[str] = mapped_column(String(36), primary_key=True)
    display_name: Mapped[str] = mapped_column(String(64))
    role: Mapped[str] = mapped_column(String(16), nullable=False, default="member")
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="active")
    created_at: Mapped[object] = mapped_column(DATETIME)


class UserConfig(Base):
    """用户级键值配置；阈值/默认模型/默认数据集/默认 XAI/指标勾选的唯一权威来源。"""

    __tablename__ = "user_config"

    user_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("user.user_id"), primary_key=True
    )
    config_key: Mapped[str] = mapped_column(String(64), primary_key=True)
    value_json: Mapped[str] = mapped_column(Text)
    value_type: Mapped[str] = mapped_column(String(16))
    updated_at: Mapped[object] = mapped_column(DATETIME)


class Job(Base):
    """统一任务表：collect/clean/train/predict_batch/evaluate/explain 五态生命周期。"""

    __tablename__ = "job"
    __table_args__ = (Index("ix_job_kind_status", "kind", "status"),)

    job_id: Mapped[str] = mapped_column(String(36), primary_key=True)
    kind: Mapped[str] = mapped_column(String(16))
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="queued")
    params_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    total: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    done: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    current_item: Mapped[str | None] = mapped_column(String(64), nullable=True)
    started_at: Mapped[object | None] = mapped_column(DATETIME, nullable=True)
    finished_at: Mapped[object | None] = mapped_column(DATETIME, nullable=True)
    error_log: Mapped[str | None] = mapped_column(Text, nullable=True)
    retry_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    output_ref_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[object] = mapped_column(DATETIME)


class Algorithm(Base):
    """算法库：训练表单与超参校验的元数据单源；family 供解释兼容矩阵复用。"""

    __tablename__ = "algorithm"

    line: Mapped[str] = mapped_column(String(16), primary_key=True)
    algo: Mapped[str] = mapped_column(String(64), primary_key=True)
    family: Mapped[str] = mapped_column(String(32))
    hyperparams_json: Mapped[str] = mapped_column(Text)
    enabled: Mapped[int] = mapped_column(TINYINT1, nullable=False, default=1)
    description: Mapped[str | None] = mapped_column(String(255), nullable=True)


class ModelArtifact(Base):
    """模型工件登记：模型名单唯一登记源，model 行由其派生；加载前校验 checksum。"""

    __tablename__ = "model_artifact"
    __table_args__ = (
        Index("uk_artifact_model", "model_name", unique=True),
        Index("ix_artifact_line", "line"),
    )

    artifact_id: Mapped[str] = mapped_column(String(36), primary_key=True)
    model_name: Mapped[str] = mapped_column(String(64), ForeignKey("model.model_name"))
    line: Mapped[str] = mapped_column(String(16))
    algo: Mapped[str | None] = mapped_column(String(64), nullable=True)
    version_key: Mapped[str] = mapped_column(String(64), nullable=False, default="")
    weight_path: Mapped[str] = mapped_column(String(255))
    checksum_sha256: Mapped[str] = mapped_column(CHAR(64))
    size_bytes: Mapped[int] = mapped_column(BIGINT, nullable=False, default=0)
    feature_version: Mapped[str | None] = mapped_column(String(32), nullable=True)
    train_job_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("job.job_id"), nullable=True
    )
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="available")
    trained_at: Mapped[object | None] = mapped_column(DATETIME, nullable=True)
    created_at: Mapped[object] = mapped_column(DATETIME)


class Dataset(Base):
    """数据集元数据：收集/清洗产出的版本化输入；一期单版本，多版本押二期。"""

    __tablename__ = "dataset"

    dataset_id: Mapped[str] = mapped_column(String(36), primary_key=True)
    name: Mapped[str] = mapped_column(String(128))
    source_type: Mapped[str] = mapped_column(String(16), nullable=False, default="git_repo")
    source_url: Mapped[str | None] = mapped_column(String(512), nullable=True)
    repo_name: Mapped[str | None] = mapped_column(String(128), nullable=True)
    repo_source: Mapped[str] = mapped_column(String(255), default="")
    branch: Mapped[str | None] = mapped_column(String(128), nullable=True)
    head_hash: Mapped[str | None] = mapped_column(CHAR(40), nullable=True)
    time_start: Mapped[object | None] = mapped_column(DATETIME, nullable=True)
    time_end: Mapped[object | None] = mapped_column(DATETIME, nullable=True)
    mode: Mapped[str] = mapped_column(String(16), nullable=False, default="full")
    sample_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    pos_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    neg_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="collecting")
    job_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("job.job_id"), nullable=True
    )
    created_at: Mapped[object] = mapped_column(DATETIME)


class DatasetCommit(Base):
    """数据集的已打标二维表成员行；联合主键保证同一数据集内按提交幂等。"""

    __tablename__ = "dataset_commit"

    dataset_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("dataset.dataset_id"), primary_key=True
    )
    commit_hash: Mapped[str] = mapped_column(
        CHAR(40), ForeignKey("commit.commit_hash"), primary_key=True
    )
    repo_name: Mapped[str | None] = mapped_column(String(128), nullable=True)
    repo_url: Mapped[str | None] = mapped_column(String(512), nullable=True)
    author_name: Mapped[str | None] = mapped_column(String(128), nullable=True)
    author_email: Mapped[str | None] = mapped_column(String(128), nullable=True)
    committed_at: Mapped[object | None] = mapped_column(DATETIME, nullable=True)
    message: Mapped[str | None] = mapped_column(Text, nullable=True)
    parent_hash: Mapped[str | None] = mapped_column(CHAR(40), nullable=True)
    is_bug_inducing: Mapped[int | None] = mapped_column(Integer, nullable=True)
    label_method: Mapped[str | None] = mapped_column(String(32), nullable=True)
    label_source: Mapped[str] = mapped_column(String(32), nullable=False, default="git_szz")
    labeled_at: Mapped[object | None] = mapped_column(DATETIME, nullable=True)
    fix_commit_hash: Mapped[str | None] = mapped_column(CHAR(40), nullable=True)
    source_type: Mapped[str] = mapped_column(String(16), nullable=False, default="git_repo")
    row_no: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    created_at: Mapped[object] = mapped_column(DATETIME, default=datetime.utcnow)


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
    # 重构新增 7 表（契约见 docs/database/）
    ("user", ("user_id",), True),
    ("user_config", ("user_id", "config_key"), True),
    ("job", ("job_id",), True),
    ("job", ("kind", "status"), False),
    ("algorithm", ("line", "algo"), True),
    ("model_artifact", ("artifact_id",), True),
    ("model_artifact", ("model_name",), True),
    ("model_artifact", ("line",), False),
    ("dataset", ("dataset_id",), True),
    ("dataset_commit", ("dataset_id", "commit_hash"), True),
)
