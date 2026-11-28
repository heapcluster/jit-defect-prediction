"""外部 CSV / Excel 逐列校验与提交标识校验。"""

from __future__ import annotations

from datetime import datetime

from app.constants import EXPERT_COLUMNS, META_COLUMNS, SEMANTIC_COLUMNS
from app.errors import AppError


def parse_time(value) -> datetime | None:
    if value in (None, ""):
        return None
    if isinstance(value, datetime):
        return value.replace(tzinfo=None) if value.tzinfo else value
    text = str(value).strip().replace("Z", "+00:00")
    try:
        parsed = datetime.fromisoformat(text)
    except ValueError:
        for fmt in ("%Y-%m-%d %H:%M:%S", "%Y/%m/%d %H:%M:%S", "%Y-%m-%d"):
            try:
                return datetime.strptime(text, fmt)
            except ValueError:
                continue
        raise AppError(42201, "提交时间格式非法", {"invalid_rows": []})
    return parsed.astimezone().replace(tzinfo=None) if parsed.tzinfo else parsed


def _mismatch(expected: list[str], actual: list[str], offset: int = 0) -> dict | None:
    for index in range(max(len(expected), len(actual))):
        want = expected[index] if index < len(expected) else None
        got = actual[index] if index < len(actual) else None
        if want != got:
            return {"column_index": index + 1, "expected": want, "actual": got}
    return None


def detect_line(columns: list[str], allow_missing_bug: bool = False) -> str:
    candidates = []
    for line, expected in (("expert", EXPERT_COLUMNS), ("semantic", SEMANTIC_COLUMNS)):
        target = expected[:-1] if allow_missing_bug else expected
        if columns == target:
            return line
        candidates.append((line, target, _mismatch(target, columns)))
    candidates.sort(key=lambda item: (
        0 if item[2] is None else 1,
        abs(len(item[1]) - len(columns)),
        item[2]["column_index"] if item[2] else 999,
    ))
    line, _, mismatch = candidates[0]
    raise AppError(42201, "表头与字段契约不一致", {"mismatch": mismatch or {"column_index": 1, "expected": candidates[0][1][0] if candidates[0][1] else None, "actual": columns[0] if columns else None}})


def expected_columns(line: str) -> list[str]:
    return EXPERT_COLUMNS if line == "expert" else SEMANTIC_COLUMNS


def validate_rows(rows: list[dict], line: str, require_bug: bool = True, require_unique: bool = True) -> None:
    from app.utils import is_commit_hash

    invalid_rows: list[int] = []
    projects: set[str] = set()
    hashes: set[str] = set()
    duplicate: str | None = None
    for index, row in enumerate(rows, start=1):
        commit = str(row.get("commit_id", "")).strip()
        if not is_commit_hash(commit):
            invalid_rows.append(index)
            continue
        if commit in hashes and require_unique:
            duplicate = commit
        hashes.add(commit)
        project = str(row.get("project", "")).strip()
        if project:
            projects.add(project)
        if require_bug:
            bug = str(row.get("bug", "")).strip()
            if bug not in ("0", "1"):
                invalid_rows.append(index)
        parse_time(row.get("commit_time"))
    if invalid_rows:
        raise AppError(42201, "数据行不符合契约", {"invalid_rows": invalid_rows[:20]})
    if len(projects) > 1:
        raise AppError(42201, "同一数据集只允许一个 project（仓库）", {"projects": sorted(projects)})
    if duplicate and require_unique:
        raise AppError(42201, "提交哈希重复，请先按 commit_hash 去重", {"duplicate_commit_id": duplicate})


def validate_table(columns: list[str], rows: list[dict], allow_missing_bug: bool = False, require_unique: bool = True) -> str:
    line = detect_line(columns, allow_missing_bug=allow_missing_bug)
    require_bug = "bug" in columns
    validate_rows(rows, line, require_bug=require_bug, require_unique=require_unique)
    return line


def normalize_feature_rows(rows: list[dict], line: str) -> list[list[float]]:
    from app.constants import EXPERT_FEATURES, SEMANTIC_FEATURES

    features = EXPERT_FEATURES if line == "expert" else SEMANTIC_FEATURES
    return [[float(row.get(name, 0) or 0) for name in features] for row in rows]


def meta_of(row: dict) -> dict:
    return {name: row.get(name, "") for name in META_COLUMNS}
