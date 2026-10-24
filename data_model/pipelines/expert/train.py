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
from .model import (
    MODEL_NAMES,
    SHAP_LINEAR_MODELS,
    SHAP_TREE_MODELS,
    TabNetWithEarlyStop,
    build_model,
)


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
    p.add_argument("--report", type=Path, default=None,
                   help="报告输出路径。默认 model_metrics.md（重训产出的权威指标）；"
                        "--from-saved 时默认落到 model_metrics_from_saved.md —— 旧权重复算"
                        "属于探索性结果，不覆盖权威报告（评审意见 #1）")
    p.add_argument("--shap-rows", type=int, default=config.SHAP_ROWS)
    p.add_argument("--skip-shap", action="store_true")
    p.add_argument("--no-export", action="store_true", help="只出指标不导出 .pkl")
    p.add_argument("--no-charts", action="store_true")
    p.add_argument("--from-saved", action="store_true",
                   help="不训练：读 --model-dir 下已有的 *_v1.pkl 复算指标，重写报告并补 figures")
    return p.parse_args()


def fig_dir_for(args: argparse.Namespace) -> Path:
    """图表输出目录：``--from-saved`` 恒落 ``<报告目录>/figs_from_saved/``。

    旧权重复算属于探索性结果（报告已隔离到 ``model_metrics_from_saved.md``），
    图表必须同样隔离 —— 否则重训之后跑一次 ``--from-saved``，就会用来源不明的
    旧权重覆盖权威报告关联的 ``reports/figs/`` 三张图，造成图文口径混杂
    （PR #88 复审阻断项 2）。回归测试：``tests/test_from_saved_isolation.py``。
    """
    return args.report.parent / report.fig_dir_name(args.from_saved)


def from_saved(args: argparse.Namespace, train, test, X_test: np.ndarray, y_test: np.ndarray,
               effort_sets: dict, effort_loc: np.ndarray, wanted: list[str]) -> int:
    """不重训，用已保存的 .pkl 复算指标 → 重写 Markdown 报告 + 出图。

    SHAP 这一段不重算（需要 shap 与逐条前向，且旧值属于旧批次模型），
    报告里会如实显示「未实测」。
    """
    results: dict[str, dict] = {}
    probas: dict[str, np.ndarray] = {}
    for name in wanted:
        pkl = args.model_dir / (f"{name}_v1.pkl")
        if not pkl.is_file():
            print(f"[expert] 缺权重，跳过：{pkl.name}")
            continue
        try:
            model = joblib.load(pkl)
        except AttributeError:
            # 旧脚本产物：包装类被 pickle 成 __main__.TabNetWithEarlyStop，注入别名后重试
            import __main__
            if not hasattr(__main__, TabNetWithEarlyStop.__name__):
                setattr(__main__, TabNetWithEarlyStop.__name__, TabNetWithEarlyStop)
            try:
                model = joblib.load(pkl)
                print(f"[expert] {pkl.name} 为旧产物（类定义在 __main__），已用兼容别名回读")
            except Exception as exc:  # noqa: BLE001 —— 旧 pickle 反序列化可能抛任意异常
                print(f"[expert] 无法回读 {pkl.name}：{type(exc).__name__}: {exc}")
                continue
        except Exception as exc:  # noqa: BLE001 —— pkl 反序列化可能抛任意异常
            print(f"[expert] 无法回读 {pkl.name}：{type(exc).__name__}: {exc}")
            continue
        proba = model.predict_proba(X_test)[:, 1]
        probas[name] = proba
        results[name] = {"model_name": f"{name}_v1", "label": MODEL_NAMES.get(name, name),
                         **effort_unaware(y_test, proba),
                         # 评审下限按口径各配一份（LOC→行 / nf→文件），不能共用 10
                         "effort": {k: effort_aware_metrics(
                             proba, y_test, e,
                             review_floor=config.EFFORT_REVIEW_FLOORS.get(k))
                             for k, e in effort_sets.items()}}
        print(f"[expert] {name:<8} AUC={results[name]['auc']:.4f} "
              f"F1={results[name]['f1']:.4f}（自 {pkl.name} 复算）")
    if not results:
        print("[expert] 没有可用权重，未出报告")
        return 2

    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(report.render(args, train, test, results),
                           encoding="utf-8", newline="\n")
    print(f"[expert] 报告：{args.report}")

    if not args.no_charts:
        try:
            figs = report.make_charts(results, probas, y_test, effort_loc,
                                      fig_dir_for(args))
        except ImportError as exc:
            print(f"[expert] 出图需要 matplotlib（environment.yml 已固定 3.10.1）：{exc}")
            return 3
        for f in figs:
            print(f"[expert] 图表：{f}")
    return 0


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
    """写交付清单副本（契约二第三节的副本，不是权威）。

    ``[models]`` = 契约交付集（``--delivery-models``，默认 lr/rf/xgb）；
    ``[evaluated]`` = **目录里真实存在的** ``*_v1.pkl`` 减交付集
    （specs/model-coverage R6：只进评估）。两段都写，是为了让「目录里有 8 个
    .pkl、清单里只有 3 个」不被读成漏交付；取磁盘而不是取
    ``config.DEFAULT_MODELS``，是因为训练口径会变，写死的清单只会漂移。

    注意：仓库里 ``feature_order.txt`` 还带 ``[contract]`` / ``[how_to_load]`` /
    ``[dependencies]`` 三段手工维护内容，本函数**不生成**这三段 —— 重训会用本函数
    的输出覆盖整个文件，那三段会丢（既有问题，非本次引入）。要保住它们，得先把
    本函数改成「读原文件、保留未知段」再重写。
    """
    order_file = model_dir / "feature_order.txt"
    delivered = {f"{m}_v1" for m in wanted}
    on_disk = sorted(p.stem for p in model_dir.glob("*_v1.pkl"))
    evaluated = [m for m in on_disk if m not in delivered]

    def _label(stem: str) -> str:
        base = stem.removesuffix("_v1")
        return MODEL_NAMES.get(base, base)

    text = (
        "# 模型交付清单（expert 线包内副本；唯一权威是 docs/model/feature-columns.md）\n\n"
        "[models]\n"
        + "".join(f"{m}_v1.pkl\t{MODEL_NAMES.get(m, m)}\n" for m in wanted)
    )
    if evaluated:
        text += (
            "\n[evaluated]\n"
            "# 本轮已训练、仅进评估不进交付（specs/model-coverage R6）。如需投放，\n"
            "# 先按 expert/README.md「权重投放与联调自检」一节自检，再改 [models]。\n"
            + "".join(f"{m}.pkl\t{_label(m)}\n" for m in evaluated)
        )
    text += (
        "\n[feature_order]\n"
        + "".join(f"{i + 1:2d}. {c}\n" for i, c in enumerate(config.FEATURE_FIELDS))
        + f"\n[decision]\n风险阈值 {config.DECISION_THRESHOLD:.2f}（服务端常量）\n"
    )
    order_file.write_text(text, encoding="utf-8", newline="\n")
    return order_file


def main() -> int:
    args = parse_args()
    if args.report is None:
        args.report = config.REPORTS_DIR / (
            "model_metrics_from_saved.md" if args.from_saved else "model_metrics.md")
    train, test = load_splits(args.train, args.test)
    overlap = set(train["commit_hash"]) & set(test["commit_hash"])
    if overlap:
        # 泄漏闸门：时间序切分一旦被测集复用就会把 AUC 抬高，宁可不出报告
        print(f"[expert] 训练集与检验集重叠 {len(overlap)} 条提交，拒绝出报告（先修切分）")
        return 2
    X_train, y_train = xy(train)
    X_test, y_test = xy(test)
    effort_raw = load_effort(args.features_raw, test["commit_hash"])
    effort_sets = {"LOC（改动行数 la+ld）": effort_raw["effort_loc"].to_numpy(),
                   "改动文件数 nf": effort_raw["effort_files"].to_numpy()}

    wanted = [m.strip() for m in args.models.split(",") if m.strip()]
    if args.from_saved:
        return from_saved(args, train, test, X_test, y_test, effort_sets,
                          effort_raw["effort_loc"].to_numpy(), wanted)

    results: dict[str, dict] = {}
    probas: dict[str, np.ndarray] = {}
    for name in wanted:
        model = build_model(name, args.seed)
        model.fit(X_train, y_train)
        proba = model.predict_proba(X_test)[:, 1]
        probas[name] = proba
        eu = effort_unaware(y_test, proba)
        row = {"model_name": f"{name}_v1", "label": MODEL_NAMES.get(name, name), **eu,
               "effort": {k: effort_aware_metrics(
                   proba, y_test, e,
                   review_floor=config.EFFORT_REVIEW_FLOORS.get(k))
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
        print("[expert] 交付清单：{}（[models] = {}）".format(order_file, ",".join(delivery)))

    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(report.render(args, train, test, results),
                           encoding="utf-8", newline="\n")
    print(f"[expert] 报告：{args.report}")
    if not args.no_charts:
        figs = report.make_charts(results, probas, y_test,
                                  effort_raw["effort_loc"].to_numpy(),
                                  fig_dir_for(args))
        for f in figs:
            print(f"[expert] 图表：{f}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
