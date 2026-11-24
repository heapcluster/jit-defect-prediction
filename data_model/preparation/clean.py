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
original02 = _original("02_szz_labeling.py")
original03 = _original("03_extract_features.py")
original05 = _original("05_split_dataset.py")
FEATURES = tuple(original03.FEATURE_FIELDS)
OPS = ("merge_filter", "szz_label", "d5_exclude", "anomaly_exclude", "label_validate",
       "feature_align", "log_transform", "standardize", "time_split")
REMOVING = {"merge_filter", "d5_exclude", "anomaly_exclude"}


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
    names = {"merge_filter": "合并提交过滤", "szz_label": "SZZ 文件标签复核", "d5_exclude": "D5 排除",
             "anomaly_exclude": "异常样本排除", "label_validate": "标签校验", "feature_align": "特征对齐",
             "log_transform": "对数特征检查", "standardize": "训练侧标准化", "time_split": "时间序切分"}
    descriptions = {
        "merge_filter": "仅凭多个有效父提交哈希过滤合并，不从提交信息猜测。",
        "szz_label": "复核文件已有 SZZ 方法标签，不重新运行 blame，也不推断缺失标签。",
        "d5_exclude": "排除携带所选方法但缺回溯标签的 NULL 修复候选，保留真实正标签。",
        "anomaly_exclude": "按参数排除特征异常；标签比例只做自检，不重采样或改标签。",
        "label_validate": "校验同表提交哈希与二值标签对齐，未打标保持空值。",
        "feature_align": "保持 Kamei 14 项固定列序和特征版本。",
        "log_transform": "输入已为 v1 对数值，报告跳过，避免二次 log 或有损逆变换。",
        "standardize": "只使用最终时间序训练样本拟合 13 项非 fix 特征，记录独立版本和 scaler。",
        "time_split": "按时间序切分，复用原 floor 与严格秒级边界断言，不支持随机。",
    }
    params = {
        "szz_label": [_param("method", "string", "szz", "Existing label evidence method.", choices=list(original02.METHODS))],
        "anomaly_exclude": [
            _param("max_abs", "number", 1e6, "Finite positive absolute feature threshold.", 0),
            _param("positive_ratio_low", "number", original02.ABNORMAL_LOW, "Warning lower bound among labeled rows only.", 0, 1),
            _param("positive_ratio_high", "number", original02.ABNORMAL_HIGH, "Warning upper bound among labeled rows only.", 0, 1),
        ],
        "standardize": [_param("with_mean", "boolean", True, "Center using training means."),
                        _param("with_std", "boolean", True, "Scale using training population standard deviations.")],
        "time_split": [_param("ratio", "number", 0.7, "Training ratio; inherits top-level split_ratio when omitted.", 0, 1)],
    }
    constraints = {
        "merge_filter": [{"type": "first"}, {"type": "before", "op": "standardize"}],
        "szz_label": [{"type": "before", "op": "d5_exclude"}],
        "d5_exclude": [{"type": "after", "op": "szz_label"}, {"type": "requires", "op": "szz_label"},
                       {"type": "before", "op": "standardize"}],
        "anomaly_exclude": [{"type": "before", "op": "standardize"}],
        "feature_align": [{"type": "before", "op": "log_transform"}, {"type": "before", "op": "standardize"}],
        "log_transform": [{"type": "requires", "op": "feature_align"}, {"type": "before", "op": "standardize"}],
        "standardize": [{"type": "requires", "op": "feature_align"},
                        {"type": "requires", "op": "time_split"}, {"type": "before", "op": "time_split"}],
        "time_split": [{"type": "last"}],
    }
    schema = {"type": "table", "columns": list(fc.COMMITS_COLUMNS), "features": list(FEATURES),
              "nullable": ["is_bug_inducing", "labeled_at", "label_method", "parent_hash", "author_email"]}
    return [{"op": op, "name": names[op], "description": descriptions[op],
             "input_schema": copy.deepcopy(schema), "output_schema": copy.deepcopy(schema),
             "params_schema": params.get(op, []), "order_constraints": constraints.get(op, []),
             "supports_preview": True, "default_enabled": op not in ("standardize", "anomaly_exclude")}
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


def validate_config(raw: dict) -> dict:
    fields = {"mode", "steps", "features", "seed", "split_ratio", "format"}
    if not isinstance(raw, dict) or set(raw) - fields or not {"mode", "steps"} <= set(raw):
        _invalid("Config requires mode and steps and permits no unknown keys")
    if not isinstance(raw["mode"], str) or raw["mode"] not in ("preview", "apply"):
        _invalid("mode must be preview or apply")
    if not isinstance(raw["steps"], list):
        _invalid("steps must be a list")
    features = raw.get("features", list(FEATURES))
    if (not isinstance(features, list) or not features or any(not isinstance(f, str) or f not in FEATURES for f in features)
            or len(set(features)) != len(features)):
        _invalid("features must be a nonempty unique list of Kamei14 features")
    seed = raw.get("seed", 42)
    if type(seed) is not int:
        _invalid("seed must be an integer, not boolean")
    ratio = _ratio(raw.get("split_ratio", 0.7), "split_ratio")
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
            default = ratio if op == "time_split" and name == "ratio" else spec["default"]
            value = params.get(name, default)
            if spec["type"] == "boolean":
                if type(value) is not bool:
                    _invalid(f"{op}.{name} must be boolean")
            elif spec["type"] == "string":
                if not isinstance(value, str) or value not in spec["choices"]:
                    _invalid(f"{op}.{name} is unsupported")
            else:
                value = _number(value, f"{op}.{name}")
                if (spec["min"] is not None and value < spec["min"] or
                        spec["max"] is not None and value > spec["max"]):
                    _invalid(f"{op}.{name} is out of range")
                if name in ("ratio", "max_abs") and value <= 0 or name == "ratio" and value >= 1:
                    _invalid(f"{op}.{name} must be strictly within bounds")
            normalized[name] = value
        if op == "anomaly_exclude" and normalized["positive_ratio_low"] >= normalized["positive_ratio_high"]:
            _invalid("Positive ratio lower bound must precede upper bound")
        steps.append({"op": op, "enabled": enabled, "params": normalized})
    enabled = [s["op"] for s in steps if s["enabled"]]
    positions = {op: i for i, op in enumerate(enabled)}
    for op in enabled:
        for rule in catalog[op]["order_constraints"]:
            other = rule.get("op")
            kind = rule["type"]
            if kind == "requires" and other not in positions:
                _invalid(f"{op} requires enabled {other}")
            if kind == "first" and positions[op] != 0 or kind == "last" and positions[op] != len(enabled) - 1:
                _invalid(f"{op} must be {kind}")
            if other in positions and (kind == "before" and positions[op] >= positions[other] or
                                       kind == "after" and positions[op] <= positions[other]):
                _invalid(f"{op} must be {kind} {other}")
    if "standardize" in positions and any(positions[op] > positions["standardize"] for op in REMOVING & positions.keys()):
        _invalid("No row-removing operation may follow standardize")
    return {"mode": raw["mode"], "steps": steps, "features": [f for f in FEATURES if f in features],
            "seed": seed, "split_ratio": ratio, "format": fmt}


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


def _rows(source):
    if not isinstance(source, list) or len(source) > fc.MAX_ROWS:
        _invalid("Rows must be a bounded list")
    result, hashes = [], set()
    for raw in source:
        if not isinstance(raw, dict) or set(raw) != set(fc.COMMITS_COLUMNS):
            _invalid("Rows must have exactly canonical COMMITS_COLUMNS")
        row = dict(raw)
        for field in ("commit_hash", "repo_name", "author_name", "author_email", "message", "parent_hash", "label_method"):
            value = row[field]
            if value in (None, "") and field in ("author_email", "parent_hash", "label_method"):
                row[field] = None
                continue
            if not isinstance(value, str) or not value.strip() or "\x00" in value or fc._formula(value):
                _invalid(f"Invalid text or formula in {field}")
        commit_hash = row["commit_hash"]
        if not re.fullmatch(r"[0-9a-f]{40}", commit_hash):
            _invalid("commit_hash must be 40 lowercase hexadecimal characters")
        if row["commit_hash"] in hashes:
            _invalid("Duplicate commit_hash; same-table label alignment is ambiguous")
        hashes.add(row["commit_hash"])
        if row["parent_hash"]:
            parents = row["parent_hash"].split()
            if any(not re.fullmatch(r"[0-9a-f]{40}", p) for p in parents) or len(set(parents)) != len(parents):
                _invalid("parent_hash must contain distinct lowercase 40-hex parents")
        if row["label_method"] not in (None, "szz", "szz_lite"):
            _invalid("label_method must be NULL, szz or szz_lite")
        row["committed_at"] = _timestamp(row["committed_at"], "committed_at")
        row["labeled_at"] = None if row["labeled_at"] in (None, "") else _timestamp(row["labeled_at"], "labeled_at")
        for field in FEATURES:
            row[field] = _binary(row[field], field) if field == "fix" else float(_decimal(row[field], field))
        row["is_bug_inducing"] = _binary(row["is_bug_inducing"], "is_bug_inducing", nullable=True)
        row["is_test"] = _binary(row["is_test"], "is_test")
        result.append({field: row[field] for field in fc.COMMITS_COLUMNS})
    return result


def _feature_metadata(metadata):
    if metadata is not None and not isinstance(metadata, dict):
        _invalid("metadata must be an object")
    metadata = metadata or {}
    version = metadata.get("feature_version", "v1")
    state = metadata.get("feature_state", "standardized_v1" if version.endswith("-standardized") else "log_v1") if isinstance(version, str) else None
    if not isinstance(version, str) or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.-]{0,31}", version):
        _invalid("feature_version must be declared and valid")
    if state not in ("log_v1", "standardized_v1") or state == "standardized_v1" and version == "v1":
        _invalid("Only log_v1 or distinctly-versioned standardized_v1 file features are supported")
    if version.endswith("-standardized") and state != "standardized_v1":
        _invalid("Standardized feature_version contradicts feature_state")
    return version, state


def parse_input(name: str, content: bytes, manifest: bytes | None = None) -> tuple[list[dict], dict]:
    columns, raw = fc.read_table(name, content)
    if tuple(columns) != fc.COMMITS_COLUMNS:
        _invalid("Input columns and order must exactly match canonical COMMITS_COLUMNS")
    rows = _rows(raw)
    metadata = {"feature_version": "v1", "feature_state": "log_v1", "manifest_verified": False,
                "warnings": ["No companion manifest: declared default feature_version=v1, feature_state=log_v1."],
                "input": {"name": name, "sha256": fc.sha256(content), "rows": len(rows)}}
    if manifest is not None:
        verified = fc.verify_manifest(name, content, manifest)
        if "feature_version" not in verified["config"]:
            _invalid("Verified manifest must declare feature_version")
        version, state = _feature_metadata(verified["config"])
        metadata.update(feature_version=version, feature_state=state, manifest_verified=True, warnings=[],
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


def _split(rows, ratio):
    ordered = sorted(rows, key=lambda r: (datetime.fromisoformat(r["committed_at"].replace("Z", "+00:00")), r["commit_hash"]))
    total = len(ordered)
    warnings = []
    if total < 2:
        cut = total
        warnings.append("Empty data: temporal split has empty sides." if not total else "One row: temporal split is train-only.")
    else:
        cut = original05.split_index(total, ratio)
        # Original05's strict second-level guard must not be weakened by fractional timestamps.
        adapter = [{"committed_at": datetime.fromisoformat(r["committed_at"].replace("Z", "+00:00")).strftime(original05.TIMESTAMP_FORMAT)} for r in ordered]
        failures = original05.validate_split(adapter[:cut], adapter[cut:], total)
        if failures:
            _invalid("Temporal split rejected by original05: " + "; ".join(failures))
    boundary = {"train_rows": cut, "test_rows": total - cut,
                "train_max": ordered[cut - 1]["committed_at"] if cut else None,
                "test_min": ordered[cut]["committed_at"] if cut < total else None,
                "train_last_hash": ordered[cut - 1]["commit_hash"] if cut else None,
                "test_first_hash": ordered[cut]["commit_hash"] if cut < total else None}
    return ordered, cut, boundary, warnings


def _standardize(rows, plot_features, params, cut, boundary):
    import numpy as np
    from sklearn.preprocessing import StandardScaler
    selected = [f for f in FEATURES if f != "fix"]
    snapshot = {**params, "features": selected, "plot_features": list(plot_features),
                "train_hashes": [r["commit_hash"] for r in rows[:cut]],
                "boundary": boundary, "fitted": False, "mean_": None, "var_": None, "scale_": None,
                "n_samples_seen_": cut, "n_features_in_": len(selected), "feature_names_in_": selected}
    warnings = []
    if not cut:
        warnings.append("Standardize skipped fit: Empty training data.")
        return rows, snapshot, warnings
    values = np.array([[r[f] for f in selected] for r in rows], dtype=float)
    scaler = StandardScaler(**params).fit(values[:cut])
    transformed = scaler.transform(values)
    for row, vector in zip(rows, transformed, strict=True):
        for feature, value in zip(selected, vector, strict=True):
            _decimal(float(value), feature)
            row[feature] = float(value)
    snapshot.update(fitted=True, mean_=None if scaler.mean_ is None else scaler.mean_.tolist(),
                    var_=None if scaler.var_ is None else scaler.var_.tolist(),
                    scale_=None if scaler.scale_ is None else scaler.scale_.tolist(),
                    n_samples_seen_=int(scaler.n_samples_seen_), n_features_in_=int(scaler.n_features_in_))
    return rows, snapshot, warnings


def run(rows: list[dict], config: dict, *, metadata: dict | None = None, progress=None) -> dict:
    normalized = validate_config(config)
    before = _rows(rows)
    version, state = _feature_metadata(metadata)
    if state == "standardized_v1" and any(s["enabled"] and s["op"] == "standardize" for s in normalized["steps"]):
        _invalid("Cannot repeat standardize on standardized input")
    normalized.update(feature_version=version, feature_state=state, feature_order=list(FEATURES),
                      canonical_feature_order=list(FEATURES), operation_order=[s["op"] for s in normalized["steps"] if s["enabled"]])
    warnings = list((metadata or {}).get("warnings", []))
    if metadata is None:
        warnings.append("No metadata: declared default feature_version=v1, feature_state=log_v1.")
    if any(r["is_bug_inducing"] is not None and r["label_method"] is None for r in before):
        warnings.append("Known labels without label_method retained; method evidence is unavailable.")
    if (metadata or {}).get("evidence"):
        normalized["input_evidence"] = copy.deepcopy(metadata["evidence"])
    current = copy.deepcopy(before)
    stats = []
    requested_method = next((s["params"]["method"] for s in normalized["steps"] if s["op"] == "szz_label" and s["enabled"]), None)
    split_ratio = next((s["params"]["ratio"] for s in normalized["steps"] if s["op"] == "time_split" and s["enabled"]), normalized["split_ratio"])
    total = len(normalized["steps"])
    for index, step in enumerate(normalized["steps"]):
        op, enabled, params = step["op"], step["enabled"], step["params"]
        if progress:
            progress(op, index, total)
        started = time.perf_counter()
        prior = {r["commit_hash"]: dict(r) for r in current}
        label_before = _label_dist(current)
        excluded, step_warnings = [], []
        if enabled:
            if op == "merge_filter":
                kept = []
                for row in current:
                    if row["parent_hash"] and len(row["parent_hash"].split()) > 1:
                        excluded.append({"commit_hash": row["commit_hash"], "reason": "File parent_hash proves a merge (multiple valid parents)."})
                    else:
                        kept.append(row)
                current = kept
            elif op == "szz_label":
                for row in current:
                    method = row["label_method"]
                    if method and method != requested_method:
                        _invalid(f"Existing label_method mismatch for {row['commit_hash']}: {method} != {requested_method}")
                step_warnings.append("SZZ file evidence reuse/validation only; no fresh SZZ blame, backtracking or message-inferred labels.")
                if any(r["is_bug_inducing"] is not None and r["label_method"] is None for r in current):
                    step_warnings.append("Known labels without label_method retained; method evidence is unavailable.")
            elif op == "d5_exclude":
                kept = []
                for row in current:
                    is_fix = original02.is_fix_commit(row["message"])
                    if is_fix and row["is_bug_inducing"] is None and row["label_method"] == requested_method:
                        excluded.append({"commit_hash": row["commit_hash"], "reason": f"File's {requested_method} unresolved/no-backtracking evidence for a NULL fix row; not a fresh SZZ run."})
                    else:
                        if is_fix and row["is_bug_inducing"] is None and not row["label_method"]:
                            step_warnings.append("NULL fix row without label_method retained; D5 has no method evidence.")
                        kept.append(row)
                current = kept
            elif op == "anomaly_exclude":
                kept = []
                for row in current:
                    bad = [f for f in FEATURES if abs(row[f]) > params["max_abs"]]
                    if bad:
                        excluded.append({"commit_hash": row["commit_hash"], "reason": "Absolute feature outlier beyond max_abs: " + ", ".join(bad)})
                    else:
                        kept.append(row)
                current = kept
                dist = _label_dist(current)
                labeled = dist["positive"] + dist["negative"]
                if not labeled:
                    step_warnings.append("No labeled rows: positive ratio is undefined; NULL labels retained.")
                elif not dist["positive"]:
                    step_warnings.append("Zero positive labels among labeled rows; no class-ratio rebalancing or label removal.")
                if labeled and params["positive_ratio_low"] <= dist["positive"] / labeled <= params["positive_ratio_high"]:
                    step_warnings.append("Abnormal positive ratio among labeled rows only; no class-ratio rebalancing or label removal.")
            elif op == "label_validate":
                current = _rows(current)
            elif op == "feature_align":
                current = [{field: row[field] for field in fc.COMMITS_COLUMNS} for row in current]
            elif op == "log_transform":
                if state == "standardized_v1":
                    step_warnings.append("Log transform skipped: standardized input retained without additional log or inverse.")
                else:
                    step_warnings.append("Log transform skipped: input already contains log-v1 features; no double log or inverse.")
            elif op == "standardize":
                current, cut, boundary, split_warnings = _split(current, split_ratio)
                current, snapshot, scaler_warnings = _standardize(current, normalized["features"], params, cut, boundary)
                scaled_version = version + "-standardized"
                if len(scaled_version) > 32:
                    scaled_version = hashlib.sha256(version.encode()).hexdigest()[:19] + "-standardized"
                scaled_version, scaled_state = _feature_metadata({"feature_version": scaled_version,
                                                                 "feature_state": "standardized_v1"})
                normalized.update(scaler=snapshot, source_feature_version=version,
                                  feature_version=scaled_version, feature_state=scaled_state)
                step_warnings.extend(split_warnings + scaler_warnings)
            elif op == "time_split":
                current, cut, boundary, split_warnings = _split(current, split_ratio)
                normalized["split"] = {"ratio": split_ratio, **boundary,
                                       "train_hashes": [r["commit_hash"] for r in current[:cut]]}
                for i, row in enumerate(current):
                    row["is_test"] = int(i >= cut)
                step_warnings.extend(split_warnings)
        modified = []
        for row in current:
            old = prior[row["commit_hash"]]
            changes = {field: {"before": old[field], "after": row[field]} for field in fc.COMMITS_COLUMNS if old[field] != row[field]}
            if changes:
                modified.append({"commit_hash": row["commit_hash"], "changes": changes})
        step_warnings = list(dict.fromkeys(step_warnings))
        stats.append({"op": op, "enabled": enabled, "rows_before": len(prior), "rows_after": len(current),
                      "removed": len(excluded), "modified": len(modified), "label_dist": _label_dist(current),
                      "label_dist_before": label_before, "elapsed_ms": (time.perf_counter() - started) * 1000,
                      "excluded_samples": excluded, "modified_samples": modified, "warnings": step_warnings})
        warnings.extend(step_warnings)
        if progress:
            progress(op, index + 1, total)
    if normalized["mode"] == "apply" and any(r["parent_hash"] and len(r["parent_hash"].split()) > 1 for r in current):
        _invalid("Apply output incompatible with canonical single parent_hash: enable merge_filter")
    feature_stats = {f: {"before": _feature_side(before, f), "after": _feature_side(current, f)} for f in normalized["features"]}
    return {"rows": current, "config": normalized,
            "summary": {"input_rows": len(before), "output_rows": len(current), "label_dist": _label_dist(current),
                        "enabled_steps": normalized["operation_order"], "warnings": list(dict.fromkeys(warnings))},
            "steps_stats": stats, "feature_stats": feature_stats}


def _encode(rows, fmt):
    cells = []
    for row in rows:
        cell = {field: "" if value is None else value for field, value in row.items()}
        for feature in FEATURES:
            if feature != "fix":
                cell[feature] = f"{_decimal(cell[feature], feature).quantize(Decimal('0.0000000001')):.10f}"
        cells.append(cell)
    content = fc.encode_table(fc.COMMITS_COLUMNS, cells, fmt)
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
        histogram = stats[side]["histogram"]
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
    if config["mode"] == "apply":
        if any(r["parent_hash"] and len(r["parent_hash"].split()) > 1 for r in result["rows"]):
            _invalid("Cannot encode surviving merge parents in canonical apply output")
        for fmt in (config["format"], "xlsx" if config["format"] == "csv" else "csv"):
            output[f"clean_cleaned_{job_id}.{fmt}"] = _encode(result["rows"], fmt)
    output[f"clean_steps_stats_{job_id}.json"] = _json(result["steps_stats"])
    output[f"clean_feature_stats_{job_id}.json"] = _json(result["feature_stats"])
    for feature, stats in result["feature_stats"].items():
        output[f"clean_feature_distribution_{feature}_{job_id}.png"] = _distribution(stats, feature)
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
    parser = argparse.ArgumentParser(description="File-only W4 cleaning; no database, Git or online collection")
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("operations")
    command = sub.add_parser("run")
    command.add_argument("--input", required=True, type=Path)
    command.add_argument("--chain", required=True)
    command.add_argument("--mode", required=True, choices=("preview", "apply"))
    command.add_argument("--features")
    command.add_argument("--seed", type=int, default=42)
    command.add_argument("--split-ratio", type=float, default=0.7)
    command.add_argument("--format", choices=("csv", "xlsx"), default="csv")
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
        raw = {"mode": args.mode, "steps": chain["steps"], "seed": args.seed,
               "split_ratio": args.split_ratio, "format": args.format}
        if args.features is not None:
            raw["features"] = args.features.split(",")
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
