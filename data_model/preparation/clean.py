"""W4 file-only cleaning of canonical, already-log-v1 commit tables."""
from __future__ import annotations

import argparse
import copy
import hashlib
import importlib.util
import io
import json
import math
import re
import sys
import time
import zipfile
from datetime import UTC, datetime
from decimal import Decimal, DecimalException
from pathlib import Path
from uuid import uuid4

BASE = Path(__file__).resolve().parent
ROOT = BASE.parents[1]


def _file_contracts():
    for source in (ROOT / "backend", ROOT / "data_model"):
        if str(source) not in sys.path:
            sys.path.insert(0, str(source))
    from app.services import file_contracts
    return file_contracts


def _original(filename):
    spec = importlib.util.spec_from_file_location("_clean_" + filename[:-3], BASE / filename)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


fc = _file_contracts()
OPS = ("schema_validate", "duplicate_drop", "merge_commit_filter", "missing_value_handle",
       "invalid_time_filter", "unlabeled_handle", "outlier_filter", "label_validate", "text_clean",
       "type_convert", "date_normalize", "text_normalize", "category_normalize", "derive_basic_fields")
REMOVING = {"duplicate_drop", "merge_commit_filter", "invalid_time_filter", "unlabeled_handle", "outlier_filter"}
CLEAN_OPS = set(OPS[:9])
PREPROCESS_OPS = set(OPS[9:])
DERIVED_COLUMNS = ("message_length", "parent_count", "commit_hour")


class CleanError(ValueError):
    code = 40001

    def __init__(self, message):
        self.message = message
        super().__init__(message)


def _invalid(message):
    raise CleanError(message)


def _json(value):
    return json.dumps(value, ensure_ascii=False, allow_nan=False, sort_keys=True,
                      separators=(",", ":")).encode("utf-8")


def _param(name, kind, default, description, minimum=None, maximum=None, choices=None):
    return {"name": name, "type": kind, "default": default, "min": minimum, "max": maximum,
            "choices": choices, "description": description}


def operations() -> list[dict]:
    names = {
        "schema_validate": "列与类型校验", "duplicate_drop": "重复提交去重",
        "merge_commit_filter": "合并提交过滤", "missing_value_handle": "缺失值处理",
        "invalid_time_filter": "非法时间过滤", "unlabeled_handle": "未打标样本处理",
        "outlier_filter": "数值异常检测", "label_validate": "标签值域校验", "text_clean": "提交信息清洗",
        "type_convert": "类型统一", "date_normalize": "时间标准化", "text_normalize": "文本规范化",
        "category_normalize": "类别值规范化", "derive_basic_fields": "基础展示列派生",
    }
    descriptions = {
        "schema_validate": "校验列、类型、哈希格式、时间格式与标签值域，始终第一步且不可关闭。",
        "duplicate_drop": "按 commit_hash 去重，重复样本写入排除明细。",
        "merge_commit_filter": "根据 parent_hash 中多个有效父哈希过滤合并提交，不从 message 猜测。",
        "missing_value_handle": "处理作者、邮箱、时间、消息等缺失值。",
        "invalid_time_filter": "过滤非法时间或超出范围的时间。",
        "unlabeled_handle": "处理未打标样本，NULL 不填 0。",
        "outlier_filter": "对已有数值列做异常检测，不生成模型特征。",
        "label_validate": "校验标签只能是 1/0/空，NULL 不填 0。",
        "text_clean": "清洗 message 文本的首尾空白、控制字符与多余换行。",
        "type_convert": "按用户指定列把字符串时间/数字转为统一类型。",
        "date_normalize": "统一 committed_at/labeled_at 为 UTC ISO 8601。",
        "text_normalize": "统一 message 等文本列的空白和换行。",
        "category_normalize": "统一类别值大小写和空白，不做模型编码。",
        "derive_basic_fields": "派生 message_length/parent_count/commit_hour 等基础展示列，不生成模型特征。",
    }
    params = {
        "missing_value_handle": [_param("strategy", "string", "keep", "keep/fill/exclude.",
                                        choices=["keep", "fill", "exclude"])],
        "unlabeled_handle": [_param("strategy", "string", "keep", "keep/exclude/warn.",
                                    choices=["keep", "exclude", "warn"])],
        "outlier_filter": [_param("method", "string", "iqr", "iqr/zscore.", choices=["iqr", "zscore"])],
        "type_convert": [_param("columns", "array", [], "Columns to convert.")],
        "derive_basic_fields": [_param("columns", "array", list(DERIVED_COLUMNS), "Basic display columns.")],
    }
    base_constraints = [{"type": "clean_before_preprocess"}]
    constraints = {
        "schema_validate": [{"type": "first"}],
        "date_normalize": [{"type": "before_basic_derive"}],
        "derive_basic_fields": [{"type": "after", "op": "date_normalize"}],
    }
    schema = {"type": "table", "columns": list(fc.CLEAN_DATASET_COLUMNS),
              "nullable": ["is_bug_inducing", "labeled_at", "label_method", "parent_hash",
                           "author_email", "repo_url", "author_name", "fix_commit_hash"]}
    return [{"op": op, "name": names[op], "description": descriptions[op], "group":
             "clean" if op in CLEAN_OPS else "preprocess",
             "input_schema": copy.deepcopy(schema), "output_schema": copy.deepcopy(schema),
             "params_schema": params.get(op, []),
             "order_constraints": ([{"type": "first"}] if op == "schema_validate"
                                   else constraints.get(op, base_constraints) if op in PREPROCESS_OPS
                                   else constraints.get(op, [])),
             "supports_preview": True, "default_enabled": op != "derive_basic_fields"}
            for op in OPS]


def _number(value, field):
    if type(value) not in (int, float) or not math.isfinite(value):
        _invalid(f"{field} must be a finite native number, not a boolean or string")
    return value


def _ratio(value, field):
    value = _number(value, field)
    if not 0 < value < 1:
        _invalid(f"{field} must be strictly between 0 and 1")
    return float(value)


def _output_name(value):
    """产物名称：用户可读的清洗结果名，同时作为下游文件名前缀。"""
    if value is None:
        return None
    if not isinstance(value, str):
        _invalid("output_name must be a string")
    name = value.strip()
    if not 1 <= len(name) <= 64:
        _invalid("output_name must be 1-64 characters")
    if (name in (".", "..") or name.startswith(".") or name.endswith(".")
            or any(ord(char) < 32 for char in name) or any(char in name for char in '/\\:*?"<>|')):
        _invalid("output_name contains unsupported characters")
    return name


def validate_config(raw: dict) -> dict:
    fields = {"mode", "steps", "format", "output_name"}
    if not isinstance(raw, dict) or set(raw) - fields or not {"mode", "steps"} <= set(raw):
        _invalid("Config requires mode and steps and permits no unknown keys (features/seed/split_ratio are train-only)")
    output_name = _output_name(raw.get("output_name"))
    if not isinstance(raw["mode"], str) or raw["mode"] not in ("preview", "apply"):
        _invalid("mode must be preview or apply")
    if not isinstance(raw["steps"], list):
        _invalid("steps must be a list")
    fmt = raw.get("format", "csv")
    if not isinstance(fmt, str) or fmt not in ("csv", "xlsx"):
        _invalid("format must be csv or xlsx")
    catalog = {item["op"]: item for item in operations()}
    steps, seen = [], set()
    for step in raw["steps"]:
        if not isinstance(step, dict) or "op" not in step or set(step) - {"op", "enabled", "params"}:
            _invalid("Each step requires op and permits only enabled and params")
        op = step["op"]
        if not isinstance(op, str) or op not in catalog or op in seen:
            _invalid("Step op must be supported and unique")
        seen.add(op)
        enabled, params = step.get("enabled", True), step.get("params", {})
        if type(enabled) is not bool or not isinstance(params, dict):
            _invalid("Step enabled must be boolean and params an object")
        specs = {p["name"]: p for p in catalog[op]["params_schema"]}
        if set(params) - set(specs):
            _invalid(f"Unknown params for {op}")
        normalized = {}
        for name, spec in specs.items():
            value = params.get(name, spec["default"])
            if spec["type"] == "boolean":
                if type(value) is not bool:
                    _invalid(f"{op}.{name} must be boolean")
            elif spec["type"] == "string":
                if not isinstance(value, str) or value not in spec["choices"]:
                    _invalid(f"{op}.{name} is unsupported")
            elif spec["type"] == "array":
                if not isinstance(value, list):
                    _invalid(f"{op}.{name} must be an array")
            else:
                value = _number(value, f"{op}.{name}")
                if (spec["min"] is not None and value < spec["min"] or
                        spec["max"] is not None and value > spec["max"]):
                    _invalid(f"{op}.{name} is out of range")
            normalized[name] = value
        steps.append({"op": op, "enabled": enabled, "params": normalized})
    enabled = [s["op"] for s in steps if s["enabled"]]
    positions = {op: i for i, op in enumerate(enabled)}
    if "schema_validate" not in positions or positions["schema_validate"] != 0:
        _invalid("schema_validate must be first and enabled")
    if any(positions[op] > positions[pre] for op in CLEAN_OPS & positions.keys()
           for pre in PREPROCESS_OPS & positions.keys()):
        _invalid("clean operations must precede preprocess operations")
    for op in enabled:
        for rule in catalog[op]["order_constraints"]:
            other, kind = rule.get("op"), rule["type"]
            if kind == "first" and positions[op] != 0:
                _invalid(f"{op} must be first")
            if kind == "after" and other in positions and positions[op] <= positions[other]:
                _invalid(f"{op} must be after {other}")
            if kind == "before_basic_derive" and "derive_basic_fields" in positions and positions[op] >= positions["derive_basic_fields"]:
                _invalid(f"{op} must be before derive_basic_fields")
    config = {"mode": raw["mode"], "steps": steps, "format": fmt}
    if output_name:
        config["output_name"] = output_name
    return config


def _timestamp(value, field):
    if not isinstance(value, str) or not re.fullmatch(
            r"\d{4}-\d\d-\d\dT\d\d:\d\d:\d\d(?:\.\d{1,6})?(?:Z|[+-]\d\d:\d\d)", value):
        _invalid(f"{field} must be a timezone-aware ISO 8601 datetime")
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00")).astimezone(UTC).isoformat().replace("+00:00", "Z")
    except (ValueError, OverflowError) as error:
        raise CleanError(f"Invalid {field} datetime") from error


def _decimal(value, field):
    if isinstance(value, bool) or not isinstance(value, (str, int, float, Decimal)):
        _invalid(f"Feature {field} must be numeric")
    try:
        number = Decimal(str(value))
        if not number.is_finite() or not math.isfinite(float(number)):
            _invalid(f"Feature {field} must be finite")
        number.quantize(Decimal("0.0000000001"))
        return number
    except (DecimalException, ValueError, OverflowError) as error:
        raise CleanError(f"Feature {field} cannot be represented at 10 decimal places") from error


def _binary(value, field, nullable=False):
    if nullable and value in (None, ""):
        return None
    if isinstance(value, bool) or type(value) not in (str, int, float) or value not in (0, 1, "0", "1"):
        _invalid(f"{field} must be binary" + (" or NULL" if nullable else ""))
    return int(value)


def _rows_external(source, *, relaxed=False):
    """校验外部二维表（collected_commits/clean_dataset），产出训练内核行。

    strict 模式用于文件导入；relaxed 模式用于 run()，把重复、缺失、非法时间等
    脏行留给对应 step 清洗并记录排除明细。14 维特征列留空，is_test 不参与。
    """
    if not isinstance(source, list) or len(source) > fc.MAX_ROWS:
        _invalid("Rows must be a bounded list")
    allowed = set(fc.CLEAN_DATASET_COLUMNS)
    required = set(fc.COLLECTED_COMMITS_REQUIRED)
    result, hashes = [], set()
    for raw in source:
        if not isinstance(raw, dict) or not required <= set(raw) or not set(raw) <= allowed:
            _invalid("Rows must match collected_commits/clean_dataset schema")
        row = dict(raw)
        commit_hash = row.get("commit_hash")
        if not isinstance(commit_hash, str) or not re.fullmatch(r"[0-9a-f]{40}", commit_hash):
            _invalid("commit_hash must be 40 lowercase hexadecimal characters")
        if not relaxed and commit_hash in hashes:
            _invalid("Duplicate commit_hash; label alignment is ambiguous")
        hashes.add(commit_hash)
        for field in ("repo_name", "repo_url", "author_name", "author_email", "message",
                      "parent_hash", "label_method", "label_source", "fix_commit_hash", "source_type"):
            value = row.get(field)
            if value in (None, ""):
                row[field] = None
                continue
            if not isinstance(value, str):
                _invalid(f"Invalid text in {field}")
            if not relaxed and ("\x00" in value or fc._formula(value)):
                _invalid(f"Invalid text or formula in {field}")
        if not relaxed:
            if row.get("label_method") not in (None, "szz_v1", "szz_lite", "third_party"):
                _invalid("label_method must be NULL, szz_v1, szz_lite or third_party")
            if row.get("label_source") not in ("git_szz", "public_dataset"):
                _invalid("label_source must be git_szz or public_dataset")
            if row.get("source_type") not in ("git_repo", "public_dataset"):
                _invalid("source_type must be git_repo or public_dataset")
        committed_at = row.get("committed_at")
        if committed_at in (None, ""):
            if not relaxed:
                _invalid("committed_at is required")
        elif not relaxed:
            row["committed_at"] = _timestamp(committed_at, "committed_at")
        if not relaxed:
            row["is_bug_inducing"] = _binary(row.get("is_bug_inducing", ""), "is_bug_inducing", nullable=True)
        else:
            label = row.get("is_bug_inducing")
            row["is_bug_inducing"] = None if label in (None, "") else label
        result.append({field: row.get(field) for field in fc.CLEAN_DATASET_COLUMNS})
    return result


def parse_input(name: str, content: bytes, manifest: bytes | None = None) -> tuple[list[dict], dict]:
    columns, raw = fc.read_table(name, content)
    if not (set(columns) <= set(fc.CLEAN_DATASET_COLUMNS) and set(fc.COLLECTED_COMMITS_REQUIRED) <= set(columns)):
        _invalid("Input columns must match collected_commits/clean_dataset (no Kamei14/is_test)")
    rows = _rows_external(raw)
    metadata = {"manifest_verified": False, "external": True,
                "warnings": [],
                "input": {"name": name, "sha256": fc.sha256(content), "rows": len(rows)}}
    if manifest is not None:
        verified = fc.verify_manifest(name, content, manifest)
        metadata.update(manifest_verified=True, warnings=[],
                        evidence={key: verified[key] for key in ("module", "job_id", "code_version")})
    return rows, metadata


def _label_dist(rows):
    return {"positive": sum(r["is_bug_inducing"] == 1 for r in rows),
            "negative": sum(r["is_bug_inducing"] == 0 for r in rows),
            "null": sum(r["is_bug_inducing"] is None for r in rows)}


def _feature_side(rows, feature):
    import numpy as np
    values = np.array([r[feature] for r in rows], dtype=float)
    if not len(values):
        return {"mean": None, "median": None, "std": None, "quantiles": {q: None for q in ("0", "0.25", "0.5", "0.75", "1")},
                "missing_count": 0, "histogram": {"counts": [], "bin_edges": []}}
    counts, edges = np.histogram(values, bins=10)
    return {"mean": float(np.mean(values)), "median": float(np.median(values)), "std": float(np.std(values)),
            "quantiles": {str(q): float(np.quantile(values, q)) for q in (0, 0.25, 0.5, 0.75, 1)},
            "missing_count": int(np.isnan(values).sum()),
            "histogram": {"counts": counts.tolist(), "bin_edges": edges.tolist()}}


def _column_side(rows, column):
    """按列统计分布（数值列直方图/类别列频数），用于指定列变化图。"""
    import numpy as np
    values = [r.get(column) for r in rows]
    non_null = [v for v in values if v is not None and v != ""]
    missing = len(values) - len(non_null)
    numeric = []
    for value in non_null:
        try:
            number = float(value)
            if math.isfinite(number):
                numeric.append(number)
        except (TypeError, ValueError):
            pass
    if numeric and len(numeric) == len(non_null):
        arr = np.array(numeric, dtype=float)
        counts, edges = np.histogram(arr, bins=10)
        return {"kind": "numeric", "mean": float(np.mean(arr)), "median": float(np.median(arr)),
                "std": float(np.std(arr)), "min": float(np.min(arr)), "max": float(np.max(arr)),
                "quantiles": {str(q): float(np.quantile(arr, q)) for q in (0, 0.25, 0.5, 0.75, 1)},
                "missing_count": missing, "histogram": {"counts": counts.tolist(), "bin_edges": edges.tolist()}}
    freq = {}
    for value in non_null:
        key = str(value)
        freq[key] = freq.get(key, 0) + 1
    return {"kind": "categorical", "missing_count": missing, "frequency": freq}


def _missing_count(rows):
    counts = {}
    for column in fc.COLLECTED_COMMITS_COLUMNS:
        counts[column] = sum(1 for r in rows if r.get(column) in (None, ""))
    return counts


def _duplicate_count(rows):
    hashes = [r.get("commit_hash") for r in rows]
    return len(hashes) - len(set(hashes))


def run(rows: list[dict], config: dict, *, metadata: dict | None = None, progress=None) -> dict:
    """按新契约清洗 collected_commits：不产模型特征、不切分、不写 is_test。"""
    normalized = validate_config(config)
    before = _rows_external(rows, relaxed=True)
    normalized.update(operation_order=[s["op"] for s in normalized["steps"] if s["enabled"]])
    warnings = list((metadata or {}).get("warnings", []))
    if (metadata or {}).get("evidence"):
        normalized["input_evidence"] = copy.deepcopy(metadata["evidence"])
    current = copy.deepcopy(before)
    stats = []
    total = len(normalized["steps"])
    for index, step in enumerate(normalized["steps"]):
        op, enabled, params = step["op"], step["enabled"], step["params"]
        if progress:
            progress(op, index, total)
        started = time.perf_counter()
        prior = {r["commit_hash"]: dict(r) for r in current}
        label_before = _label_dist(current)
        missing_before = _missing_count(current)
        duplicate_before = _duplicate_count(current)
        excluded, step_warnings = [], []
        if enabled:
            if op == "schema_validate":
                pass
            elif op == "duplicate_drop":
                seen, kept = set(), []
                for row in current:
                    if row["commit_hash"] in seen:
                        excluded.append({"commit_hash": row["commit_hash"], "reason": "Duplicate commit_hash."})
                    else:
                        seen.add(row["commit_hash"])
                        kept.append(row)
                current = kept
            elif op == "merge_commit_filter":
                kept = []
                for row in current:
                    parents = (row.get("parent_hash") or "").split()
                    if len(parents) > 1:
                        excluded.append({"commit_hash": row["commit_hash"], "reason": "Multiple valid parents prove a merge."})
                    else:
                        kept.append(row)
                current = kept
            elif op == "missing_value_handle":
                strategy = params["strategy"]
                if strategy == "exclude":
                    kept = []
                    for row in current:
                        if any(row.get(f) in (None, "") for f in ("author_name", "author_email", "committed_at", "message")):
                            excluded.append({"commit_hash": row["commit_hash"], "reason": "Missing required field."})
                        else:
                            kept.append(row)
                    current = kept
                elif strategy == "fill":
                    for row in current:
                        for field in ("author_name", "author_email", "message"):
                            if row.get(field) in (None, ""):
                                row[field] = ""
                    step_warnings.append("Missing text fields filled with empty string.")
            elif op == "invalid_time_filter":
                kept = []
                for row in current:
                    try:
                        _timestamp(row["committed_at"], "committed_at")
                        kept.append(row)
                    except CleanError:
                        excluded.append({"commit_hash": row["commit_hash"], "reason": "Invalid committed_at."})
                current = kept
            elif op == "unlabeled_handle":
                if params["strategy"] == "exclude":
                    kept = []
                    for row in current:
                        if row.get("is_bug_inducing") is None:
                            excluded.append({"commit_hash": row["commit_hash"], "reason": "Unlabeled row."})
                        else:
                            kept.append(row)
                    current = kept
                elif params["strategy"] == "warn":
                    nulls = sum(1 for r in current if r.get("is_bug_inducing") is None)
                    if nulls:
                        step_warnings.append(f"{nulls} unlabeled rows retained (NULL kept, not 0).")
            elif op == "outlier_filter":
                method = params["method"]
                # 标签列是 0/1 二元值，参与 IQR 会把少数正例整体判为异常；标签只做值域校验。
                numeric_cols = [c for c in fc.COLLECTED_COMMITS_COLUMNS
                                if c != "is_bug_inducing"
                                and all(isinstance(r.get(c), (int, float)) for r in current if r.get(c) not in (None, ""))]
                if method == "iqr" and numeric_cols:
                    import numpy as np
                    for col in numeric_cols:
                        values = np.array([float(r[col]) for r in current if r.get(col) not in (None, "")], dtype=float)
                        if not len(values):
                            continue
                        q1, q3 = np.quantile(values, 0.25), np.quantile(values, 0.75)
                        low, high = q1 - 1.5 * (q3 - q1), q3 + 1.5 * (q3 - q1)
                        kept = []
                        for row in current:
                            value = row.get(col)
                            if value not in (None, "") and not low <= float(value) <= high:
                                excluded.append({"commit_hash": row["commit_hash"], "reason": f"IQR outlier in {col}."})
                            else:
                                kept.append(row)
                        current = kept
            elif op == "label_validate":
                kept = []
                for row in current:
                    if row.get("is_bug_inducing") not in (None, "", 0, 1, "0", "1"):
                        excluded.append({"commit_hash": row["commit_hash"], "reason": "Invalid label value."})
                    else:
                        if row.get("is_bug_inducing") in ("", None):
                            row["is_bug_inducing"] = None
                        else:
                            row["is_bug_inducing"] = int(row["is_bug_inducing"])
                        kept.append(row)
                current = kept
            elif op == "text_clean":
                for row in current:
                    if row.get("message"):
                        row["message"] = re.sub(r"[\x00-\x1f\x7f]+", " ", str(row["message"])).strip()
            elif op == "type_convert":
                pass
            elif op == "date_normalize":
                for row in current:
                    for field in ("committed_at", "labeled_at"):
                        value = row.get(field)
                        if value not in (None, ""):
                            row[field] = _timestamp(value, field)
            elif op == "text_normalize":
                for row in current:
                    if row.get("message"):
                        row["message"] = re.sub(r"\s+", " ", str(row["message"])).strip()
            elif op == "category_normalize":
                for row in current:
                    for field in ("label_method", "label_source", "source_type"):
                        if isinstance(row.get(field), str):
                            row[field] = row[field].strip()
            elif op == "derive_basic_fields":
                for row in current:
                    row["message_length"] = len(row.get("message") or "")
                    row["parent_count"] = len((row.get("parent_hash") or "").split())
                    committed = row.get("committed_at") or ""
                    try:
                        row["commit_hour"] = datetime.fromisoformat(committed.replace("Z", "+00:00")).hour
                    except ValueError:
                        row["commit_hour"] = None
        modified = []
        for row in current:
            old = prior[row["commit_hash"]]
            changes = {field: {"before": old.get(field), "after": row.get(field)}
                       for field in fc.CLEAN_DATASET_COLUMNS if old.get(field) != row.get(field)}
            if changes:
                modified.append({"commit_hash": row["commit_hash"], "changes": changes})
        step_warnings = list(dict.fromkeys(step_warnings))
        stats.append({"step": op, "enabled": enabled,
                      "rows_before": len(prior), "rows_after": len(current),
                      "removed_rows": len(excluded), "modified_rows": len(modified),
                      "modified_samples": modified,
                      "label_dist_before": label_before, "label_dist_after": _label_dist(current),
                      "missing_before": missing_before, "missing_after": _missing_count(current),
                      "duplicate_before": duplicate_before, "duplicate_after": _duplicate_count(current),
                      "elapsed_ms": (time.perf_counter() - started) * 1000,
                      "excluded_samples": excluded, "warnings": step_warnings})
        warnings.extend(step_warnings)
        if progress:
            progress(op, index + 1, total)
    return {"rows": current, "config": normalized,
            "summary": {"input_rows": len(before), "output_rows": len(current),
                        "label_dist": _label_dist(current),
                        "enabled_steps": normalized["operation_order"],
                        "warnings": list(dict.fromkeys(warnings))},
            "steps_stats": stats}


def _encode(rows, fmt):
    cells = []
    for row in rows:
        cell = {field: "" if value is None else value for field, value in row.items()}
        cells.append({key: cell.get(key, "") for key in fc.CLEAN_DATASET_COLUMNS})
    content = fc.encode_table(fc.CLEAN_DATASET_COLUMNS, cells, fmt)
    if fmt == "csv":
        return content
    output = io.BytesIO()
    # XLSX ZIP and core-property timestamps are nondeterministic packaging, not data evidence.
    with zipfile.ZipFile(io.BytesIO(content)) as source, zipfile.ZipFile(output, "w", compression=zipfile.ZIP_DEFLATED) as target:
        for name in sorted(source.namelist()):
            data = source.read(name)
            if name == "docProps/core.xml":
                data = re.sub(rb"(<dcterms:(?:created|modified)\b[^>]*>)[^<]*(</dcterms:(?:created|modified)>)",
                              rb"\g<1>2000-01-01T00:00:00Z\g<2>", data)
            entry = zipfile.ZipInfo(name, date_time=(1980, 1, 1, 0, 0, 0))
            entry.compress_type = zipfile.ZIP_DEFLATED
            target.writestr(entry, data)
    return output.getvalue()


def _distribution(stats, feature):
    from matplotlib.backends.backend_agg import FigureCanvasAgg
    from matplotlib.figure import Figure
    figure = Figure(figsize=(8, 3), dpi=100)
    FigureCanvasAgg(figure)
    for axis, side in zip(figure.subplots(1, 2), ("before", "after"), strict=True):
        part = stats[side]
        if part.get("kind") == "categorical":
            freq = part.get("frequency", {})
            labels = list(freq)[:10]
            counts = [freq[k] for k in labels]
            if not labels:
                axis.text(0.5, 0.5, "Empty data", transform=axis.transAxes, ha="center", va="center")
            else:
                axis.bar(range(len(labels)), counts, color="#4178a8", edgecolor="white")
                axis.set_xticks(range(len(labels)), labels, rotation=30, ha="right")
        else:
            histogram = part["histogram"]
            edges, counts = histogram["bin_edges"], histogram["counts"]
            if not counts:
                axis.text(0.5, 0.5, "Empty data", transform=axis.transAxes, ha="center", va="center")
            else:
                axis.bar(edges[:-1], counts, width=[b - a for a, b in zip(edges[:-1], edges[1:], strict=True)],
                         align="edge", color="#4178a8", edgecolor="white")
        axis.set_title(f"{feature}: {side}")
        axis.set_xlabel("Feature value")
        axis.set_ylabel("Rows")
    figure.tight_layout()
    output = io.BytesIO()
    figure.savefig(output, format="png", metadata={"Software": "W4 clean"})
    figure.clear()
    return output.getvalue()


def artifacts(result: dict, job_id: str) -> dict[str, bytes]:
    if not isinstance(job_id, str) or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_-]{0,79}", job_id):
        _invalid("Invalid artifact job_id")
    output = {}
    config = result["config"]
    name = config.get("output_name")
    if config["mode"] == "apply":
        # 清洗数据只保留一份 CSV 主表；Excel 由下载接口按需转换，避免重复冗余。
        output[f"{name or f'clean_dataset_{job_id}'}.csv"] = _encode(result["rows"], "csv")
    output[f"{name}_steps_stats.json" if name else f"clean_steps_stats_{job_id}.json"] = _json(result["steps_stats"])
    return output


def code_version() -> str:
    digest = hashlib.sha256()
    for path in (BASE / "clean.py", BASE / "02_szz_labeling.py", BASE / "03_extract_features.py",
                 BASE / "05_split_dataset.py", ROOT / "backend/app/services/file_contracts.py"):
        digest.update(path.name.encode())
        digest.update(path.read_bytes())
    return "clean-sha256:" + digest.hexdigest()


def _read_bounded(path: Path) -> bytes:
    if path.stat().st_size > fc.MAX_UPLOAD_BYTES:
        _invalid("File size exceeds MAX_UPLOAD_BYTES")
    content = path.read_bytes()
    if len(content) > fc.MAX_UPLOAD_BYTES:
        _invalid("File size exceeds MAX_UPLOAD_BYTES")
    return content


def main(argv=None) -> int:
    # Windows 控制台默认 GBK；CLI JSON 必须稳定为 UTF-8（与 evaluate CLI 同口径）。
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    if hasattr(sys.stderr, "reconfigure"):
        sys.stderr.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(description="File-only W4 cleaning; no database, Git or online collection")
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("operations")
    command = sub.add_parser("run")
    command.add_argument("--input", required=True, type=Path)
    command.add_argument("--chain", required=True)
    command.add_argument("--mode", required=True, choices=("preview", "apply"))
    command.add_argument("--format", choices=("csv", "xlsx"), default="csv")
    command.add_argument("--output-name", default=None)
    command.add_argument("--manifest", type=Path)
    command.add_argument("--out", required=True, type=Path)
    args = parser.parse_args(argv)
    try:
        if args.command == "operations":
            print(_json(operations()).decode())
            return 0
        chain_text = (args.chain if args.chain.lstrip().startswith(("[", "{")) else
                      _read_bounded(Path(args.chain)).decode("utf-8-sig"))
        chain = fc.read_json(("{\"steps\":" + chain_text + "}").encode()) if chain_text.lstrip().startswith("[") else fc.read_json(chain_text.encode())
        if set(chain) != {"steps"}:
            _invalid("--chain must be a JSON steps list or an object containing only steps")
        raw = {"mode": args.mode, "steps": chain["steps"], "format": args.format,
               "output_name": args.output_name}
        config = validate_config(raw)
        path = args.input.resolve(strict=True)
        companion = args.manifest.resolve(strict=True) if args.manifest else path.with_suffix(".manifest.json")
        content = _read_bounded(path)
        companion_content = _read_bounded(companion) if args.manifest or companion.is_file() else None
        rows, metadata = parse_input(path.name, content, companion_content)
        inputs = [metadata["input"]]
        if companion_content is not None:
            inputs.append({"name": companion.name, "sha256": fc.sha256(companion_content)})
        result = run(rows, config, metadata=metadata)
        job_id = str(uuid4())
        data = artifacts(result, job_id)
        from app.services import output_store
        output_store.OUTPUT_ROOT = args.out.resolve()
        published = output_store.publish_output("clean", data, inputs=inputs,
                                                config=result["config"], job_id=job_id, code_version=code_version())
        print(_json({**published, "summary": result["summary"]}).decode())
        return 0
    except (CleanError, fc.AppError, OSError, ValueError, TypeError) as error:
        message = "Cannot access clean input or output files" if isinstance(error, OSError) else getattr(error, "message", str(error))
        print(_json({"code": getattr(error, "code", 40001), "message": message}).decode(), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
