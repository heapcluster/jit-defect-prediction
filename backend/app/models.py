"""ORM 模型：与 infra/schema.sql 的 15 张表一一对应。"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import (
    JSON,
    BigInteger,
    CHAR,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class User(Base):
    __tablename__ = "user"
    user_id: Mapped[str] = mapped_column(CHAR(36), primary_key=True)
    username: Mapped[str] = mapped_column(String(64, collation="utf8mb4_bin"), unique=True, nullable=False)
    password: Mapped[str] = mapped_column(String(128, collation="utf8mb4_bin"), nullable=False)
    display_name: Mapped[str] = mapped_column(String(64), nullable=False)
    status: Mapped[str] = mapped_column(String(16), default="active", nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    last_login_at: Mapped[datetime | None] = mapped_column(DateTime)


class UserSession(Base):
    __tablename__ = "user_session"
    session_id: Mapped[str] = mapped_column(CHAR(64), primary_key=True)
    user_id: Mapped[str] = mapped_column(
        CHAR(36), ForeignKey("user.user_id", ondelete="CASCADE"), nullable=False, index=True
    )
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    last_seen_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, index=True)


class UserConfig(Base):
    __tablename__ = "user_config"
    user_id: Mapped[str] = mapped_column(
        CHAR(36), ForeignKey("user.user_id"), primary_key=True
    )
    config_key: Mapped[str] = mapped_column(String(64), primary_key=True)
    value_json: Mapped[str] = mapped_column(Text, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)


class UserPageState(Base):
    __tablename__ = "user_page_state"
    user_id: Mapped[str] = mapped_column(
        CHAR(36), ForeignKey("user.user_id"), primary_key=True
    )
    page: Mapped[str] = mapped_column(String(16), primary_key=True)
    state_json: Mapped[str] = mapped_column(Text, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)


class Commit(Base):
    __tablename__ = "commit"
    commit_id: Mapped[str] = mapped_column(CHAR(36), primary_key=True)
    commit_hash: Mapped[str] = mapped_column(CHAR(40), nullable=False, index=True)
    repo_name: Mapped[str] = mapped_column(String(128), nullable=False)
    author_name: Mapped[str] = mapped_column(String(128), nullable=False)
    author_email: Mapped[str | None] = mapped_column(String(128))
    committed_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, index=True)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    parent_hash: Mapped[str | None] = mapped_column(CHAR(40))
    __table_args__ = (UniqueConstraint("repo_name", "commit_hash", name="uk_commit_repo_hash"),)


class CommitFeature(Base):
    __tablename__ = "commit_feature"
    commit_id: Mapped[str] = mapped_column(
        CHAR(36), ForeignKey("commit.commit_id"), primary_key=True
    )
    feature_version: Mapped[str] = mapped_column(String(32), primary_key=True)
    ns: Mapped[float] = mapped_column(Numeric(20, 10), nullable=False)
    nd: Mapped[float] = mapped_column(Numeric(20, 10), nullable=False)
    nf: Mapped[float] = mapped_column(Numeric(20, 10), nullable=False)
    entropy: Mapped[float] = mapped_column(Numeric(20, 10), nullable=False)
    la: Mapped[float] = mapped_column(Numeric(20, 10), nullable=False)
    ld: Mapped[float] = mapped_column(Numeric(20, 10), nullable=False)
    lt: Mapped[float] = mapped_column(Numeric(20, 10), nullable=False)
    fix: Mapped[int] = mapped_column(Integer, nullable=False)
    ndev: Mapped[float] = mapped_column(Numeric(20, 10), nullable=False)
    age: Mapped[float] = mapped_column(Numeric(20, 10), nullable=False)
    nuc: Mapped[float] = mapped_column(Numeric(20, 10), nullable=False)
    exp: Mapped[float] = mapped_column(Numeric(20, 10), nullable=False)
    rexp: Mapped[float] = mapped_column(Numeric(20, 10), nullable=False)
    sexp: Mapped[float] = mapped_column(Numeric(20, 10), nullable=False)
    is_bug_inducing: Mapped[int | None] = mapped_column(Integer)
    labeled_at: Mapped[datetime | None] = mapped_column(DateTime)


class Job(Base):
    __tablename__ = "job"
    job_id: Mapped[str] = mapped_column(CHAR(36), primary_key=True)
    owner_user_id: Mapped[str] = mapped_column(
        CHAR(36), ForeignKey("user.user_id"), nullable=False
    )
    kind: Mapped[str] = mapped_column(String(16), nullable=False)
    status: Mapped[str] = mapped_column(String(16), default="queued", nullable=False)
    params_json: Mapped[str | None] = mapped_column(Text)
    total: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    done: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    current_stage: Mapped[str | None] = mapped_column(String(64))
    output_ref_json: Mapped[str | None] = mapped_column(Text)
    error_message: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    started_at: Mapped[datetime | None] = mapped_column(DateTime)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime)
    __table_args__ = (
        Index("ix_job_owner_status", "owner_user_id", "status"),
        Index("ix_job_kind_status", "kind", "status"),
    )


class Algorithm(Base):
    __tablename__ = "algorithm"
    line: Mapped[str] = mapped_column(String(16), primary_key=True)
    algo: Mapped[str] = mapped_column(String(64), primary_key=True)
    family: Mapped[str] = mapped_column(String(32), nullable=False)
    hyperparams_json: Mapped[str] = mapped_column(Text, nullable=False)
    enabled: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    description: Mapped[str | None] = mapped_column(String(255))


class Dataset(Base):
    __tablename__ = "dataset"
    dataset_id: Mapped[str] = mapped_column(CHAR(36), primary_key=True)
    owner_user_id: Mapped[str] = mapped_column(
        CHAR(36), ForeignKey("user.user_id"), nullable=False
    )
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    line: Mapped[str] = mapped_column(String(16), default="expert", nullable=False)
    source_type: Mapped[str] = mapped_column(String(16), default="git_repo", nullable=False)
    parent_dataset_id: Mapped[str | None] = mapped_column(
        CHAR(36), ForeignKey("dataset.dataset_id", ondelete="SET NULL")
    )
    repo_url: Mapped[str | None] = mapped_column(String(512))
    repo_name: Mapped[str | None] = mapped_column(String(128))
    platform: Mapped[str | None] = mapped_column(String(16))
    branch: Mapped[str | None] = mapped_column(String(128))
    head_hash: Mapped[str | None] = mapped_column(CHAR(40))
    time_start: Mapped[datetime | None] = mapped_column(DateTime)
    time_end: Mapped[datetime | None] = mapped_column(DateTime)
    sample_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    pos_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    neg_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    feature_version: Mapped[str | None] = mapped_column(String(32))
    dedupe_key: Mapped[str | None] = mapped_column(CHAR(64))
    status: Mapped[str] = mapped_column(String(16), default="ready", nullable=False)
    job_id: Mapped[str | None] = mapped_column(CHAR(36), ForeignKey("job.job_id"))
    manifest_path: Mapped[str | None] = mapped_column(String(512))
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    __table_args__ = (
        Index("ix_dataset_owner", "owner_user_id", "created_at"),
        Index("ix_dataset_parent", "parent_dataset_id"),
        UniqueConstraint("owner_user_id", "dedupe_key", name="uk_dataset_dedupe"),
    )


class DatasetCommit(Base):
    __tablename__ = "dataset_commit"
    dataset_id: Mapped[str] = mapped_column(
        CHAR(36), ForeignKey("dataset.dataset_id", ondelete="CASCADE"), primary_key=True
    )
    commit_id: Mapped[str] = mapped_column(
        CHAR(36), ForeignKey("commit.commit_id"), nullable=False
    )
    commit_hash: Mapped[str] = mapped_column(CHAR(40), primary_key=True)
    repo_url: Mapped[str | None] = mapped_column(String(512))
    branch: Mapped[str | None] = mapped_column(String(128))
    author_name: Mapped[str | None] = mapped_column(String(128))
    author_email: Mapped[str | None] = mapped_column(String(128))
    committed_at: Mapped[datetime | None] = mapped_column(DateTime)
    message: Mapped[str | None] = mapped_column(Text)
    parent_hash: Mapped[str | None] = mapped_column(CHAR(40))
    is_bug_inducing: Mapped[int | None] = mapped_column(Integer)
    label_method: Mapped[str | None] = mapped_column(String(32))
    fix_commit_hash: Mapped[str | None] = mapped_column(CHAR(40))
    feature_json: Mapped[dict | None] = mapped_column(JSON)
    row_no: Mapped[int] = mapped_column(Integer, default=0, nullable=False)


class Model(Base):
    __tablename__ = "model"
    model_name: Mapped[str] = mapped_column(String(64), primary_key=True)
    owner_user_id: Mapped[str] = mapped_column(
        CHAR(36), ForeignKey("user.user_id"), nullable=False, index=True
    )
    line: Mapped[str] = mapped_column(String(16), default="expert", nullable=False, index=True)
    algo: Mapped[str | None] = mapped_column(String(64))
    version_key: Mapped[str] = mapped_column(String(64), default="", nullable=False)
    trained_at: Mapped[datetime | None] = mapped_column(DateTime)
    feature_version: Mapped[str | None] = mapped_column(String(32))
    train_dataset_id: Mapped[str | None] = mapped_column(
        CHAR(36), ForeignKey("dataset.dataset_id", ondelete="SET NULL")
    )
    test_dataset_id: Mapped[str | None] = mapped_column(
        CHAR(36), ForeignKey("dataset.dataset_id", ondelete="SET NULL")
    )
    params_json: Mapped[str | None] = mapped_column(Text)
    metrics_json: Mapped[str | None] = mapped_column(Text)


class ModelArtifact(Base):
    __tablename__ = "model_artifact"
    artifact_id: Mapped[str] = mapped_column(CHAR(36), primary_key=True)
    model_name: Mapped[str] = mapped_column(
        String(64), ForeignKey("model.model_name", ondelete="CASCADE"), unique=True, nullable=False
    )
    line: Mapped[str] = mapped_column(String(16), nullable=False, index=True)
    algo: Mapped[str | None] = mapped_column(String(64))
    framework: Mapped[str] = mapped_column(String(16), default="sklearn", nullable=False)
    format: Mapped[str] = mapped_column(String(8), default="pkl", nullable=False)
    version_key: Mapped[str] = mapped_column(String(64), default="", nullable=False)
    weight_path: Mapped[str] = mapped_column(String(255), nullable=False)
    checksum_sha256: Mapped[str] = mapped_column(CHAR(64), nullable=False)
    size_bytes: Mapped[int] = mapped_column(BigInteger, default=0, nullable=False)
    feature_version: Mapped[str | None] = mapped_column(String(32))
    train_job_id: Mapped[str | None] = mapped_column(CHAR(36), ForeignKey("job.job_id"))
    status: Mapped[str] = mapped_column(String(16), default="available", nullable=False)
    trained_at: Mapped[datetime | None] = mapped_column(DateTime)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)


class Prediction(Base):
    __tablename__ = "prediction"
    dataset_id: Mapped[str] = mapped_column(
        CHAR(36), ForeignKey("dataset.dataset_id", ondelete="CASCADE"), primary_key=True
    )
    commit_hash: Mapped[str] = mapped_column(CHAR(40), primary_key=True)
    commit_id: Mapped[str | None] = mapped_column(
        CHAR(36), ForeignKey("commit.commit_id", ondelete="SET NULL")
    )
    model_name: Mapped[str | None] = mapped_column(
        String(64), ForeignKey("model.model_name", ondelete="SET NULL"), index=True
    )
    model_label: Mapped[str | None] = mapped_column(String(128))
    risk_score: Mapped[float] = mapped_column(Numeric(6, 5), nullable=False)
    predicted_label: Mapped[int] = mapped_column(Integer, nullable=False)
    threshold: Mapped[float] = mapped_column(Numeric(4, 3), default=0.5, nullable=False)
    actual_label: Mapped[int | None] = mapped_column(Integer)
    feature_version: Mapped[str | None] = mapped_column(String(32))
    predicted_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)


class Evaluation(Base):
    __tablename__ = "evaluation"
    evaluation_id: Mapped[str] = mapped_column(CHAR(36), primary_key=True)
    owner_user_id: Mapped[str] = mapped_column(
        CHAR(36), ForeignKey("user.user_id", ondelete="CASCADE"), nullable=False
    )
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    source_kind: Mapped[str] = mapped_column(String(16), nullable=False)
    source_label: Mapped[str] = mapped_column(String(255), nullable=False)
    dataset_id: Mapped[str | None] = mapped_column(
        CHAR(36), ForeignKey("dataset.dataset_id", ondelete="SET NULL")
    )
    model_name: Mapped[str | None] = mapped_column(
        String(64), ForeignKey("model.model_name", ondelete="SET NULL")
    )
    model_label: Mapped[str | None] = mapped_column(String(128))
    threshold: Mapped[float] = mapped_column(Numeric(4, 3), default=0.5, nullable=False)
    metrics_json: Mapped[dict] = mapped_column(JSON, nullable=False)
    sample_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    pos_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    neg_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    __table_args__ = (
        UniqueConstraint("owner_user_id", "name", name="uq_evaluation_user_name"),
        Index("ix_evaluation_user_created", "owner_user_id", "created_at"),
    )


class EvaluationFigure(Base):
    __tablename__ = "evaluation_figure"
    figure_id: Mapped[str] = mapped_column(CHAR(36), primary_key=True)
    evaluation_id: Mapped[str] = mapped_column(
        CHAR(36), ForeignKey("evaluation.evaluation_id", ondelete="CASCADE"),
        nullable=False, index=True,
    )
    figure_type: Mapped[str] = mapped_column(String(16), nullable=False)
    file_path: Mapped[str] = mapped_column(String(512), nullable=False)
    sha256: Mapped[str] = mapped_column(CHAR(64), nullable=False)
    width: Mapped[int | None] = mapped_column(Integer)
    height: Mapped[int | None] = mapped_column(Integer)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    __table_args__ = (
        UniqueConstraint("evaluation_id", "figure_type", name="uq_evaluation_figure_type"),
    )
