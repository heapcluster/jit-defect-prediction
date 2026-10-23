"""e2e 线数据：文本加载、共享切分对齐、Dataset、工作量。"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd
import torch
from torch.utils.data import Dataset


def load_texts(path: Path) -> pd.DataFrame:
    if not path.is_file():
        print(f"[e2e] 找不到文本数据集：{path}（先跑 build_text_dataset.py）",
              file=sys.stderr)
        raise SystemExit(2)
    df = pd.read_csv(path)
    missing = [c for c in ("commit_hash", "text") if c not in df.columns]
    if missing:
        print(f"[e2e] 文本数据集缺列：{missing}", file=sys.stderr)
        raise SystemExit(2)
    return df.dropna(subset=["text"]).reset_index(drop=True)


def align_to_shared_split(text_df: pd.DataFrame,
                          train_csv: Path, test_csv: Path):
    """按共享切分的 commit_hash 对齐 —— 与 expert/semantic/fused 同一切分（跨线可比）。

    返回 (train_df, test_df, aligned: bool)。切分文件缺失时返回 (None, None, False)。
    """
    if not train_csv.is_file() or not test_csv.is_file():
        return None, None, False
    index = {h: i for i, h in enumerate(text_df["commit_hash"])}
    out = []
    for csv_path in (train_csv, test_csv):
        split = pd.read_csv(csv_path)
        miss = [h for h in split["commit_hash"] if h not in index]
        if miss:
            print(f"[e2e] 文本缺 {len(miss)} 条切分内提交（例：{miss[0]}）—— 文本与切分窗口不一致", file=sys.stderr)
            raise SystemExit(2)
        part = text_df.iloc[[index[h] for h in split["commit_hash"]]].reset_index(drop=True)
        part["label"] = split["is_bug_inducing"].astype(int).to_numpy()  # 以切分文件标签为准
        out.append(part)
    return out[0], out[1], True


class TextDataset(Dataset):
    def __init__(self, texts, labels, tokenizer, max_len: int):
        self.enc = tokenizer(list(texts), truncation=True, padding="max_length",
                             max_length=max_len, return_tensors="pt")
        self.labels = torch.tensor(np.asarray(labels, dtype=float), dtype=torch.long)

    def __len__(self):
        return len(self.labels)

    def __getitem__(self, i):
        item = {k: v[i] for k, v in self.enc.items()}
        item["labels"] = self.labels[i]
        return item


def load_effort(path: Path, hashes: pd.Series) -> np.ndarray:
    """LOC = la + ld（取自 03 原始表，同 06 口径）。"""
    if not path.is_file():
        print(f"[e2e] 找不到原始特征表：{path}（Effort-aware 指标将缺省）",
              file=sys.stderr)
        return None
    raw = pd.read_csv(path).set_index("commit_hash")
    missing = [h for h in hashes if h not in raw.index]
    if missing:
        print(f"[e2e] 原始特征表缺 {len(missing)} 条提交（例：{missing[0]}）",
              file=sys.stderr)
        return None
    sub = raw.loc[list(hashes)]
    return (sub["la"].astype(float) + sub["ld"].astype(float)).to_numpy()
