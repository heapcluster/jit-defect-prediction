"""Offline tests for the PR review decision and fail-closed gates."""

from __future__ import annotations

import importlib.util
import io
import json
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest.mock import patch

SCRIPT = Path(__file__).resolve().parents[1] / "pr_auto_review.py"
SPEC = importlib.util.spec_from_file_location("pr_auto_review", SCRIPT)
review = importlib.util.module_from_spec(SPEC)
assert SPEC and SPEC.loader
SPEC.loader.exec_module(review)

SHA = "a" * 40
CONFIG = {"enabled": True, "publish": False, "provider": "none",
          "required_checks": ["CI"], "max_files": 80, "max_patch_bytes": 200000}
FILES = [{"filename": "infra/example.py", "patch": "@@ -1 +1 @@\n-old\n+new",
          "additions": 1, "deletions": 1}]


class ReviewPolicyTest(unittest.TestCase):
    def test_disabled_provider_never_approves(self):
        self.assertEqual(review.choose_action(None, FILES, CONFIG, {"CI": "success"}, SHA)[0], "SKIP")

    def test_approve_requires_successful_ci(self):
        decision = {"head_sha": SHA, "action": "APPROVE", "findings": []}
        self.assertEqual(review.choose_action(decision, FILES, CONFIG, {}, SHA)[0], "SKIP")
        self.assertEqual(review.choose_action(decision, FILES, CONFIG, {"CI": "failure"}, SHA)[0], "SKIP")
        self.assertEqual(review.choose_action(decision, FILES, CONFIG, {"CI": "success"}, SHA)[0], "APPROVE")

    def test_stale_decision_is_not_published(self):
        decision = {"head_sha": "b" * 40, "action": "APPROVE", "findings": []}
        self.assertEqual(review.choose_action(decision, FILES, CONFIG, {"CI": "success"}, SHA)[0], "SKIP")

    def test_request_changes_needs_patch_evidence(self):
        decision = {"head_sha": SHA, "action": "REQUEST_CHANGES", "findings": [
            {"path": "infra/example.py", "reason": "Changed behavior", "evidence": "+new"}]}
        self.assertEqual(review.choose_action(decision, FILES, CONFIG, {}, SHA)[0], "REQUEST_CHANGES")
        decision["findings"][0]["evidence"] = "not in diff"
        self.assertEqual(review.choose_action(decision, FILES, CONFIG, {}, SHA)[0], "SKIP")

    def test_missing_or_truncated_patch_skips(self):
        self.assertFalse(review.inspect_files([{"filename": "binary.png"}], CONFIG)[0])
        truncated = [dict(FILES[0], additions=2)]
        self.assertFalse(review.inspect_files(truncated, CONFIG)[0])

    def test_approval_with_findings_is_invalid(self):
        decision = {"head_sha": SHA, "action": "APPROVE", "findings": [
            {"path": "infra/example.py", "reason": "Bug", "evidence": "+new"}]}
        self.assertEqual(review.choose_action(decision, FILES, CONFIG, {"CI": "success"}, SHA)[0], "SKIP")

    def test_default_config_never_publishes(self):
        config = json.loads(SCRIPT.with_name("pr_review_config.json").read_text(encoding="utf-8"))
        self.assertFalse(config["publish"])
        self.assertEqual(config["provider"], "none")

    def test_event_without_model_decision_only_reads(self):
        with tempfile.TemporaryDirectory() as directory:
            event = Path(directory) / "event.json"
            event.write_text(json.dumps({"number": 7,
                "repository": {"full_name": "heapcluster/jit-defect-prediction"},
                "pull_request": {"number": 7, "head": {"sha": SHA}}}), encoding="utf-8")
            args = type("Args", (), {"config": SCRIPT.with_name("pr_review_config.json"),
                "event": event, "decision_file": None, "publish": False})()
            calls = []
            def fake_api(path, token, method="GET", data=None):
                calls.append(method)
                if path.endswith("/pulls/7"):
                    return {"state": "open", "draft": False, "head": {"sha": SHA}}
                return FILES
            with patch.object(review, "api_request", side_effect=fake_api), \
                 patch.dict(review.os.environ, {"GITHUB_TOKEN": "test-token"}), \
                 redirect_stdout(io.StringIO()) as output:
                self.assertEqual(review.run(args), 0)
            self.assertIn("SKIP: no model decision", output.getvalue())
            self.assertEqual(calls, ["GET", "GET"])


if __name__ == "__main__":
    unittest.main()
