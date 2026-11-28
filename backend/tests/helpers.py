"""测试数据构造。"""

from __future__ import annotations

import random
from datetime import datetime, timedelta

from app.constants import EXPERT_COLUMNS, EXPERT_FEATURES, FEATURE_VERSION
from app.db import SessionLocal
from app.models import Job
from app.services import artifacts
from app.utils import dumps, new_id, now


def expert_rows(count: int = 40, positive: bool = True, repo: str = "owner/repo") -> list[dict]:
    rows = []
    start = datetime(2024, 1, 1, 10, 0, 0)
    random.seed(7)
    for index in range(count):
        commit_hash = f"{index + 1:040x}"
        label = index % 2 if positive else 0
        row = {
            "project": repo,
            "commit_id": commit_hash,
            "commit_time": (start + timedelta(days=index)).isoformat(),
            "author_name": f"dev{index % 4}",
            "author_email": f"dev{index % 4}@example.com",
            "commit_message": f"change {index}",
            "bug": label,
        }
        for name in EXPERT_FEATURES:
            row[name] = round(random.uniform(0, 10) + (2 if label else 0), 4)
        rows.append(row)
    return rows


def make_job(
    user_id: str,
    kind: str,
    rows: list[dict] | None = None,
    repo_name: str = "owner/repo",
    branch: str = "main",
    source_type: str | None = None,
    parent_dataset_id: str | None = None,
    file_sha256: str | None = None,
    ops_hash: str | None = None,
    line: str = "expert",
) -> str:
    job_id = new_id("job")
    out_dir = artifacts.output_dir(user_id, job_id)
    ref: dict = {
        "line": line,
        "feature_version": FEATURE_VERSION[line],
        "repo": {"repo_url": f"https://github.com/{repo_name}", "repo_name": repo_name,
                 "platform": "github", "branch": branch, "head_hash": None},
        "source_type": source_type or ("git_repo" if kind == "collect" else "upload"),
        "parent_dataset_id": parent_dataset_id,
        "file_sha256": file_sha256,
        "ops_hash": ops_hash,
    }
    if rows is not None:
        data_path = out_dir / "data.csv"
        artifacts.write_csv(data_path, EXPERT_COLUMNS, rows)
        artifacts.write_json(out_dir / "steps.json", {"steps": []})
        pos = sum(1 for row in rows if str(row.get("bug")) == "1")
        ref.update({
            "data_path": artifacts.rel(data_path),
            "columns": EXPERT_COLUMNS,
            "row_count": len(rows),
            "summary": {"total": len(rows), "pos": pos, "neg": len(rows) - pos},
            "manifest": {"columns": EXPERT_COLUMNS, "row_count": len(rows)},
        })
    with SessionLocal() as session:
        session.add(Job(
            job_id=job_id, owner_user_id=user_id, kind=kind, status="success",
            params_json=dumps({"source": {"kind": "dataset", "id": parent_dataset_id}}),
            total=0, done=0,
            output_ref_json=dumps(ref), created_at=now(),
        ))
        session.commit()
    return job_id
