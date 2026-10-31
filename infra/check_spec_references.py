"""Check live Markdown paths and active OpenSpec change contracts.

Only repository files are checked. Historical change archives, version logs,
quoted migration notes, generated data and model artifacts are outside scope.
In docs/, only actual Markdown links are checked: inline code there often quotes
historical paths or planned artifacts. Live specs also check inline paths.
"""

from __future__ import annotations

import argparse
import re
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REPO_PREFIXES = ("docs/", "openspec/", "infra/", "backend/", "frontend/", "data_model/")
FILE_SUFFIXES = {".md", ".py", ".sql", ".yml", ".yaml", ".json", ".js", ".vue", ".txt"}
INLINE_CODE = re.compile(r"`([^`\n]+)`")
MARKDOWN_LINK = re.compile(r"!?\[[^\]]*\]\(([^)]+)\)")
REQUIREMENT = re.compile(r"^### Requirement:\s*(.+?)\s*$")
MODIFIED = "## MODIFIED Requirements"
TASK_NUMBER = re.compile(r"^\s*[-*]\s*\[[ xX]\]\s*(\d+)\.(\d+)\b")
VERIFY_TITLES = (
    "单元测试",
    "集成测试",
    "验收测试",
    "非功能验证",
    "已知缺口",
)


def live_markdown_files(root: Path) -> list[Path]:
    docs = (root / "docs").rglob("*.md")
    specs = (root / "openspec" / "specs").rglob("*.md")
    return sorted((*docs, *specs))


def _is_historical_line(line: str, in_history: bool) -> bool:
    return (
        in_history
        or line.lstrip().startswith(">")
        or bool(re.match(r"^\|\s*20\d\d-\d\d-\d\d\s*\|", line))
    )


def _candidate_path(raw: str, source: Path, root: Path, *, inline: bool) -> Path | None:
    value = raw.strip().strip("<>").split("#", 1)[0]
    if not value or any(marker in value for marker in ("*", "{", "}", "<", ">", "$")):
        return None
    if "://" in value or value.startswith(("#", "mailto:", "/")):
        return None
    if inline:
        if " " in value or not value.startswith(REPO_PREFIXES):
            return None
        if Path(value).suffix.lower() not in FILE_SUFFIXES:
            return None
        target = root / value
    else:
        # Standard Markdown links are relative to their source. The project
        # also uses root-prefixed links such as docs/model/feature-columns.md.
        target = source.parent / value
        if not target.exists() and value.startswith(REPO_PREFIXES):
            target = root / value
    resolved = target.resolve()
    try:
        resolved.relative_to(root.resolve())
    except ValueError:
        return None
    return resolved


def broken_links(root: Path) -> list[str]:
    errors: list[str] = []
    for source in live_markdown_files(root):
        in_history = False
        for number, line in enumerate(source.read_text(encoding="utf-8").splitlines(), 1):
            if line.startswith("## "):
                in_history = bool(
                    re.search(r"变更日志|历史|Changelog|History", line, re.IGNORECASE)
                )
            if _is_historical_line(line, in_history):
                continue
            candidates = [(match.group(1), False) for match in MARKDOWN_LINK.finditer(line)]
            if root / "openspec" / "specs" in source.parents:
                candidates += [(match.group(1), True) for match in INLINE_CODE.finditer(line)]
            for raw, inline in candidates:
                target = _candidate_path(raw, source, root, inline=inline)
                if target is not None and not target.exists():
                    errors.append(f"{source.relative_to(root)}:{number}: {raw} -> missing")
    return errors


def modified_collisions(root: Path) -> list[str]:
    by_key: dict[tuple[str, str], list[str]] = defaultdict(list)
    changes = root / "openspec" / "changes"
    for change in sorted(changes.iterdir()):
        if not change.is_dir() or change.name == "archive":
            continue
        for source in sorted((change / "specs").glob("*/spec.md")):
            modified = False
            for number, line in enumerate(source.read_text(encoding="utf-8").splitlines(), 1):
                if line.startswith("## "):
                    modified = line.strip() == MODIFIED
                if modified and (match := REQUIREMENT.match(line)):
                    title = " ".join(match.group(1).split())
                    by_key[(source.parent.name, title.casefold())].append(
                        f"{source.relative_to(root)}:{number}"
                    )
    return [
        f"{capability} / {title}: {'; '.join(locations)}"
        for (capability, title), locations in sorted(by_key.items())
        if len(locations) > 1
    ]


def modified_missing_targets(root: Path) -> list[str]:
    """A MODIFIED Requirement must identify an existing live title exactly."""
    live_root = root / "openspec" / "specs"
    titles: dict[str, set[str]] = {}
    for source in live_root.glob("*/spec.md"):
        titles[source.parent.name] = {
            " ".join(match.group(1).split()).casefold()
            for line in source.read_text(encoding="utf-8").splitlines()
            if (match := REQUIREMENT.match(line))
        }
    errors: list[str] = []
    changes = root / "openspec" / "changes"
    for change in sorted(changes.iterdir()):
        if not change.is_dir() or change.name == "archive":
            continue
        for source in sorted((change / "specs").glob("*/spec.md")):
            modified = False
            for number, line in enumerate(source.read_text(encoding="utf-8").splitlines(), 1):
                if line.startswith("## "):
                    modified = line.strip() == MODIFIED
                if modified and (match := REQUIREMENT.match(line)):
                    title = " ".join(match.group(1).split()).casefold()
                    if title not in titles.get(source.parent.name, set()):
                        errors.append(
                            f"{source.relative_to(root)}:{number}: "
                            f"MODIFIED title has no live target: {match.group(1)}"
                        )
    return errors


def active_change_format(root: Path) -> list[str]:
    """Validate the shared header, manifest, task numbering and five evidence sections."""
    errors: list[str] = []
    changes = root / "openspec" / "changes"
    for change in sorted(changes.iterdir()):
        if not change.is_dir() or change.name == "archive":
            continue
        manifest = change / ".openspec.yaml"
        task = change / "tasks.md"
        proposal = change / "proposal.md"
        if not manifest.is_file() or not task.is_file() or not proposal.is_file():
            for path in (manifest, task, proposal):
                if not path.is_file():
                    errors.append(f"{path.relative_to(root)}: missing")
            continue

        manifest_text = manifest.read_text(encoding="utf-8")
        if not re.search(r"^schema: spec-driven$", manifest_text, re.M):
            errors.append(f"{manifest.relative_to(root)}: schema must be spec-driven")
        if not re.search(r"^created: \d{4}-\d{2}-\d{2}$", manifest_text, re.M):
            errors.append(f"{manifest.relative_to(root)}: missing created date")
        has_delta = any((change / "specs").glob("*/spec.md"))
        if not has_delta and not re.search(r"^skip_specs: true$", manifest_text, re.M):
            errors.append(f"{manifest.relative_to(root)}: no delta requires skip_specs")

        proposal_text = proposal.read_text(encoding="utf-8")
        for heading in ("Why", "What Changes", "Capabilities", "Impact"):
            if not re.search(r"^## " + re.escape(heading) + r"\b", proposal_text, re.M):
                errors.append(f"{proposal.relative_to(root)}: missing {heading}")

        lines = task.read_text(encoding="utf-8").splitlines()
        header = lines[2:6]
        if len(header) != 4 or not all(line.startswith("> ") for line in header) or not (
            "提案：" in header[0]
            and "设计决策：" in header[0]
            and "规格：" in header[0]
            and "负责人：" in header[1]
            and "创建：" in header[1]
            and "状态：" in header[1]
            and header[2].startswith("> 关联需求：")
            and "统一格式" in header[3]
        ):
            errors.append(f"{task.relative_to(root)}: four-line header differs from template")
        if not re.search(r"^## 测试与验证", "\n".join(lines), re.M):
            errors.append(f"{task.relative_to(root)}: missing verification section")
            task_body = lines
        else:
            split = next(i for i, line in enumerate(lines) if line.startswith("## 测试与验证"))
            task_body = lines[:split]
            verification = "\n".join(lines[split:])
            for number, title in enumerate(VERIFY_TITLES, 1):
                if not re.search(rf"^### {number}\. {title}", verification, re.M):
                    errors.append(f"{task.relative_to(root)}: missing verification {number} {title}")
        numbers = [(int(m.group(1)), int(m.group(2))) for line in task_body if (m := TASK_NUMBER.match(line))]
        if not numbers:
            errors.append(f"{task.relative_to(root)}: no numbered tasks")
        else:
            stages = sorted(set(stage for stage, _ in numbers))
            if stages != list(range(1, max(stages) + 1)):
                errors.append(f"{task.relative_to(root)}: stage numbers must start at 1 and be continuous")
            for stage in stages:
                items = [item for current, item in numbers if current == stage]
                if items != list(range(1, len(items) + 1)):
                    errors.append(f"{task.relative_to(root)}: task numbers in stage {stage} are not continuous")
        for number, line in enumerate(task_body, 1):
            if not re.match(r"^\s*[-*] \[[xX]\] ", line):
                continue
            # An immutable link to the pre-migration file is historical proof,
            # never proof that the artifact still exists in the current tree.
            current = re.sub(r"\[历史版 `[^`]+`\]\([^)]+\)", "", line)
            for match in INLINE_CODE.finditer(current):
                raw = match.group(1).strip().rstrip("/")
                if (
                    raw.startswith(REPO_PREFIXES + (".github/",))
                    and not any(char in raw for char in ("*", "{", "}", "<", ">", " "))
                    and not (root / raw).exists()
                ):
                    errors.append(
                        f"{task.relative_to(root)}:{number}: checked task cites missing current path: {raw}"
                    )
    return errors


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("check", choices=("links", "deltas", "format"))
    args = parser.parse_args()
    if args.check == "links":
        errors = broken_links(ROOT)
    elif args.check == "deltas":
        errors = modified_collisions(ROOT) + modified_missing_targets(ROOT)
    else:
        errors = active_change_format(ROOT)
    if errors:
        for error in errors:
            print(error)
        print(f"{args.check}: {len(errors)} problem(s)")
        return 1
    print(f"{args.check}: passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
