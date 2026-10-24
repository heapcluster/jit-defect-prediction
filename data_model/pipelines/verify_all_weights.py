"""权重交付校验与 md5 清单（离线，**不进后端运行时**）。

背景
----
`#98` 的表述是「补齐 `sys.path` 后 8/8 全过（本地已验证）」。2026-10-24 交叉核对
发现同一个 `tabnet_v1.pkl` 存在两份**不同导出上下文**：

- 工作目录那份（300,437 B）：类路径 `pipelines.expert.model.TabNetWithEarlyStop`
- `data/expert_models_20261021.zip` 内那份（300,421 B）：`__main__.TabNetWithEarlyStop`

两份都能跑训练，但只有前者能被干净进程加载。根因不是导出脚本写错，而是
`data_model/pipelines/*/models/**` 被 `.gitignore` 排除、权重只靠 zip 人工传递，
且**没有 md5 清单** —— 于是「本地已验证」在别人机器上必然复现不到。
复现不到的验证结论等于虚证，和「性能只写已实现」是同一类问题。

本脚本的定位（三件事，都离线）
------------------------------
1. 把「8 个权重全部可用」变成**可核验**的结论：逐个加载、记录类模块路径、md5、
   文件大小与特征宽度；任一权重加载失败或类路径不可导入 → 退出码 1。
2. 生成 / 校验 `models/manifest.txt`（纯文本，`.gitignore` 已白名单，可入库）：
   `--write-manifest` 生成，`--check` 与清单逐项比对，漂移即退出码 2。
3. 守住交付边界：**不写库、不进后端进程、不动 `feature_order.txt`**。在线模型集
   仍是 `[models]` 段声明的 3 个（`specs/model-coverage` R6），8 个权重只是
   「评估可用」，不等于「在线可切换」。

用法
----
    cd data_model
    python -m pipelines.verify_all_weights                  # 全量校验（默认 expert 线）
    python -m pipelines.verify_all_weights --write-manifest # 生成 models/manifest.txt
    python -m pipelines.verify_all_weights --check          # 验收/CI：清单不匹配即失败
    python -m pipelines.verify_all_weights --line semantic  # 其他线（宽度自动取 768）
    python -m pipelines.verify_all_weights --no-load        # 无依赖环境只算 md5

退出码：0 全部通过 / 1 有加载或类路径问题 / 2 参数错误或清单不一致
"""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import sys
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path

# 各线的权重目录与期望特征宽度（e2e 是端到端微调，不吃表格特征 → 0 = 不校验）
LINES: dict[str, tuple[str, int]] = {
    "expert": ("pipelines/expert/models", 14),
    "semantic": ("pipelines/semantic/models", 768),
    "fused": ("pipelines/fused/models", 782),
    "e2e": ("pipelines/e2e/models", 0),
}

# 只有 `__main__` 是真问题：类定义在训练脚本里，干净进程 import 不到它。
NOT_IMPORTABLE = {"__main__"}

MANIFEST_NAME = "manifest.txt"
HEADER_PREFIX = "#"


@dataclass
class WeightRecord:
    file: str
    md5: str
    size: int
    module: str
    n_features: int | None
    loaded: bool
    error: str = ""
    # Pipeline 内层估计器的类路径 —— tabnet 的 `__main__` 就藏在这一层，
    # 只看 `type(obj).__module__` 会被 `sklearn.pipeline.Pipeline` 挡住。
    inner: list[str] = field(default_factory=list)


def md5_of(path: Path, chunk: int = 8 << 20) -> str:
    """分块算 md5 —— 权重单个最大 546MB，一次性读入会白占内存。"""
    h = hashlib.md5()
    with path.open("rb") as fh:
        for block in iter(lambda: fh.read(chunk), b""):
            h.update(block)
    return h.hexdigest()


def is_importable_module(name: str) -> bool:
    """类路径能否被干净进程加载。`__main__` 一律判为不可导入。"""
    if not name or name in NOT_IMPORTABLE:
        return False
    try:
        return importlib.util.find_spec(name) is not None
    except (ImportError, AttributeError, ValueError):
        return False


def load_weight(path: Path):
    """joblib 优先、pickle 兜底（lr/rf 是 joblib，xgb 是标准 pickle）。"""
    first = ""
    try:
        import joblib

        return joblib.load(path), ""
    except Exception as exc:  # noqa: BLE001 —— 加载失败要原样回显，不能吞
        first = f"joblib: {type(exc).__name__}: {exc}"
    try:
        import pickle

        with path.open("rb") as fh:
            return pickle.load(fh), ""
    except Exception as exc:  # noqa: BLE001
        return None, f"{first}; pickle: {type(exc).__name__}: {exc}"


def nested_modules(obj) -> list[str]:
    """`Pipeline` 里真正干活的估计器类路径；非 Pipeline 返回空。

    为什么必须看内层：`tabnet_v1.pkl` 的顶层对象是 `sklearn.pipeline.Pipeline`，
    只看顶层永远看不到 `__main__.TabNetWithEarlyStop` —— 而失败恰恰发生在内层。
    """
    steps = getattr(obj, "steps", None)
    if not steps:
        return []
    return [f"{type(est).__module__}.{type(est).__qualname__}" for _, est in steps]


def scan(models_dir: Path, with_load: bool = True) -> list[WeightRecord]:
    """逐个权重算 md5；`with_load` 时再回读并记录类模块路径。"""
    records: list[WeightRecord] = []
    for path in sorted(models_dir.glob("*.pkl")):
        rec = WeightRecord(
            file=path.name,
            md5=md5_of(path),
            size=path.stat().st_size,
            module="",
            n_features=None,
            loaded=False,
        )
        if with_load:
            obj, err = load_weight(path)
            if err:
                rec.error = err
            else:
                rec.loaded = True
                rec.module = f"{type(obj).__module__}.{type(obj).__qualname__}"
                rec.inner = nested_modules(obj)
                rec.n_features = getattr(obj, "n_features_in_", None)
        records.append(rec)
    return records


def verdict(records: list[WeightRecord], expect_width: int) -> list[str]:
    """返回问题清单（空 = 全过）。分开报「加载失败」与「类路径不可导入」两类。"""
    problems: list[str] = []
    for rec in records:
        if not rec.loaded and rec.error:
            problems.append(f"{rec.file}: 加载失败 —— {rec.error}")
            continue
        if not rec.module:
            continue
        for dotted in [rec.module, *rec.inner]:
            top = dotted.split(".")[0]
            if top in NOT_IMPORTABLE:
                problems.append(f"{rec.file}: 类路径落在 `__main__`（{dotted}），干净进程无法加载")
            elif not is_importable_module(top):
                problems.append(f"{rec.file}: 顶层模块 `{top}` 不可导入（{dotted}）")
        if expect_width and rec.n_features not in (None, expect_width):
            problems.append(
                f"{rec.file}: 特征宽度 {rec.n_features} != 期望 {expect_width}（错序/错版静默错答）"
            )
    return problems


def env_versions() -> list[str]:
    """复现结论必须连同环境一起登记 —— 只写「已验证」不写版本等于没验。"""
    import platform

    versions = [f"python {platform.python_version()}"]
    for mod in ("sklearn", "xgboost", "lightgbm", "torch"):
        try:
            versions.append(f"{mod} {__import__(mod).__version__}")
        except Exception:  # noqa: BLE001 —— 缺依赖不该阻断清单生成
            versions.append(f"{mod} -")
    return versions


def render_manifest(records: list[WeightRecord], line: str, generated_at: str) -> str:
    """清单格式固定 5 列，`--check` 按这 5 列逐项比对。"""
    versions = env_versions()
    lines = [
        f"{HEADER_PREFIX} 权重清单（自动生成，勿手改）—— `python -m pipelines.verify_all_weights --write-manifest`",
        f"{HEADER_PREFIX} 线：{line} ｜ 生成时间：{generated_at} ｜ 环境：{' / '.join(versions)}",
        f"{HEADER_PREFIX} 口径：交付与验收以 **md5 匹配的那份**为准；md5 不同即另一版导出，须先核对类路径与指标再入库。",
        f"{HEADER_PREFIX} 在线加载清单不在此表：仍由 feature_order.txt 的 [models] 段声明（R6）。",
        f"{HEADER_PREFIX} 列：md5  size_bytes  module  n_features  file",
    ]
    for rec in records:
        width = "" if rec.n_features is None else str(rec.n_features)
        lines.append(f"{rec.md5}  {rec.size}  {rec.module or '-'}  {width or '-'}  {rec.file}")
    return "\n".join(lines) + "\n"


def render_report(records: list[WeightRecord], line: str, generated_at: str,
                  problems: list[str], expect_width: int) -> str:
    """验收用的 markdown 证据：md5 + 顶层/内层类路径 + 判定。"""
    total = len(records)
    ok = total - len({p.split(":")[0] for p in problems})
    lines = [
        f"# 权重交付校验证据（{line} 线）",
        "",
        f"> 生成：{generated_at} ｜ 脚本：`python -m pipelines.verify_all_weights --report`（离线，不进后端运行时）",
        f"> 环境：{' / '.join(env_versions())}",
        f"> 结论：**{ok}/{total} 可加载**"
        + (f"；{len(problems)} 项问题" if problems else "；无问题")
        + f" ｜ 期望特征宽度 {expect_width or '不校验'}",
        "",
        "## 口径",
        "",
        "- 本表只证明「**评估可用**」：8 个权重都能被干净进程回读、指标可复算。",
        "- **不等于在线可切换**：在线加载清单仍由 `feature_order.txt` 的 `[models]` 段声明（`specs/model-coverage` R6），本脚本不改交付边界。",
        "- 交付与验收**以 md5 匹配的那份为准**；md5 不同即另一版导出，须先核对类路径与指标。",
        "",
        "## 逐权重",
        "",
        "| 文件 | md5 | 大小 | 顶层类 | 内层估计器 | 特征宽度 | 加载 |",
        "|---|---|---|---|---|---|---|",
    ]
    for rec in records:
        size_mb = f"{rec.size / (1 << 20):.1f}MB"
        inner = "<br>".join(f"`{x}`" for x in rec.inner) or "—"
        lines.append(
            f"| `{rec.file}` | `{rec.md5}` | {size_mb} | `{rec.module or '—'}` | {inner} "
            f"| {rec.n_features if rec.n_features is not None else '—'} "
            f"| {'✅' if rec.loaded else '❌ ' + rec.error} |"
        )
    if problems:
        lines += ["", "## 问题", ""] + [f"- {p}" for p in problems]
    lines += ["", "## 复现命令", "", "```bash", "cd data_model",
              "python -m pipelines.verify_all_weights --check", "```", ""]
    return "\n".join(lines)


def parse_manifest(text: str) -> list[tuple[str, str, str, str, str]]:
    rows = []
    for raw in text.splitlines():
        line = raw.strip()
        if not line or line.startswith(HEADER_PREFIX):
            continue
        parts = line.split()
        if len(parts) != 5:
            raise ValueError(f"清单行列数不对（应 5 列）：{line}")
        rows.append((parts[0], parts[1], parts[2], parts[3], parts[4]))
    return rows


def _rows(records: list[WeightRecord]) -> list[tuple[str, str, str, str, str]]:
    out = []
    for rec in records:
        width = "" if rec.n_features is None else str(rec.n_features)
        out.append((rec.md5, str(rec.size), rec.module or "-", width or "-", rec.file))
    return out


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="权重交付校验与 md5 清单（离线）")
    parser.add_argument("--line", default="expert", choices=sorted(LINES))
    parser.add_argument("--models-dir", type=Path, default=None,
                        help="覆盖默认权重目录（相对 data_model 或绝对路径）")
    parser.add_argument("--expect-width", type=int, default=None,
                        help="期望特征宽度；默认按线取（expert 14 / semantic 768 / fused 782 / e2e 0）")
    parser.add_argument("--write-manifest", action="store_true", help="生成 models/manifest.txt")
    parser.add_argument("--check", action="store_true", help="与 models/manifest.txt 比对，漂移即失败")
    parser.add_argument("--no-load", action="store_true", help="只算 md5，不回读权重（无依赖环境用）")
    parser.add_argument("--json", action="store_true", help="以 JSON 输出，便于流水线消费")
    parser.add_argument("--report", type=Path, default=None,
                        help="另存一份 markdown 证据（含内层估计器类路径），供验收归档")
    args = parser.parse_args(argv)

    default_dir, default_width = LINES[args.line]
    models_dir = args.models_dir or (Path(__file__).resolve().parents[1] / default_dir)
    expect_width = default_width if args.expect_width is None else args.expect_width

    if not models_dir.is_dir():
        print(f"[verify] 权重目录不存在：{models_dir}", file=sys.stderr)
        return 2

    started = time.time()
    records = scan(models_dir, with_load=not args.no_load)
    if not records:
        print(f"[verify] 目录里没有 *.pkl：{models_dir}", file=sys.stderr)
        return 2

    if args.json:
        print(json.dumps([asdict(r) for r in records], ensure_ascii=False, indent=2))
    else:
        print(f"[verify] 线={args.line} 目录={models_dir} 共 {len(records)} 个权重")
        print(f"{'file':<22}{'md5':<34}{'size':>12}  module")
        for rec in records:
            size_mb = rec.size / (1 << 20)
            print(f"{rec.file:<22}{rec.md5:<34}{size_mb:>9.1f}MB  {rec.module or '-':<44}"
                  f"{'' if rec.loaded or args.no_load else '  [LOAD FAILED]'}")
            for dotted in rec.inner:
                print(f"{'':<22}{'':<34}{'':>12}    └ {dotted}")

    problems = [] if args.no_load else verdict(records, expect_width)
    generated_at = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())

    manifest_path = models_dir / MANIFEST_NAME
    if args.write_manifest:
        manifest_path.write_text(render_manifest(records, args.line, generated_at), encoding="utf-8")
        print(f"[verify] 已写清单：{manifest_path}")

    if args.report:
        args.report.parent.mkdir(parents=True, exist_ok=True)
        args.report.write_text(
            render_report(records, args.line, generated_at, problems, expect_width), encoding="utf-8"
        )
        print(f"[verify] 已写证据：{args.report}")

    if args.check:
        if not manifest_path.is_file():
            print(f"[verify] 找不到清单：{manifest_path}（先跑 --write-manifest）", file=sys.stderr)
            return 2
        expected = parse_manifest(manifest_path.read_text(encoding="utf-8"))
        actual = _rows(records)
        if expected != actual:
            exp_map = {r[4]: r for r in expected}
            act_map = {r[4]: r for r in actual}
            for name in sorted(set(exp_map) | set(act_map)):
                if exp_map.get(name) != act_map.get(name):
                    print(f"[verify] 清单漂移 {name}: 清单={exp_map.get(name)} 实况={act_map.get(name)}",
                          file=sys.stderr)
            print("[verify] 清单与实况不一致 —— 权重被替换或重新导出过，须核对后重新生成", file=sys.stderr)
            return 2
        print(f"[verify] 清单一致（{len(actual)} 项）")

    if args.no_load:
        print("[verify] --no-load：已跳过回读与类路径校验")
        return 0

    if problems:
        for item in problems:
            print(f"[verify] {item}", file=sys.stderr)
        print(f"[verify] 未通过：{len(problems)} 项（{time.time() - started:.1f}s）", file=sys.stderr)
        return 1

    widths = {r.n_features for r in records if r.n_features is not None}
    print(f"[verify] 全部通过：{len(records)}/{len(records)} 可加载"
          f"{'，特征宽度 ' + str(sorted(widths)) if widths else ''}（{time.time() - started:.1f}s）")
    print("[verify] 注意：本结论只覆盖「评估可用」，在线加载清单仍由 feature_order.txt "
          "的 [models] 段决定（R6），本脚本不改交付边界。")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
