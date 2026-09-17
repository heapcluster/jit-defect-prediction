"""CSV 灌入：python -m app.ingest <commits|labels|features|predictions> <csv>（design D4 幂等键）。"""

from __future__ import annotations

import csv
import sys
from datetime import datetime

from sqlalchemy import select

from app.db import SessionLocal
from app.models import Commit, CommitFeature, CommitLabel, Prediction

_KINDS = ("commits", "labels", "features", "predictions")


def _dt(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00")).replace(tzinfo=None)


def _upsert_commits(session, row: dict, lineno: int) -> None:
    _require(row, ("repo_name", "commit_hash", "author_name", "committed_at", "message"), lineno)
    existing = session.execute(select(Commit).where(Commit.commit_hash == row["commit_hash"])).scalar_one_or_none()
    if existing is None:
        existing = Commit(commit_hash=row["commit_hash"])
        session.add(existing)
    existing.repo_name = row["repo_name"]
    existing.author_name = row["author_name"]
    existing.author_email = row.get("author_email") or None
    existing.committed_at = _dt(row["committed_at"])
    existing.message = row["message"]
    existing.parent_hash = row.get("parent_hash") or None


def _upsert_labels(session, row: dict, lineno: int) -> None:
    _require(row, ("commit_hash", "is_bug_inducing", "label_method", "labeled_at"), lineno)
    key = {"commit_hash": row["commit_hash"], "label_method": row["label_method"]}
    existing = session.execute(select(CommitLabel).filter_by(**key)).scalar_one_or_none()
    if existing is None:
        existing = CommitLabel(**key)
        session.add(existing)
    existing.is_bug_inducing = int(row["is_bug_inducing"])
    existing.bug_fix_hash = row.get("bug_fix_hash") or None
    existing.labeled_at = _dt(row["labeled_at"])


def _upsert_features(session, row: dict, lineno: int) -> None:
    from app import config

    _require(row, ("commit_hash", "committed_at", "feature_version", *config.FEATURE_COLUMNS), lineno)
    existing = session.execute(
        select(CommitFeature).where(CommitFeature.commit_hash == row["commit_hash"])
    ).scalar_one_or_none()
    if existing is None:
        existing = CommitFeature(commit_hash=row["commit_hash"])
        session.add(existing)
    existing.committed_at = _dt(row["committed_at"])
    existing.feature_version = row["feature_version"]
    for name in config.FEATURE_COLUMNS:
        setattr(existing, name, int(row[name]) if name == "fix" else float(row[name]))


def _upsert_predictions(session, row: dict, lineno: int) -> None:
    _require(row, ("commit_hash", "model_name", "risk_score", "predicted_at", "feature_version"), lineno)
    key = {"commit_hash": row["commit_hash"], "model_name": row["model_name"]}
    existing = session.execute(select(Prediction).filter_by(**key)).scalar_one_or_none()
    if existing is None:
        existing = Prediction(**key)
        session.add(existing)
    existing.risk_score = float(row["risk_score"])
    existing.predicted_at = _dt(row["predicted_at"])
    existing.feature_version = row["feature_version"]


_UPSERTERS = {
    "commits": _upsert_commits,
    "labels": _upsert_labels,
    "features": _upsert_features,
    "predictions": _upsert_predictions,
}


def _require(row: dict, fields: tuple[str, ...], lineno: int) -> None:
    missing = [name for name in fields if not (row.get(name) or "").strip()]
    if missing:
        raise ValueError(f"第 {lineno} 行缺少字段：{', '.join(missing)}")


def ingest(kind: str, path: str) -> int:
    upserter = _UPSERTERS[kind]
    with SessionLocal() as session:
        try:
            with open(path, newline="", encoding="utf-8") as fh:
                reader = csv.DictReader(fh)
                count = 0
                for lineno, row in enumerate(reader, start=2):
                    upserter(session, row, lineno)
                    count += 1
            session.commit()
        except Exception as exc:  # noqa: BLE001 —— 规格：任何一行失败整批回滚并报行号
            session.rollback()
            print(f"灌入失败（{kind}）：{exc}", file=sys.stderr)
            return 1
    print(f"灌入完成（{kind}）：{count} 行")
    return 0


def main(argv: list[str]) -> int:
    if len(argv) != 3 or argv[1] not in _KINDS:
        print(f"用法：python -m app.ingest <{'|'.join(_KINDS)}> <csv 路径>", file=sys.stderr)
        return 2
    return ingest(argv[1], argv[2])


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
