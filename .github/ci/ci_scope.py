"""Select the smallest useful PR check set from changed repository paths.

The required CI job always runs. Documentation-only changes finish after this
selection step; push and manual runs still exercise the complete suite.
"""

from __future__ import annotations

import subprocess
import sys
from collections.abc import Iterable
from pathlib import PurePosixPath

DOC_SUFFIXES = {".md", ".mdx", ".pdf", ".png", ".jpg", ".jpeg", ".gif", ".svg", ".webp", ".txt"}


def is_documentation(path: str) -> bool:
    suffix = PurePosixPath(path).suffix.lower()
    return suffix in {".md", ".mdx"} or (path.startswith("docs/") and suffix in DOC_SUFFIXES)


def select_checks(paths: Iterable[str]) -> dict[str, bool]:
    changed = list(paths)
    checks = {"backend": False, "frontend": False, "model": False, "infra": False}
    if not changed:
        return dict.fromkeys(checks, True)

    for path in changed:
        if is_documentation(path):
            continue
        if path.startswith("openspec/changes/") and path.endswith("/.openspec.yaml"):
            # Change-local OpenSpec metadata follows the document review path.
            continue
        if path == ".gitignore":
            checks["infra"] = True
            continue
        if path in {".github/workflows/ci.yml", ".github/ci/ci_scope.py"} or path.startswith(
            ".github/ci/"
        ):
            checks["infra"] = True
        elif path.startswith("frontend/"):
            checks["frontend"] = True
        elif path.startswith("backend/"):
            checks["backend"] = True
        elif path == "data_model/environment.yml":
            return dict.fromkeys(checks, True)
        elif path.startswith("data_model/"):
            checks["model"] = True
        elif path == "openspec/check_structure.py" or path.startswith("infra/"):
            checks["infra"] = True
            if path in {"infra/schema.sql", "infra/setup_mysql.py"}:
                checks["backend"] = True
        else:
            # A new path is never silently treated as documentation.
            return dict.fromkeys(checks, True)
    return checks


def changed_paths(base_sha: str) -> list[str]:
    if not base_sha:
        return []
    result = subprocess.run(
        ["git", "diff", "--name-only", "-z", base_sha, "HEAD"],
        check=True,
        capture_output=True,
    )
    return [path.decode("utf-8", "surrogateescape") for path in result.stdout.split(b"\0") if path]


def main() -> None:
    checks = select_checks(changed_paths(sys.argv[1] if len(sys.argv) > 1 else ""))
    for name, enabled in checks.items():
        print(f"{name}={str(enabled).lower()}")
    print(f"python={str(any(checks[name] for name in ('backend', 'model', 'infra'))).lower()}")
    print(f"lightweight={str(not any(checks.values())).lower()}")


if __name__ == "__main__":
    main()
