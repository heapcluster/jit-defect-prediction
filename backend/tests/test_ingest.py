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
                "repo_name": "camel",
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
                "repo_name": "camel",
                "commit_hash": "f" * 40,
                "author_name": "bob",
                "author_email": "",
                "committed_at": "2026-01-02T00:00:00Z",
                "message": "ok row",
                "parent_hash": "",
            },
            {
                "repo_name": "camel",
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


def test_ingest_cli_covers_usage_and_success(tmp_path, engine, capsys):
    """`python -m app.ingest` 的 CLI 出口：参数不足 rc=2、种类非法 rc=2、正常路径走 `get_engine()` + `ingest()`。

    补 Sprint 2 报告 §6 第 5 项里 `app/ingest.py:109-115` 的缺口（`__main__` 守卫由
    `test_db.py::test_module_guard_exits_with_usage` 参数化覆盖）。
    """
    from app.ingest import main

    assert main(["app.ingest"]) == 2
    assert "用法：python -m app.ingest" in capsys.readouterr().err
    assert main(["app.ingest", "nope", "x.csv"]) == 2
    assert "用法：python -m app.ingest" in capsys.readouterr().err

    csv_path = tmp_path / "commits.csv"
    fields = ["repo_name", "commit_hash", "author_name", "author_email", "committed_at", "message", "parent_hash"]
    _write(
        csv_path,
        [
            {
                "repo_name": "camel",
                "commit_hash": "9" * 40,
                "author_name": "alice",
                "author_email": "",
                "committed_at": "2026-01-04T00:00:00Z",
                "message": "cli",
                "parent_hash": "",
            }
        ],
        fields,
    )
    assert main(["app.ingest", "commits", str(csv_path)]) == 0
    assert "灌入完成（commits）：1 行" in capsys.readouterr().out
    with SessionLocal() as session:
        rows = session.execute(select(Commit).where(Commit.commit_hash == "9" * 40)).all()
    assert len(rows) == 1
