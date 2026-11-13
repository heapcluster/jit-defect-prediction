"""导出 MySQL 8.0 测试集初始化 SQL。

建表 DDL 的唯一真源是仓库根 `infra/schema.sql`（docker compose / CI 实际执行它），
本模块不再导出 schema 副本；只负责生成 `data_init.sql`（测试集 INSERT）。

字段口径以 `docs/database/*.md` 为准：
- `commit` / `prediction` / `model_figure` 用自然键做主键（不再造自增 id）；
- `commit_label` 已下线，SZZ 真标签并入 `commit_feature.is_bug_inducing` / `labeled_at`；
- `runtime_setting` 已下线（默认模型 = 已加载模型中 `version_key` 最大者）；
- `commit_feature.committed_at`、`prediction.feature_version` 为冗余列，不再落库。
"""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

import numpy as np
import pandas as pd

from . import config


# ── 值转义 ──────────────────────────────────────────────────────────────────
def _q(v) -> str:
    if v is None:
        return "NULL"
    if isinstance(v, float) and np.isnan(v):
        return "NULL"
    s = str(v)
    if s in ("", "nan", "NaT", "None"):
        return "NULL" if s in ("nan", "NaT", "None") else "''"
    return "'" + s.replace("\\", "\\\\").replace("'", "''") + "'"


def _q_ns(v) -> str:
    """可空字符串：空串、None、NaN → NULL。"""
    if v is None:
        return "NULL"
    if isinstance(v, float) and np.isnan(v):
        return "NULL"
    s = str(v)
    return "NULL" if s == "" else "'" + s.replace("\\", "\\\\").replace("'", "''") + "'"


def _num(v, nd: int = 10) -> str:
    if v is None:
        return "NULL"
    f = float(v)
    if np.isnan(f):
        return "NULL"
    return f"{f:.{nd}f}"


def _row(vals: list[str]) -> str:
    return "(" + ", ".join(vals) + ")"


def _write_inserts(
    f, table: str, columns: list[str], rows: list[str], batch: int = 1000, ignore: bool = False
) -> None:
    cols = ", ".join(f"`{c}`" for c in columns)
    verb = "INSERT IGNORE" if ignore else "INSERT"
    for i in range(0, len(rows), batch):
        chunk = rows[i : i + batch]
        f.write(f"{verb} INTO `{table}` ({cols}) VALUES\n")
        f.write(",\n".join(chunk))
        f.write(";\n\n")


# ── 导出 ────────────────────────────────────────────────────────────────────
def write_data_init(path: Path, test: pd.DataFrame, preds: pd.DataFrame, figures: list[dict]) -> Path:
    test_hashes = test["commit_hash"].tolist()
    predicted_at = datetime.now(UTC).strftime("%Y-%m-%d %H:%M:%S")

    commits = pd.read_csv(config.COMMITS_CSV).set_index("commit_hash")
    missing = [h for h in test_hashes if h not in commits.index]
    if missing:
        raise SystemExit(f"[eval] commits.csv 缺 {len(missing)} 条测试集提交（例：{missing[0]}）")
    commits = commits.loc[test_hashes].reset_index()

    labels = pd.read_csv(config.LABELS_SZZ_CSV)
    labels = labels[labels["label_method"] == "szz"].set_index("commit_hash")
    lmissing = [h for h in test_hashes if h not in labels.index]
    if lmissing:
        raise SystemExit(f"[eval] commit_labels_szz.csv 缺 {len(lmissing)} 条（例：{lmissing[0]}）")

    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="\n") as f:
        f.write("-- JIT 缺陷预测 测试集初始化数据（MySQL 8.0）\n")
        f.write("-- 先执行 schema.sql 建表，再在空表上执行本文件。\n")
        f.write(f"-- 测试集 {len(test_hashes)} 条；模型 {len(config.MODEL_LIST)} 个；"
                f"预测 {len(preds)} 行；图元数据 {len(figures)} 行。\n")
        f.write("SET NAMES utf8mb4;\n\n")

        # 1) commit
        rows = [
            _row([
                _q(r.repo_name),
                _q(r.commit_hash),
                _q(r.author_name),
                _q_ns(r.author_email),
                _q(r.committed_at),
                _q(r.message),
                _q_ns(r.parent_hash),
            ])
            for r in commits.itertuples(index=False)
        ]
        f.write("-- 1) commit\n")
        _write_inserts(f, "commit", ["repo_name", "commit_hash", "author_name",
                                     "author_email", "committed_at", "message", "parent_hash"], rows)

        # 2) model
        rows = []
        for line, algo in config.MODEL_LIST:
            name = config.model_name(line, algo)
            rows.append(_row([
                _q(name), "''", "NULL", _q(algo),
                _q(config.FEATURE_VERSION[line]), _q(line),
            ]))
        f.write("-- 2) model（25 个；已存在同名模型时跳过，保证幂等）\n")
        _write_inserts(f, "model", ["model_name", "version_key", "trained_at",
                                    "algo", "feature_version", "line"], rows, ignore=True)

        # 3) commit_feature（is_test=1；14 维特征 + SZZ 真标签同表）
        rows = []
        for r in test.itertuples(index=False):
            lab = labels.loc[r.commit_hash]
            vals = [_q(r.commit_hash), _q(r.feature_version)]
            for c in config.FEATURE_FIELDS:
                v = getattr(r, c)
                vals.append(str(int(round(float(v)))) if c == "fix" else _num(v))
            vals.append("1")
            vals.append(str(int(lab["is_bug_inducing"])))
            vals.append(_q(lab["labeled_at"]))
            rows.append(_row(vals))
        f.write("-- 3) commit_feature（is_test=1；14 维特征 + SZZ 真标签）\n")
        _write_inserts(f, "commit_feature",
                       ["commit_hash", "feature_version",
                        *config.FEATURE_FIELDS, "is_test", "is_bug_inducing", "labeled_at"], rows)

        # 4) prediction（25 模型 × 测试集；特征版本由 model.feature_version 决定，不落本表）
        rows = [
            _row([
                _q(r.commit_hash), _q(r.model_name),
                _num(r.risk_score, 5), _q(predicted_at),
            ])
            for r in preds.itertuples(index=False)
        ]
        f.write("-- 4) prediction（25 模型 × 测试集）\n")
        _write_inserts(f, "prediction", ["commit_hash", "model_name", "risk_score",
                                         "predicted_at"], rows)

        # 5) model_figure
        rows = [
            _row([_q(g["model_name"]), _q(g["figure_type"]), _q(g["title"]),
                  _q(g["file_path"]), _q(g["generated_at"])])
            for g in figures
        ]
        f.write("-- 5) model_figure\n")
        _write_inserts(f, "model_figure", ["model_name", "figure_type", "title",
                                           "file_path", "generated_at"], rows)

    print(f"[eval] 数据初始化脚本：{path}")
    return path
