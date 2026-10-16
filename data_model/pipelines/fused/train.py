"""fused 线训练 + 验证主流程：Kamei14 ⊕ 语义 768 = 782 维 → 8 个分类器。

入口：`python -m pipelines.fused.train`
前置：semantic 线已产出编码缓存（pipelines/semantic/data/semantic_embeddings.npz）。
流程：双模态对齐（内连接 + 覆盖率断言）→ 拼接 782 维 → 训 8 分类器 → 两类指标 →
      导出 .pkl + manifest → 报告 + 图表。
"""

from __future__ import annotations

import argparse
from pathlib import Path

import joblib
import numpy as np

from . import config, report
from .data import fuse, load_effort, load_embeddings, load_split
from .metrics import effort_aware_metrics, effort_unaware
from .model import MODEL_NAMES, build_model


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="fused 线（Kamei14 ⊕ 语义）训练与验证")
    p.add_argument("--train", type=Path, default=config.TRAIN_CSV)
    p.add_argument("--test", type=Path, default=config.TEST_CSV)
    p.add_argument("--features-raw", type=Path, default=config.FEATURES_RAW_CSV)
    p.add_argument("--embeddings", type=Path, default=config.EMBEDDINGS_NPZ)
    p.add_argument("--models", default=",".join(config.DEFAULT_MODELS))
    p.add_argument("--seed", type=int, default=config.SEED)
    p.add_argument("--model-dir", type=Path, default=config.MODELS_DIR)
    p.add_argument("--report", type=Path, default=config.REPORTS_DIR / "model_metrics.md")
    p.add_argument("--no-export", action="store_true")
    p.add_argument("--no-charts", action="store_true")
    return p.parse_args()


def main() -> int:
    args = parse_args()
    train_df, X_train_k, y_train = load_split(args.train)
    test_df, X_test_k, y_test = load_split(args.test)
    emb_index, emb = load_embeddings(args.embeddings)

    train_df, X_train, _ = fuse(train_df, X_train_k, emb_index, emb)
    test_df, X_test, _ = fuse(test_df, X_test_k, emb_index, emb)
    y_train = train_df[config.LABEL_COL].astype(int).to_numpy()
    y_test = test_df[config.LABEL_COL].astype(int).to_numpy()
    print("[fused] 训练 %d 条 / 检验 %d 条，维度 %d"
          % (len(X_train), len(X_test), X_train.shape[1]))

    effort_loc = load_effort(args.features_raw, test_df["commit_hash"])
    wanted = [m.strip() for m in args.models.split(",") if m.strip()]
    results: dict[str, dict] = {}
    probas: dict[str, np.ndarray] = {}
    for name in wanted:
        model = build_model(name, args.seed)
        model.fit(X_train, y_train)
        proba = model.predict_proba(X_test)[:, 1]
        probas[name] = proba
        eu = effort_unaware(y_test, proba)
        results[name] = {"model_name": "%s_fused_v1" % name,
                         "label": MODEL_NAMES.get(name, name), **eu,
                         "effort": {"LOC（改动行数 la+ld）":
                                    effort_aware_metrics(proba, y_test, effort_loc)}}
        if not args.no_export:
            args.model_dir.mkdir(parents=True, exist_ok=True)
            joblib.dump(model, args.model_dir / ("%s_fused_v1.pkl" % name))
        print("[fused] %-8s AUC=%.4f  F1=%.4f  P=%.4f  R=%.4f"
              % (name, eu["auc"], eu["f1"], eu["precision"], eu["recall"]))

    if not args.no_export:
        (args.model_dir / "manifest.txt").write_text(
            "[input]\nKamei 14（契约二第三节顺序）⊕ 冻结语义 768 = %d 维\n"
            "语义缓存：%s\n\n[models]\n%s\n"
            % (config.EXPECTED_DIM, config.EMBEDDINGS_NPZ,
               "".join("%s_fused_v1.pkl\t%s\n" % (m, MODEL_NAMES.get(m, m))
                       for m in wanted)),
            encoding="utf-8", newline="\n")

    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(report.render(args, results, len(X_train), len(X_test),
                                         y_test),
                           encoding="utf-8", newline="\n")
    print("[fused] 报告：%s" % args.report)
    if not args.no_charts:
        figs = report.make_charts(results, probas, y_test, effort_loc,
                                  args.report.parent / report.FIG_DIR_NAME)
        for f in figs:
            print("[fused] 图表：%s" % f)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
