"""W7 独立评估核心：predictions（真标签随行透传）→ §3.6 指标/混淆/比较/两类 effort 图/报告。

公式单源 evaluation/metrics.py；不训练、不改概率、不依赖业务库或上游服务。
effort-aware 需 LOC 工作量输入（可选 §3.1 commits / §3.2 cleaned，按 la/ld 反变换还原），缺省时披露 missing_effort，但两类 effort 图仍作为课程硬产物交付。
"""

from __future__ import annotations

import argparse
import hashlib
import io
import json
import math
import sys
from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

BASE = Path(__file__).resolve().parent
ROOT = BASE.parents[1]


def _services():
    for source in (ROOT / "backend", ROOT / "data_model"):
        if str(source) not in sys.path:
            sys.path.insert(0, str(source))
    from app.services import file_contracts, output_store

    from evaluation import metrics

    return file_contracts, output_store, metrics


fc, output_store, metrics = _services()
METRIC_COLUMNS = [
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
]
CONFUSION_COLUMNS = ["model_name", "threshold", "tp", "fp", "fn", "tn"]


class EvaluateError(ValueError):
    code = 40001


def _invalid(message):
    raise EvaluateError(message)


def _json(value):
    return json.dumps(value, ensure_ascii=False, allow_nan=False, sort_keys=True).encode("utf-8")


def validate_config(raw):
    allowed = {
        "threshold",
        "metrics",
        "primary_metric",
        "effort_enabled",
        "report_format",
        "format",
        "model_names",
    }
    if not isinstance(raw, dict) or set(raw) - allowed:
        _invalid("评估配置含未知字段")
    threshold = raw.get("threshold", metrics.DECISION_THRESHOLD)
    if (
        isinstance(threshold, bool)
        or not isinstance(threshold, (int, float))
        or not 0 < threshold < 1
    ):
        _invalid("threshold 必须在开区间 (0,1)")
    keys = metrics.metric_keys()
    selected = raw.get("metrics", metrics.DEFAULT_METRICS)
    if (
        not isinstance(selected, list)
        or not selected
        or any(k not in keys for k in selected)
        or len(set(selected)) != len(selected)
    ):
        _invalid("metrics 必须为注册表内非空去重列表")
    primary = raw.get("primary_metric", "auc")
    if primary not in selected:
        _invalid("primary_metric 必须属于本次 metrics")
    effort_enabled = raw.get("effort_enabled", True)
    if type(effort_enabled) is not bool:
        _invalid("effort_enabled 必须为布尔")
    report_format = raw.get("report_format", "md")
    if report_format not in ("md", "html"):
        _invalid("report_format 只支持 md/html")
    fmt = raw.get("format", "csv")
    if fmt not in ("csv", "xlsx"):
        _invalid("format 只支持 csv/xlsx")
    model_names = raw.get("model_names")
    if model_names is not None and (
        not isinstance(model_names, list) or any(not isinstance(m, str) for m in model_names)
    ):
        _invalid("model_names 必须为字符串列表")
    return {
        "threshold": float(threshold),
        "metrics": selected,
        "primary_metric": primary,
        "effort_enabled": effort_enabled,
        "report_format": report_format,
        "format": fmt,
        "model_names": model_names,
    }


def parse_predictions(name, content):
    columns, rows = fc.read_table(name, content)
    if columns != list(fc.PREDICTIONS_COLUMNS):
        _invalid("predictions 列必须严格符合 §3.4")
    seen = set()
    out = []
    for row in rows:
        key = (row["commit_hash"], row["model_name"])
        if key in seen:
            _invalid("predictions 存在重复 (commit_hash, model_name)")
        seen.add(key)
        try:
            risk = float(row["risk_score"])
        except (TypeError, ValueError):
            _invalid("risk_score 必须为数值")
        if not 0 <= risk <= 1:
            _invalid("risk_score 必须在 [0,1]")
        if row["predicted_label"] not in ("0", "1", 0, 1):
            _invalid("predicted_label 必须为 0/1")
        label = row.get("is_bug_inducing")
        out.append(
            {
                **row,
                "risk_score": risk,
                "predicted_label": int(row["predicted_label"]),
                "is_bug_inducing": None if label in (None, "") else int(label),
            }
        )
    return out


def parse_effort(name, content):
    """新契约 §3.2/§3.3 不含 la/ld 模型特征，无法还原 LOC；返回空表触发 missing_effort。"""
    columns, _rows = fc.read_table(name, content)
    if not (set(columns) <= set(fc.CLEAN_DATASET_COLUMNS) and set(fc.COLLECTED_COMMITS_REQUIRED) <= set(columns)):
        _invalid("effort 输入须为 §3.3 train_testset（clean_dataset schema）")
    return {}


def join_labels(pred_rows):
    """新契约：真标签只在 predictions 行内，不再与独立标签文件合并。"""
    merged = [{**row, "is_bug_inducing": row["is_bug_inducing"]} for row in pred_rows]
    unlabeled = sum(1 for r in merged if r["is_bug_inducing"] is None)
    return merged, {"unlabeled": unlabeled}


def _figure():
    from matplotlib.backends.backend_agg import FigureCanvasAgg
    from matplotlib.figure import Figure

    figure = Figure(figsize=(6, 4), dpi=100)
    FigureCanvasAgg(figure)
    return figure


def _save(figure):
    buffer = io.BytesIO()
    figure.savefig(buffer, format="png", metadata={"Software": "W7 evaluate"})
    figure.clear()
    return buffer.getvalue()


def _annotate(figure, text):
    figure.subplots().text(
        0.5, 0.5, text, ha="center", va="center", transform=figure.subplots().transAxes
    )
    return _save(figure)


def run(pred_rows, config, *, effort=None, explanations=None, progress=None):
    import numpy as np
    from sklearn.metrics import confusion_matrix, precision_recall_curve, roc_curve

    cfg = validate_config(config)
    merged, label_stats = join_labels(pred_rows)
    models = {}
    for row in merged:
        models.setdefault(row["model_name"], []).append(row)
    if cfg["model_names"]:
        models = {name: rows for name, rows in models.items() if name in cfg["model_names"]}
    computed_at = datetime.now(UTC).replace(tzinfo=None, microsecond=0).isoformat() + "Z"
    dataset_version = hashlib.sha256(_json([r["commit_hash"] for r in pred_rows])).hexdigest()[:16]
    metric_rows, confusion_rows, comparison, unavailable, figures = [], [], [], [], {}
    effort_map = effort or {}
    for name, rows in models.items():
        if progress:
            progress(name, len(comparison), len(models))
        labeled = [r for r in rows if r["is_bug_inducing"] is not None]
        meta = rows[0]
        if not labeled:
            unavailable.append(
                {
                    "model_name": name,
                    "reason_code": "missing_labels",
                    "message": "无可用真标签，无法计算有监督指标",
                }
            )
            comparison.append(
                {
                    "model_name": name,
                    "metrics": {},
                    "n": 0,
                    "pos_rate": None,
                    "status": "unavailable",
                }
            )
            continue
        y = np.array([r["is_bug_inducing"] for r in labeled])
        proba = np.array([r["risk_score"] for r in labeled])
        eff = (
            np.array([effort_map.get(r["commit_hash"], 0) for r in labeled]) if effort_map else None
        )
        selected = (
            cfg["metrics"]
            if cfg["effort_enabled"]
            else [k for k in cfg["metrics"] if k not in metrics._EFFORT_KEYS]
        )
        values, reasons = metrics.compute_metrics(
            y, proba, cfg["threshold"], effort=eff, selected=selected
        )
        for reason in reasons:
            unavailable.append(
                {
                    "model_name": name,
                    "reason_code": reason["reason_code"],
                    "message": reason["message"],
                }
            )
        pos_rate = float(y.mean())
        for key in selected:
            metric_rows.append(
                {
                    "model_name": name,
                    "line": meta.get("line", "expert"),
                    "metric": key,
                    "value": values.get(key),
                    "threshold": cfg["threshold"],
                    "n": len(labeled),
                    "pos_rate": pos_rate,
                    "dataset_version": dataset_version,
                    "model_version": meta.get("model_version", ""),
                    "computed_at": computed_at,
                }
            )
        pred = (proba >= cfg["threshold"]).astype(int)
        tn, fp, fn, tp = confusion_matrix(y, pred, labels=[0, 1]).ravel()
        confusion_rows.append(
            {
                "model_name": name,
                "threshold": cfg["threshold"],
                "tp": int(tp),
                "fp": int(fp),
                "fn": int(fn),
                "tn": int(tn),
            }
        )
        comparison.append(
            {
                "model_name": name,
                "metrics": values,
                "n": len(labeled),
                "pos_rate": pos_rate,
                "model_version": meta.get("model_version", ""),
                "feature_version": meta.get("feature_version", ""),
                "status": "ok",
            }
        )
        if len(np.unique(y)) >= 2:
            fpr, tpr, _ = roc_curve(y, proba)
            fig = _figure()
            ax = fig.subplots()
            ax.plot(fpr, tpr, label=name)
            ax.plot([0, 1], [0, 1], "--", color="grey")
            ax.set_xlabel("FPR")
            ax.set_ylabel("TPR")
            ax.set_title("ROC")
            ax.legend()
            figures.setdefault("roc", []).append((name, _save(fig)))
            prec, rec, _ = precision_recall_curve(y, proba)
            fig = _figure()
            ax = fig.subplots()
            ax.plot(rec, prec, label=name)
            ax.set_xlabel("Recall")
            ax.set_ylabel("Precision")
            ax.set_title("PR")
            ax.legend()
            figures.setdefault("pr", []).append((name, _save(fig)))
        else:
            unavailable.append(
                {
                    "model_name": name,
                    "reason_code": "single_class_auc_undefined",
                    "message": "单类样本，ROC/PR 无定义",
                }
            )
    comparison.sort(
        key=lambda item: (
            item["metrics"].get(cfg["primary_metric"]) is None,
            -(item["metrics"].get(cfg["primary_metric"]) or 0),
        )
    )
    figures["confusion"] = [("all", _confusion_figure(confusion_rows))]
    figures["calibration"] = [("all", _calibration_figure(merged, cfg["threshold"]))]
    figures["effort_unaware"] = [("all", _effort_unaware_figure(merged))]
    figures["effort_aware"] = [("all", _effort_aware_figure(merged, effort_map))]
    if explanations:
        figures["feat_importance"] = [("all", _feat_importance_figure(explanations))]
    summary = {
        "models": list(models),
        "rows": len(merged),
        "unavailable": unavailable,
        "primary_metric": cfg["primary_metric"],
        "threshold": cfg["threshold"],
        "label_stats": label_stats,
        "effort": {"provided": len(effort_map),
                   "matched": sum(1 for r in merged if r["commit_hash"] in effort_map)},
    }
    return {
        "config": {**cfg, "dataset_version": dataset_version},
        "summary": summary,
        "metrics_rows": metric_rows,
        "confusion_rows": confusion_rows,
        "comparison": comparison,
        "unavailable": unavailable,
        "figures": figures,
    }


def _confusion_figure(confusion_rows):
    fig = _figure()
    ax = fig.subplots()
    if not confusion_rows:
        return _annotate(fig, "Empty data")
    labels = [r["model_name"] for r in confusion_rows]
    tp = [r["tp"] for r in confusion_rows]
    fp = [r["fp"] for r in confusion_rows]
    fn = [r["fn"] for r in confusion_rows]
    tn = [r["tn"] for r in confusion_rows]
    x = range(len(labels))
    width = 0.2
    ax.bar([i - 1.5 * width for i in x], tp, width, label="TP")
    ax.bar([i - 0.5 * width for i in x], fp, width, label="FP")
    ax.bar([i + 0.5 * width for i in x], fn, width, label="FN")
    ax.bar([i + 1.5 * width for i in x], tn, width, label="TN")
    ax.set_xticks(list(x))
    ax.set_xticklabels(labels, rotation=30, ha="right")
    ax.set_title("Confusion")
    ax.legend()
    fig.tight_layout()
    return _save(fig)


def _calibration_figure(merged, threshold):
    import numpy as np

    fig = _figure()
    ax = fig.subplots()
    labeled = [r for r in merged if r["is_bug_inducing"] is not None]
    if not labeled:
        return _annotate(fig, "Empty data")
    proba = np.array([r["risk_score"] for r in labeled])
    y = np.array([r["is_bug_inducing"] for r in labeled])
    bins = np.linspace(0, 1, 11)
    means, rates = [], []
    for lo, hi in zip(bins[:-1], bins[1:], strict=True):
        mask = (proba >= lo) & (proba < hi)
        if mask.any():
            means.append(float(proba[mask].mean()))
            rates.append(float(y[mask].mean()))
    ax.plot([0, 1], [0, 1], "--", color="grey")
    ax.plot(means, rates, "o-")
    ax.set_xlabel("Mean predicted")
    ax.set_ylabel("Observed positive rate")
    ax.set_title("Calibration")
    return _save(fig)


def _effort_unaware_figure(merged):
    fig = _figure()
    ax = fig.subplots()
    labeled = [r for r in merged if r["is_bug_inducing"] is not None]
    if not labeled:
        return _annotate(fig, "Empty data")
    order = sorted(labeled, key=lambda r: -r["risk_score"])
    total = sum(r["is_bug_inducing"] for r in order)
    xs, ys, cum = [0.0], [0.0], 0
    for i, row in enumerate(order, 1):
        cum += row["is_bug_inducing"]
        xs.append(i / len(order))
        ys.append(cum / total if total else 0)
    ax.plot(xs, ys)
    ax.set_xlabel("Fraction of commits reviewed")
    ax.set_ylabel("Recall")
    ax.set_title("Effort-unaware (probability order)")
    return _save(fig)


def _effort_aware_figure(merged, effort_map):
    import numpy as np

    fig = _figure()
    ax = fig.subplots()
    labeled = [r for r in merged if r["is_bug_inducing"] is not None]
    if not effort_map or not labeled:
        return _annotate(fig, "Effort data unavailable (LOC required)")
    effort = np.array([max(effort_map.get(r["commit_hash"], 0), 1) for r in labeled])
    y = np.array([r["is_bug_inducing"] for r in labeled])
    proba = np.array([r["risk_score"] for r in labeled])
    order = np.argsort(-(proba / effort), kind="stable")
    xs, ys = metrics.cumulative_curve(order, effort, y)
    ax.plot(xs, ys)
    ax.set_xlabel("Fraction of effort (LOC)")
    ax.set_ylabel("Recall")
    ax.set_title("Effort-aware (density order)")
    return _save(fig)


def _feat_importance_figure(explanations):
    fig = _figure()
    ax = fig.subplots()
    totals = {}
    for row in explanations:
        feature = row.get("feature")
        if feature:
            totals[feature] = totals.get(feature, 0) + abs(float(row.get("contribution", 0)))
    if not totals:
        return _annotate(fig, "Empty data")
    items = sorted(totals.items(), key=lambda kv: -kv[1])[:14]
    ax.barh([k for k, _ in items][::-1], [v for _, v in items][::-1])
    ax.set_title("Feature importance (|SHAP|)")
    fig.tight_layout()
    return _save(fig)


def _report(result):
    cfg = result["config"]
    summary = result["summary"]
    lines = [
        "# 评估报告",
        "",
        f"阈值：{cfg['threshold']} · 主指标：{cfg['primary_metric']} · 数据集版本：{cfg['dataset_version']}",
        f"样本行数：{summary['rows']} · 标签统计：{json.dumps(summary['label_stats'], ensure_ascii=False)}",
        "",
        "## 指标",
        "",
        "| 模型 | 指标 | 值 | n | 正样本率 |",
        "|---|---|---|---|---|",
    ]
    for row in result["metrics_rows"]:
        value = "" if row["value"] is None else f"{row['value']:.6f}"
        lines.append(
            f"| {row['model_name']} | {row['metric']} | {value} | {row['n']} | {row['pos_rate']:.4f} |"
        )
    lines += ["", "## 混淆矩阵", "", "| 模型 | TP | FP | FN | TN |", "|---|---|---|---|---|"]
    for row in result["confusion_rows"]:
        lines.append(
            f"| {row['model_name']} | {row['tp']} | {row['fp']} | {row['fn']} | {row['tn']} |"
        )
    lines += ["", "## 图件", ""]
    for kind in result["figures"]:
        lines.append(f"- evaluate_{kind}_<job_id>.png")
    lines += ["", "## 不可用原因", ""]
    if result["unavailable"]:
        for item in result["unavailable"]:
            lines.append(
                f"- {item.get('model_name', item.get('key', ''))}: {item['reason_code']} — {item['message']}"
            )
    else:
        lines.append("- 无")
    return "\n".join(lines) + "\n"


def artifacts(result, job_id):
    cfg = result["config"]
    fmt = cfg["format"]
    out = {}
    primary_metrics = fc.encode_table(METRIC_COLUMNS, result["metrics_rows"], fmt)
    out[f"evaluate_metrics_{job_id}.{fmt}"] = primary_metrics
    out[f"evaluate_metrics_{job_id}.{'xlsx' if fmt == 'csv' else 'csv'}"] = fc.encode_table(
        METRIC_COLUMNS, result["metrics_rows"], "xlsx" if fmt == "csv" else "csv"
    )
    out[f"evaluate_confusion_{job_id}.{fmt}"] = fc.encode_table(
        CONFUSION_COLUMNS, result["confusion_rows"], fmt
    )
    out[f"evaluate_confusion_{job_id}.{'xlsx' if fmt == 'csv' else 'csv'}"] = fc.encode_table(
        CONFUSION_COLUMNS, result["confusion_rows"], "xlsx" if fmt == "csv" else "csv"
    )
    out[f"evaluate_comparison_{job_id}.json"] = _json(
        {
            "primary_metric": cfg["primary_metric"],
            "models": result["comparison"],
            "unavailable": result["unavailable"],
        }
    )
    report = _report(result)
    if cfg["report_format"] == "html":
        report = (
            "<html><body><pre>"
            + report.replace("&", "&amp;").replace("<", "&lt;")
            + "</pre></body></html>"
        )
    out[f"evaluate_report_{job_id}.{cfg['report_format']}"] = report.encode("utf-8")
    for kind, items in result["figures"].items():
        out[f"evaluate_{kind}_{job_id}.png"] = items[0][1]
    return out


def code_version():
    digest = hashlib.sha256()
    for path in (
        BASE / "metrics.py",
        BASE / "evaluate.py",
        ROOT / "backend/app/services/file_contracts.py",
    ):
        digest.update(path.name.encode())
        digest.update(path.read_bytes())
    return "evaluate-sha256:" + digest.hexdigest()


def _bounded(path):
    if path.stat().st_size > fc.MAX_UPLOAD_BYTES:
        _invalid("文件超过大小限制")
    return path.read_bytes()


def main(argv=None):
    # CLI JSON stdout must be UTF-8 on every platform (Windows console defaults to GBK).
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(description="独立评估 CLI（无业务库）")
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("metrics")
    command = sub.add_parser("run")
    command.add_argument("--predictions", required=True)
    command.add_argument("--effort")
    command.add_argument("--threshold", type=float, default=0.5)
    command.add_argument("--metrics")
    command.add_argument("--primary-metric", default="auc")
    command.add_argument("--effort-enabled", default="true")
    command.add_argument("--report-format", choices=("md", "html"), default="md")
    command.add_argument("--format", choices=("csv", "xlsx"), default="csv")
    command.add_argument("--out", required=True)
    args = parser.parse_args(argv)
    try:
        if args.command == "metrics":
            print(_json(metrics.registry()).decode())
            return 0
        config = {
            "threshold": args.threshold,
            "primary_metric": args.primary_metric,
            "effort_enabled": args.effort_enabled.lower() == "true",
            "report_format": args.report_format,
            "format": args.format,
        }
        if args.metrics:
            config["metrics"] = args.metrics.split(",")
        cfg = validate_config(config)
        pred_path = Path(args.predictions).resolve(strict=True)
        pred_rows = parse_predictions(pred_path.name, _bounded(pred_path))
        effort_map = (
            parse_effort(Path(args.effort).name, _bounded(Path(args.effort)))
            if args.effort
            else None
        )
        result = run(pred_rows, cfg, effort=effort_map)
        job_id = str(uuid4())
        data = artifacts(result, job_id)
        output_store.OUTPUT_ROOT = Path(args.out).resolve()
        inputs = [
            {
                "name": pred_path.name,
                "sha256": fc.sha256(_bounded(pred_path)),
                "rows": len(pred_rows),
            }
        ]
        if args.effort:
            inputs.append(
                {"name": Path(args.effort).name, "sha256": fc.sha256(_bounded(Path(args.effort)))}
            )
        published = output_store.publish_output(
            "evaluate", data, inputs=inputs, config=cfg, job_id=job_id, code_version=code_version()
        )
        print(_json({**published, "summary": result["summary"]}).decode())
        return 0
    except (EvaluateError, fc.AppError, OSError, ValueError, TypeError) as error:
        print(
            _json(
                {
                    "code": getattr(error, "code", 40001),
                    "message": getattr(error, "message", str(error)),
                }
            ).decode(),
            file=sys.stderr,
        )
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
