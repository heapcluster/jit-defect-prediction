"""06 训练 2–3 个经典模型并产出两类指标。

对应 OpenSpec change: model-training-and-delivery（第 3.2 / 3.3 / 4.1 / 4.4 条任务）
标签: 只用 `szz`（主标签，契约一见 `docs/contracts/data-fields.md` 表二）
特征列序: docs/contracts/feature-columns.md 第三节（14 项，顺序即交付清单顺序）
指标口径: 见下方「两类指标」一节

── 两类指标，缺一不可 ────────────────────────────────────────────────────
① **Effort-unaware**：AUC / F1 / Precision / Recall / Accuracy —— 只看预测对不对，
   不看「要先审多少代码」。
② **Effort-aware**：JIT 场景下评审者只有有限的审查预算，真正关心的是
   「按风险排序后，前 20% 的工作量能抓到多少缺陷」。所以还要报工作量感知指标。

工作量感知指标的定义（本脚本采用的写法，逐项写清以便复算）：

  设检验集有 N 条提交，第 i 条的风险预测为 `p_i`、真实标签为 `y_i ∈ {0,1}`、
  工作量（effort）为 `e_i`。

  · **模型排序**：按 `p_i` 降序。
  · **最优排序**：按**真实缺陷密度** `y_i / e_i` 降序（上帝视角的上界）。
  · 沿某个排序依次累加，得到两条累计曲线：
      横轴 = 累计工作量占比 `Σe / Σe_total`，纵轴 = 累计召回率 `Σy / Σy_total`
  · **面积** = 该排序曲线的下面积（梯形法）
  · **P_norm** = `(面积 - 0.5) / (上界面积 - 0.5)` —— 随机排序为 0、上界为 1

  本脚本对**四种排序**各算一次，缺一不可：
      ① 模型排序（`risk_score` 降序）—— **契约三的当前口径**，是产品的真实行为
      ② 按 `risk_score / 工作量` 降序 —— Kamei 原文的 `R_d(x) = Y(x)/Effort(x)`，仅作对照
      ③ 按**真实**缺陷密度降序 —— 上界（上帝视角）
      ④ 随机排序（固定种子）—— **基线，面积必须落在 0.5 附近，这是本节的自我校验**

  > ④ 不是装饰：若随机排序算出来的面积不是 0.5，说明面积算法本身有问题，
  > 那么另外三行一个都不能信。

  > 为什么横轴用工作量而不是提交条数：同样一条提交，改 1 行和改 900 行的审查
  > 成本差三个数量级。Kamei 原文同时用 **LOC（改动行数）** 与 **改动文件数**
  > 两种工作量代理，本脚本两种都报 —— 只报一种，结论会随代理变量的选择而变。

  > 工作量取自 `03` 产出的**原始特征表**（`data/commit_features_raw.csv`）——
  > 样本集里的 `la`/`ld`/`nf` 已做归一化与对数变换，不能当工作量用。

── 可复现（tasks.md 3.2）──────────────────────────────────────────────────
随机种子显式固定（`--seed`，默认 42），且写进报告。同一命令连跑两次，指标逐项一致。

── 交付清单（tasks.md 4.1）────────────────────────────────────────────────
模型导出 `models/<model_name>.pkl`（不入库）；同时产出 `models/feature_order.txt`，
写明 `.pkl` 路径、14 项特征顺序、依赖版本 pin。按裁定（PR #20）**这份清单是契约二
第三节的副本、不是独立来源**，两者不一致时以契约为准。
"""

from __future__ import annotations

import argparse
import csv
import json
import sys
import time
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (accuracy_score, f1_score, precision_score,
                             recall_score, roc_auc_score)
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

BASE = Path(__file__).resolve().parent
DATA_DIR = BASE / "data"
REPORTS_DIR = BASE / "reports"
MODELS_DIR = BASE / "models"

# 契约二第三节的 14 项特征，**顺序即交付清单顺序**
FEATURE_FIELDS = [
    "ns", "nd", "nf", "entropy",
    "la", "ld", "lt",
    "fix",
    "ndev", "age", "nuc",
    "exp", "rexp", "sexp",
]

LABEL_COL = "is_bug_inducing"
MODEL_NAMES = {"lr": "逻辑回归", "rf": "随机森林", "xgb": "XGBoost"}
DEFAULT_SEED = 42
DECISION_THRESHOLD = 0.5
# 随机基线的抽样次数与种子（固定，保证可复现）
RANDOM_BASELINE_REPEATS = 200
RANDOM_BASELINE_SEED = 0
# 契约三第四节：预测接口性能要求「95% 的请求 < 500ms」
LATENCY_BUDGET_MS = 500.0


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description="训练 LR / RF / XGBoost 并产出 Effort-unaware + Effort-aware 两类指标",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    p.add_argument("--train", type=Path, default=DATA_DIR / "split_szz_train.csv")
    p.add_argument("--test", type=Path, default=DATA_DIR / "split_szz_test.csv")
    p.add_argument("--features-raw", type=Path,
                   default=DATA_DIR / "commit_features_raw.csv",
                   help="03 产出的原始特征表，用于取工作量（LOC / 文件数）")
    p.add_argument("--models", default="lr,rf,xgb", help="要训练的模型，逗号分隔")
    p.add_argument("--seed", type=int, default=DEFAULT_SEED, help="随机种子（必须固定）")
    p.add_argument("--model-dir", type=Path, default=MODELS_DIR)
    p.add_argument("--report", type=Path,
                   default=REPORTS_DIR / "model_metrics.md")
    p.add_argument("--shap-rows", type=int, default=100,
                   help="SHAP 单条耗时实测的样本条数（tasks.md 4.4）")
    p.add_argument("--skip-shap", action="store_true", help="跳过 SHAP 实测（调试用）")
    p.add_argument("--no-export", action="store_true",
                   help="只出指标、不导出 .pkl（做敏感性对照时用，避免覆盖主模型文件）")
    return p.parse_args()


# ─────────────────────────── 工作量感知指标 ───────────────────────────

def cumulative_area(order: np.ndarray, effort: np.ndarray, y: np.ndarray) -> float:
    """按给定顺序累加，返回「累计召回率 ~ 累计工作量占比」曲线的下面积（梯形法）。"""
    total_e = float(effort.sum())
    total_y = float(y.sum())
    if total_e <= 0 or total_y <= 0:
        return float("nan")
    area = 0.0
    cum_e = 0.0
    cum_y = 0.0
    prev_recall = 0.0
    for i in order:
        cum_e += float(effort[i])
        cum_y += float(y[i])
        recall = cum_y / total_y
        area += 0.5 * (prev_recall + recall) * (float(effort[i]) / total_e)
        prev_recall = recall
    return area


def recall_at_effort(order: np.ndarray, effort: np.ndarray, y: np.ndarray,
                     frac: float) -> float:
    """按给定顺序审查，累计工作量达到 frac 时已抓到多少比例的缺陷。"""
    total_e = float(effort.sum())
    total_y = float(y.sum())
    if total_e <= 0 or total_y <= 0:
        return float("nan")
    cum_e = 0.0
    cum_y = 0.0
    for i in order:
        cum_e += float(effort[i])
        cum_y += float(y[i])
        if cum_e / total_e >= frac:
            break
    return cum_y / total_y


def effort_aware_metrics(proba: np.ndarray, y: np.ndarray,
                         effort: np.ndarray) -> dict:
    """对四种排序各算一次曲线下面积与截断召回。

    四种排序（都只改「怎么排」，不改模型与工作量）：
      · model   —— 按预测概率降序。**这是本项目契约三的实际口径**（`risk_score` 降序）。
      · density —— 按「预测概率 / 工作量」降序。Kamei 原文里写作 `R_d(x) = Y(x)/Effort(x)`，
                    即先算「每一行代码的风险密度」再排。**它需要契约变更**，此处只作对照。
      · optimal —— 按**真实**缺陷密度 `y/e` 降序，上帝视角的上界。
      · random  —— 固定种子 0 的随机排列，作为基线。**它必须落在 0.5 附近**，
                    否则说明面积算法本身有问题 —— 这是本节的自我校验。
    """
    effort = np.maximum(effort.astype(float), 1.0)  # 0 行改动会让密度除零
    orders = {
        "model": np.argsort(-proba, kind="stable"),
        "density": np.argsort(-(proba / effort), kind="stable"),
        "optimal": np.argsort(-(y / effort), kind="stable"),
    }
    out: dict[str, dict] = {}
    for key, order in orders.items():
        out[key] = {
            "area": cumulative_area(order, effort, y),
            "recall@20": recall_at_effort(order, effort, y, 0.20),
            "recall@50": recall_at_effort(order, effort, y, 0.50),
        }

    # 随机基线：**取多次抽样的均值**，不能只抽一次。
    # 本数据集工作量是重尾的（LOC 中位数 23、最大 32 万行），一次随机排列的面积
    # 会被「那几个超大提交落在哪个位置」主导 —— 实测单次可到 0.62，而理论期望是 0.5。
    # 单抽一次就把它当基线，会把归一化的锚点带偏。
    rng = np.random.default_rng(RANDOM_BASELINE_SEED)
    areas = []
    for _ in range(RANDOM_BASELINE_REPEATS):
        perm = rng.permutation(len(y))
        areas.append(cumulative_area(perm, effort, y))
    baseline = float(np.mean(areas))
    out["random"] = {
        "area": baseline,
        "area_std": float(np.std(areas)),
        "repeats": RANDOM_BASELINE_REPEATS,
        "recall@20": float("nan"),
        "recall@50": float("nan"),
    }

    # P_norm：以「随机排序（实测均值）= 0」与「上界 = 1」为两端线性归一。
    # 锚点用**实测**的随机均值而不是写死的 0.5 —— 让基线本身可核对。
    denom = out["optimal"]["area"] - baseline
    for key in out:
        out[key]["p_norm"] = (
            (out[key]["area"] - baseline) / denom if abs(denom) > 1e-12
            else float("nan"))
    return out


# ─────────────────────────── 模型与工作量 ───────────────────────────

def build_model(name: str, seed: int):
    if name == "lr":
        # 逻辑回归对量纲敏感，必须先标准化，否则 14 项特征量级差会主导系数
        return Pipeline([
            ("scaler", StandardScaler()),
            ("lr", LogisticRegression(max_iter=1000, random_state=seed)),
        ])
    if name == "rf":
        return RandomForestClassifier(
            n_estimators=300, min_samples_leaf=2,
            random_state=seed, n_jobs=-1)
    if name == "xgb":
        from xgboost import XGBClassifier
        return XGBClassifier(
            n_estimators=300, learning_rate=0.1, max_depth=6,
            subsample=0.9, colsample_bytree=0.9,
            random_state=seed, n_jobs=-1,
            eval_metric="logloss")
    raise ValueError("未知模型：%s" % name)


def load_effort(path: Path, hashes: pd.Series) -> pd.DataFrame:
    """从原始特征表取工作量：LOC = la + ld，文件数 = nf。"""
    raw = pd.read_csv(path)
    raw = raw.set_index("commit_hash")
    missing = [h for h in hashes if h not in raw.index]
    if missing:
        raise SystemExit(
            "[06] 原始特征表缺 %d 条提交（例：%s）—— 工作量口径无法对齐，"
            "请确认 03 与 04 用的是同一窗口" % (len(missing), missing[0]))
    sub = raw.loc[list(hashes)]
    return pd.DataFrame({
        "effort_loc": (sub["la"].astype(float) + sub["ld"].astype(float)).values,
        "effort_files": sub["nf"].astype(float).values,
    }, index=hashes.values)


# ─────────────────────────── SHAP 单条耗时 ───────────────────────────

def shap_latency(name: str, model, X_test: np.ndarray, n_rows: int) -> dict:
    """实测单条 SHAP 解释耗时（tasks.md 4.4）。不达标不静默降级，只如实记录。"""
    import shap

    rows = X_test[:n_rows]
    t0 = time.perf_counter()
    if name == "lr":
        scaler = model.named_steps["scaler"]
        lr = model.named_steps["lr"]
        background = scaler.transform(X_test[:200])
        explainer = shap.LinearExplainer(lr, background)
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
    return {
        "cold_ms": cold_ms,
        "p50_ms": float(np.percentile(lat, 50)),
        "p95_ms": float(np.percentile(lat, 95)),
        "max_ms": float(lat.max()),
        "rows": len(lat),
    }


# ─────────────────────────── 主流程 ───────────────────────────

def main() -> int:
    args = parse_args()
    for path in (args.train, args.test):
        if not path.is_file():
            print("[06] 找不到切分文件：%s（先跑 05_split_dataset.py）" % path,
                  file=sys.stderr)
            return 2

    train = pd.read_csv(args.train)
    test = pd.read_csv(args.test)
    missing = [c for c in FEATURE_FIELDS + [LABEL_COL] if c not in train.columns]
    if missing:
        print("[06] 训练集缺列：%s" % missing, file=sys.stderr)
        return 2
    if LABEL_COL not in test.columns:
        print("[06] 检验集缺 `%s` —— 本 change 只认主标签 `szz`，"
              "不回退到 szz_lite" % LABEL_COL, file=sys.stderr)
        return 2

    X_train = train[FEATURE_FIELDS].to_numpy(dtype=float)
    y_train = train[LABEL_COL].astype(int).to_numpy()
    X_test = test[FEATURE_FIELDS].to_numpy(dtype=float)
    y_test = test[LABEL_COL].astype(int).to_numpy()

    effort_raw = load_effort(args.features_raw, test["commit_hash"])
    effort_sets = {
        "LOC（改动行数 la+ld）": effort_raw["effort_loc"].to_numpy(),
        "改动文件数 nf": effort_raw["effort_files"].to_numpy(),
    }

    args.model_dir.mkdir(parents=True, exist_ok=True)
    wanted = [m.strip() for m in args.models.split(",") if m.strip()]

    results: dict[str, dict] = {}
    for name in wanted:
        model = build_model(name, args.seed)
        model.fit(X_train, y_train)
        proba = model.predict_proba(X_test)[:, 1]
        pred = (proba >= DECISION_THRESHOLD).astype(int)
        row = {
            "model_name": "%s_v1" % name,
            "auc": roc_auc_score(y_test, proba),
            "f1": f1_score(y_test, pred, zero_division=0),
            "precision": precision_score(y_test, pred, zero_division=0),
            "recall": recall_score(y_test, pred, zero_division=0),
            "accuracy": accuracy_score(y_test, pred),
            "effort": {},
        }
        for label, effort in effort_sets.items():
            row["effort"][label] = effort_aware_metrics(proba, y_test, effort)
        if not args.skip_shap:
            try:
                row["shap"] = shap_latency(name, model, X_test, args.shap_rows)
            except Exception as exc:  # 实测失败要写进报告，不能当没发生
                row["shap"] = {"error": "%s: %s" % (type(exc).__name__, exc)}
        results[name] = row

        if not args.no_export:
            joblib.dump(model, args.model_dir / ("%s_v1.pkl" % name))
        print("[06] %-4s AUC=%.4f  F1=%.4f  P=%.4f  R=%.4f"
              % (name, row["auc"], row["f1"], row["precision"], row["recall"]))

    if args.no_export:
        args.report.parent.mkdir(parents=True, exist_ok=True)
        args.report.write_text(
            render_report(args, train, test, results, warranted=wanted),
            encoding="utf-8")
        print("[06] --no-export：未导出模型文件；指标报告：%s" % args.report)
        return 0

    # 交付清单（tasks.md 4.1）
    order_file = args.model_dir / "feature_order.txt"
    order_file.write_text(
        "# 模型交付清单（A 方案：后端加载 .pkl）\n"
        "# 生成：data_model/06_train_model.py\n"
        "#\n"
        "# 说明：本清单是 `docs/contracts/feature-columns.md` 第三节的**副本**，\n"
        "#       不是独立来源。两者不一致时**以契约为准**；契约二升版时本文件须同步。\n"
        "\n"
        "[models]\n"
        + "".join("%s_v1.pkl\t%s\n" % (m, MODEL_NAMES.get(m, m)) for m in wanted)
        + "\n[feature_order]\n"
        + "".join("%2d. %s\n" % (i + 1, c)
                  for i, c in enumerate(FEATURE_FIELDS))
        + "\n[contract]\n"
        + "docs/contracts/feature-columns.md 第三节（14 项特征列，顺序即上表顺序）\n"
        + "\n[dependencies]\n"
        + _dependency_pins()
        + "\n[decision]\n"
        + "风险阈值 %.2f（服务端常量，见 docs/contracts/api-format.md 第三节）\n"
        % DECISION_THRESHOLD,
        encoding="utf-8")

    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(
        render_report(args, train, test, results, warranted=wanted),
        encoding="utf-8")

    print("[06] 模型已导出：%s" % args.model_dir)
    print("[06] 交付清单：%s" % order_file)
    print("[06] 指标报告：%s" % args.report)
    return 0


def _dependency_pins() -> str:
    try:
        import sklearn
        import xgboost
        import pandas as pd
        import numpy as np
        import shap
        return "\n".join([
            "scikit-learn==%s" % sklearn.__version__,
            "xgboost==%s" % xgboost.__version__,
            "shap==%s" % shap.__version__,
            "pandas==%s" % pd.__version__,
            "numpy==%s" % np.__version__,
        ]) + "\n"
    except Exception as exc:
        return "# 依赖版本探测失败：%s\n" % exc


def render_report(args, train, test, results, warranted) -> str:
    y_test = test[LABEL_COL].astype(int).to_numpy()
    head = f"""# 模型评估指标（06_train_model.py 产出）

> 本文件可入库，是 OpenSpec change `model-training-and-delivery` 第 3.3 条任务的证据。
> 两类指标的定义与公式见 `data_model/06_train_model.py` 文件头。

## 数据与参数

| 项 | 值 |
|---|---|
| 训练集 | `{args.train.name}` —— {len(train)} 条 |
| 检验集 | `{args.test.name}` —— {len(test)} 条 |
| 特征列 | 契约二第三节 14 项（顺序即交付清单顺序） |
| 标签 | `szz`（主标签；`is_bug_inducing`） |
| 训练集正样本比例 | {train[LABEL_COL].mean() * 100:.2f}% |
| 检验集正样本比例 | {y_test.mean() * 100:.2f}% |
| 随机种子 | `{args.seed}`（显式固定，写进报告） |
| 判定阈值 | {DECISION_THRESHOLD}（服务端常量，非请求参数） |
| 检验集时间范围 | {test['committed_at'].iloc[0]} ~ {test['committed_at'].iloc[-1]} |

> **注意训练/检验的正样本比例差**：训练集 {train[LABEL_COL].mean() * 100:.2f}% vs 检验集 {y_test.mean() * 100:.2f}%。
> 这是时间序切分的自然结果（早期历史里「一个修复提交指控多个引入方」更密集），
> **不是 bug**。但它意味着模型在检验集上会**系统性高估风险** —— 看 Precision 与
> Recall 的落差比看 Accuracy 有意义。

## 一、Effort-unaware 指标（检验集）

| 模型 | AUC | F1 | Precision | Recall | Accuracy |
|---|---|---|---|---|---|
"""
    lines = [head]
    for name in warranted:
        r = results[name]
        lines.append("| `%s`（%s） | %.4f | %.4f | %.4f | %.4f | %.4f |\n" % (
            r["model_name"], MODEL_NAMES.get(name, name),
            r["auc"], r["f1"], r["precision"], r["recall"], r["accuracy"]))

    lines.append("""
## 二、Effort-aware 指标（检验集）

沿某个排序依次累加，横轴 = 累计工作量占比、纵轴 = 累计召回率，取曲线下面积。
`P_norm` 以**随机排序（实测均值）= 0**、**真实密度上界 = 1** 两端线性归一：
`P_norm = (面积 − 随机基线) / (上界面积 − 随机基线)`。

**随机基线那一行是本节的自我校验** —— 它由 200 次随机排列取均值得到（固定种子），
若它偏得很远，说明面积算法有问题，其余数字一个都不能信。

> 锚点为什么用**实测均值**而不是写死的 `0.5`：在本数据集上，一次随机排列算出的
> 面积并不总在 0.5 —— 工作量是重尾的（LOC 中位数 23、最大 32 万行），单次结果被
> 「那几个超大提交排在第几位」主导。写死 0.5 会把归一化的基准带偏，实测均值则可核对
> —— 下表「±」后面那个数就是它的波动幅度，可以直接看出单次抽样有多不可靠。

""")
    for label in results[warranted[0]]["effort"]:
        lines.append("### 工作量代理：%s\n\n" % label)
        lines.append("| 排序方式 | 模型 | 曲线下面积 | **P_norm** | Recall@20% | Recall@50% |\n")
        lines.append("|---|---|---|---|---|---|\n")
        for name in warranted:
            m = results[name]["effort"][label]["model"]
            lines.append("| **模型排序**（`risk_score` 降序，**契约三当前口径**） | `%s` | %.4f | **%.4f** | %.4f | %.4f |\n"
                         % (results[name]["model_name"], m["area"], m["p_norm"],
                            m["recall@20"], m["recall@50"]))
        for name in warranted:
            m = results[name]["effort"][label]["density"]
            lines.append("| 对照：按 `risk_score / 工作量` 降序 | `%s` | %.4f | **%.4f** | %.4f | %.4f |\n"
                         % (results[name]["model_name"], m["area"], m["p_norm"],
                            m["recall@20"], m["recall@50"]))
        o = results[warranted[0]]["effort"][label]["optimal"]
        r = results[warranted[0]]["effort"][label]["random"]
        lines.append("| 上界：按**真实**缺陷密度降序 | — | %.4f | %.4f | %.4f | %.4f |\n"
                     % (o["area"], o["p_norm"], o["recall@20"], o["recall@50"]))
        lines.append("| 基线：随机排序（%d 次抽样均值） | — | %.4f ± %.4f | %.4f | — | — |\n"
                     % (r["repeats"], r["area"], r["area_std"], r["p_norm"]))
        lines.append("\n")

    lines.append("""
### 这两张表说明什么

1. **按 `risk_score` 排序（契约三当前口径），在 LOC 工作量代理下不如随机排序** ——
   模型排序的 `P_norm` 为负，而随机基线在 0 附近。原因可解释：LOC 密度 `y/e` 的
   上界排序被**极小提交**主导（本数据集 LOC 中位数只有 23 行，一条改 1 行的缺陷
   修复密度就是 1.0，而一次改 19 万行的提交密度几乎为 0）；模型按**概率**排序，
   概率与提交大小正相关，于是把大提交排在前面 —— 而大提交恰恰是「按行数算不值当
   先审」的那一类。
2. **按 `risk_score / 工作量` 排序（Kamei 原文的 `R_d(x) = Y(x)/Effort(x)`）明显更好**：
   同一个模型、同一份特征，**只改排序方式**，`P_norm` 就回到正值以上。
   代价 —— **这需要契约变更**：契约三第三节规定风险列表按 `risk_score` 降序，改成按
   风险密度排序要同时改接口语义、前端排序展示与趋势看板的聚合口径。
   → 登记为契约变更**提案**，不在本 change 里静默改掉。
3. **工作量代理的选择会改变结论**：文件数代理下模型略好于随机，LOC 代理下不如随机。
   所以两种都报 —— 只报一种，等于替读者选了一个可能对他不利的口径。

> 上界那一行不是「另一个模型」的成绩，是上帝视角 —— 它只回答「这个指标的理论天花板
> 有多高」，不能拿去和模型比分数。

## 三、SHAP 单条解释耗时（tasks.md 4.4）

契约三第四节要求「预测接口 95% 的请求 < 500ms」。SHAP 是其中最主要的开销项，
故单独实测；**不达标只如实记录，不静默降级**（降级要提契约变更）。

> ⚠️ 本节是**实测耗时**，随机器负载波动 —— **连跑两次这一节会变，其余各表不变**。
> 所以核对「可复现」时要比对的是上面两张指标表，**不要把本节算进去**
> （把计时结果也要求逐字节一致，只会得出「不可复现」的错误结论）。

""")
    lines.append("| 模型 | 解释器冷启动 | p50 | p95 | 最大 | 实测条数 | 是否满足 95% < 500ms |\n")
    lines.append("|---|---|---|---|---|---|---|\n")
    for name in warranted:
        s = results[name].get("shap")
        if not s:
            lines.append("| `%s` | — | — | — | — | — | 未实测 |\n" % name)
        elif "error" in s:
            lines.append("| `%s` | 实测失败：`%s` | | | | | ⚠️ 未取得数据 |\n"
                         % (name, s["error"].replace("|", "/")))
        else:
            ok = "✅ 满足" if s["p95_ms"] < LATENCY_BUDGET_MS else "❌ 不满足"
            lines.append("| `%s` | %.1f ms | %.1f ms | **%.1f ms** | %.1f ms | %d | %s |\n"
                         % (name, s["cold_ms"], s["p50_ms"], s["p95_ms"],
                            s["max_ms"], s["rows"], ok))

    lines.append("""
> 冷启动是**一次性**开销（后端加载模型时构建解释器），不进请求路径；
> 请求路径上是 p95 那一列。

## 交付清单（A 方案）

`data_model/models/feature_order.txt`（**不入库**，随包交付）含：

- `.pkl` 文件路径与对应模型名
- 14 项特征顺序（契约二第三节的副本，不一致时以契约为准）
- 依赖版本 pin
- 风险判定阈值

同一份清单的内容打印在下面，便于在不 clone 模型目录的情况下核对：

```
""")
    order = MODELS_DIR / "feature_order.txt"
    if order.is_file():
        lines.append(order.read_text(encoding="utf-8"))
    else:
        lines.append("（未找到 models/feature_order.txt）\n")
    lines.append("```\n")
    return "".join(lines)


if __name__ == "__main__":
    raise SystemExit(main())
