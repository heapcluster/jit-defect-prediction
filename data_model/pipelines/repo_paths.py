"""报告与证据里的路径渲染：**只写仓内相对路径**。

背景（2026-10-25 缺陷修复）：`fused/reports/model_metrics.md` 与
`e2e/reports/prediction_stats.md` 曾把 `config.EMBEDDINGS_NPZ` / `args.out`
的**绝对路径**原样写进报告 —— 那些路径经 `Path.resolve()` 必然带本机盘符，
而 `reports/` 是可入库证据：任何机器上重跑都会把该机器的盘符写进仓库，
且已入库的两份报告要靠手工清洗（治标不治本）。

规矩：凡是要写进入库证据的路径，一律过 `rel_to_data_model()`；
仓库外的路径只写文件名，不写目录。
"""

from __future__ import annotations

from pathlib import Path

DATA_MODEL_ROOT = Path(__file__).resolve().parents[1]


def rel_to_data_model(path: Path | str) -> str:
    """把路径渲染成相对 `data_model/` 的 POSIX 形式；仓库外只留文件名。"""
    p = Path(path)
    try:
        return p.resolve().relative_to(DATA_MODEL_ROOT).as_posix()
    except (ValueError, OSError):
        return p.name
