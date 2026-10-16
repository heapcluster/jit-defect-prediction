"""CI 的静态防回退约束；不是 GitHub 执行或业务测试的替代品。"""

import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
WORKFLOW = (ROOT / ".github/workflows/ci.yml").read_text(encoding="utf-8")


class CIContractTests(unittest.TestCase):
    def test_single_required_job_has_no_job_condition(self):
        jobs = WORKFLOW.split("\njobs:\n", 1)[1]
        self.assertEqual(re.findall(r"^  ([a-z_]+):$", jobs, re.MULTILINE), ["ci"])
        job_header = jobs.split("    steps:\n", 1)[0]
        self.assertIn("    name: CI\n", job_header)
        self.assertNotRegex(job_header, r"(?m)^    if:")

    def test_stages_run_in_order(self):
        stages = ["Lint frontend", "Lint Python", "Lint specifications",
                  "Test CI contract", "Test backend", "Test frontend",
                  "Test data model", "Build frontend", "Build Python"]
        positions = [WORKFLOW.index("- name: " + stage + "\n") for stage in stages]
        self.assertEqual(positions, sorted(positions))

    def test_failures_are_not_ignored(self):
        for bypass in ("continue-on-error", "|| true", "--if-present", "--passWithNoTests"):
            with self.subTest(bypass=bypass):
                self.assertNotIn(bypass, WORKFLOW)
        # 必跑后端套件不得被加上条件，也不能只选择容易通过的用例。
        backend = WORKFLOW.split("- name: Test backend\n", 1)[1].split("- name:", 1)[0]
        self.assertNotIn("if:", backend)
        self.assertIn("run: python -m pytest -q\n", backend)

    def test_pr_and_merge_queue_are_supported(self):
        self.assertIn("  pull_request:\n    branches: [main]\n", WORKFLOW)
        self.assertIn("  merge_group:\n", WORKFLOW)
        self.assertNotIn("pull_request_target", WORKFLOW)
        self.assertNotRegex(WORKFLOW, r"(?m)^\s+paths(?:-ignore)?:")

    def test_token_is_read_only_and_not_persisted(self):
        self.assertIn("permissions:\n  contents: read\n", WORKFLOW)
        self.assertIn("persist-credentials: false", WORKFLOW)
        self.assertNotIn("secrets.", WORKFLOW)

    def test_actions_are_immutable(self):
        actions = re.findall(r"uses: (\S+)", WORKFLOW)
        self.assertEqual(len(actions), 3)
        for action in actions:
            self.assertRegex(action, r"^actions/[a-z-]+@[a-f0-9]{40}$")

    def test_missing_future_tests_are_not_misrepresented(self):
        for step in ("Test frontend", "Test data model"):
            block = WORKFLOW.split("- name: " + step + "\n", 1)[1].split("- name:", 1)[0]
            self.assertIn("if: hashFiles(", block)
        self.assertIn("run: npm run test:unit\n", WORKFLOW)

    def test_install_uses_repository_manifests(self):
        self.assertIn("npm ci --ignore-scripts", WORKFLOW)
        self.assertIn("-r backend/requirements.txt -r data_model/requirements.txt", WORKFLOW)


if __name__ == "__main__":
    unittest.main()
