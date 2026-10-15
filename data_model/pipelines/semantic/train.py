"""semantic 线训练 + 验证主流程：冻结 CodeBERT 768 维向量 → 8 个分类器。

入口：`python -m pipelines.semantic.train`
流程：取文本（缺则自建）→ 冻结编码（缓存）→ 按共享切分对齐 → 训 8 分类器 →
      两类指标 → 导出 .pkl + manifest → 报告 + 图表。

关键点：
  · **同一切分**：训练/检验行来自 data/split_szz_{train,test}.csv 的 commit_hash，
    编码缓存按 hash 索引 —— 与 expert/e2e 严格同切分，跨线可比。
  · **编码只前向**：冻结 CodeBERT 无梯度；缓存 npz 后二次运行秒级。
  · 分类器族与 expert 完全一致 —— 跨线差异只归因于「特征模态」。
"""

from __future__ import annotations

import argparse
from pathlib import Path

import joblib
import numpy as np

from . import config, report
from .data import (encode_texts, load_effort, load_embeddings, load_split_hashes,
                   load_texts, extract_texts_from_repo, save_embeddings)
from .metrics import effort_aware_metrics, effort_unaware
from .model import MODEL_NAMES, build_model


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="semantic 线（冻结 CodeBERT）训练与验证")
    p.add_argument("--text-csv", type=Path, default=config.TEXT_CSV)
    p.add_argument("--repo", type=Path, default=None,
                   help="文本缺失时自动建；指向克隆仓库（data/camel）")
    p.add_argument("--embeddings", type=Path, default=config.EMBEDDINGS_NPZ)
    p.add_argument("--force-encode", action="store_true", help="忽略缓存重新编码")
    p.add_argument("--train", type=Path, default=config.TRAIN_CSV)
    p.add_argument("--test", type=Path, default=config.TEST_CSV)
    p.add_argument("--features-raw", type=Path, default=config.FEATURES_RAW_CSV)
    p.add_argument("--models", default=",".join(config.DEFAULT_MODELS))
    p.add_argument("--seed", type=int, default=config.SEED)
    p.add_argument("--model-dir", type=Path, default=config.MODELS_DIR)
    p.add_argument("--report", type=Path, default=config.REPORTS_DIR / "model_metrics.md")
    p.add_argument("--no-export", action="store_true")
    p.add_argument("--no-charts", action="store_true")
    return p.parse_args()


def get_embeddings(args) -> tuple[list[str], np.ndarray]:
    if args.embeddings.is_file() and not args.force_encode:
        hashes, emb, _, fv = load_embeddings(args.embeddings)
        print("[semantic] 读缓存：%s（%d 条 × %d 维，fv=%s）"
              % (args.embeddings, len(hashes), emb.shape[1], fv))
        return hashes, emb
    df = load_texts(args.text_csv)
    print("[semantic] 冻结编码 %d 条文本（%s）…" % (len(df), config.TEXT_MODEL))
    emb = encode_texts(df["text"].tolist(), config.TEXT_MODEL,
                       config.MAX_LEN, config.ENCODE_BATCH)
    save_embeddings(args.embeddings, df, emb)
    print("[semantic] 缓存已写：%s" % args.embeddings)
    return df["commit_hash"].tolist(), emb


def main() -> int:
    args = parse_args()
    if not args.train.is_file() or not args.test.is_file():
        raise SystemExit("[semantic] 缺切分文件（先跑 05）")
    if args.force_encode or not args.embeddings.is_file():
        if not args.text_csv.is_file():
            if not args.repo:
                raise SystemExit("[semantic] 文本与缓存都缺：传 --repo 自动建文本")
            out = extract_texts_from_repo(args.repo, config.DATASET_CSV,
                                          args.text_csv, config.MAX_CHARS)
            print("[semantic] 文本已建：%s" % out)

    hashes, emb = get_embeddings(args)
    index = {h: i for i, h in enumerate(hashes)}
    train_hashes, y_train = load_split_hashes(args.train)
    test_hashes, y_test = load_split_hashes(args.test)
    miss = [h for h in train_hashes + test_hashes if h not in index]
    if miss:
        raise SystemExit("[semantic] 编码缓存缺 %d 条切分内提交（例：%s）—— "
                         "文本与切分窗口不一致" % (len(miss), miss[0]))
    X_train = emb[[index[h] for h in train_hashes]]
    X_test = emb[[index[h] for h in test_hashes]]

    effort_loc = load_effort(args.features_raw, __import__("pandas").Series(test_hashes))
    wanted = [m.strip() for m in args.models.split(",") if m.strip()]
    results: dict[str, dict] = {}
    probas: dict[str, np.ndarray] = {}
    for name in wanted:
        model = build_model(name, args.seed)
        model.fit(X_train, y_train)
        proba = model.predict_proba(X_test)[:, 1]
        probas[name] = proba
        eu = effort_unaware(y_test, proba)
        results[name] = {"model_name": "%s_semantic_v1" % name,
                         "label": MODEL_NAMES.get(name, name), **eu,
                         "effort": {"LOC（改动行数 la+ld）":
                                    effort_aware_metrics(proba, y_test, effort_loc)}}
        if not args.no_export:
            args.model_dir.mkdir(parents=True, exist_ok=True)
            joblib.dump(model, args.model_dir / ("%s_semantic_v1.pkl" % name))
        print("[semantic] %-8s AUC=%.4f  F1=%.4f  P=%.4f  R=%.4f"
              % (name, eu["auc"], eu["f1"], eu["precision"], eu["recall"]))

    if not args.no_export:
        (args.model_dir / "manifest.txt").write_text(
            "[encoder]\n%s（冻结，mean-pool，%d 维）\n\n[models]\n%s\n\n[split]\n"
            "data/split_szz_{train,test}.csv（与 expert 同一切分）\n"
            % (config.TEXT_MODEL, X_train.shape[1],
               "".join("%s_semantic_v1.pkl\t%s\n" % (m, MODEL_NAMES.get(m, m))
                       for m in wanted)),
            encoding="utf-8", newline="\n")

    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(report.render(args, results, len(train_hashes),
                                         len(test_hashes), y_test),
                           encoding="utf-8", newline="\n")
    print("[semantic] 报告：%s" % args.report)
    if not args.no_charts:
        figs = report.make_charts(results, probas, y_test, effort_loc,
                                  args.report.parent / report.FIG_DIR_NAME)
        for f in figs:
            print("[semantic] 图表：%s" % f)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
