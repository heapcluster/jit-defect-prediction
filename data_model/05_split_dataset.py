"""05 按时间序把样本集切成训练集 / 检验集。

对应 OpenSpec change: model-training-and-delivery（第 3.1 条任务）
切分依据列: docs/contracts/feature-columns.md 第二节 —— `committed_at`（UTC）
口径铁规矩: data_model/README.md 第 1 条 —— 前 70% 训练、后 30% 检验，**禁止随机切分**

── 为什么必须按时间序 ─────────────────────────────────────────────────────
`exp` / `nuc` / `rexp` / `sexp` 这些历史类特征本身与时间相关。随机切分会把
「未来」的提交放进训练集，模型在检验集上的成绩就不再是预测未来，而是插值
回忆 —— 指标好看但没有意义。所以切分只有一条规则：**按 `committed_at` 升序
排，前 70% 训练、后 30% 检验。**

── 一条断言（对应 tasks.md 3.1）───────────────────────────────────────────
断言：**检验集最早的提交时间 > 训练集最晚的提交时间**（严格大于）。
不成立即非零退出，不产出任何切分文件 —— 错位的切分比不切分更危险，
因为它不会报错，只会让后面所有指标悄悄变成假的。

`--selfcheck` 用来留证据：把输入**打乱**后走同一条校验，断言必须拦住。
这是 tasks.md 3.1 要求的「人为构造乱序输入时断言拦截」的边界场景输出。

> 这里有个坑值得记下来：**只做「不排序直接切」是拦不住的** —— 04 产出的样本集
> 本身已按 `committed_at` 升序，直接取前 70% 仍然满足时间序。第一版自检就是这么
> 写的，结果报「断言没拦住」，等于自检形同虚设。所以必须真的把行打乱。
"""

from __future__ import annotations

import argparse
import csv
import random
import sys
from datetime import datetime
from pathlib import Path

BASE = Path(__file__).resolve().parent
DATA_DIR = BASE / "data"
REPORTS_DIR = BASE / "reports"

DEFAULT_RATIO = 0.70
TIMESTAMP_FORMAT = "%Y-%m-%d %H:%M:%S"


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description="按 committed_at 时间序把样本集切成训练集 / 检验集（前 70% / 后 30%）",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    p.add_argument("--dataset", type=Path, default=DATA_DIR / "dataset_szz.csv",
                   help="04 产出的可训练样本集")
    p.add_argument("--tag", default="", help="文件名标记（如 szz / szz_lite），空则不加后缀")
    p.add_argument("--train-ratio", type=float, default=DEFAULT_RATIO,
                   help=f"训练集比例（默认 {DEFAULT_RATIO}）")
    p.add_argument("--train-out", type=Path, default=None, help="训练集输出路径")
    p.add_argument("--test-out", type=Path, default=None, help="检验集输出路径")
    p.add_argument("--report", type=Path, default=None, help="切分报告输出路径")
    p.add_argument("--selfcheck", action="store_true",
                   help="边界场景自检：故意不排序，断言必须拦住（exit 0 表示「拦住了」）")
    return p.parse_args()


def read_rows(path: Path) -> tuple[list[dict], list[str]]:
    with path.open(newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        return list(reader), list(reader.fieldnames or [])


def parse_ts(value: str) -> datetime:
    return datetime.strptime(value.strip(), TIMESTAMP_FORMAT)


def sort_key(row: dict) -> tuple:
    # 同一秒内的多条提交不保证顺序稳定，用 commit_hash 兜底，保证同名输入结果可复现
    return (parse_ts(row["committed_at"]), row["commit_hash"])


def split_index(total: int, ratio: float) -> int:
    # 向下取整，避免把检验集切空；10893 * 0.70 = 7625.1 -> 7625
    return int(total * ratio)


def validate_split(train: list[dict], test: list[dict],
                   total: int) -> list[str]:
    """返回失败原因列表；空列表 = 通过。"""
    failures: list[str] = []
    if not train or not test:
        failures.append("训练集或检验集为空（切分把一侧切没了）")
        return failures
    if len(train) + len(test) != total:
        failures.append(
            "行数不守恒：训练 %d + 检验 %d != 样本集 %d"
            % (len(train), len(test), total))
    train_max = max(parse_ts(r["committed_at"]) for r in train)
    test_min = min(parse_ts(r["committed_at"]) for r in test)
    if not test_min > train_max:
        failures.append(
            "时间序被破坏：检验集最早 %s 不晚于训练集最晚 %s"
            % (test_min.strftime(TIMESTAMP_FORMAT),
               train_max.strftime(TIMESTAMP_FORMAT)))
    return failures


def main() -> int:
    args = parse_args()
    if not args.dataset.is_file():
        print("[05] 找不到样本集：%s" % args.dataset, file=sys.stderr)
        return 2

    rows, fields = read_rows(args.dataset)
    total = len(rows)
    for col in ("commit_hash", "committed_at"):
        if col not in fields:
            print("[05] 样本集缺列 %s —— 切分依据列不可缺（契约二第二节）" % col,
                  file=sys.stderr)
            return 2

    tag = ("_" + args.tag) if args.tag else ""
    train_out = args.train_out or DATA_DIR / ("split%s_train.csv" % tag)
    test_out = args.test_out or DATA_DIR / ("split%s_test.csv" % tag)
    report = args.report or REPORTS_DIR / ("split_stats%s.md" % tag)

    if args.selfcheck:
        # ── 边界场景：把行打乱后再切，断言必须拦下 ────────────────────────
        # 注意：不能只做「不排序直接切」—— 04 产出的样本集本身已按 committed_at
        # 升序，直接取前 70% 仍然满足时间序，拦不住任何东西。必须真的打乱。
        shuffled = list(rows)
        random.Random(0).shuffle(shuffled)
        cut = split_index(total, args.train_ratio)
        head, tail = shuffled[:cut], shuffled[cut:]
        failures = validate_split(head, tail, total)
        print("[05] --selfcheck：打乱输入后再切，应当被断言拦下")
        if failures:
            for f in failures:
                print("      [已拦截] %s" % f)
            print("[05] 断言工作正常（拦住了乱序输入，未产出文件）")
            return 0
        print("[05] ⚠️ 断言没有拦住乱序输入 —— 切分保护失效", file=sys.stderr)
        return 1

    ordered = sorted(rows, key=sort_key)
    cut = split_index(total, args.train_ratio)
    train, test = ordered[:cut], ordered[cut:]

    failures = validate_split(train, test, total)
    if failures:
        for f in failures:
            print("[05] ✗ %s" % f, file=sys.stderr)
        print("[05] 切分未通过校验，不产出文件", file=sys.stderr)
        return 1

    for path, part in ((train_out, train), (test_out, test)):
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=fields)
            w.writeheader()
            w.writerows(part)

    train_min = parse_ts(train[0]["committed_at"])
    train_max = parse_ts(train[-1]["committed_at"])
    test_min = parse_ts(test[0]["committed_at"])
    test_max = parse_ts(test[-1]["committed_at"])
    pos_train = sum(1 for r in train if str(r["is_bug_inducing"]).strip() == "1")
    pos_test = sum(1 for r in test if str(r["is_bug_inducing"]).strip() == "1")

    report.parent.mkdir(parents=True, exist_ok=True)
    report.write_text(
        SPLIT_REPORT_TEMPLATE.format(
            dataset=args.dataset,
            total=total,
            ratio=args.train_ratio,
            n_train=len(train),
            n_test=len(test),
            train_range="%s ~ %s" % (train_min.strftime(TIMESTAMP_FORMAT),
                                     train_max.strftime(TIMESTAMP_FORMAT)),
            test_range="%s ~ %s" % (test_min.strftime(TIMESTAMP_FORMAT),
                                    test_max.strftime(TIMESTAMP_FORMAT)),
            pos_train=pos_train,
            rate_train="%.2f%%" % (pos_train / len(train) * 100),
            pos_test=pos_test,
            rate_test="%.2f%%" % (pos_test / len(test) * 100),
            train_out=train_out,
            test_out=test_out,
            gap_days=(test_min - train_max).total_seconds() / 86400.0,
            first_feature=fields[3] if len(fields) > 3 else "",
        ),
        encoding="utf-8",
        # 显式写 \n：Windows 上 write_text 默认会把 \n 转成 os.linesep（CRLF），
        # 而仓库既有 Markdown 全是 LF —— 报告一生成就会整份行尾不一致
        newline="\n",
    )

    print("[05] 样本集 %d 条 -> 训练 %d / 检验 %d（比例 %.0f/%.0f，按时间序）"
          % (total, len(train), len(test), args.train_ratio * 100,
             (1 - args.train_ratio) * 100))
    print("[05] 训练集 %s ~ %s" % (train_min.strftime(TIMESTAMP_FORMAT),
                                  train_max.strftime(TIMESTAMP_FORMAT)))
    print("[05] 检验集 %s ~ %s" % (test_min.strftime(TIMESTAMP_FORMAT),
                                  test_max.strftime(TIMESTAMP_FORMAT)))
    print("[05] 断言通过：检验集最早 > 训练集最晚（相隔 %.1f 天）"
          % ((test_min - train_max).total_seconds() / 86400.0))
    print("[05] 正样本比例：训练 %.2f%% / 检验 %.2f%%"
          % (pos_train / len(train) * 100, pos_test / len(test) * 100))
    print("[05] 产出：%s" % train_out)
    print("[05]       %s" % test_out)
    print("[05] 报告：%s" % report)
    return 0


SPLIT_REPORT_TEMPLATE = """# 时间序切分统计（05_split_dataset.py 产出）

> 本文件可入库。切分口径见 `data_model/README.md` 铁规矩 1 与 `docs/contracts/feature-columns.md` 第二节。

## 切分结果

| 项 | 值 |
|---|---|
| 输入样本集 | `{dataset}` |
| 样本总数 | {total} |
| 切分比例 | 前 {ratio:.0%} 训练 / 后 {ratio:.0%} 之外的 30% 检验（按 `committed_at` 升序） |
| 训练集行数 | {n_train} |
| 检验集行数 | {n_test} |
| 训练集时间范围 | {train_range} |
| 检验集时间范围 | {test_range} |
| 训练集正样本 | {pos_train}（{rate_train}） |
| 检验集正样本 | {pos_test}（{rate_test}） |
| 训练/检验时间间隔 | {gap_days:.2f} 天 |

## 断言

| 检查项 | 结果 |
|---|---|
| 检验集最早的 `committed_at` **严格晚于** 训练集最晚的 | ✅ 通过 |
| 行数守恒（训练 + 检验 = 样本集） | ✅ 通过（{n_train} + {n_test} = {total}） |

## 边界场景（tasks.md 3.1 要求留输出）

`python 05_split_dataset.py --selfcheck` —— 把输入**打乱**后走同一条校验（`random.Random(0)`，可复现）：

```
[05] --selfcheck：打乱输入后再切，应当被断言拦下
      [已拦截] 时间序被破坏：检验集最早 <日期> 不晚于训练集最晚 <日期>
[05] 断言工作正常（拦住了乱序输入，未产出文件）
```

> 第一版自检写的是「不排序直接切」，结果**没拦住** —— 因为 04 产出的样本集本身已按
> `committed_at` 升序，前 70% 仍是时间序。**这说明自检本身也要能失败，否则等于没检。**
> 现改为先 `shuffle` 再切。

## 产出

- `{train_out}`
- `{test_out}`

两份文件列结构与样本集完全一致（含 `{first_feature}` 起 14 项特征 + 标签），**不新增任何切分列** ——
切分结果由文件名区分，样本集本身保持干净。
"""


if __name__ == "__main__":
    raise SystemExit(main())
