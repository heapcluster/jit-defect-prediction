"""e2e 线训练 + 验证主流程：CodeBERT 端到端微调（唯一需要 GPU 的线）。

入口：`python -m pipelines.e2e.train`（先跑 build_text_dataset.py 产文本）
流程：文本 → **共享切分对齐**（与 expert/semantic/fused 同一切分）→ Trainer 微调
      （自动 CUDA + fp16，load_best_model_at_end）→ 检验集两类指标 → 保存模型 →
      报告 + 图表。

可复现：种子全固定（torch/numpy/transformers）；同一命令连跑两次指标逐项一致
（GPU 非确定性算子可能带来小数点后三位的抖动，报告如实登记设备）。
"""

from __future__ import annotations

import argparse
import time
from pathlib import Path

import numpy as np
import torch
from torch.utils.data import DataLoader
from transformers import Trainer, TrainingArguments
from transformers.trainer_utils import set_seed as hf_set_seed

from . import config, report
from .data import TextDataset, align_to_shared_split, load_effort, load_texts
from .metrics import effort_aware_metrics, effort_unaware
from .model import build_model, load_tokenizer, predict_proba


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="e2e 线（CodeBERT 微调）训练与验证")
    p.add_argument("--text-csv", type=Path, default=config.TEXT_CSV)
    p.add_argument("--train", type=Path, default=config.TRAIN_CSV,
                   help="共享切分训练集（对齐 commit_hash）；缺省时按 --eval-frac 兜底")
    p.add_argument("--test", type=Path, default=config.TEST_CSV)
    p.add_argument("--features-raw", type=Path, default=config.FEATURES_RAW_CSV)
    p.add_argument("--text-model", default=config.TEXT_MODEL)
    p.add_argument("--model-dir", type=Path, default=config.MODEL_DIR)
    p.add_argument("--report", type=Path, default=config.REPORT)
    p.add_argument("--max-len", type=int, default=config.MAX_LEN)
    p.add_argument("--epochs", type=int, default=config.EPOCHS)
    p.add_argument("--batch-size", type=int, default=config.BATCH_SIZE)
    p.add_argument("--lr", type=float, default=config.LEARNING_RATE)
    p.add_argument("--weight-decay", type=float, default=config.WEIGHT_DECAY)
    p.add_argument("--seed", type=int, default=config.SEED)
    p.add_argument("--eval-frac", type=float, default=config.EVAL_FRAC)
    p.add_argument("--no-charts", action="store_true")
    return p.parse_args()


def main() -> int:
    args = parse_args()
    hf_set_seed(args.seed)
    torch.manual_seed(args.seed)
    np.random.seed(args.seed)

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    print("[e2e] 设备：%s%s" % (device, "（fp16 已开启）" if torch.cuda.is_available()
                                else "（CPU，微调极慢，建议 4060）"))

    df = load_texts(args.text_csv)
    tokenizer = load_tokenizer(args.text_model)

    # 切分：优先共享切分（跨线可比）；缺失时按时间序尾部分留验兜底
    train_df, test_df, aligned = align_to_shared_split(df, args.train, args.test)
    if not aligned:
        n_eval = max(1, int(len(df) * args.eval_frac))
        test_df = df.tail(n_eval).reset_index(drop=True)
        train_df = df.head(len(df) - n_eval).reset_index(drop=True)
        print("[e2e] ⚠ 未找到共享切分文件，按时间序尾部分留 %.0f%% 兜底 —— "
              "跨线对比请先跑 05" % (args.eval_frac * 100))
    y_test = test_df["label"].to_numpy().astype(int)

    # 验证集：从训练尾部按时间序切 10%，仅供 Trainer 选最佳模型。
    # 检验集绝不参与模型选择（否则 load_best_model_at_end 就是信息泄漏）。
    n_val = max(1, int(len(train_df) * args.eval_frac))
    val_df = train_df.tail(n_val).reset_index(drop=True)
    train_core = train_df.head(len(train_df) - n_val).reset_index(drop=True)
    print("[e2e] 训练 %d / 验证 %d / 检验 %d（验证集来自训练尾部时间序）"
          % (len(train_core), len(val_df), len(test_df)))

    train_ds = TextDataset(train_core["text"].tolist(), train_core["label"].tolist(),
                           tokenizer, args.max_len)
    val_ds = TextDataset(val_df["text"].tolist(), val_df["label"].tolist(),
                         tokenizer, args.max_len)
    test_ds = TextDataset(test_df["text"].tolist(), y_test, tokenizer, args.max_len)
    test_loader = DataLoader(test_ds, batch_size=args.batch_size, shuffle=False)

    model = build_model(args.text_model)
    grad_accum = max(1, config.GRAD_ACCUM_TARGET // args.batch_size)
    training_args = TrainingArguments(
        output_dir=str(args.model_dir / "checkpoints"),
        num_train_epochs=args.epochs,
        per_device_train_batch_size=args.batch_size,
        per_device_eval_batch_size=args.batch_size,
        gradient_accumulation_steps=grad_accum,
        learning_rate=args.lr,
        weight_decay=args.weight_decay,
        fp16=torch.cuda.is_available(),
        eval_strategy="epoch",
        save_strategy="epoch",
        load_best_model_at_end=True,
        metric_for_best_model="loss",
        greater_is_better=False,
        save_total_limit=1,
        logging_steps=50,
        seed=args.seed,
        report_to="none",
    )
    trainer = Trainer(model=model, args=training_args,
                      train_dataset=train_ds, eval_dataset=val_ds)
    t0 = time.perf_counter()
    trainer.train()
    print("[e2e] 训练耗时 %.1fs（最佳模型已加载）" % (time.perf_counter() - t0))

    proba = predict_proba(trainer.model, test_loader, device)
    res = effort_unaware(y_test, proba)
    effort_loc = load_effort(args.features_raw, test_df["commit_hash"])
    if effort_loc is not None and len(effort_loc) == len(y_test):
        res["effort"] = effort_aware_metrics(proba, y_test, effort_loc)

    args.model_dir.mkdir(parents=True, exist_ok=True)
    trainer.model.save_pretrained(str(args.model_dir))
    tokenizer.save_pretrained(str(args.model_dir))
    print("[e2e] 模型已保存：%s" % args.model_dir)

    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(report.render(args, len(train_core), len(val_df),
                                         len(test_df), y_test, res),
                           encoding="utf-8", newline="\n")
    print("[e2e] AUC=%.4f  F1=%.4f  P=%.4f  R=%.4f"
          % (res["auc"], res["f1"], res["precision"], res["recall"]))
    print("[e2e] 报告：%s" % args.report)
    if not args.no_charts:
        for f in report.make_charts(y_test, proba, effort_loc,
                                    args.report.parent / report.FIG_DIR_NAME):
            print("[e2e] 图表：%s" % f)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
