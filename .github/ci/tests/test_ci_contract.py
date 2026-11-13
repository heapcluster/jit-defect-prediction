"""核心回归工作流的最小配置约束。"""

import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
WORKFLOW = (ROOT / ".github/workflows/ci.yml").read_text(encoding="utf-8")


class CIContractTests(unittest.TestCase):
    def test_one_workflow_and_one_required_job(self):
        workflows = sorted((ROOT / ".github/workflows").glob("*.y*ml"))
        self.assertEqual([p.name for p in workflows], ["ci.yml"])
        self.assertIn("name: 应用运行与核心回归\n", WORKFLOW)
        jobs = WORKFLOW.split("\njobs:\n", 1)[1]
        self.assertEqual(re.findall(r"^  ([a-z_]+):$", jobs, re.MULTILINE), ["ci"])
        self.assertIn("    name: CI\n", jobs)

    def test_runtime_checks_follow_changed_paths(self):
        self.assertIn("fetch-depth: 0", WORKFLOW)
        self.assertIn("python3 .github/ci/ci_scope.py", WORKFLOW)
        self.assertIn("- name: Report lightweight PR", WORKFLOW)
        for name, command, scope in (
            ("Test infra", "python -m pytest -q infra/tests", "infra"),
            ("Test backend", "python -m pytest -q", "backend"),
            ("Test frontend", "npm run test:unit", "frontend"),
            ("Test data model", "python -m pytest -q", "model"),
            ("Build frontend", "npm run build", "frontend"),
            ("Build Python", "python -m compileall", "python"),
        ):
            with self.subTest(name=name):
                block = WORKFLOW.split(f"- name: {name}\n", 1)[1].split("- name:", 1)[0]
                self.assertIn(command, block)
                self.assertIn(f"if: steps.scope.outputs.{scope} == 'true'", block)
        for bypass in ("continue-on-error", "|| true", "--if-present", "--passWithNoTests"):
            self.assertNotIn(bypass, WORKFLOW)

    def test_database_and_dependencies_are_real(self):
        self.assertTrue((ROOT / "data_model/environment.yml").is_file())
        self.assertIn("environment-file: data_model/environment.yml", WORKFLOW)
        self.assertTrue((ROOT / "frontend/package-lock.json").is_file())
        self.assertIn("npm ci --ignore-scripts", WORKFLOW)
        self.assertIn("image: mysql:8.0", WORKFLOW)
        self.assertIn("python infra/setup_mysql.py", WORKFLOW)

    def test_pr_and_merge_queue_supported_with_read_only_token(self):
        self.assertIn("  pull_request:\n    branches: [main]", WORKFLOW)
        self.assertIn("  merge_group:\n", WORKFLOW)
        self.assertIn("permissions:\n  contents: read\n", WORKFLOW)
        self.assertIn("persist-credentials: false", WORKFLOW)
        self.assertNotIn("secrets.", WORKFLOW)


if __name__ == "__main__":
    unittest.main()
