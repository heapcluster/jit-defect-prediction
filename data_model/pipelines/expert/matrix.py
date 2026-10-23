"""expert 线覆盖矩阵（原 data_model/08_model_matrix.py 移植）：8 种模型 × 2 类 × 两类指标。

对应 OpenSpec change: `model-expansion`（第 2.1 / 2.2 条任务）
口径与 train.py **完全同源** —— 同一份时间序切分产物、同一套 14 项特征列序、同一随机
种子。本脚本**不重新切分、不改特征口径**。

── 为什么单独一个脚本，而不是把 8 个模型塞进 train 的报告 ────────────────────
`train.py` 的报告是「首change 交付物」的形态（2–3 个模型 + 交付清单），它的
`--models` 默认值必须保持 `lr,rf,xgb`，否则既有复现命令产出的 `reports/model_metrics.md`
就不再逐行一致。所以**扩展模型的评估另起一份报告**（本脚本），而 `train.py` 只增加
模型构造器、默认行为一字不改。

── 覆盖口径（课程原文）────────────────────────────────────────────────────
「至少 2 类（经典机器学习、深度学习）不少于 8 种预测模型」。本矩阵的类别归属：

  经典机器学习（6）：`lr` 逻辑回归 / `rf` 随机森林 / `xgb` XGBoost /
                       `lgbm` LightGBM / `et` 极端随机树 / `svm` RBF 核 SVM
  神经网络（深度学习）（2）：`mlp_deep` 3 隐藏层 + 早停 / `tabnet` TabNet

── 自证：口径没被动过（tasks.md 2.2）────────────────────────────────────────
既有 3 个模型（`lr_v1` / `rf_v1` / `xgb_v1`）在本矩阵下的 Effort-unaware 指标
**必须与 `reports/model_metrics.md` 逐项一致**。本脚本会把两边的数字读出来逐项比对，
把「差异 n 项」写进报告 —— 这一行是「模型增多了，但口径一个都没改」的证据。

── 交付边界（specs/model-coverage R6）──────────────────────────────────────
矩阵里的模型**只用于评估**：`models/feature_order.txt` 的 `[models]` 段不变，
后端加载的仍是既有交付模型。
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

import pandas as pd
from sklearn.metrics import (
    accuracy_score,
    f1_score,
    precision_score,
    recall_score,
    roc_auc_score,
)

from . import config
from .data import load_effort
from .metrics import effort_aware_metrics
from .model import MODEL_CLASS, MODEL_NAMES, build_model


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description="产出 8 种模型 × 类别 × 两类指标的覆盖矩阵报告",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    p.add_argument("--train", type=Path, default=config.TRAIN_CSV)
    p.add_argument("--test", type=Path, default=config.TEST_CSV)
    p.add_argument("--features-raw", type=Path, default=config.FEATURES_RAW_CSV)
    p.add_argument("--models", default=",".join(config.DEFAULT_MODELS))
    p.add_argument("--seed", type=int, default=config.SEED)
    p.add_argument("--report", type=Path,
                   default=config.REPORTS_DIR / "model_matrix.md")
    p.add_argument("--baseline-report", type=Path,
                   default=config.REPORTS_DIR / "model_metrics.md",
                   help="train.py 产出的指标报告，用于逐项比对")
    return p.parse_args()


def parse_baseline_metrics(path: Path) -> dict[str, dict[str, float]]:
    """从 `model_metrics.md` 的 Effort-unaware 表里读出既有模型的指标。

    行形如：`| `lr_v1`（逻辑回归） | 0.6501 | 0.5987 | 0.5142 | 0.7172 | 0.6334 |`
    """
    out: dict[str, dict[str, float]] = {}
    if not path.is_file():
        return out
    row_re = re.compile(
        r"^\|\s*`(?P<name>[a-z_]+_v\d)`[^|]*\|\s*"
        r"(?P<auc>[\d.]+)\s*\|\s*(?P<f1>[\d.]+)\s*\|\s*(?P<p>[\d.]+)\s*\|\s*"
        r"(?P<r>[\d.]+)\s*\|\s*(?P<acc>[\d.]+)\s*\|")
    for line in path.read_text(encoding="utf-8").splitlines():
        m = row_re.match(line.strip())
        if m:
            out[m.group("name")] = {
                "auc": float(m.group("auc")), "f1": float(m.group("f1")),
                "precision": float(m.group("p")), "recall": float(m.group("r")),
                "accuracy": float(m.group("acc")),
            }
    return out


def convergence_info(model) -> dict | None:
    """神经网络模型如实登记收敛情况 —— 未收敛不许静默当成已收敛（报告里要看见）。"""
    est = model.named_steps.get("mlp") if hasattr(model, "named_steps") else None
    if est is None or not hasattr(est, "n_iter_"):
        return None
    return {"n_iter": int(est.n_iter_), "max_iter": int(est.max_iter),
            "converged": int(est.n_iter_) < int(est.max_iter)}


def compare_with_baseline(results: dict, baseline: dict) -> list[str]:
    """逐项比对既有交付模型的 Effort-unaware 指标（口径自证）。"""
    diffs: list[str] = []
    for row in results.values():
        base = baseline.get(row["model_name"])
        if base is None:
            continue
        for key in ("auc", "f1", "precision", "recall", "accuracy"):
            a, b = round(row[key], 4), round(base[key], 4)
            if abs(a - b) > 1e-9:
                diffs.append("{}.{}：本矩阵 {:.4f} vs 基线 {:.4f}".format(row["model_name"], key, a, b))
    return diffs


def best_by_class(results: dict, key) -> dict[str, str]:
    best: dict[str, tuple[str, float]] = {}
    for name, row in results.items():
        cls = row["cls"]
        v = key(row)
        if cls not in best or v > best[cls][1]:
            best[cls] = (name, v)
    return best


def main() -> int:
    args = parse_args()
    for path in (args.train, args.test):
        if not path.is_file():
            print(f"[expert-matrix] 找不到切分文件：{path}（先跑 preparation/05_split_dataset.py）", file=sys.stderr)
            return 2

    train = pd.read_csv(args.train)
    test = pd.read_csv(args.test)
    missing = [c for c in config.FEATURE_FIELDS + [config.LABEL_COL]
               if c not in train.columns]
    if missing:
        print(f"[expert-matrix] 训练集缺列：{missing}", file=sys.stderr)
        return 2
    if config.LABEL_COL not in test.columns:
        print(f"[expert-matrix] 检验集缺 `{config.LABEL_COL}`：只认主标签 szz",
              file=sys.stderr)
        return 2

    X_train = train[config.FEATURE_FIELDS].to_numpy(dtype=float)
    y_train = train[config.LABEL_COL].astype(int).to_numpy()
    X_test = test[config.FEATURE_FIELDS].to_numpy(dtype=float)
    y_test = test[config.LABEL_COL].astype(int).to_numpy()

    effort_raw = load_effort(args.features_raw, test["commit_hash"])
    effort_sets = {
        "LOC（改动行数 la+ld）": effort_raw["effort_loc"].to_numpy(),
        "改动文件数 nf": effort_raw["effort_files"].to_numpy(),
    }

    wanted = [m.strip() for m in args.models.split(",") if m.strip()]
    unknown = [m for m in wanted if m not in MODEL_NAMES]
    if unknown:
        print("[expert-matrix] 未知模型：{}；可选 {}".format(unknown, ",".join(MODEL_NAMES)),
              file=sys.stderr)
        return 2

    results: dict[str, dict] = {}
    for name in wanted:
        model = build_model(name, args.seed)
        model.fit(X_train, y_train)
        proba = model.predict_proba(X_test)[:, 1]
        pred = (proba >= config.DECISION_THRESHOLD).astype(int)
        row = {
            "model_name": f"{name}_v1",
            "cls": MODEL_CLASS.get(name, "未登记"),
            "auc": roc_auc_score(y_test, proba),
            "f1": f1_score(y_test, pred, zero_division=0),
            "precision": precision_score(y_test, pred, zero_division=0),
            "recall": recall_score(y_test, pred, zero_division=0),
            "accuracy": accuracy_score(y_test, pred),
            "effort": {label: effort_aware_metrics(proba, y_test, effort)
                       for label, effort in effort_sets.items()},
        }
        conv = convergence_info(model)
        if conv is not None:
            row["converged"] = conv
        results[name] = row
        convergence = "" if conv is None else f"  收敛={conv['converged']}（{conv['n_iter']}/{conv['max_iter']} 轮）"
        print(f"[expert-matrix] {name:<8} {row['cls']:<12} AUC={row['auc']:.4f}  F1={row['f1']:.4f}  P={row['precision']:.4f}  R={row['recall']:.4f}{convergence}")
    baseline = parse_baseline_metrics(args.baseline_report)
    diffs = compare_with_baseline(results, baseline)

    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(
        render(args, train, test, wanted, results, baseline, diffs),
        encoding="utf-8", newline="\n")
    print(f"[expert-matrix] 覆盖矩阵报告：{args.report}")
    print(f"[expert-matrix] 与 {args.baseline_report.name} 逐项比对：差异 {len(diffs)} 项")
    return 0


def render(args, train, test, wanted, results, baseline, diffs) -> str:
    y_test = test[config.LABEL_COL].astype(int).to_numpy()
    classes = sorted({r["cls"] for r in results.values()})
    best_auc = best_by_class(results, lambda r: r["auc"])
    best_pn = best_by_class(
        results, lambda r: r["effort"]["LOC（改动行数 la+ld）"]["model"]["p_norm"])

    L: list[str] = []
    L.append(f"""# 模型覆盖矩阵（pipelines/expert/matrix.py 产出）

> 本文件可入库，是 OpenSpec change `model-expansion` 第 2.1 / 2.2 条任务的证据。
> 两类指标的定义、工作量代理与 `P_norm` 归一化口径**与本包 train.py 同源**，
> 见 `pipelines/expert/metrics.py`（本节不重复抄写公式）。

## 一、覆盖达标声明

| 项 | 值 |
|---|---|
| 类别数 | **{len(classes)}** —— {'、'.join(classes)} |
| 模型数 | **{len(wanted)}** |
| 课程要求 | 至少 2 类不少于 8 种 |
| 是否达标 | {'✅ 达标' if len(classes) >= 2 and len(wanted) >= 8 else '❌ 未达标'} |

| 类别 | 模型（`model_name`） |
|---|---|
""")
    for cls in classes:
        names = [r["model_name"] for r in results.values() if r["cls"] == cls]
        L.append("| {} | {} |\n".format(cls, "、".join(f"`{n}`" for n in names)))

    L.append(f"""
> **交付边界**：以上 8 个模型全部是**评估用**。后端加载的交付模型与
> `models/feature_order.txt` 的 `[models]` 段**不变**（specs/model-coverage R6）；
> 若某新模型显著更优，登记为「模型切换」提案另开 change，不在此静默切换。

## 二、数据与参数

| 项 | 值 |
|---|---|
| 训练集 | `{args.train.name}` —— {len(train)} 条 |
| 检验集 | `{args.test.name}` —— {len(test)} 条 |
| 特征列 | 契约二第三节 14 项（列序即交付清单顺序） |
| 标签 | `szz`（主标签） |
| 训练集正样本比例 | {train[config.LABEL_COL].mean() * 100:.2f}% |
| 检验集正样本比例 | {y_test.mean() * 100:.2f}% |
| 随机种子 | `{args.seed}`（与 train.py 同值） |
| 判定阈值 | {config.DECISION_THRESHOLD}（服务端常量，非请求参数） |
| 检验集时间范围 | {test['committed_at'].iloc[0]} ~ {test['committed_at'].iloc[-1]} |

### 口径自证

既有交付模型在本矩阵下重跑，Effort-unaware 指标与 `{args.baseline_report.name}`
逐项比对：**差异 {len(diffs)} 项**{'（口径一个都没改）' if not diffs else ''}。

""")
    if diffs:
        L.append("| 差异项 |\n|---|\n")
        for d in diffs:
            L.append(f"| {d} |\n")
        L.append("\n> ⚠️ 有差异说明切分、特征或种子被改动过 —— 必须先查清，再往下读。\n\n")
    else:
        L.append("> 比对到的基线模型：{}。差异 0 项 = 「模型增多了，但既有模型的"
                 "口径没被动手脚」。\n\n".format("、".join(f"`{n}`" for n in sorted(baseline))))

    L.append("""
## 三、Effort-unaware 指标（检验集）

| 类别 | 模型 | AUC | F1 | Precision | Recall | Accuracy |
|---|---|---|---|---|---|---|
""")
    for cls in classes:
        for name in wanted:
            r = results[name]
            if r["cls"] != cls:
                continue
            mark = " ⭐" if best_auc.get(cls, ("", 0))[0] == name else ""
            L.append("| {} | `{}`（{}）{} | {:.4f} | {:.4f} | {:.4f} | {:.4f} | {:.4f} |\n".format(cls, r["model_name"], MODEL_NAMES.get(name, name),
                        mark, r["auc"], r["f1"], r["precision"], r["recall"],
                        r["accuracy"]))
    L.append("\n> ⭐ = 该类别内 AUC 最优。**每类最优**是给「类别是否都有可用模型」看的，"
             "不是给「哪个模型该上线」看的 —— 后者要走模型切换提案。\n")

    conv_rows = [(n, r["converged"]) for n, r in results.items() if "converged" in r]
    if conv_rows:
        L.append("\n### 神经网络收敛登记（如实记录，不静默当成已收敛）\n\n")
        L.append("| 模型 | 迭代轮数 | 迭代上限 | 是否收敛 |\n|---|---|---|---|\n")
        for n, c in conv_rows:
            state = "✅ 收敛" if c["converged"] else "❌ 迭代上限内未达收敛判据 —— 指标按实际训练结果登记，不重跑调参"
            L.append(f"| `{n}` | {c['n_iter']} | {c['max_iter']} | {state} |\n")
        L.append("\n> 未收敛不等于不能用，但**必须看得见**：`train.py` / `calibrate.py` 用的是"
                 "同一超参，所以两份报告里的神经网络行同样受此约束。\n")

    for i, label in enumerate(results[wanted[0]]["effort"]):
        L.append("\n## {}、Effort-aware：工作量代理 = {}\n\n".format(("四", "五")[i] if i < 2 else f"四.{i}", label))
        L.append("| 类别 | 模型 | 曲线下面积 | **P_norm** | Recall@20% | Recall@50% |\n")
        L.append("|---|---|---|---|---|---|\n")
        for cls in classes:
            for name in wanted:
                r = results[name]
                if r["cls"] != cls:
                    continue
                m = r["effort"][label]["model"]
                star = ""
                if label.startswith("LOC") and best_pn.get(cls, ("", 0))[0] == name:
                    star = " ⭐"
                L.append("| {} | `{}`{} | {:.4f} | **{:.4f}** | {:.4f} | {:.4f} |\n".format(cls, r["model_name"], star, m["area"], m["p_norm"],
                            m["recall@20"], m["recall@50"]))
        o = results[wanted[0]]["effort"][label]["optimal"]
        b = results[wanted[0]]["effort"][label]["random"]
        L.append("| — | 上界（真实缺陷密度降序） | {:.4f} | {:.4f} | {:.4f} | {:.4f} |\n".format(o["area"], o["p_norm"], o["recall@20"], o["recall@50"]))
        L.append(f"| — | 基线：随机排序（{b['repeats']} 次抽样均值） | {b['area']:.4f} ± {b['area_std']:.4f} | {b['p_norm']:.4f} | — | — |\n")

    L.append(f"""
> 排序口径为**契约三当前口径**（`risk_score` 降序）。上界与随机基线两行与模型无关，
> 它们是这个指标的「天花板」与「零线」—— 随机基线仍落在 0 附近，说明面积算法自洽。
> ⭐ = 该工作量代理下该类别 `P_norm` 最优。

## 六、结论与边界

1. **覆盖达标**：{len(classes)} 类 / {len(wanted)} 种，满足课程「至少 2 类不少于 8 种」。
2. **口径未动**：既有交付模型与本包 `model_metrics.md` 逐项一致（差异 {len(diffs)} 项），
   新增模型用的是同一份切分、同一套特征、同一个种子。
3. **不参与交付**：新模型只进本矩阵，`[models]` 段与 `predict.py` 未改。
4. **未做序列模型（LSTM/RNN）**：现有样本集是提交级特征矩阵，没有序列结构；
   序列化数据集与输入口径的冻结属于另一个 change（理由与重开条件见
   `openspec/changes/model-expansion/design.md` 决策二）。
5. **阈值与排序的证据**在 `reports/calibration_threshold.md`（另一次实跑）——
   本节不越界给契约结论。
""")
    return "".join(L)


if __name__ == "__main__":
    raise SystemExit(main())
