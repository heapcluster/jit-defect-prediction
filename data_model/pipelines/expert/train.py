"""expert 线训练 + 验证主流程（baseline）。

入口：`python -m pipelines.expert.train`（在 data_model/ 目录下）
流程：加载切分 → 逐模型 fit → 两类指标 → SHAP 实测 → 导出 .pkl + 交付清单 → 报告 + 图表。

与 `data_model/06_train_model.py` 的关系：本包是 06 的模块化等价实现（口径逐字一致），
产物落在本包 `models/`、`reports/` 下，不覆盖 06 的根目录产物。六条铁规矩照抄：
时间序切分不在此重切、特征口径以契约为准、数据集与模型不入库、不写接口不建库表。
"""

from __future__ import annotations

import argparse
import time
from pathlib import Path

import joblib
import numpy as np

from . import config, report
from .data import load_effort, load_splits, xy
from .metrics import effort_aware_metrics, effort_unaware
from .model import MODEL_NAMES, SHAP_LINEAR_MODELS, SHAP_TREE_MODELS, build_model


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="expert 线（Kamei14 baseline）训练与验证")
    p.add_argument("--train", type=Path, default=config.TRAIN_CSV)
    p.add_argument("--test", type=Path, default=config.TEST_CSV)
    p.add_argument("--features-raw", type=Path, default=config.FEATURES_RAW_CSV)
    p.add_argument("--models", default=",".join(config.DEFAULT_MODELS))
    p.add_argument("--delivery-models", default="lr,rf,xgb",
                   help="写入 feature_order.txt [models] 段的交付清单（默认契约口径）；"
                        "扩展模型只进评估不进交付（specs/model-coverage R6）")
    p.add_argument("--seed", type=int, default=config.SEED)
    p.add_argument("--model-dir", type=Path, default=config.MODELS_DIR)
    p.add_argument("--report", type=Path, default=config.REPORTS_DIR / "model_metrics.md")
    p.add_argument("--shap-rows", type=int, default=config.SHAP_ROWS)
    p.add_argument("--skip-shap", action="store_true")
    p.add_argument("--no-export", action="store_true", help="只出指标不导出 .pkl")
    p.add_argument("--no-charts", action="store_true")
    return p.parse_args()


def shap_latency(name: str, model, X_test: np.ndarray, n_rows: int) -> dict:
    if name not in SHAP_TREE_MODELS | SHAP_LINEAR_MODELS:
        return {"skipped": "无精确 SHAP 解释器（Tree/Linear Explainer 不适用）"}
    import shap
    rows = X_test[:n_rows]
    t0 = time.perf_counter()
    if name == "lr":
        explainer = shap.LinearExplainer(
            model.named_steps["lr"], model.named_steps["scaler"].transform(X_test[:200]))
    else:
        explainer = shap.TreeExplainer(model)
    cold_ms = (time.perf_counter() - t0) * 1000.0
    lat = []
    for i in range(len(rows)):
        x = rows[i:i + 1]
        t1 = time.perf_counter()
        if name == "lr":
            x = model.named_steps["scaler"].transform(x)
        explainer(x)
        lat.append((time.perf_counter() - t1) * 1000.0)
    lat = np.array(lat)
    return {"cold_ms": cold_ms, "p50_ms": float(np.percentile(lat, 50)),
            "p95_ms": float(np.percentile(lat, 95)), "max_ms": float(lat.max()),
            "rows": len(lat)}


def write_feature_order(model_dir: Path, wanted: list[str]) -> Path:
    order_file = model_dir / "feature_order.txt"
    order_file.write_text(
        "# 模型交付清单（expert 线包内副本；唯一权威是 docs/model/feature-columns.md）\n\n"
        "[models]\n"
        + "".join(f"{m}_v1.pkl\t{MODEL_NAMES.get(m, m)}\n" for m in wanted)
        + "\n[feature_order]\n"
        + "".join(f"{i + 1:2d}. {c}\n" for i, c in enumerate(config.FEATURE_FIELDS))
        + f"\n[decision]\n风险阈值 {config.DECISION_THRESHOLD:.2f}（服务端常量）\n",
        encoding="utf-8", newline="\n")
    return order_file


def main() -> int:
    args = parse_args()
    train, test = load_splits(args.train, args.test)
    X_train, y_train = xy(train)
    X_test, y_test = xy(test)
    effort_raw = load_effort(args.features_raw, test["commit_hash"])
    effort_sets = {"LOC（改动行数 la+ld）": effort_raw["effort_loc"].to_numpy(),
                   "改动文件数 nf": effort_raw["effort_files"].to_numpy()}

    wanted = [m.strip() for m in args.models.split(",") if m.strip()]
    results: dict[str, dict] = {}
    probas: dict[str, np.ndarray] = {}
    for name in wanted:
        model = build_model(name, args.seed)
        model.fit(X_train, y_train)
        proba = model.predict_proba(X_test)[:, 1]
        probas[name] = proba
        eu = effort_unaware(y_test, proba)
        row = {"model_name": f"{name}_v1", "label": MODEL_NAMES.get(name, name), **eu,
               "effort": {k: effort_aware_metrics(proba, y_test, e)
                          for k, e in effort_sets.items()}}
        if not args.skip_shap:
            try:
                row["shap"] = shap_latency(name, model, X_test, args.shap_rows)
            except (ImportError, AttributeError, TypeError, ValueError, RuntimeError, OSError) as exc:
                row["shap"] = {"error": f"{type(exc).__name__}: {exc}"}
        results[name] = row
        if not args.no_export:
            args.model_dir.mkdir(parents=True, exist_ok=True)
            joblib.dump(model, args.model_dir / (f"{name}_v1.pkl"))
        print(f"[expert] {name:<8} AUC={row['auc']:.4f}  F1={row['f1']:.4f}  P={row['precision']:.4f}  R={row['recall']:.4f}")

    if not args.no_export:
        delivery = [m.strip() for m in args.delivery_models.split(",") if m.strip()]
        order_file = write_feature_order(args.model_dir, delivery)
        print("[expert] 交付清单：{}（[models] = {}；其余模型仅评估）".format(order_file, ",".join(delivery)))

    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(report.render(args, train, test, results),
                           encoding="utf-8", newline="\n")
    print(f"[expert] 报告：{args.report}")
    if not args.no_charts:
        figs = report.make_charts(results, probas, y_test,
                                  effort_raw["effort_loc"].to_numpy(),
                                  args.report.parent / report.FIG_DIR_NAME)
        for f in figs:
            print(f"[expert] 图表：{f}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
