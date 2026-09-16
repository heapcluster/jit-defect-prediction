"""04 汇总样本集并报出七项统计。

对应 OpenSpec change: data-collection-and-szz-labeling（第 4 组任务）
字段口径: docs/contracts/data-fields.md 表一/表二/表四；特征列见 docs/contracts/feature-columns.md
七项统计的定义与验收标准: docs/data-pipeline.md 第 6 节

── 这一步只做「对齐」，不造新数 ──────────────────────────────────────────
输入三份文件，按 `commit_hash` 对齐：
  ① 01 的提交清单  —— 谁存在
  ② 02 的标签表    —— 谁是正样本（一行 = 一条已判定的提交；被 D5 排除的不在里面）
  ③ 03 的特征表    —— 每条提交的 14 项特征

**样本集的行数 = 标签表的行数。** 因为 D5 规定「回溯未命中的修复提交既不入样本也不记 0」，
可以判定的提交集合完全由标签表决定；特征表比它大是正常的（多了被排除的那些）。

── 两条断言（对应 tasks.md 4.2）─────────────────────────────────────────
A. 不存在「有标签却不在提交清单里」的行 —— 出现了说明三份产物的仓库版本不一致
B. 不存在「有标签却没有特征」的行     —— 出现了说明 03 的窗口与 02 的窗口不一致
任一不成立即失败退出，不产出样本集：错位的样本集比没有样本集更危险。

── 切分不在这里（tasks.md 4.5）──────────────────────────────────────────
样本集**不含任何切分列**，也不产出切分文件。按 `committed_at` 前 70%/后 30% 的时间序
切分属下游 change；写在这一步会让「同一份样本集」这个基准随切分口径变化而漂移。
"""

from __future__ import annotations

import argparse
import csv
import importlib.util
import re
import sys
from pathlib import Path

BASE = Path(__file__).resolve().parent
DATA_DIR = BASE / "data"
REPORTS_DIR = BASE / "reports"
SZZ_SCRIPT = BASE / "02_szz_labeling.py"

FEATURE_FIELDS = [
    "ns", "nd", "nf", "entropy",
    "la", "ld", "lt",
    "fix",
    "ndev", "age", "nuc",
    "exp", "rexp", "sexp",
]

COMMIT_FIELDS = ["repo_name", "commit_hash", "author_name", "author_email", "committed_at", "message", "parent_hash"]
LABEL_FIELDS = ["commit_hash", "is_bug_inducing", "label_method", "bug_fix_hash", "labeled_at"]

DATASET_FIELDS = ["commit_hash", "committed_at", "feature_version", *FEATURE_FIELDS,
                  "is_bug_inducing", "label_method", "bug_fix_hash"]

# 样本集里绝不允许出现的列名：出现即说明切分被提前做进了样本集
FORBIDDEN_FIELDS = {"split", "is_train", "is_test", "train", "test", "fold", "partition", "set"}

# docs/data-pipeline.md 第 6 节：正样本比例落在该区间就要先查打标逻辑
ABNORMAL_LOW, ABNORMAL_HIGH = 0.40, 0.60


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description="汇总提交清单 + 标签 + 特征，产出可训练样本集并报出七项统计",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    p.add_argument("--commits", type=Path, default=DATA_DIR / "commits.csv", help="01 产出的提交清单")
    p.add_argument("--features", type=Path, default=DATA_DIR / "commit_features.csv", help="03 产出的特征表")
    p.add_argument(
        "--labels",
        type=Path,
        action="append",
        required=True,
        help="02 产出的标签表，可传多次（两套打标方法各一份，各产出一个样本集）",
    )
    p.add_argument("--out-dir", type=Path, default=DATA_DIR, help=f"样本集输出目录（默认 {DATA_DIR}）")
    p.add_argument("--tag", default="", help="输出文件名后缀（例：--tag window2023）")
    p.add_argument(
        "--review-sample",
        type=int,
        default=0,
        metavar="N",
        help="额外产出「修缺陷提交识别」的抽样复核名单，A/B 两组各 N 条（task 3.7 用，0=不产出）",
    )
    return p.parse_args()


def load_is_fix_commit():
    """复用 02 的判据实现（文件名以数字开头，无法用 import 语句导入，故按路径加载）。"""
    spec = importlib.util.spec_from_file_location("szz_labeling", SZZ_SCRIPT)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"无法加载判据模块：{SZZ_SCRIPT}")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod.is_fix_commit


def read_csv(path: Path, what: str) -> list[dict[str, str]]:
    if not path.exists():
        raise FileNotFoundError(f"找不到{what}：{path}")
    with path.open(encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def check_fields(actual: list[str], expected: list[str], what: str) -> list[str]:
    """逐字比对列名，返回差异描述（空列表 = 完全一致）。

    tasks.md 2.4 的同一条纪律：列名对不上，链路就断在中间，且断得无声无息。
    """
    problems = []
    missing = [c for c in expected if c not in actual]
    extra = [c for c in actual if c not in expected]
    if missing:
        problems.append(f"缺列：{missing}")
    if extra:
        problems.append(f"多列（疑似自造列名）：{extra}")
    return problems


def write_review_sample(path: Path, commits: dict[str, dict], n: int, is_fix_commit) -> int:
    """产出「修缺陷提交识别」的抽样复核名单（tasks.md 3.7）。

    两组分开抽，因为两类错误要用不同的样本才能发现：
      A 组 = 被判为修缺陷提交的   → 查**误判**（把新功能/文档当成了修复）
      B 组 = 未判为修缺陷提交、但含缺陷编号的 → 查**漏判**（是真修复却没写修复关键词）

    抽样用**固定步长**而不是随机数：同一份输入每次产出同一份名单，别人才能复算
    「我复核的是哪 30 条」。用随机数就得连种子一起登记，反而更麻烦。
    """
    if n <= 0:
        return 0
    ordered = sorted(commits.values(), key=lambda r: (r["committed_at"], r["commit_hash"]))
    flagged = [r for r in ordered if is_fix_commit(r["message"])]
    unflagged = [
        r for r in ordered
        if not is_fix_commit(r["message"]) and re.search(r"AMQ-\d+", r["message"], re.IGNORECASE)
    ]

    def sample(rows: list[dict], k: int) -> list[dict]:
        if len(rows) <= k:
            return rows
        step = len(rows) / k
        return [rows[int(i * step)] for i in range(k)]

    def short(s: str) -> str:
        s = s.replace("\n", " ").replace("|", "\\|").strip()
        return s[:110] + ("…" if len(s) > 110 else "")

    L: list[str] = []
    L.append("# 修缺陷提交识别抽样复核（tasks.md 3.7）\n")
    L.append("> 判据 D4 = 含缺陷编号 `AMQ-<数字>` **且** 含修复语义 `fix`/`bug`/`patch`，见 `docs/data-pipeline.md` 第 7 节\n")
    L.append(f"> 抽样方式：按 `committed_at` 排序后**固定步长**各取 {n} 条。用步长而非随机数，是为了同一份输入每次产出同一份名单，便于他人复算。\n")
    L.append("| 输入 | 值 |\n|---|---|")
    L.append(f"| 提交清单 | {len(commits)} 条 |")
    L.append(f"| 判为修缺陷提交 | {len(flagged)} 条 |")
    L.append(f"| 未判为修缺陷提交但含缺陷编号 | {len(unflagged)} 条 |")

    a = sample(flagged, n)
    L.append("\n## A. 被判为「修缺陷提交」的抽样 —— 查**误判**\n")
    L.append("| # | commit | 提交时间 | 提交信息（截断） | 是修复吗？ | 备注 |\n|---|---|---|---|---|---|")
    for i, r in enumerate(a, 1):
        L.append(f"| {i} | `{r['commit_hash'][:12]}` | {r['committed_at'][:10]} | {short(r['message'])} |  |  |")

    b = sample(unflagged, n)
    L.append("\n## B. 未被判为「修缺陷提交」但含缺陷编号的抽样 —— 查**漏判**\n")
    L.append("| # | commit | 提交时间 | 提交信息（截断） | 其实是修复吗？ | 备注 |\n|---|---|---|---|---|---|")
    for i, r in enumerate(b, 1):
        L.append(f"| {i} | `{r['commit_hash'][:12]}` | {r['committed_at'][:10]} | {short(r['message'])} |  |  |")

    L.append("\n## 复核结论（由复核人填写）\n")
    L.append("| 项 | 值 |\n|---|---|")
    L.append(f"| A 组抽样条数 | {len(a)} |")
    L.append("| A 组误判条数（判为修复、实为非修复） | 待填 |")
    L.append("| **误判率** | 待填 |")
    L.append(f"| B 组抽样条数 | {len(b)} |")
    L.append("| B 组漏判条数（未判、实为修复） | 待填 |")
    L.append("| **漏判率** | 待填 |")
    L.append("\n> 结论栏为「待填」时，本表只是一份**待办名单**，不能当作 3.7 已完成的证据。判据的漏判率由设计决策 D4 明确承认（会漏掉没写修复关键词的修复提交），这一栏就是量化它的地方。")

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(L) + "\n", encoding="utf-8")
    return len(a) + len(b)


def build_one(
    label_path: Path,
    commits: dict[str, dict],
    features: dict[str, dict],
    out_dir: Path,
    tag: str,
) -> dict:
    """按一份标签表产出一个样本集，并返回该次运行的统计。"""
    label_rows = read_csv(label_path, "标签表")
    if not label_rows:
        raise RuntimeError(f"标签表为空：{label_path}")

    problems = check_fields(list(label_rows[0].keys()), LABEL_FIELDS, "标签表")
    if problems:
        raise RuntimeError(f"标签表列名与契约不符：{problems}")

    method = label_rows[0]["label_method"]
    methods = {r["label_method"] for r in label_rows}
    if len(methods) > 1:
        raise RuntimeError(f"同一份标签表里混了多个 label_method：{sorted(methods)}；契约要求一表一方法")

    # ── 断言 A：有标签却不在提交清单里 ──
    orphan_label = [r["commit_hash"] for r in label_rows if r["commit_hash"] not in commits]
    if orphan_label:
        raise RuntimeError(
            f"[断言 A 失败] {len(orphan_label)} 条提交有标签却不在提交清单里，"
            f"如 {orphan_label[0]} —— 三份产物的仓库版本或过滤口径不一致"
        )

    # ── 断言 B：有标签却没有特征 ──
    missing_feature = [r["commit_hash"] for r in label_rows if r["commit_hash"] not in features]
    if missing_feature:
        raise RuntimeError(
            f"[断言 B 失败] {len(missing_feature)} 条提交有标签却没有特征，"
            f"如 {missing_feature[0]} —— 03 的 --since 窗口比 02 的样本窄"
        )

    rows: list[dict] = []
    for r in label_rows:
        h = r["commit_hash"]
        f = features[h]
        rows.append(
            {
                "commit_hash": h,
                "committed_at": commits[h]["committed_at"],
                "feature_version": f["feature_version"],
                **{c: f[c] for c in FEATURE_FIELDS},
                "is_bug_inducing": int(r["is_bug_inducing"]),
                "label_method": method,
                "bug_fix_hash": r["bug_fix_hash"],
            }
        )
    rows.sort(key=lambda r: (r["committed_at"], r["commit_hash"]))

    versions = {r["feature_version"] for r in rows}
    if len(versions) > 1:
        raise RuntimeError(f"样本集里混了多个 feature_version：{sorted(versions)}；口径不统一不能当一份样本集")

    # tasks.md 4.5：样本集不得含切分列
    leaked = FORBIDDEN_FIELDS & {c.lower() for c in rows[0].keys()}
    if leaked:
        raise RuntimeError(f"样本集里出现了切分列 {sorted(leaked)}；切分属下游 change，不能提前做进来")

    out_dir.mkdir(parents=True, exist_ok=True)
    stem = f"dataset_{tag}_{method}" if tag else f"dataset_{method}"
    out_path = out_dir / f"{stem}.csv"
    with out_path.open("w", encoding="utf-8", newline="") as fp:
        w = csv.DictWriter(fp, fieldnames=DATASET_FIELDS, quoting=csv.QUOTE_ALL)
        w.writeheader()
        w.writerows(rows)

    pos = sum(1 for r in rows if r["is_bug_inducing"] == 1)
    neg = len(rows) - pos
    return {
        "method": method,
        "path": out_path,
        "rows": rows,
        "pos": pos,
        "neg": neg,
        "ratio": pos / len(rows) if rows else 0.0,
        "labeled_commits": len({r["commit_hash"] for r in label_rows}),
    }


def write_report(path: Path, ctx: dict, results: list[dict], labels: list[Path]) -> None:
    L: list[str] = []
    L.append("# 样本集统计（04_build_dataset.py 产出）—— 第 6 项交付物的证据\n")
    L.append("> 本文件可入库，七项统计的定义与验收标准见 `docs/data-pipeline.md` 第 6 节\n")

    commits = ctx["commits"]
    times = sorted(r["committed_at"] for r in commits.values())
    L.append("## 七项统计\n")
    L.append("| 指标 | 值 | 说明 |\n|---|---|---|")
    L.append(f"| 总提交数 | {len(commits)} | 过滤合并提交之后的数 |")
    L.append(f"| 时间跨度 | {times[0]} ~ {times[-1]} | 最早 ~ 最晚提交时间（UTC） |")
    for r in results:
        L.append(
            f"| 打标成功数（`{r['method']}`） | {r['pos'] + r['neg']} | 能判定标签的提交数；"
            f"被 D5 排除的修复提交不计入 |"
        )
        L.append(f"| **正样本数**（`{r['method']}`） | {r['pos']} | `is_bug_inducing = 1` |")
        L.append(f"| 负样本数（`{r['method']}`） | {r['neg']} | `is_bug_inducing = 0` |")
        L.append(f"| **正样本比例**（`{r['method']}`） | **{r['ratio']:.2%}** | 正样本数 ÷ 打标成功数 |")
    L.append(f"| 打标方法 | {'、'.join('`' + r['method'] + '`' for r in results)} | 见 `contracts/data-fields.md` 表二 |")

    L.append("\n## 正样本比例是否落在合理区间\n")
    L.append(f"判定依据：`docs/data-pipeline.md` 第 6 节 —— 落在 {ABNORMAL_LOW:.0%}–{ABNORMAL_HIGH:.0%} 就先查打标逻辑。\n")
    for r in results:
        if ABNORMAL_LOW <= r["ratio"] <= ABNORMAL_HIGH:
            L.append(f"- ❌ `{r['method']}`：**{r['ratio']:.2%} 落在异常区间**，不要进下游，先复核判据")
        else:
            L.append(f"- ✅ `{r['method']}`：{r['ratio']:.2%} 不在异常区间（JIT 经验区间为个位数到十几百分点）")

    L.append("\n## 对齐与断言\n")
    L.append("| 检查项 | 结果 |\n|---|---|")
    L.append(f"| 断言 A：无「有标签却不在提交清单里」的行 | ✅ 通过（0 条） |")
    L.append(f"| 断言 B：无「有标签却没有特征」的行 | ✅ 通过（0 条） |")
    L.append(f"| 样本集不含切分列 | ✅ 通过 |")
    L.append(f"| 特征表行数（03 产出，含被 D5 排除的提交） | {ctx['n_features']} |")
    for r in results:
        excluded = ctx["n_commits"] - (r["pos"] + r["neg"])
        L.append(
            f"| `{r['method']}`：提交清单中未进样本的条数 | {excluded}（含回溯未命中被 D5 排除的、以及窗口内未被任何修复提交指控的） |"
        )

    L.append("\n## 产出\n")
    for r in results:
        L.append(f"- `{r['path']}` —— {r['pos'] + r['neg']} 行 × {len(DATASET_FIELDS)} 列（14 项特征 + 标签），`label_method = {r['method']}`")
    L.append("\n## 说明\n")
    L.append("- 样本集**不含任何切分列，也不产出切分文件**：按 `committed_at` 前 70%/后 30% 的时间序切分属下游 change（`AGENTS.md` 禁止随机切分）")
    L.append("- 标签来源：`docs/data-pipeline.md` 第 7 节判据 D4（缺陷编号 且 修复语义双命中）+ 决策 D5（回溯未命中者不入样本、不记 0）")
    L.append("- 特征口径：`docs/contracts/feature-columns.md` 第四节（归一化 + 自然对数变换），版本号见样本集 `feature_version` 列")
    L.append(f"- 输入文件：" + "；".join(f"`{p.name}`" for p in labels))

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(L) + "\n", encoding="utf-8")


def main() -> int:
    args = parse_args()

    commit_rows = read_csv(args.commits, "提交清单")
    feature_rows = read_csv(args.features, "特征表")
    if not commit_rows or not feature_rows:
        print("[失败] 提交清单或特征表为空，样本集会空手而归", file=sys.stderr)
        return 2

    problems = check_fields(list(commit_rows[0].keys()), COMMIT_FIELDS, "提交清单")
    if problems:
        print(f"[失败] 提交清单列名与契约表一不符：{problems}", file=sys.stderr)
        return 3
    problems = check_fields(list(feature_rows[0].keys()), ["commit_hash", "committed_at", "feature_version", *FEATURE_FIELDS], "特征表")
    if problems:
        print(f"[失败] 特征表列名与契约不符：{problems}", file=sys.stderr)
        return 3

    commits = {r["commit_hash"]: r for r in commit_rows}
    features = {r["commit_hash"]: r for r in feature_rows}
    ctx = {"commits": commits, "n_commits": len(commit_rows), "n_features": len(feature_rows)}

    try:
        results = [build_one(p, commits, features, args.out_dir, args.tag) for p in args.labels]
    except RuntimeError as e:
        print(f"[失败] {e}", file=sys.stderr)
        return 4

    report = REPORTS_DIR / "dataset_stats.md"
    write_report(report, ctx, results, args.labels)

    print(f"[完成] 提交清单 {len(commit_rows)} 条 / 特征表 {len(feature_rows)} 条")
    for r in results:
        print(
            f"       {r['method']}：样本 {r['pos'] + r['neg']} 条，"
            f"正 {r['pos']} / 负 {r['neg']}，正样本比例 {r['ratio']:.2%}"
        )
        print(f"       样本集：{r['path']}")
    print(f"       七项统计：{report}")

    if args.review_sample:
        review = REPORTS_DIR / "labeling_review_sample.md"
        try:
            cnt = write_review_sample(review, commits, args.review_sample, load_is_fix_commit())
        except RuntimeError as e:
            print(f"       抽样复核名单：跳过（{e}）")
        else:
            print(f"       抽样复核名单：{review}（A/B 两组共 {cnt} 条，复核结论需人工填写）")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
