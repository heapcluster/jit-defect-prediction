"""清空演示数据：保留表结构与随仓库交付的模型权重，回到「首次使用」状态。

清空内容：
- 业务数据：prediction / model_figure / dataset_commit / dataset / job / commit_feature / commit
- 用户配置：user_config（设置页与各页偏好回到出厂值）
- 自训练模型：model_artifact 与对应 model 行（随仓库交付的模型保留）
- 运行时文件：temp/outputs 与各类输入/缓存目录

用法（在 backend/ 目录）：
    python -m scripts.reset_demo_data --yes
    python -m scripts.reset_demo_data --yes --keep-config   # 只清业务数据
"""

from __future__ import annotations

import argparse
import shutil
import sys
from pathlib import Path

from sqlalchemy import select, text

from app import config
from app.db import SessionLocal, get_engine
from app.models import Model

# 先删子表再删父表，避免外键约束失败。
TABLES = (
    "prediction",
    "model_figure",
    "dataset_commit",
    "dataset",
    "model_artifact",
    "job",
    "commit_feature",
    "commit",
)

RUNTIME_DIRS = (
    "outputs",
    "collect_inputs",
    "collect_cache",
    "clean_inputs",
    "train_inputs",
    "predict_inputs",
    "evaluate_inputs",
    "explain_inputs",
)

# 随仓库交付的模型权重文件名（不含扩展名），这些 model 行保留。
def shipped_models() -> set[str]:
    if not config.MODEL_DIR.is_dir():
        return set()
    return {path.stem for path in config.MODEL_DIR.glob("*.pkl")}


def counts(session) -> dict[str, int]:
    result = {}
    for table in ("prediction", "dataset", "dataset_commit", "job", "commit", "commit_feature",
                  "model_artifact", "model", "user_config"):
        result[table] = session.execute(text(f"SELECT COUNT(*) FROM `{table}`")).scalar_one()
    return result


def clear_tables(session, keep_config: bool) -> None:
    for table in TABLES:
        session.execute(text(f"DELETE FROM `{table}`"))
    if not keep_config:
        session.execute(text("DELETE FROM `user_config`"))
        session.execute(text("DELETE FROM `user` WHERE `user_id` <> 'global'"))
    keep = shipped_models()
    stale = session.scalars(select(Model.model_name)).all()
    for name in stale:
        if name not in keep:
            session.execute(text("DELETE FROM `model` WHERE `model_name` = :name"), {"name": name})
    session.commit()


def clear_runtime_files() -> list[str]:
    removed = []
    for name in RUNTIME_DIRS:
        path: Path = config.TEMP_ROOT / name
        if not path.is_dir():
            continue
        for child in path.iterdir():
            if child.is_dir() and not child.is_symlink():
                shutil.rmtree(child, ignore_errors=True)
            else:
                child.unlink(missing_ok=True)
        removed.append(str(path.relative_to(config.REPO_ROOT)))
    return removed


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description="清空演示数据并回到空白配置")
    parser.add_argument("--yes", action="store_true", help="确认执行删除")
    parser.add_argument("--keep-config", action="store_true", help="保留 user_config 配置")
    parser.add_argument("--keep-files", action="store_true", help="保留 temp 运行时文件")
    args = parser.parse_args(argv[1:])
    if not args.yes:
        print("将删除业务数据、自训练模型与运行时文件；确认后加 --yes 再执行。", file=sys.stderr)
        return 2

    get_engine()  # 初始化连接池后再创建 Session
    with SessionLocal() as session:
        before = counts(session)
        print("清理前：", before)
        clear_tables(session, args.keep_config)
        after = counts(session)
        print("清理后：", after)
    if not args.keep_files:
        print("已清理运行时目录：", clear_runtime_files())
    print("完成。请重启后端以清空内存中的自训练模型。")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
