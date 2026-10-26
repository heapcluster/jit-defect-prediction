"""本地开发库一键就绪：建表 → 导入历史数据 → 用真实权重预跑一遍。

设计取舍（为什么这是一个「开发引导脚本」而不是数据入口）：

* **数据入口仍然只有实时同步端点**（`POST /api/sync` / `POST /api/sync-prs`）。本脚本只把仓库里
  已有的数据线产物（`data_model/data/*.csv`）灌进**本地开发库**，让 clone 完的人不用等几十分钟
  同步就能看到「列表 / 详情 / 趋势」三页的真实规模数据。
* 目标库就是 `backend/.env` 配的那套 MySQL（`DB_HOST` / `DB_PORT` / `DB_USER` / `DB_PASSWORD` /
  `DB_NAME`）：脚本只负责「把仓库里已有的数据线产物灌进本地开发库」，不引入第二种数据库。

常见用法（cwd = 仓库根）：

    python infra/bootstrap_dev.py                        # 建表 + 最新 5000 条 + xgb_v1 预测
    python infra/bootstrap_dev.py --limit 20000          # 再多灌些（首次约 1~2 分钟）
    python infra/bootstrap_dev.py --models xgb_v1,lr_v1  # 多模型一起预跑，前端可切换对比
    python infra/bootstrap_dev.py --reset                # 清空重建（换库/表结构变了时用）
"""

from __future__ import annotations

import argparse
import sys
from datetime import UTC, datetime
from pathlib import Path

import pandas as pd

REPO_ROOT = Path(__file__).resolve().parent.parent
BACKEND_DIR = REPO_ROOT / "backend"
DATA_DIR = REPO_ROOT / "data_model" / "data"

sys.path.insert(0, str(BACKEND_DIR))
sys.path.insert(0, str(REPO_ROOT / "data_model"))

from app import config, db, model_registry  # noqa: E402
from app.models import Base, Commit, CommitFeature, CommitLabel, Prediction  # noqa: E402

FEATURE_COLUMNS = list(config.FEATURE_COLUMNS)


def _now() -> datetime:
    """库里的时间列是「无时区 UTC」（契约一），这里统一成 naive。"""
    return datetime.now(UTC).replace(tzinfo=None)


def _load_commits(limit: int) -> pd.DataFrame:
    """取**最新**的 N 条提交：趋势图与列表页看的是近期数据，不是 2007 年的起点。"""
    frame = pd.read_csv(
        DATA_DIR / "commits.csv",
        usecols=[
            "repo_name",
            "commit_hash",
            "author_name",
            "author_email",
            "committed_at",
            "message",
            "parent_hash",
        ],
    )
    frame["committed_at"] = pd.to_datetime(frame["committed_at"], errors="coerce")
    frame = frame.dropna(subset=["commit_hash", "committed_at"])
    frame = frame.sort_values("committed_at", ascending=False).head(limit)
    return frame.sort_values("committed_at").reset_index(drop=True)


def _existing_hashes(session, model, hashes: list[str]) -> set[str]:
    if not hashes:
        return set()
    rows = session.query(model.commit_hash).filter(model.commit_hash.in_(hashes)).all()
    return {row[0] for row in rows}


def import_commits(limit: int) -> list[str]:
    commits = _load_commits(limit)
    hashes = commits["commit_hash"].tolist()
    with db.SessionLocal() as session:
        known = _existing_hashes(session, Commit, hashes)
        fresh = commits[~commits["commit_hash"].isin(known)]
        session.bulk_insert_mappings(
            Commit,
            [
                {
                    "repo_name": row.repo_name,
                    "commit_hash": row.commit_hash,
                    "author_name": row.author_name or "",
                    "author_email": row.author_email if isinstance(row.author_email, str) else None,
                    "committed_at": row.committed_at.to_pydatetime(),
                    "message": row.message or "",
                    "parent_hash": row.parent_hash if isinstance(row.parent_hash, str) else None,
                }
                for row in fresh.itertuples(index=False)
            ],
        )
        session.commit()
    print(f"[bootstrap] commit：新增 {len(fresh)} 条（已存在 {len(known)} 条）")
    return hashes


def import_features(hashes: list[str]) -> int:
    wanted = set(hashes)
    frame = pd.read_csv(DATA_DIR / "commit_features.csv")
    frame = frame[frame["commit_hash"].isin(wanted)]
    if frame.empty:
        print("[bootstrap] commit_feature：没有可导入的行（特征 CSV 与提交对不上？）")
        return 0
    frame["committed_at"] = pd.to_datetime(frame["committed_at"], errors="coerce")
    with db.SessionLocal() as session:
        known = _existing_hashes(session, CommitFeature, frame["commit_hash"].tolist())
        fresh = frame[~frame["commit_hash"].isin(known)]
        session.bulk_insert_mappings(
            CommitFeature,
            [
                {
                    "commit_hash": row.commit_hash,
                    "committed_at": row.committed_at.to_pydatetime()
                    if pd.notna(row.committed_at)
                    else _now(),
                    "feature_version": row.feature_version,
                    **{name: float(getattr(row, name)) for name in FEATURE_COLUMNS},
                    "fix": int(row.fix),
                }
                for row in fresh.itertuples(index=False)
            ],
        )
        session.commit()
    print(f"[bootstrap] commit_feature：新增 {len(fresh)} 条")
    return len(fresh)


def import_labels(hashes: list[str]) -> int:
    wanted = set(hashes)
    frame = pd.read_csv(
        DATA_DIR / "dataset_szz.csv",
        usecols=["commit_hash", "is_bug_inducing", "label_method", "bug_fix_hash"],
    )
    frame = frame[frame["commit_hash"].isin(wanted)].dropna(subset=["is_bug_inducing"])
    if frame.empty:
        print("[bootstrap] commit_label：没有可导入的行")
        return 0
    with db.SessionLocal() as session:
        known = _existing_hashes(session, CommitLabel, frame["commit_hash"].tolist())
        fresh = frame[~frame["commit_hash"].isin(known)]
        now = _now()
        session.bulk_insert_mappings(
            CommitLabel,
            [
                {
                    "commit_hash": row.commit_hash,
                    "is_bug_inducing": int(row.is_bug_inducing),
                    "label_method": row.label_method or "szz",
                    "bug_fix_hash": row.bug_fix_hash if isinstance(row.bug_fix_hash, str) else None,
                    "labeled_at": now,
                }
                for row in fresh.itertuples(index=False)
            ],
        )
        session.commit()
    print(
        f"[bootstrap] commit_label：新增 {len(fresh)} 条（正样本 {int(fresh['is_bug_inducing'].sum())} 条）"
    )
    return len(fresh)


def predict_all(hashes: list[str], models: list[str]) -> int:
    """用真实权重把已导入的提交批量打分，页面上立刻有风险分布与趋势。"""
    model_registry.load_models()
    available = {entry.name for entry in model_registry.all_models()}
    if not available:
        print("[bootstrap] 跳过预测：一个模型都没加载成功，先看 backend 启动日志")
        return 0
    missing = [name for name in models if name not in available]
    if missing:
        print(f"[bootstrap] 这些模型不存在或加载失败，已跳过：{missing}")
        models = [name for name in models if name in available]
    total = 0
    wanted = set(hashes)
    with db.SessionLocal() as session:
        rows = session.query(CommitFeature).filter(CommitFeature.commit_hash.in_(wanted)).all()
        existing = {
            (row[0], row[1])
            for row in session.query(Prediction.commit_hash, Prediction.model_name).all()
        }
        now = _now()
        for name in models:
            entry = model_registry.get_model(name)
            payload = []
            for feature in rows:
                key = (feature.commit_hash, name)
                if key in existing:
                    continue
                vector = [
                    int(getattr(feature, column))
                    if column == "fix"
                    else float(getattr(feature, column))
                    for column in FEATURE_COLUMNS
                ]
                payload.append(
                    {
                        "commit_hash": feature.commit_hash,
                        "model_name": name,
                        "risk_score": model_registry.predict_proba(entry.model, vector),
                        "predicted_at": now,
                        "feature_version": feature.feature_version,
                    }
                )
            session.bulk_insert_mappings(Prediction, payload)
            session.commit()
            total += len(payload)
            print(f"[bootstrap] prediction[{name}]：新增 {len(payload)} 条")
    return total


def summary() -> None:
    with db.SessionLocal() as session:
        counts = {
            "commit": session.query(Commit).count(),
            "commit_label": session.query(CommitLabel).count(),
            "commit_feature": session.query(CommitFeature).count(),
            "prediction": session.query(Prediction).count(),
        }
        high = session.query(Prediction).filter(Prediction.risk_score >= 0.5).count()
    print("[bootstrap] 库内统计：" + "  ".join(f"{key}={value}" for key, value in counts.items()))
    print(f"[bootstrap] 其中 risk>=0.5 的预测 {high} 条")
    print(
        f"[bootstrap] 连接：MySQL {config.DB_USER}@{config.DB_HOST}:{config.DB_PORT}/{config.DB_NAME}"
    )
    print("[bootstrap] 下一步：cd backend && uvicorn app.main:app --reload")
    print("            cd frontend && npm run dev        # 另开一个终端")


def main() -> int:
    parser = argparse.ArgumentParser(
        description="本地开发库一键就绪（建表 + 导入历史数据 + 预跑预测）"
    )
    parser.add_argument("--limit", type=int, default=5000, help="导入最新多少条提交（默认 5000）")
    parser.add_argument(
        "--models",
        default="xgb_v1",
        help="用哪些模型预跑预测，逗号分隔（默认 xgb_v1；可选 lr_v1,rf_v1,lgbm_v1,et_v1,svm_v1,mlp_deep_v1,tabnet_v1）",
    )
    parser.add_argument("--reset", action="store_true", help="先删表再重建（清空本地库）")
    parser.add_argument("--skip-predict", action="store_true", help="只导数据，不预跑预测")
    args = parser.parse_args()

    print(f"[bootstrap] 目标库：{config.DATABASE_URL}")
    engine = db.get_engine()
    if args.reset:
        Base.metadata.drop_all(engine)
        print("[bootstrap] 已清空既有表")
    db.init_db()

    hashes = import_commits(args.limit)
    import_features(hashes)
    import_labels(hashes)
    if not args.skip_predict:
        models = [name.strip() for name in args.models.split(",") if name.strip()]
        predict_all(hashes, models)
    summary()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
