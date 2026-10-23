"""expert 线数据加载与预处理。

输入是 05 切分好的时间序数据集（前 70% 训练 / 后 30% 检验），本模块**不切分**——
切分口径唯一属于 05，这里只做加载 + 列校验 + 工作量表对齐。
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

from . import config


def load_splits(train_csv: Path, test_csv: Path) -> tuple[pd.DataFrame, pd.DataFrame]:
    """加载训练/检验集并校验列完整性与标签存在性。缺列直接失败，不静默补。"""
    for path in (train_csv, test_csv):
        if not path.is_file():
            print(f"[expert] 找不到切分文件：{path}（先跑 05_split_dataset.py）",
                  file=sys.stderr)
            raise SystemExit(2)
    train = pd.read_csv(train_csv)
    test = pd.read_csv(test_csv)
    missing = [c for c in config.FEATURE_FIELDS + [config.LABEL_COL]
               if c not in train.columns]
    if missing:
        print(f"[expert] 训练集缺列：{missing}", file=sys.stderr)
        raise SystemExit(2)
    if config.LABEL_COL not in test.columns:
        print(f"[expert] 检验集缺 `{config.LABEL_COL}` —— 只认主标签 szz",
              file=sys.stderr)
        raise SystemExit(2)
    return train, test


def xy(df: pd.DataFrame) -> tuple[np.ndarray, np.ndarray]:
    """取特征矩阵与标签向量（顺序 = config.FEATURE_FIELDS）。"""
    return (df[config.FEATURE_FIELDS].to_numpy(dtype=float),
            df[config.LABEL_COL].astype(int).to_numpy())


def load_effort(path: Path, hashes: pd.Series) -> pd.DataFrame:
    """从原始特征表取工作量：LOC = la + ld，文件数 = nf。

    样本集里的 la/ld/nf 已归一化/取对数，不能当工作量用 —— 必须回 03 的原始表。
    """
    if not path.is_file():
        print(f"[expert] 找不到原始特征表：{path}（先跑 03_extract_features.py）",
              file=sys.stderr)
        raise SystemExit(2)
    raw = pd.read_csv(path).set_index("commit_hash")
    missing = [h for h in hashes if h not in raw.index]
    if missing:
        print(f"[expert] 原始特征表缺 {len(missing)} 条提交（例：{missing[0]}）—— 03 与 04/05 窗口不一致", file=sys.stderr)
        raise SystemExit(2)
    sub = raw.loc[list(hashes)]
    return pd.DataFrame({
        "effort_loc": (sub["la"].astype(float) + sub["ld"].astype(float)).to_numpy(),
        "effort_files": sub["nf"].astype(float).to_numpy(),
    }, index=hashes.to_numpy())
