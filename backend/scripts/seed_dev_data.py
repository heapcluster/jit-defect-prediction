"""种子数据：灌入当前 DATABASE_URL 指向的 MySQL 库（默认 jit_demo），用于联调 / 演示 / 测试起步数据。命名带 seed；只进本地库，不入库，见 design D5。"""

from __future__ import annotations

from datetime import datetime

from app.db import SessionLocal, init_db
from app.models import Commit, CommitFeature, Prediction
from sqlalchemy.exc import IntegrityError

_SEED_FEATURES = {
    "ns": 1.0986,
    "nd": 1.6094,
    "nf": 1.9459,
    "entropy": 1.42,
    "la": -4.2720,
    "ld": -5.2753,
    "lt": 7.1136,
    "fix": 1,
    "ndev": 1.3863,
    "age": 2.5257,
    "nuc": 0.2513,
    "exp": 5.7683,
    "rexp": 3.8114,
    "sexp": 2.8904,
}


def seed() -> None:
    init_db()
    with SessionLocal() as session:
        for i in range(1, 4):
            hash_ = f"{i:040x}"
            # 幂等判据用自然键 commit_hash，不用自增主键 id —— id=1 是否存在取决于
            # 历史灌库顺序，半灌/自增偏移的场景会误判成「已灌过」或漏判后撞唯一索引。
            if session.query(Commit).filter_by(commit_hash=hash_).first() is not None:
                continue
            session.add(
                Commit(
                    commit_hash=hash_,
                    repo_name="camel",
                    author_name=f"seed-author-{i}",
                    committed_at=datetime(2026, 8, i, 9, 0, 0),
                    message=f"seed commit {i}",
                )
            )
            session.add(
                CommitFeature(
                    commit_hash=hash_,
                    committed_at=datetime(2026, 8, i, 9, 0, 0),
                    feature_version="v1",
                    **_SEED_FEATURES,
                )
            )
            session.add(
                Prediction(
                    commit_hash=hash_,
                    model_name="seed_v1",
                    risk_score=0.1 * i,
                    predicted_at=datetime(2026, 9, 1, 8, 0, 0),
                    feature_version="v1",
                )
            )
        try:
            session.commit()
        except IntegrityError:
            # 半灌状态（例如 commit 在、feature 缺）会撞唯一索引：回滚并说清原因，
            # 不留一个事务失败、连接却挂着半改状态的会话。
            session.rollback()
            raise SystemExit(
                "seed 失败：库内已有部分冲突行（半灌状态）。请先清理冲突数据或重建库再跑；"
                "本脚本不做任何删除。"
            ) from None
    print("seed 数据写入完成（3 提交 / 3 特征 / 3 预测）")


if __name__ == "__main__":
    seed()
