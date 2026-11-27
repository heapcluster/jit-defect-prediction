"""W5 训练 CORE（file-only，无数据库；CLI 与 API 共用同一 run/artifacts）。

单一来源复用（不复制公式/构造器/切分/解析）：
  · 构造器：pipelines/expert/model.py build_model(algo, seed)（8 算法 × 2 线）；
    超参覆盖用返回对象的 sklearn set_params（Pipeline 步前缀如 lr__C）。
  · 切分：preparation/05_split_dataset.py split_index(floor) + validate_split
    （严格秒级边界：检验集最早 > 训练集最晚），经 preparation.clean 的 importlib
    路径加载复用；禁止随机切分。
  · 表格解析：preparation/clean.py parse_input（collected_commits/clean_dataset schema）；
    行校验复用 clean._rows_external。
  · 指标：evaluation/metrics.py safe_summary（effort_unaware 同口径 + 退化包装）。
  · 编解码/发布：backend file_contracts + output_store（同茎 manifest，批次不可覆盖）。

确定性：model_name=f'{algo}_{fp8}_v1'、version_key=fp16，
fp=sha256(canonical json{input_sha, feature_version, line, algo, sorted applied
hyperparams, split, seed}) —— CLI/API 同输入同身份。权重字节不保证逐字节一致
（joblib/torch 非确定包装），复现核对以身份 + 指标为准。

失败隔离：单算法 fit/评估异常只把该子项置 failed（带 sanitized error、无模型包），
不中断其余算法。CLI 不做 register/auto_load（DB-only，由服务端作业层负责）。
"""

from __future__ import annotations

import argparse
import hashlib
import io
import json
import math
import re
import sys
import time
from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

BASE = Path(__file__).resolve().parent
ROOT = BASE.parents[1]


def _modules():
    for source in (ROOT / "backend", ROOT / "data_model"):
        if str(source) not in sys.path:
            sys.path.insert(0, str(source))
    from app.services import file_contracts
    from evaluation import metrics
    from pipelines import registry
    from pipelines.expert import model
    from preparation import clean

    return file_contracts, metrics, registry, model, clean


fc, metrics_core, registry, expert_model, clean_core = _modules()
TrainError = registry.TrainError


def _load_split05():
    import importlib.util
    script = Path(__file__).resolve().parents[1] / "preparation" / "05_split_dataset.py"
    spec = importlib.util.spec_from_file_location("_train_split05", script)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


split05 = _load_split05()

METRICS_COLUMNS = (
    "model_name",
    "line",
    "metric",
    "value",
    "threshold",
    "n",
    "pos_rate",
    "dataset_version",
    "model_version",
    "computed_at",
)
_CONFIG_FIELDS = {
    "line",
    "feature_set",
    "algos",
    "hyperparams",
    "split",
    "seed",
    "decision_threshold",
    "register",
    "auto_load",
}
# One authoritative mapping: line decides the only legal feature_set, and vice versa.
FEATURE_SETS = {"kamei14": "expert", "codebert768": "semantic"}


def _invalid(message):
    raise TrainError(message)


def _json(value):
    return json.dumps(
        value, ensure_ascii=False, allow_nan=False, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")


def _now_z():
    return datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


def _number(value, field):
    if type(value) not in (int, float) or not math.isfinite(value):
        _invalid(f"{field} must be a finite native number, not a boolean or string")
    return value


def _unit_interval(value, field):
    value = _number(value, field)
    if not 0 < value < 1:
        _invalid(f"{field} must be strictly between 0 and 1")
    return float(value)


def _boundary(value):
    try:
        return clean_core._timestamp(value, "split.time_boundary")
    except clean_core.CleanError as error:
        raise TrainError(error.message) from error


def validate_config(raw: dict) -> dict:
    if not isinstance(raw, dict) or set(raw) - _CONFIG_FIELDS or not {"line", "algos"} <= set(raw):
        _invalid("Config requires line and algos and permits no unknown keys")
    selection = registry.validate_selection(raw["line"], raw["algos"], raw.get("hyperparams", {}))
    feature_set = raw.get("feature_set") or ("kamei14" if selection["line"] == "expert" else "codebert768")
    if not isinstance(feature_set, str) or feature_set not in FEATURE_SETS:
        _invalid("feature_set must be one of kamei14/codebert768")
    if FEATURE_SETS[feature_set] != selection["line"]:
        _invalid(f"feature_set {feature_set} is incompatible with line {selection['line']}")
    split = raw.get("split", {"ratio": 0.7})
    if not isinstance(split, dict) or not split or set(split) - {"ratio", "time_boundary"}:
        _invalid("split must be exactly one of ratio or time_boundary (random split forbidden)")
    if "ratio" in split and "time_boundary" in split:
        _invalid("split accepts ratio XOR time_boundary, not both")
    if "ratio" in split:
        split = {"ratio": _unit_interval(split["ratio"], "split.ratio")}
    else:
        split = {"time_boundary": _boundary(split["time_boundary"])}
    seed = raw.get("seed", 42)
    if type(seed) is not int or seed < 0:
        _invalid("seed must be a nonnegative integer, not boolean")
    threshold = _unit_interval(raw.get("decision_threshold", 0.5), "decision_threshold")
    for field in ("register", "auto_load"):
        if type(raw.get(field, False)) is not bool:
            _invalid(f"{field} must be boolean")
    return {
        "line": selection["line"],
        "feature_set": feature_set,
        "algos": selection["algos"],
        "hyperparams": selection["hyperparams"],
        "split": split,
        "seed": seed,
        "decision_threshold": threshold,
        "register": raw.get("register", False),
        "auto_load": raw.get("auto_load", False),
    }


def _ts(row):
    return datetime.fromisoformat(row["committed_at"].replace("Z", "+00:00"))


def _sorted_labeled(rows):
    labeled = [r for r in rows if r["is_bug_inducing"] is not None]
    return sorted(labeled, key=lambda r: (_ts(r), r["commit_hash"]))


def _strict_split(ordered, cut):
    """05 的严格秒级边界断言（与 clean._split 同一适配口径）。"""
    adapter = [{"committed_at": _ts(r).strftime(split05.TIMESTAMP_FORMAT)} for r in ordered]
    failures = split05.validate_split(adapter[:cut], adapter[cut:], len(ordered))
    if failures:
        _invalid("Temporal split rejected by 05_split_dataset: " + "; ".join(failures))


def _split_rows(ordered, split):
    if "ratio" in split:
        cut = split05.split_index(len(ordered), split["ratio"])
        _strict_split(ordered, cut)
        train, test = ordered[:cut], ordered[cut:]
        spec = {"ratio": split["ratio"]}
    else:
        boundary = datetime.fromisoformat(split["time_boundary"].replace("Z", "+00:00"))
        train = [r for r in ordered if _ts(r) <= boundary]
        test = [r for r in ordered if _ts(r) > boundary]
        if not train or not test:
            _invalid("time_boundary leaves an empty train or test side")
        _strict_split(ordered, len(train))
        spec = {"time_boundary": split["time_boundary"]}
    record = {
        **spec,
        "train_max": train[-1]["committed_at"],
        "test_min": test[0]["committed_at"],
        "train_hashes": [r["commit_hash"] for r in train],
        "test_hashes": [r["commit_hash"] for r in test],
    }
    return train, test, record


def _fingerprint(input_sha, feature_version, line, algo, applied, split, seed):
    payload = {
        "input_sha": input_sha,
        "feature_version": feature_version,
        "line": line,
        "algo": algo,
        "hyperparams": applied,
        "split": split,
        "seed": seed,
    }
    return hashlib.sha256(_json(payload)).hexdigest()


def _positive_proba(model, X):
    """predict_proba[:, 1]；单类训练退化时 sklearn 只给一列，按 classes_ 映射风险。"""
    import numpy as np

    matrix = model.predict_proba(X)
    if matrix.shape[1] == 2:
        return matrix[:, 1]
    classes = list(getattr(model, "classes_", [0]))
    return np.full(len(X), 1.0 if classes and classes[0] == 1 else 0.0)


def _bundle(algo, model, meta, feature_order):
    """单算法交付：直接导出 .pkl 权重 + 侧车元数据 JSON（不再打包 ZIP）。"""
    import joblib

    buffer = io.BytesIO()
    joblib.dump(model, buffer)
    feature_schema = {
        "line": meta.get("line"),
        "feature_set": meta.get("feature_set"),
        "feature_version": meta.get("feature_version"),
        "features": [
            {
                "name": name,
                "dtype": "float64",
                "source": meta.get("feature_set"),
                "version": meta.get("feature_version"),
            }
            for name in feature_order
        ],
        "training_transforms": ["log_transform", "standardize", "categorical_encode"],
    }
    sidecar = {**meta, "feature_schema": feature_schema}
    return {"pkl": buffer.getvalue(), "meta": _json(sidecar)}


def _sanitize(text):
    return re.sub(r"[\x00-\x1f\x7f]", " ", str(text))[:500]


def extract_features(commit_hashes: list[str], repo: str | None = None) -> list[dict]:
    """训练特征现算入口（可替换）；生产从绑定仓库计算，测试可 monkeypatch。"""
    from app import feature_source
    return feature_source.extract_many(commit_hashes, repo)


def run(rows: list[dict], config: dict, *, metadata: dict | None = None, progress=None) -> dict:
    import numpy as np

    normalized = validate_config(config)
    # 新契约：输入仅为 collected_commits/clean_dataset 二维表，不含模型特征；
    # 训练内核按线现算：expert 从绑定仓库算 14 维，semantic 用预计算/在线编码 768 维。
    # 缺来源即前置拒绝，不伪造向量。
    validated = clean_core._rows_external(rows)
    line = normalized["line"]
    repo = (metadata or {}).get("repo")
    if not repo:
        raise TrainError("external dataset requires a bound repository (metadata.repo) for feature extraction")
    feature_set = normalized["feature_set"]
    feature_order = (list(fc.FEATURE_COLUMNS) if feature_set == "kamei14"
                     else [f"semantic_{i}" for i in range(768)])
    try:
        if line == "expert":
            from app import feature_source
            computed = extract_features([row["commit_hash"] for row in validated], repo)
            by_hash = {item["commit_hash"]: item for item in computed}
            missing = [row["commit_hash"] for row in validated if row["commit_hash"] not in by_hash]
            if missing:
                raise TrainError(f"feature extraction missing {len(missing)} commits (e.g. {missing[0]})")
            for row in validated:
                row["_vector"] = feature_source.vector_from(by_hash[row["commit_hash"]])
        else:
            from app import semantic_source
            for row in validated:
                vector = semantic_source.embedding_for(row["commit_hash"])
                if vector is None:
                    raise TrainError(
                        f"semantic embedding unavailable for {row['commit_hash']} "
                        "(neither precomputed nor encodable from bound repository)"
                    )
                row["_vector"] = vector.astype(float).tolist()
    except TrainError:
        raise
    except Exception as error:
        raise TrainError(f"feature extraction failed: {error}") from error
    version = (metadata or {}).get("feature_version", "v1")
    if not isinstance(version, str) or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.-]{0,31}", version):
        raise TrainError("feature_version must be a valid string")
    input_sha = ((metadata or {}).get("input") or {}).get("sha256") or fc.sha256(_json(validated))
    ordered = _sorted_labeled(validated)
    unlabeled = len(validated) - len(ordered)
    train, test, split_record = _split_rows(ordered, normalized["split"])
    normalized.update(feature_version=version, split=split_record, input_sha=input_sha)
    warnings = [f"Input table lacked model features; {line} features computed in-train from bound repository."]
    warnings += list((metadata or {}).get("warnings", []))
    if unlabeled:
        warnings.append(f"{unlabeled} unlabeled rows excluded from training and evaluation.")
    X_train = np.array([r["_vector"] for r in train], dtype=float)
    y_train = np.array([r["is_bug_inducing"] for r in train], dtype=int)
    X_test = np.array([r["_vector"] for r in test], dtype=float)
    y_test = np.array([r["is_bug_inducing"] for r in test], dtype=int)
    threshold = normalized["decision_threshold"]
    fingerprint_split = {
        k: split_record[k] for k in ("ratio", "time_boundary") if k in split_record
    }
    models, metrics_rows, packages, predictions = [], [], {}, {}
    log = [
        "# W5 train log",
        f"line={normalized['line']} seed={normalized['seed']} "
        f"threshold={threshold} train_rows={len(train)} test_rows={len(test)}",
    ]
    total = len(normalized["algos"])
    for index, algo in enumerate(normalized["algos"]):
        applied = normalized["hyperparams"].get(algo, {})
        fp = _fingerprint(
            input_sha,
            version,
            normalized["line"],
            algo,
            applied,
            fingerprint_split,
            normalized["seed"],
        )
        model_name, version_key = f"{algo}_{fp[:8]}_v1", fp[:16]
        log.append(f"[{algo}] start model_name={model_name}")
        started = time.perf_counter()
        item = {
            "algo": algo,
            "model_name": model_name,
            "version_key": version_key,
            "feature_version": version,
            "status": "failed",
            "metrics": None,
            "warnings": [],
            "error": None,
            "elapsed_ms": 0.0,
            "hyperparams": dict(applied),
        }
        try:
            model = expert_model.build_model(algo, normalized["seed"])
            if applied:
                model.set_params(**applied)
            model.fit(X_train, y_train)
            proba = _positive_proba(model, X_test)
            summary, algo_warnings = metrics_core.safe_summary(y_test, proba, threshold)
            item.update(status="success", metrics=summary, warnings=algo_warnings)
            warnings.extend(algo_warnings)
            meta = {
                "model_name": model_name,
                "line": normalized["line"],
                "feature_set": feature_set,
                "algo": algo,
                "version_key": version_key,
                "feature_version": version,
                "trained_at": _now_z(),
                "hyperparams_snapshot": dict(applied),
                "split": {
                    k: split_record[k]
                    for k in (
                        "ratio",
                        "time_boundary",
                        "train_max",
                        "test_min",
                        "train_hashes",
                        "test_hashes",
                    )
                    if k in split_record
                },
                "seed": normalized["seed"],
                "feature_order": feature_order,
            }
            packages[algo] = _bundle(algo, model, meta, feature_order)
            predictions[algo] = {"y": y_test.tolist(), "proba": proba.tolist()}
            for metric in ("auc", "f1", "precision", "recall", "accuracy"):
                metrics_rows.append(
                    {
                        "model_name": model_name,
                        "line": normalized["line"],
                        "metric": metric,
                        "value": summary[metric],
                        "threshold": threshold,
                        "n": len(test),
                        "pos_rate": float(y_test.sum()) / len(test),
                        "dataset_version": input_sha,
                        "model_version": version_key,
                        "computed_at": _now_z(),
                    }
                )
        except Exception as error:  # 失败隔离：单算法失败不中断其余算法，也不产包
            item["error"] = _sanitize(error)
            log.append(f"[{algo}] error: {item['error']}")
        item["elapsed_ms"] = (time.perf_counter() - started) * 1000
        log.append(f"[{algo}] end status={item['status']} elapsed_ms={item['elapsed_ms']:.1f}")
        models.append(item)
        if progress:
            progress(algo, index + 1, total)
    success = [m for m in models if m["status"] == "success"]
    comparison = {
        "line": normalized["line"],
        "models": models,
        "split": split_record,
        "seed": normalized["seed"],
        "feature_version": version,
        "input_sha": input_sha,
    }
    return {
        "config": normalized,
        "summary": {
            "input_rows": len(validated),
            "labeled_rows": len(ordered),
            "unlabeled_rows": unlabeled,
            "train_rows": len(train),
            "test_rows": len(test),
            "success_count": len(success),
            "failed_count": len(models) - len(success),
            "warnings": list(dict.fromkeys(warnings)),
        },
        "models": models,
        "metrics_rows": metrics_rows,
        "trainset_rows": [{key: row.get(key) for key in fc.CLEAN_DATASET_COLUMNS} for row in train],
        "testset_rows": [{key: row.get(key) for key in fc.CLEAN_DATASET_COLUMNS} for row in test],
        "comparison": comparison,
        "packages": packages,
        "predictions": predictions,
        "log": "\n".join(log) + "\n",
    }


# ── figures（matplotlib 本地对象，确定性字节；退化场景显式标注）─────────────


def _figure(draw):
    from matplotlib.backends.backend_agg import FigureCanvasAgg
    from matplotlib.figure import Figure

    figure = Figure(figsize=(8, 5), dpi=100)
    FigureCanvasAgg(figure)
    draw(figure)
    figure.tight_layout()
    output = io.BytesIO()
    figure.savefig(output, format="png", metadata={"Software": "W5 train"})
    figure.clear()
    return output.getvalue()


def _curve_figure(result, kind):
    import numpy as np
    from sklearn.metrics import precision_recall_curve, roc_curve

    successes = [m for m in result["models"] if m["status"] == "success"]

    def draw(figure):
        axis = figure.subplots()
        skipped, plotted = [], False
        for item in successes:
            prediction = result["predictions"][item["algo"]]
            y = np.array(prediction["y"])
            proba = np.array(prediction["proba"])
            if len(np.unique(y)) < 2:
                skipped.append(item["algo"])
                continue
            if kind == "roc":
                xs, ys, _ = roc_curve(y, proba)
                axis.plot(xs, ys, label=item["algo"])
            else:
                xs, ys, _ = precision_recall_curve(y, proba)
                axis.plot(ys, xs, label=item["algo"])
            plotted = True
        if not plotted:
            axis.text(
                0.5,
                0.5,
                "Empty data" if not successes else "single class",
                transform=axis.transAxes,
                ha="center",
                va="center",
            )
        if kind == "roc":
            axis.plot([0, 1], [0, 1], linestyle="--", color="gray", linewidth=0.8)
            axis.set_xlabel("False positive rate")
            axis.set_ylabel("True positive rate")
        else:
            axis.set_xlabel("Recall")
            axis.set_ylabel("Precision")
        title = "ROC" if kind == "roc" else "Precision-Recall"
        if skipped:
            title += " (single class skipped: " + ", ".join(skipped) + ")"
        axis.set_title(title)
        if plotted:
            axis.legend(fontsize=8)

    return _figure(draw)


def _confusion_figure(result):
    import numpy as np
    from sklearn.metrics import confusion_matrix

    successes = [m for m in result["models"] if m["status"] == "success"]
    threshold = result["config"]["decision_threshold"]

    def draw(figure):
        if not successes:
            axis = figure.subplots()
            axis.text(0.5, 0.5, "Empty data", transform=axis.transAxes, ha="center", va="center")
            return
        axes = figure.subplots(1, len(successes), squeeze=False)
        for axis, item in zip(axes[0], successes, strict=True):
            prediction = result["predictions"][item["algo"]]
            y = np.array(prediction["y"])
            pred = (np.array(prediction["proba"]) >= threshold).astype(int)
            matrix = confusion_matrix(y, pred)
            axis.imshow(matrix, cmap="Blues")
            for (row, col), value in np.ndenumerate(matrix):
                axis.text(col, row, str(value), ha="center", va="center")
            axis.set_title(f"{item['algo']} @ {threshold}")
            axis.set_xlabel("Predicted")
            axis.set_ylabel("Actual")

    return _figure(draw)


def _metric_bars_figure(result):
    import numpy as np

    successes = [m for m in result["models"] if m["status"] == "success"]

    def draw(figure):
        axis = figure.subplots()
        if not successes:
            axis.text(0.5, 0.5, "Empty data", transform=axis.transAxes, ha="center", va="center")
            return
        names = [item["algo"] for item in successes]
        positions = np.arange(len(names))
        has_none = False
        for offset, metric, color in ((-0.2, "auc", "#4178a8"), (0.2, "f1", "#d98c38")):
            values = []
            for item in successes:
                value = item["metrics"][metric]
                has_none = has_none or value is None
                values.append(0.0 if value is None else value)
            axis.bar(positions + offset, values, width=0.4, label=metric, color=color)
        axis.set_xticks(positions, names)
        axis.set_ylim(0, 1)
        axis.set_ylabel("Score")
        title = "Effort-unaware metrics"
        if has_none:
            title += " (None drawn as 0)"
        axis.set_title(title)
        axis.legend(fontsize=8)

    return _figure(draw)


def artifacts(result: dict, job_id: str) -> dict[str, bytes]:
    if not isinstance(job_id, str) or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_-]{0,79}", job_id):
        _invalid("Invalid artifact job_id")
    output = {}
    for item in result["models"]:
        if item["status"] == "success":
            bundle = result["packages"][item["algo"]]
            output[f"train_{item['algo']}_model_{job_id}.pkl"] = bundle["pkl"]
            output[f"train_{item['algo']}_meta_{job_id}.json"] = bundle["meta"]
    testset = result.get("testset_rows")
    if not isinstance(testset, list) or not testset:
        _invalid("train result contains no testset rows; train_testset cannot be fabricated")
    if any(row.get("is_bug_inducing") in (None, "") for row in testset):
        _invalid("train testset rows must all carry a non-null is_bug_inducing label")
    trainset = result.get("trainset_rows")
    if not isinstance(trainset, list) or not trainset:
        _invalid("train result contains no trainset rows; train_trainset cannot be fabricated")
    for name, rows in (("train_trainset", trainset), ("train_testset", testset)):
        output[f"{name}_{job_id}.csv"] = fc.encode_table(fc.CLEAN_DATASET_COLUMNS, rows, "csv")
    return output


def code_version() -> str:
    digest = hashlib.sha256()
    for path in (
        BASE / "train.py",
        BASE / "registry.py",
        ROOT / "data_model/evaluation/metrics.py",
        ROOT / "data_model/pipelines/expert/model.py",
        ROOT / "data_model/pipelines/expert/metrics.py",
        ROOT / "data_model/preparation/05_split_dataset.py",
        ROOT / "data_model/preparation/clean.py",
        ROOT / "backend/app/services/file_contracts.py",
    ):
        digest.update(path.name.encode())
        digest.update(path.read_bytes())
    return "train-sha256:" + digest.hexdigest()


def _read_bounded(path: Path) -> bytes:
    if path.stat().st_size > fc.MAX_UPLOAD_BYTES:
        _invalid("File size exceeds MAX_UPLOAD_BYTES")
    content = path.read_bytes()
    if len(content) > fc.MAX_UPLOAD_BYTES:
        _invalid("File size exceeds MAX_UPLOAD_BYTES")
    return content


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(
        description="File-only W5 training CORE; no database. register/auto_load are DB-only "
        "server-side steps and are never performed by this CLI."
    )
    sub = parser.add_subparsers(dest="command", required=True)
    listed = sub.add_parser("algorithms", help="Print the registry catalog as JSON")
    listed.add_argument("--line", choices=registry.LINES)
    listed.add_argument("--enabled-only", action="store_true")
    command = sub.add_parser(
        "run", help="Train selected expert-line algorithms on a canonical table"
    )
    command.add_argument("--input", required=True, type=Path)
    command.add_argument("--line", required=True, choices=registry.LINES)
    command.add_argument("--feature-set", choices=tuple(FEATURE_SETS),
                         help="kamei14 for expert / codebert768 for semantic (defaults by line)")
    command.add_argument("--algos", required=True, help="Comma-separated algorithm names")
    command.add_argument("--hyperparams", type=Path, help="JSON file {algo: {param: value}}")
    command.add_argument("--split-ratio", type=float)
    command.add_argument("--time-boundary", help="ISO 8601 UTC boundary; train <= boundary < test")
    command.add_argument("--seed", type=int, default=42)
    command.add_argument("--threshold", type=float, default=0.5)
    command.add_argument("--manifest", type=Path)
    command.add_argument("--out", required=True, type=Path)
    args = parser.parse_args(argv)
    try:
        if args.command == "algorithms":
            print(
                _json(registry.algorithms(line=args.line, enabled_only=args.enabled_only)).decode()
            )
            return 0
        if args.split_ratio is not None and args.time_boundary is not None:
            _invalid("--split-ratio and --time-boundary are mutually exclusive")
        split = (
            {"time_boundary": args.time_boundary}
            if args.time_boundary is not None
            else {"ratio": args.split_ratio if args.split_ratio is not None else 0.7}
        )
        hyperparams = fc.read_json(_read_bounded(args.hyperparams)) if args.hyperparams else {}
        raw = {
            "line": args.line,
            "feature_set": args.feature_set or {"expert": "kamei14", "semantic": "codebert768"}[args.line],
            "algos": args.algos.split(","),
            "hyperparams": hyperparams,
            "split": split,
            "seed": args.seed,
            "decision_threshold": args.threshold,
            "register": False,
            "auto_load": False,
        }
        config = validate_config(raw)
        path = args.input.resolve(strict=True)
        companion = (
            args.manifest.resolve(strict=True)
            if args.manifest
            else path.with_suffix(".manifest.json")
        )
        content = _read_bounded(path)
        companion_content = (
            _read_bounded(companion) if args.manifest or companion.is_file() else None
        )
        rows, metadata = clean_core.parse_input(path.name, content, companion_content)
        inputs = [metadata["input"]]
        if companion_content is not None:
            inputs.append({"name": companion.name, "sha256": fc.sha256(companion_content)})
        repo = getattr(args, "repo", None)
        if not repo:
            try:
                from app import config as _app_config
                repo = _app_config.SOURCE_REPO
            except Exception:
                repo = None
        metadata["repo"] = str(repo) if repo else ""
        result = run(rows, config, metadata=metadata)
        job_id = str(uuid4())
        data = artifacts(result, job_id)
        from app.services import output_store

        output_store.OUTPUT_ROOT = args.out.resolve()
        published = output_store.publish_output(
            "train",
            data,
            inputs=inputs,
            config=result["config"],
            job_id=job_id,
            code_version=code_version(),
        )
        print(_json({**published, "summary": result["summary"], "models": result["models"]}).decode())
        return 0
    except (TrainError, fc.AppError, OSError, ValueError, TypeError) as error:
        message = (
            "Cannot access train input or output files"
            if isinstance(error, OSError)
            else getattr(error, "message", str(error))
        )
        print(
            _json({"code": getattr(error, "code", 40001), "message": message}).decode(),
            file=sys.stderr,
        )
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
