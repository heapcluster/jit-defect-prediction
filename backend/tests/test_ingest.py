import csv

from sqlalchemy import select

from app.db import SessionLocal
from app.ingest import ingest
from app.models import Commit


def _write(path, rows, fields):
    with open(path, "w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def test_ingest_commits_idempotent(tmp_path, engine):
    csv_path = tmp_path / "commits.csv"
    fields = ["repo_name", "commit_hash", "author_name", "author_email", "committed_at", "message", "parent_hash"]
    _write(
        csv_path,
        [
            {
                "repo_name": "activemq",
                "commit_hash": "e" * 40,
                "author_name": "alice",
                "author_email": "",
                "committed_at": "2026-01-01T00:00:00Z",
                "message": "init",
                "parent_hash": "",
            }
        ],
        fields,
    )
    assert ingest("commits", str(csv_path)) == 0
    assert ingest("commits", str(csv_path)) == 0
    with SessionLocal() as session:
        rows = session.execute(select(Commit).where(Commit.commit_hash == "e" * 40)).all()
    assert len(rows) == 1


def test_ingest_missing_key_rolls_back(tmp_path, engine):
    csv_path = tmp_path / "bad.csv"
    fields = ["repo_name", "commit_hash", "author_name", "author_email", "committed_at", "message", "parent_hash"]
    _write(
        csv_path,
        [
            {
                "repo_name": "activemq",
                "commit_hash": "f" * 40,
                "author_name": "bob",
                "author_email": "",
                "committed_at": "2026-01-02T00:00:00Z",
                "message": "ok row",
                "parent_hash": "",
            },
            {
                "repo_name": "activemq",
                "commit_hash": "",
                "author_name": "bob",
                "author_email": "",
                "committed_at": "2026-01-03T00:00:00Z",
                "message": "bad row",
                "parent_hash": "",
            },
        ],
        fields,
    )
    assert ingest("commits", str(csv_path)) == 1
    with SessionLocal() as session:
        rows = session.execute(select(Commit).where(Commit.commit_hash == "f" * 40)).all()
    assert len(rows) == 0
