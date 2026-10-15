"""仅专家（基线）pipeline 训练入口：产出 8 个模型文件与对应训练报告。

用法（在 `data_model/` 目录下）：:

    conda activate jit-defect-prediction
    python -m pipelines.expert.train                    # 8 模型 + 指标报告 + 覆盖矩阵
    python -m pipelines.expert.train --models lr,rf,xgb    # 只训交付三件套
    python -m pipelines.expert.train --skip-matrix         # 跳过 ⑧（省一半训练时间）
    python -m pipelines.expert.train --skip-shap           # 跳过 SHAP 耗时实测
    python -m pipelines.expert.train --out-root _tmp/smoke # 冒烟测试：产出挪到临时目录

产出（**全部落在本包目录**，与其余三条线隔离）：:

    pipelines/expert/models/*_v1.pkl          8 个模型文件
    pipelines/expert/models/feature_order.txt 交付清单（契约二第三节副本）
    pipelines/expert/reports/model_metrics.md ⑥ 两类指标报告
    pipelines/expert/reports/model_matrix.md  ⑧ 覆盖矩阵 + 与基线逐项自证（差异须为 0）

输入（**共享上游产物**，放 `data_model/data/`，四线共用）：:

    data/split_{tag}_train.csv / split_{tag}_test.csv   ⑤ 的时间序切分下标
    data/commit_features_raw.csv                        ③ 的原始特征表（工作量代理用）

实现复用：训练与指标计算只有一份实现，在 `data_model/06_train_model.py` 与
`08_model_matrix.py`（唯一权威，超参与口径登记在那里）。本脚本只负责**驱动**
与**产出归属**，不复制训练代码 —— 复制会产生第二份超参口径。
"""

from __future__ import annotations

import argparse
import subprocess
import sys
import time
from pathlib import Path

from . import DELIVERY_MODELS, LINE, MODELS, PKG_DIR, SHARED_DATA_DIR

#: data_model/ 目录（共享脚本 06 / 08 所在处）
DATA_MODEL_DIR = Path(__file__).resolve().parents[2]
TRAIN_SCRIPT = DATA_MODEL_DIR / "06_train_model.py"
MATRIX_SCRIPT = DATA_MODEL_DIR / "08_model_matrix.py"


def _run(cmd: list[str]) -> int:
    """执行一条子命令，命令原文回显（复现用：报告里要能照抄）。"""
    print("[%s] $ %s" % (LINE, " ".join(str(c) for c in cmd)), flush=True)
    return subprocess.call([str(c) for c in cmd])


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description="仅专家（基线）pipeline：训练 8 个模型并产出两类指标报告",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    p.add_argument("--models", default=MODELS,
                   help="要训练的模型，逗号分隔（默认 %s）" % MODELS)
    p.add_argument("--delivery-models", default=DELIVERY_MODELS,
                   help="写进 feature_order.txt [models] 段的交付模型"
                        "（默认 %s；其余仅评估对照，不进交付链）" % DELIVERY_MODELS)
    p.add_argument("--tag", default="szz",
                   help="切分文件名的标签标记（默认 szz，对应 data/split_szz_*.csv）")
    p.add_argument("--data-dir", type=Path, default=None,
                   help="共享上游产物目录（默认 data_model/data/；"
                        "冒烟测试可指向临时目录）")
    p.add_argument("--seed", type=int, default=42, help="随机种子（必须固定）")
    p.add_argument("--shap-rows", type=int, default=100,
                   help="SHAP 单条耗时实测的样本条数")
    p.add_argument("--skip-shap", action="store_true", help="跳过 SHAP 耗时实测")
    p.add_argument("--skip-matrix", action="store_true",
                   help="跳过 ⑧ 覆盖矩阵（省一半训练时间；验收需要它，别随便跳）")
    p.add_argument("--out-root", type=Path, default=None,
                   help="产出根目录（默认本包目录 pipelines/expert/）；"
                        "下设 data/ models/ reports/。冒烟测试可指向临时目录，"
                        "避免假数据混进真实产出")
    return p.parse_args()


def main() -> int:
    args = parse_args()

    # 产出目录：默认本包；--out-root 可整体挪走（冒烟测试用）
    out_root = args.out_root or PKG_DIR
    data_dir = out_root / "data"
    models_dir = out_root / "models"
    reports_dir = out_root / "reports"

    train = (args.data_dir or SHARED_DATA_DIR) / ("split_%s_train.csv" % args.tag)
    test = (args.data_dir or SHARED_DATA_DIR) / ("split_%s_test.csv" % args.tag)
    features_raw = (args.data_dir or SHARED_DATA_DIR) / "commit_features_raw.csv"
    missing = [str(p) for p in (train, test, features_raw) if not p.is_file()]
    if missing:
        print("[%s] 缺少共享上游产物：%s" % (LINE, "，".join(missing)), file=sys.stderr)
        print("[%s] 先按 docs/model/pipelines/expert-only.md §3 跑 ①–⑤"
              "（05_split_dataset.py --tag %s）" % (LINE, args.tag), file=sys.stderr)
        return 2

    # 本包三个产出目录（不存在则建；`data/` 当前留给本线私有中间结果）
    for d in (data_dir, models_dir, reports_dir):
        d.mkdir(parents=True, exist_ok=True)

    t0 = time.perf_counter()

    # ⑥ 训练 + 两类指标 + 导出 8 个 .pkl + 交付清单
    cmd = [
        sys.executable, str(TRAIN_SCRIPT),
        "--train", train,
        "--test", test,
        "--features-raw", features_raw,
        "--models", args.models,
        "--delivery-models", args.delivery_models,
        "--seed", args.seed,
        "--model-dir", models_dir,
        "--report", reports_dir / "model_metrics.md",
        "--shap-rows", args.shap_rows,
    ]
    if args.skip_shap:
        cmd.append("--skip-shap")
    rc = _run(cmd)
    if rc != 0:
        print("[%s] 06 训练失败（rc=%d）" % (LINE, rc), file=sys.stderr)
        return rc

    # ⑧ 覆盖矩阵 + 与 model_metrics.md 逐项自证（差异必须为 0）
    if not args.skip_matrix:
        rc = _run([
            sys.executable, str(MATRIX_SCRIPT),
            "--train", train,
            "--test", test,
            "--features-raw", features_raw,
            "--models", args.models,
            "--seed", args.seed,
            "--report", reports_dir / "model_matrix.md",
            "--baseline-report", reports_dir / "model_metrics.md",
        ])
        if rc != 0:
            print("[%s] 08 覆盖矩阵失败（rc=%d）" % (LINE, rc), file=sys.stderr)
            return rc

    # 产出清单：看清“到底交出了什么”，避免四线产物混杂时说不出归属
    elapsed = time.perf_counter() - t0
    pkls = sorted(models_dir.glob("*_v1.pkl"))
    print("\n[%s] ===== 产出清单（%.1f 秒） =====" % (LINE, elapsed))
    print("[%s] 模型文件 %d 个 → %s" % (LINE, len(pkls), models_dir))
    for p in pkls:
        print("[%s]   %s (%.1f MB)" % (LINE, p.name, p.stat().st_size / 1e6))
    for name in ("feature_order.txt", "model_metrics.md", "model_matrix.md"):
        f = models_dir / name if name.endswith(".txt") else reports_dir / name
        print("[%s] %s %s" % (LINE, "✅" if f.is_file() else "⬜", f))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
