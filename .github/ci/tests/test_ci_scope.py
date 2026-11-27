# === AI 辅助说明 ===
# 本文件共 7 条测试用例
# [AI生成]：0 条
# [AI生成-人工修改]：7 条（AI 生成骨架，人工补充核心断言）
# [手写]：0 条
# 使用工具：原始生成记录未归档（标注依据代码特征判断，作者于 2026-11-17 确认）
# 提示词见：docs/README.md

"""Regression tests for the required CI job's path selection."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from ci_scope import select_checks  # noqa: E402


class CIScopeTests(unittest.TestCase):
    def test_docs_are_lightweight(self):
        for paths in (
            ["docs/api/commits.md"],
            ["docs/web_page/evaluate.md"],
            ["openspec/changes/archive/old/.openspec.yaml"],
        ):
            with self.subTest(paths=paths):
                self.assertFalse(any(select_checks(paths).values()))

    def test_ignore_rule_change_checks_infra(self):
        self.assertEqual(
            select_checks(["docs/web_page/evaluate.md", ".gitignore"]),
            {"backend": False, "frontend": False, "model": False, "infra": True},
        )

    def test_frontend_only_avoids_unrelated_backend_suite(self):
        self.assertEqual(
            select_checks(["frontend/src/App.vue", "docs/web_page/risk_list.md"]),
            {"backend": False, "frontend": True, "model": False, "infra": False},
        )

    def test_schema_and_backend_changes_run_backend_suite(self):
        self.assertTrue(select_checks(["infra/schema.sql"])["backend"])
        self.assertTrue(select_checks(["backend/app/main.py"])["backend"])

    def test_ci_change_tests_infra_without_inheriting_broken_backend_baseline(self):
        self.assertEqual(
            select_checks([".github/workflows/ci.yml", ".github/ci/ci_scope.py"]),
            {"backend": False, "frontend": False, "model": False, "infra": True},
        )

    def test_openspec_checker_change_tests_infra_only(self):
        self.assertEqual(
            select_checks(["openspec/check_structure.py", "openspec/specs/ui/spec.md"]),
            {"backend": False, "frontend": False, "model": False, "infra": True},
        )

    def test_dependency_or_unknown_changes_run_all(self):
        for paths in (
            ["data_model/environment.yml"],
            ["new-tool/config.toml"],
            ["docs/scripts/validate.py"],
            [],
        ):
            with self.subTest(paths=paths):
                self.assertTrue(all(select_checks(paths).values()))


if __name__ == "__main__":
    unittest.main()
