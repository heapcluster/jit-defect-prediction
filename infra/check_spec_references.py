"""Check live Markdown repository paths and concurrent OpenSpec MODIFIED titles.

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


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("check", choices=("links", "deltas"))
    args = parser.parse_args()
    errors = broken_links(ROOT) if args.check == "links" else modified_collisions(ROOT)
    if errors:
        for error in errors:
            print(error)
        print(f"{args.check}: {len(errors)} problem(s)")
        return 1
    print(f"{args.check}: passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
