"""Kamei 14 项特征的消融与置换重要性（P5，对应 `model-line-execution-plan.md` §P5）。

回答两个问题，用两个**互不替代**的口径交叉验证：

1. **留一法消融（leave-one-out）**：每次从训练集里删掉一列重训，看**检验集 AUC** 掉多少。
   掉得多 = 该特征在当前模型容量下的边际贡献大。这是「训练侧」的口径。
2. **置换重要性（permutation）**：不动模型，把检验集某一列打乱后重算 AUC，掉得多 = 模型
   实际依赖该列。这是「推理侧」的口径，能抓到「训练时没用、但预测时被当成主证据」的列。

两个口径给出**不同排序是正常的**，报告必须把差异写出来，不能只挑顺眼的一口径。若某列
删除后 AUC **上升**，如实记为「负贡献」，不粉饰成噪声。

产物：`data_model/pipelines/expert/reports/feature_ablation.md`（Top-K 排序 + 两口径交叉 + 结论）。

用法：
    cd data_model
    python 15_feature_ablation.py                       # 默认 xgb，14 次重训
    python 15_feature_ablation.py --model lr --limit 3000   # 冒烟
    python 15_feature_ablation.py --perm-repeats 10     # 置换重复次数
"""

from __future__ import annotations

import argparse
import time
from pathlib import Path

import numpy as np
from pipelines.expert import config
from pipelines.expert.data import load_splits, xy
from pipelines.expert.model import build_model
from sklearn.metrics import f1_score, roc_auc_score

OUT_DEFAULT = config.REPORTS_DIR / "feature_ablation.md"


def _fit_eval(model_name: str, seed: int, X_tr, y_tr, X_te, y_te) -> dict:
    """训练一次并返回检验集指标（阈值固定 0.5，与契约三一致）。"""
    model = build_model(model_name, seed)
    model.fit(X_tr, y_tr)
    proba = model.predict_proba(X_te)[:, 1]
    return {
        "auc": float(roc_auc_score(y_te, proba)),
        "f1": float(f1_score(y_te, (proba >= config.DECISION_THRESHOLD).astype(int), zero_division=0)),
    }


def leave_one_out(model_name, seed, X_tr, y_tr, X_te, y_te, features) -> list[dict]:
    """逐列删除后重训；`delta` 为「删掉后的 AUC − 全量 AUC」，负值表示该列有用。"""
    base = _fit_eval(model_name, seed, X_tr, y_tr, X_te, y_te)
    rows = []
    for idx, name in enumerate(features):
        keep = [i for i in range(X_tr.shape[1]) if i != idx]
        m = _fit_eval(model_name, seed, X_tr[:, keep], y_tr, X_te[:, keep], y_te)
        rows.append({
            "feature": name,
            "auc_without": m["auc"],
            "delta_auc": m["auc"] - base["auc"],
            "delta_f1": m["f1"] - base["f1"],
        })
    return base, rows


def permutation_importance(model, X_te, y_te, features, repeats: int, seed: int) -> list[dict]:
    """打乱检验集某一列后重算 AUC；重复 `repeats` 次取均值，标准差一并回报。"""
    rng = np.random.default_rng(seed)
    base_auc = float(roc_auc_score(y_te, model.predict_proba(X_te)[:, 1]))
    rows = []
    for idx, name in enumerate(features):
        drops = []
        for _ in range(repeats):
            X_perm = X_te.copy()
            rng.shuffle(X_perm[:, idx])
            drops.append(base_auc - float(roc_auc_score(y_te, model.predict_proba(X_perm)[:, 1])))
        rows.append({
            "feature": name,
            "drop_mean": float(np.mean(drops)),
            "drop_std": float(np.std(drops, ddof=1)) if repeats > 1 else 0.0,
        })
    return base_auc, rows


def _rank(rows, key, reverse=True) -> dict[str, int]:
    order = sorted(rows, key=lambda r: r[key], reverse=reverse)
    return {r["feature"]: i + 1 for i, r in enumerate(order)}


def render_report(base, loo_rows, perm_rows, base_auc, model_name, seed, elapsed, limit) -> str:
    # 留一法的 delta 是「删掉后的 AUC − 全量 AUC」，**越负越重要**，故升序排名（最小者第 1）
    loo_rank = _rank(loo_rows, "delta_auc", reverse=False)
    perm_rank = _rank(perm_rows, "drop_mean")          # 打乱后掉得多 → 重要
    by_name = {r["feature"]: r for r in loo_rows}
    perm_by = {r["feature"]: r for r in perm_rows}

    merged = []
    for name in by_name:
        merged.append({
            "feature": name,
            "loo_delta": by_name[name]["delta_auc"],
            "loo_rank": loo_rank[name],
            "perm_drop": perm_by[name]["drop_mean"],
            "perm_std": perm_by[name]["drop_std"],
            "perm_rank": perm_rank[name],
            "avg_rank": (loo_rank[name] + perm_rank[name]) / 2,
        })
    merged.sort(key=lambda r: r["avg_rank"])

    top = [r for r in merged if r["avg_rank"] <= 5]
    bottom = [r for r in merged if r["avg_rank"] >= 10]
    negative = [r for r in merged if r["loo_delta"] > 0]

    lines = [
        "# Kamei 14 项特征消融与置换重要性（P5）",
        "",
        f"> 生成：{time.strftime('%Y-%m-%d %H:%M:%S')} ｜ 脚本：`data_model/15_feature_ablation.py`",
        f"> 模型：`{model_name}`（超参与 expert 线一致）｜ 种子：{seed}"
        + (f"｜ **冒烟模式 limit={limit}**" if limit else ""),
        f"> 判定阈值：p ≥ {config.DECISION_THRESHOLD} 即判缺陷（契约三）｜ 耗时：{elapsed:.1f}s",
        "",
        "## 1. 基线",
        "",
        f"- 全量 14 项，检验集 **AUC = {base['auc']:.4f}**、F1 = {base['f1']:.4f}",
        f"- 置换重要性的基线 AUC = {base_auc:.4f}（与上面一致才说明两次评估同口径）",
        "",
        "## 2. 两口径交叉排序（按平均名次升序，名次越小越重要）",
        "",
        "| 特征 | 留一法 ΔAUC | 留一法名次 | 置换 ΔAUC（均值±std） | 置换名次 | 平均名次 |",
        "|---|---|---|---|---|---|",
    ]
    for r in merged:
        lines.append(
            f"| `{r['feature']}` | {r['loo_delta']:+.4f} | {r['loo_rank']} | "
            f"{r['perm_drop']:+.4f} ± {r['perm_std']:.4f} | {r['perm_rank']} | {r['avg_rank']:.1f} |"
        )

    lines += ["", "## 3. 结论（按证据写，不做修辞）", ""]
    if top:
        lines.append("- **两口径都靠前（Top-5）**：" + "、".join(f"`{r['feature']}`" for r in top)
                     + " —— 可视为该模型的主要判据。")
    if bottom:
        lines.append("- **两口径都靠后（后 5 位）**：" + "、".join(f"`{r['feature']}`" for r in bottom)
                     + " —— 在当前模型容量下边际贡献小；**不等于**该特征无业务意义（可能与其他列共线）。")
    if negative:
        lines.append("- **负贡献（删除后 AUC 上升）**：" + "、".join(
            f"`{r['feature']}`（{r['loo_delta']:+.4f}）" for r in negative)
                     + " —— 如实登记，可能是噪声列或与其它列强共线；不据此直接删列（契约二的 14 项仍在交付清单内）。")
    if not negative:
        lines.append("- 未观察到「删除后 AUC 上升」的列，14 项在留一法口径下均非负贡献。")

    disagree = [r for r in merged if abs(r["loo_rank"] - r["perm_rank"]) >= 6]
    if disagree:
        lines.append("- **两口径分歧较大**：" + "、".join(
            f"`{r['feature']}`（留一 {r['loo_rank']} / 置换 {r['perm_rank']}）" for r in disagree)
                     + " —— 通常说明该列被其它列替代（训练侧可替代）但推理时模型仍依赖它，需在答辩里说明，不可只报单一口径。")

    lines += [
        "",
        "## 4. 口径与边界",
        "",
        "- **留一法**是训练侧重训，成本高（14 次重训），反映「删掉这列后模型还能不能学到同样的东西」；",
        "- **置换重要性**不动模型，只在检验集打乱该列，反映「模型实际依赖哪一列」，但会被强共线列稀释；",
        "- 两者不一致时**以分歧本身为结论**，不做「取大者」式挑选；",
        "- 消融结论**不改变交付清单**：14 项仍是契约二 v1.2 的交付特征，本报告只回答「哪些真有用」。",
        "",
        "## 5. 复现",
        "",
        "```bash",
        "cd data_model",
        f"python 15_feature_ablation.py --model {model_name} --perm-repeats 5",
        "```",
        "",
    ]
    return "\n".join(lines)


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description="Kamei 14 项特征消融 + 置换重要性")
    p.add_argument("--model", default="xgb")
    p.add_argument("--seed", type=int, default=config.SEED)
    p.add_argument("--limit", type=int, default=0, help="只取前 N 行做冒烟（0=全量）")
    p.add_argument("--perm-repeats", type=int, default=5)
    p.add_argument("--out", type=Path, default=OUT_DEFAULT)
    args = p.parse_args(argv)

    train, test = load_splits(config.TRAIN_CSV, config.TEST_CSV)
    if args.limit:
        train = train.head(args.limit)
        test = test.head(max(args.limit // 4, 100))
    X_tr, y_tr = xy(train)
    X_te, y_te = xy(test)
    features = list(config.FEATURE_FIELDS)
    assert X_tr.shape[1] == len(features), f"特征宽度 {X_tr.shape[1]} != {len(features)}"

    started = time.time()
    print(f"[ablation] train={X_tr.shape} test={X_te.shape} model={args.model}")
    base, loo_rows = leave_one_out(args.model, args.seed, X_tr, y_tr, X_te, y_te, features)
    print(f"[ablation] 留一法完成，基线 AUC={base['auc']:.4f}")

    model = build_model(args.model, args.seed)
    model.fit(X_tr, y_tr)
    base_auc, perm_rows = permutation_importance(model, X_te, y_te, features, args.perm_repeats, args.seed)
    print(f"[ablation] 置换重要性完成（repeats={args.perm_repeats}）")

    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(
        render_report(base, loo_rows, perm_rows, base_auc, args.model, args.seed,
                      time.time() - started, args.limit),
        # 显式写 \n：Windows 上 write_text 默认把 \n 转成 os.linesep（CRLF），
        # 与仓库其余报告写盘端（05/04/expert-predict）一律 LF 不一致
        encoding="utf-8", newline="\n",
    )
    print(f"[ablation] -> {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
