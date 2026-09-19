"""SQLAlchemy 模型：四张表逐字对齐契约一 v1.2 与契约二 §2/§3。"""

from __future__ import annotations

from sqlalchemy import (
    CHAR,
    DATETIME,
    DECIMAL,
    BigInteger,
    Integer,
    SmallInteger,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.mysql import TINYINT
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

# 契约一/二要求 MySQL TINYINT(1)；SQLite 测试环境落 SMALLINT
TINYINT1 = SmallInteger().with_variant(TINYINT(1), "mysql")
# SQLite 只有 INTEGER PRIMARY KEY 才自增；MySQL 落契约要求的 BIGINT
ID_TYPE = Integer().with_variant(BigInteger, "mysql")


class Base(DeclarativeBase):
    pass


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


class CommitLabel(Base):
    __tablename__ = "commit_label"
    __table_args__ = (UniqueConstraint("commit_hash", "label_method", name="uq_label_hash_method"),)

    id: Mapped[int] = mapped_column(ID_TYPE, primary_key=True, autoincrement=True)
    commit_hash: Mapped[str] = mapped_column(CHAR(40), index=True)
    is_bug_inducing: Mapped[int] = mapped_column(TINYINT1)
    label_method: Mapped[str] = mapped_column(String(32))
    bug_fix_hash: Mapped[str | None] = mapped_column(CHAR(40), nullable=True)
    labeled_at: Mapped[object] = mapped_column(DATETIME)


class CommitFeature(Base):
    __tablename__ = "commit_feature"

    commit_hash: Mapped[str] = mapped_column(CHAR(40), primary_key=True)
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


class Prediction(Base):
    __tablename__ = "prediction"
    # design D7：predict 幂等「库里只保留最新一行」落进 schema；契约一允许后端自属冗余索引
    __table_args__ = (UniqueConstraint("commit_hash", "model_name", name="uq_prediction_hash_model"),)

    id: Mapped[int] = mapped_column(ID_TYPE, primary_key=True, autoincrement=True)
    commit_hash: Mapped[str] = mapped_column(CHAR(40), index=True)
    model_name: Mapped[str] = mapped_column(String(64))
    risk_score: Mapped[float] = mapped_column(DECIMAL(6, 5))
    predicted_at: Mapped[object] = mapped_column(DATETIME)
    feature_version: Mapped[str] = mapped_column(String(32))


INDEX_ASSERTIONS = (
    ("commit", ("commit_hash",), True),
    ("commit", ("committed_at",), False),
    ("prediction", ("commit_hash", "model_name"), True),
    ("prediction", ("commit_hash",), False),
)
