"""fused 线数据：Kamei 14（切分文件）⊕ 语义 768（semantic 缓存）按 commit_hash 对齐拼接。

对齐规则：以内连接（两边都有的提交才进样本），并断言覆盖率 —— 缺口超过 1% 直接失败，
因为「特征缺一半还训练」会让跨线对比失去意义。
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

from . import config


def load_split(csv_path: Path) -> tuple[pd.DataFrame, np.ndarray, np.ndarray]:
    if not csv_path.is_file():
        print(f"[fused] 找不到切分文件：{csv_path}（先跑 05）", file=sys.stderr)
        raise SystemExit(2)
    df = pd.read_csv(csv_path)
    missing = [c for c in config.FEATURE_FIELDS + [config.LABEL_COL] if c not in df.columns]
    if missing:
        print(f"[fused] 切分文件缺列：{missing}", file=sys.stderr)
        raise SystemExit(2)
    return (
        df,
        df[config.FEATURE_FIELDS].to_numpy(dtype=float),
        df[config.LABEL_COL].astype(int).to_numpy(),
    )


def load_embeddings(path: Path) -> tuple[dict[str, int], np.ndarray]:
    if not path.is_file():
        print(
            f"[fused] 找不到语义编码缓存：{path} —— 先跑 python -m pipelines.semantic.train 生成",
            file=sys.stderr,
        )
        raise SystemExit(2)
    z = np.load(path, allow_pickle=False)
    hashes = [str(h) for h in z["commit_hash"]]
    emb = z["embeddings"]
    if emb.ndim != 2 or emb.shape[1] != 768:
        print(f"[fused] 语义缓存维度异常：{emb.shape}（期望 N×768）", file=sys.stderr)
        raise SystemExit(2)
    return {h: i for i, h in enumerate(hashes)}, emb


def fuse(kamei_df: pd.DataFrame, kamei_X: np.ndarray, emb_index: dict[str, int], emb: np.ndarray):
    """按 commit_hash 内连接拼接，返回 (对齐后的 df, X_fused, y)。"""
    idx = [emb_index.get(h, -1) for h in kamei_df["commit_hash"]]
    keep = np.array([i >= 0 for i in idx])
    coverage = keep.mean() * 100
    if coverage < 99.0:
        print(
            f"[fused] 语义覆盖率只有 {coverage:.2f}%（缺 {(~keep).sum()} 条）—— 缺口过大，拒绝训练",
            file=sys.stderr,
        )
        raise SystemExit(2)
    if coverage < 100.0:
        print(
            f"[fused] ⚠ 语义覆盖 {coverage:.2f}%：缺的 {(~keep).sum()} 条以内连接丢弃（如实登记在报告）"
        )
    sel = np.where(keep)[0]
    X_sem = emb[[idx[i] for i in sel]]
    X = np.concatenate([kamei_X[sel], X_sem], axis=1)
    if X.shape[1] != config.EXPECTED_DIM:
        print(f"[fused] 拼接维度 {X.shape[1]} ≠ 预期 {config.EXPECTED_DIM}", file=sys.stderr)
        raise SystemExit(2)
    return kamei_df.iloc[sel].reset_index(drop=True), X, sel


def load_effort(path: Path, hashes: pd.Series) -> np.ndarray:
    raw = pd.read_csv(path).set_index("commit_hash")
    missing = [h for h in hashes if h not in raw.index]
    if missing:
        print(f"[fused] 原始特征表缺 {len(missing)} 条（例：{missing[0]}）", file=sys.stderr)
        raise SystemExit(2)
    sub = raw.loc[list(hashes)]
    return (sub["la"].astype(float) + sub["ld"].astype(float)).to_numpy()
