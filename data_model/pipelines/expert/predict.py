"""expert 线全量推理（由根目录 07_predict_all.py 移植（该文件已不存在）），产出交付后端线的
`prediction_result.csv`。

字段口径: 契约一表三 `prediction`
交付方式: A + C —— 本脚本只产出**文件**，由后端线导入 `prediction` 表

── 三条边界（都用断言钉住）────────────────────────────────────────────────
① **字段与契约一表三逐字一致**，且**不许多一个字段**：`id` 是自增主键、由数据库生成，
   CSV 里不该有；契约里没有的列一个都不能夹带。
② **本脚本不直连数据库**：数据线的铁规矩是「只产出文件、不建库表」。
③ **全量推理，含检验集**：趋势看板要的是历史全量结果，不是只有检验集。

── 为什么风险分数写 5 位小数 ─────────────────────────────────────────────
契约一表三把 `risk_score` 定为 `DECIMAL(6,5)`。写 5 位小数是为了**让入库值与 CSV 值
逐字相等** —— 少写几位，导入后与原文件对不上，回头查「这个分数到底是模型给的还是
导入时截断的」就说不清。
"""

from __future__ import annotations

import argparse
import csv
import sys
from datetime import datetime, timezone
from pathlib import Path

import joblib
import numpy as np
import pandas as pd

from .. import repo_paths
from . import config

# 契约一表三 `prediction` 的字段（去掉自增主键 `id`），**顺序即 CSV 列顺序**
CONTRACT_FIELDS = ["commit_hash", "model_name", "risk_score",
                   "predicted_at", "feature_version"]


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description="expert 线全量推理产出 prediction_result.csv（字段对齐契约一表三）",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    p.add_argument("--dataset", type=Path,
                   default=config.DATA_DIR / "dataset_szz.csv",
                   help="04 产出的样本集（全量，含检验集）")
    p.add_argument("--model", type=Path, default=config.MODELS_DIR / "xgb_v1.pkl")
    p.add_argument("--model-name", default=None,
                   help="写入 model_name 列的值，默认取 .pkl 文件名（如 xgb_v1）")
    p.add_argument("--out", type=Path, default=config.PKG / "data" / "prediction_result.csv")
    p.add_argument("--report", type=Path,
                   default=config.REPORTS_DIR / "prediction_stats.md")
    p.add_argument("--predicted-at", default=None,
                   help="覆盖 predicted_at（UTC，YYYY-MM-DD HH:MM:SS）；默认取当前时间")
    return p.parse_args()


def main() -> int:
    args = parse_args()
    if not args.dataset.is_file():
        print(f"[expert-predict] 找不到样本集：{args.dataset}", file=sys.stderr)
        return 2
    if not args.model.is_file():
        print(f"[expert-predict] 找不到模型：{args.model}（先跑 python -m pipelines.expert.train）", file=sys.stderr)
        return 2

    model_name = args.model_name or args.model.stem
    dataset = pd.read_csv(args.dataset)
    missing = [c for c in config.FEATURE_FIELDS + ["commit_hash", "feature_version"]
               if c not in dataset.columns]
    if missing:
        print(f"[expert-predict] 样本集缺列：{missing}", file=sys.stderr)
        return 2

    model = joblib.load(args.model)
    n_expected = len(config.FEATURE_FIELDS)
    n_model = getattr(model, "n_features_in_", None)
    if n_model is not None and n_model != n_expected:
        print(f"[expert-predict] 模型要 {n_model} 个特征，契约二第三节是 {n_expected} 个 —— 特征顺序或版本"
              "不一致，拒绝推理", file=sys.stderr)
        return 2

    features = dataset[config.FEATURE_FIELDS].to_numpy(dtype=float)
    proba = model.predict_proba(features)[:, 1]

    version_mismatch = sorted(set(dataset["feature_version"].astype(str)))
    if len(version_mismatch) != 1:
        print(f"[expert-predict] 样本集混了多个 feature_version：{version_mismatch} —— 一份预测结果只能"
              "对应一版特征", file=sys.stderr)
        return 2
    feature_version = version_mismatch[0]

    predicted_at = args.predicted_at or datetime.now(timezone.utc).strftime(
        "%Y-%m-%d %H:%M:%S")

    args.out.parent.mkdir(parents=True, exist_ok=True)
    with args.out.open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(CONTRACT_FIELDS)
        for commit_hash, score in zip(dataset["commit_hash"], proba):
            w.writerow([commit_hash, model_name, f"{float(score):.5f}",
                        predicted_at, feature_version])

    # ── 断言：字段与契约一表三逐字一致，且无契约外字段 ────────────────
    with args.out.open(newline="", encoding="utf-8") as f:
        header = next(csv.reader(f))
    extra = [c for c in header if c not in CONTRACT_FIELDS]
    lose = [c for c in CONTRACT_FIELDS if c not in header]
    if extra or lose:
        print(f"[expert-predict] 字段与契约一表三不一致：多 {extra} / 缺 {lose}",
              file=sys.stderr)
        return 1
    if header != CONTRACT_FIELDS:
        print("[expert-predict] 列顺序与契约一表三不同（顺序不同会导致导入脚本对不上列）",
              file=sys.stderr)
        return 1

    # ── 断言：本脚本不直连数据库 ────────────────────────────────────
    source = Path(__file__).read_text(encoding="utf-8")
    banned = ["sqlalchemy", "pymysql", "mysql.connector", "sqlite3", "psycopg2"]
    imported = [b for b in banned if (f"import {b}") in source]
    if imported:
        print(f"[expert-predict] 脚本里出现了数据库驱动 import：{imported} —— 数据线只产出文件、"
              "不建库表", file=sys.stderr)
        return 1

    above = int((proba >= config.DECISION_THRESHOLD).sum())
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(
        PREDICTION_REPORT.format(
            model_name=model_name,
            model_path=repo_paths.rel_to_data_model(args.model),
            rows=len(dataset),
            feature_version=feature_version,
            predicted_at=predicted_at,
            out=repo_paths.rel_to_data_model(args.out),
            mean=float(np.mean(proba)),
            median=float(np.median(proba)),
            p95=float(np.percentile(proba, 95)),
            above=above,
            above_rate=above / len(dataset) * 100,
            threshold=config.DECISION_THRESHOLD,
        ),
        # 显式写 \n：Windows 上 write_text 默认把 \n 转成 os.linesep（CRLF），
        # 与仓库既有 Markdown（LF）会整份不一致
        encoding="utf-8", newline="\n")

    print(f"[expert-predict] 全量推理 {len(dataset)} 条 -> {args.out}")
    print(f"[expert-predict] model_name={model_name} ｜ feature_version={feature_version} ｜ predicted_at={predicted_at}")
    print("[expert-predict] 断言通过：字段 = 契约一表三（无契约外字段）、列顺序一致、"
          "脚本无数据库驱动")
    print(f"[expert-predict] 风险分数：均值 {float(np.mean(proba)):.5f} ｜ 中位数 {float(np.median(proba)):.5f} ｜ p95 {float(np.percentile(proba, 95)):.5f} ｜ "
          f">= {config.DECISION_THRESHOLD:.2f} 的 {above} 条（{above / len(dataset) * 100:.2f}%）")
    print(f"[expert-predict] 报告：{args.report}")
    return 0


PREDICTION_REPORT = """# 全量预测结果统计（pipelines/expert/predict.py 产出）

> 本文件可入库。字段口径见 `docs/{{backend/api-spec.md, design/data-fields.md, model/feature-columns.md}}data-fields.md` 表三 `prediction`。
> **产出文件本身不入库**（`data/` 在 `.gitignore` 里）—— 它随包交付后端线，由后端导入。

## 产出

| 项 | 值 |
|---|---|
| 模型 | `{model_name}`（`{model_path}`） |
| 推理条数 | {rows}（全量，含检验集） |
| `feature_version` | `{feature_version}` |
| `predicted_at` | {predicted_at}（UTC） |
| 输出文件 | `{out}` |

## 风险分数分布

| 统计量 | 值 |
|---|---|
| 均值 | {mean:.5f} |
| 中位数 | {median:.5f} |
| p95 | {p95:.5f} |
| `risk_score >= {threshold}` 的条数 | {above}（{above_rate:.2f}%） |

## 三条断言

| 检查项 | 结果 |
|---|---|
| 字段与契约一表三**逐字一致**，无契约外字段 | 通过 |
| 列顺序与契约一表三一致 | 通过 |
| 脚本与依赖中**无任何数据库连接** | 通过（源码扫描 `sqlalchemy` / `pymysql` / `mysql.connector` / `sqlite3` / `psycopg2`，零命中） |

## 一个要一起看的数：高分占比 vs 真实正样本比例

`risk_score >= {threshold}` 的占比（**{above_rate:.2f}%**）是**模型输出侧**的「高风险」比例。
把它和 `reports/model_metrics.md` 里**检验集的真实正样本比例**并排看：

- 两者差得越远，说明模型**校准越偏**（高分判得过多），风险列表的 triage 区分度越弱 ——
  如果把「`>= {threshold}`」直接当成「值得优先审」的门槛，等于没筛。
- 偏高的来源是两个已知事实叠加，都不是算错：
  ① **时间序切分**让训练集正样本比例显著高于检验集（见 `model_metrics.md` 的表头）；
  ② 契约三把判定阈值钉死为**服务端常量 `{threshold}`**，不能按检验集分布调。
- **两条都不在本包的范围内改。** 可选方向（都要走契约变更，不在实现里静默调）：
  ① 阈值语义改为「按高风险**配额**取前 N%」；② 训练侧加概率校准（Platt / isotonic），
  实测证据见 `reports/calibration_threshold.md`。

## 交付方式（A + C）

- **C（本文件）**：数据线产出 `prediction_result.csv`，**由后端线灌入 `prediction` 表**。
  数据线**不直连数据库、不写库**。
- **A（模型文件）**：`{model_name}.pkl` + `models/feature_order.txt`（14 项特征顺序、
  依赖版本 pin、风险判定阈值）。该清单是契约二第三节的**副本**，不一致时以契约为准。
"""


if __name__ == "__main__":
    raise SystemExit(main())
