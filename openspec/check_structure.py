"""Check the repository-specific OpenSpec conventions not covered by the CLI.

Run from any directory: python openspec/check_structure.py
This checks references and task bookkeeping, not whether a product feature works.
"""

from __future__ import annotations

import re
import sys
from collections import defaultdict
from pathlib import Path
from urllib.parse import unquote

ROOT = Path(__file__).resolve().parents[1]
OPEN_SPEC = ROOT / "openspec"
CHANGES = OPEN_SPEC / "changes"
PREFIXES = ("docs/", "backend/", "frontend/", "data_model/", "infra/", "openspec/", ".github/")
PROPOSAL_HEADINGS = ("## Why", "## What Changes", "## Capabilities", "## Impact")
TASK_HEADINGS = (
    "> 提案：",
    "> 负责人：",
    "> 关联需求：",
    "> 状态：",
)
VERIFICATION_HEADINGS = (
    "### 1. 单元测试",
    "### 2. 集成测试",
    "### 3. 验收测试",
    "### 4. 非功能验证",
    "### 5. 已知缺口与后续计划",
)
TASK = re.compile(r"^- \[([ xX])\] (\d+)\.(\d+)(?:\.\d+)?\b")
BACKTICK = re.compile(r"`([^`\n]+)`")
LINK = re.compile(r"\[[^\]]+\]\(([^)]+)\)")
REQUIREMENT = re.compile(r"^### Requirement: (.+)$", re.MULTILINE)
DOC_TOKEN = re.compile(r"`(docs/[^`\n]+)`")


def check_headings(text: str, headings: tuple[str, ...], source: Path) -> list[str]:
    positions = [text.find(heading) for heading in headings]
    missing = [heading for heading, pos in zip(headings, positions) if pos < 0]
    errors = [f"{source}: missing {heading}" for heading in missing]
    if not missing and positions != sorted(positions):
        errors.append(f"{source}: headings are out of order")
    return errors


def checked_paths(block: str) -> list[str]:
    """Return concrete repository paths asserted by a checked task."""
    result = []
    for token in BACKTICK.findall(block):
        token = token.split("#", 1)[0].rstrip("/")
        if not token.startswith(PREFIXES):
            continue
        if any(char in token for char in "*<>|{} []"):
            continue
        if ":" in token:
            token = token.split(":", 1)[0]
        if not (ROOT / token).exists():
            result.append(token)
    return sorted(set(result))


def check_change(directory: Path) -> list[str]:
    errors: list[str] = []
    proposal = directory / "proposal.md"
    tasks = directory / "tasks.md"
    if not proposal.is_file() or not tasks.is_file():
        return [f"{directory}: proposal.md and tasks.md are both required"]
    errors.extend(check_headings(proposal.read_text(encoding="utf-8"), PROPOSAL_HEADINGS, proposal))
    text = tasks.read_text(encoding="utf-8")
    lines = text.splitlines()
    header = [line for line in lines[1:] if line.strip()][:4]
    for actual, expected in zip(header, TASK_HEADINGS):
        if not actual.startswith(expected):
            errors.append(f"{tasks}: expected header {expected}")
    errors.extend(check_headings(text, VERIFICATION_HEADINGS, tasks))
    before_validation = text.split("## 测试与验证", 1)[0]
    section_tasks: dict[int, set[int]] = defaultdict(set)
    for line in before_validation.splitlines():
        match = TASK.match(line)
        if match:
            section, number = int(match.group(2)), int(match.group(3))
            if number in section_tasks[section]:
                errors.append(f"{tasks}: duplicate task number {section}.{number}")
            section_tasks[section].add(number)
    for section, numbers in section_tasks.items():
        expected = set(range(1, max(numbers) + 1))
        if numbers != expected:
            errors.append(f"{tasks}: section {section} task numbers have gaps: {sorted(expected - numbers)}")
    for match in re.finditer(r"(?m)^- \[x\] \d+\.\d+[^\n]*(?:\n {4,}[^\n]*)*", before_validation):
        missing = checked_paths(match.group())
        if missing:
            errors.append(f"{tasks}: checked task cites missing path(s): {', '.join(missing)}")
    return errors


def check_links(path: Path) -> list[str]:
    errors = []
    for target in LINK.findall(path.read_text(encoding="utf-8")):
        target = unquote(target.split("#", 1)[0].strip())
        if not target or target.startswith(("http://", "https://", "mailto:", "codex://")):
            continue
        resolved = (path.parent / target).resolve()
        try:
            resolved.relative_to(ROOT)
            in_repo = True
        except ValueError:
            in_repo = False
        if not in_repo or not resolved.exists():
            errors.append(f"{path}: broken link {target}")
    return errors


def check_doc_references(path: Path) -> list[str]:
    """A concrete docs/ path in a live document must resolve in this checkout."""
    errors = []
    for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        for token in DOC_TOKEN.findall(line):
            candidate = token.split("#", 1)[0].split("§", 1)[0].strip().rstrip("/")
            if any(char in candidate for char in "*<>|{} []"):
                continue
            if not (ROOT / candidate).exists():
                errors.append(f"{path}:{number}: missing docs path {token}")
    return errors


def check_collisions(changes: list[Path]) -> list[str]:
    modified: dict[tuple[str, str], list[str]] = defaultdict(list)
    for change in changes:
        for spec in (change / "specs").glob("*/spec.md"):
            text = spec.read_text(encoding="utf-8")
            block = text.split("## MODIFIED Requirements", 1)
            if len(block) < 2:
                continue
            modified_section = block[1].split("\n## ", 1)[0]
            for title in REQUIREMENT.findall(modified_section):
                modified[(spec.parent.name, title)].append(change.name)
    return [
        f"MODIFIED collision {capability}/{title}: {', '.join(names)}"
        for (capability, title), names in modified.items()
        if len(names) > 1
    ]


def check_modified_targets(changes: list[Path]) -> list[str]:
    """A MODIFIED delta must replace an existing requirement with the exact title."""
    errors = []
    for change in changes:
        for delta in (change / "specs").glob("*/spec.md"):
            parts = delta.read_text(encoding="utf-8").split("## MODIFIED Requirements", 1)
            if len(parts) < 2:
                continue
            section = parts[1].split("\n## ", 1)[0]
            titles = REQUIREMENT.findall(section)
            live = OPEN_SPEC / "specs" / delta.parent.name / "spec.md"
            if not live.is_file():
                errors.append(f"{delta}: MODIFIED capability has no live spec: {delta.parent.name}")
                continue
            live_titles = set(REQUIREMENT.findall(live.read_text(encoding="utf-8")))
            for title in titles:
                if title not in live_titles:
                    errors.append(f"{delta}: MODIFIED title not found in live spec: {title}")
    return errors


def main() -> int:
    changes = sorted(path for path in CHANGES.iterdir() if path.is_dir() and path.name != "archive")
    errors = []
    for change in changes:
        errors.extend(check_change(change))
        for path in change.rglob("*.md"):
            errors.extend(check_links(path))
            errors.extend(check_doc_references(path))
    for path in (OPEN_SPEC / "specs").rglob("*.md"):
        errors.extend(check_links(path))
        errors.extend(check_doc_references(path))
    errors.extend(check_collisions(changes))
    errors.extend(check_modified_targets(changes))
    for error in errors:
        print(error)
    if errors:
        print(f"OpenSpec structure: {len(errors)} error(s)", file=sys.stderr)
        return 1
    print(f"OpenSpec structure: {len(changes)} active changes checked; 0 errors")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
