"""图集落地：把仓库内的逐模型 PNG 同步到 `backend/static/figures/`。

`backend/static/figures/` 不入库（`.gitignore`），干净检出时为空；图集源文件在
`data_model/pipelines/{line}/reports/figs_by_model/{model}/` 并已入库。启动时按需
拷贝，保证「生成 → 静态目录」这一步不靠人工，且不覆盖已有文件（只在缺失或源更新时复制）。
"""

from __future__ import annotations

import logging
import shutil

from app import config

logger = logging.getLogger("backend.figure_store")

_LINES = ("expert", "semantic", "fused", "e2e")


def _copy_tree(src: str, dst) -> int:
    copied = 0
    for png in src.rglob("*.png"):
        rel = png.relative_to(src)
        target = dst / rel
        if target.is_file() and target.stat().st_mtime >= png.stat().st_mtime:
            continue
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(png, target)
        copied += 1
    return copied


def sync_figures() -> int:
    """把 `data_model/pipelines/{line}/reports/figs_by_model` 同步到静态图目录。

    返回本次复制的文件数；源目录缺失时跳过（接口侧再做降级）。
    """
    copied = 0
    for line in _LINES:
        src = config.PIPELINES_DIR / line / "reports" / "figs_by_model"
        if not src.is_dir():
            continue
        copied += _copy_tree(src, config.FIGURES_DIR / line)
    if copied:
        logger.info("figures synced: %s files -> %s", copied, config.FIGURES_DIR)
    return copied
