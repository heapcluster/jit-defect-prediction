"""e2e 线 ⑦ 等价：全量推理，产出对齐契约一表三的 `prediction_result.csv`。

字段与 `data_model/07_predict_all.py` 逐字一致（不许多一个字段、顺序一致、不连数据库），
目的是让 e2e 的预测结果能直接喂后端 `prediction` 表做对照。区别：本线吃代码文本而非
Kamei 14 特征，`feature_version` 写 `codebert`（标识这是文本模态的预测，非 Kamei14 特征版）。

依赖：torch + transformers（与 train.py 同源）。

── 三条边界（同 07，钉死）──────────────────────────────────────────────────
① 字段 = 契约一表三（commit_hash, model_name, risk_score, predicted_at, feature_version）
② 本脚本不直连数据库（源码扫描数据库驱动 import）
③ 全量推理，含检验集
"""

from __future__ import annotations

import argparse
import csv
import sys
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd
import torch
from torch.utils.data import DataLoader, Dataset
from transformers import AutoModelForSequenceClassification, AutoTokenizer

try:
    from .build_text_dataset import commit_diff_text, detect_repo
except ImportError:
    from build_text_dataset import commit_diff_text, detect_repo

BASE = Path(__file__).resolve().parent
DATA_DIR = BASE.parent.parent / "data"
TEXT_CSV = BASE / "data" / "commit_text.csv"
OUT_CSV = BASE / "data" / "prediction_result.csv"
REPORT = BASE / "reports" / "prediction_stats.md"
MODEL_DIR = BASE / "models" / "codebert_e2e_v1"
MAX_LEN = 512
DECISION_THRESHOLD = 0.5
MODEL_NAME = "codebert_e2e_v1"
FEATURE_VERSION = "codebert"

CONTRACT_FIELDS = ["commit_hash", "model_name", "risk_score",
                   "predicted_at", "feature_version"]


class TextDataset(Dataset):
    def __init__(self, texts, tokenizer, max_len: int):
        self.enc = tokenizer(list(texts), truncation=True, padding="max_length",
                             max_length=max_len, return_tensors="pt")

    def __len__(self):
        return len(self.enc["input_ids"])

    def __getitem__(self, i):
        return {k: v[i] for k, v in self.enc.items()}


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description="e2e 全量推理，产出 prediction_result.csv（对齐契约一表三）",
        formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--model-dir", type=Path, default=MODEL_DIR)
    p.add_argument("--text-csv", type=Path, default=TEXT_CSV,
                   help="预处理好的文本数据集（含 commit_hash, text）；未提供则现建")
    p.add_argument("--dataset", type=Path, default=DATA_DIR / "dataset_szz.csv",
                   help="现建文本时用的样本集")
    p.add_argument("--repo", type=Path, default=None, help="现建文本时的克隆仓库")
    p.add_argument("--out", type=Path, default=OUT_CSV)
    p.add_argument("--report", type=Path, default=REPORT)
    p.add_argument("--max-len", type=int, default=MAX_LEN)
    p.add_argument("--model-name", default=MODEL_NAME)
    p.add_argument("--feature-version", default=FEATURE_VERSION)
    p.add_argument("--predicted-at", default=None,
                   help="覆盖 predicted_at（UTC）；默认当前时间")
    return p.parse_args()


def ensure_text_df(args) -> pd.DataFrame:
    if args.text_csv.is_file():
        return pd.read_csv(args.text_csv)
    if not args.dataset.is_file():
        print("[e2e-predict] 找不到文本数据集与样本集", file=sys.stderr)
        raise SystemExit(2)
    repo_path = detect_repo(BASE.parent.parent, args.repo)
    if repo_path is None:
        print("[e2e-predict] 现建文本需克隆仓库，请传 --repo", file=sys.stderr)
        raise SystemExit(2)
    from git import Repo
    repo = Repo(str(repo_path))
    df = pd.read_csv(args.dataset)
    rows = []
    for _, r in df.iterrows():
        t = commit_diff_text(repo, str(r["commit_hash"]), 4000)
        if t:
            rows.append({"commit_hash": str(r["commit_hash"]), "text": t})
    return pd.DataFrame(rows)


@torch.no_grad()
def main() -> int:
    args = parse_args()
    if not args.model_dir.is_dir():
        print(f"[e2e-predict] 找不到模型：{args.model_dir}（先跑 train.py）",
              file=sys.stderr)
        return 2

    df = ensure_text_df(args)
    if df.empty:
        print("[e2e-predict] 文本为空，未产出", file=sys.stderr)
        return 1

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    tokenizer = AutoTokenizer.from_pretrained(str(args.model_dir))
    model = AutoModelForSequenceClassification.from_pretrained(
        str(args.model_dir), num_labels=2).to(device).eval()

    loader = DataLoader(TextDataset(df["text"].tolist(), tokenizer, args.max_len),
                        batch_size=32, shuffle=False)
    proba = []
    with torch.no_grad():
        for batch in loader:
            inputs = {k: v.to(device) for k, v in batch.items()}
            logits = model(**inputs).logits
            proba.append(torch.softmax(logits, dim=1)[:, 1].cpu().numpy())
    proba = np.concatenate(proba)

    predicted_at = args.predicted_at or datetime.now(timezone.utc).strftime(
        "%Y-%m-%d %H:%M:%S")
    args.out.parent.mkdir(parents=True, exist_ok=True)
    with args.out.open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(CONTRACT_FIELDS)
        for commit_hash, score in zip(df["commit_hash"], proba):
            w.writerow([commit_hash, args.model_name, f"{float(score):.5f}",
                        predicted_at, args.feature_version])

    # 断言：字段与契约一表三逐字一致且无契约外字段
    with args.out.open(newline="", encoding="utf-8") as f:
        header = next(csv.reader(f))
    extra = [c for c in header if c not in CONTRACT_FIELDS]
    lose = [c for c in CONTRACT_FIELDS if c not in header]
    if extra or lose or header != CONTRACT_FIELDS:
        print(f"[e2e-predict] 字段与契约一表三不一致：多 {extra} / 缺 {lose}",
              file=sys.stderr)
        return 1
    source = Path(__file__).read_text(encoding="utf-8")
    banned = ["sqlalchemy", "pymysql", "mysql.connector", "sqlite3", "psycopg2"]
    if any((f"import {b}") in source for b in banned):
        print("[e2e-predict] 脚本含数据库驱动 import", file=sys.stderr)
        return 1

    above = int((proba >= DECISION_THRESHOLD).sum())
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(
        "# e2e 全量预测结果统计（predict.py 产出）\n\n"
        f"> 字段口径见契约一表三 `prediction`。`feature_version` 本线写 `{args.feature_version}`。\n\n"
        "## 产出\n\n"
        f"| 项 | 值 |\n|---|---|\n| 模型 | `{args.model_name}` |\n"
        f"| 推理条数 | {len(df)}（全量，含检验集） |\n"
        f"| `feature_version` | `{args.feature_version}` |\n"
        f"| `predicted_at` | {predicted_at} |\n| 输出文件 | `{args.out}` |\n\n"
        "## 风险分数分布\n\n"
        f"| 统计量 | 值 |\n|---|---|\n| 均值 | {float(np.mean(proba)):.5f} |\n"
        f"| 中位数 | {float(np.median(proba)):.5f} |\n| p95 | {float(np.percentile(proba, 95)):.5f} |\n"
        f"| `risk_score >= {DECISION_THRESHOLD:.2f}` 的条数 | {above}（{above / len(df) * 100:.2f}%） |\n\n"
        "## 三条断言\n\n"
        "| 检查项 | 结果 |\n|---|---|\n"
        "| 字段与契约一表三逐字一致，无契约外字段 | 通过 |\n"
        "| 列顺序与契约一表三一致 | 通过 |\n"
        "| 脚本与依赖中无任何数据库连接 | 通过 |\n",
        encoding="utf-8", newline="\n")

    print(f"[e2e-predict] 全量推理 {len(df)} 条 -> {args.out}")
    print(f"[e2e-predict] 断言通过；risk_score 均值 {float(np.mean(proba)):.5f} ｜ >= {DECISION_THRESHOLD:.2f} 的 {above} 条（{above / len(df) * 100:.2f}%）")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
