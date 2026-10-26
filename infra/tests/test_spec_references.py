"""Regression tests for documentation references and concurrent OpenSpec deltas."""

import tempfile
import unittest
from pathlib import Path

from infra.check_spec_references import broken_links, modified_collisions


class SpecReferenceTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)

    def write(self, relative, content):
        path = self.root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
        return path

    def test_live_specs_check_inline_paths_but_skip_historical_quotes(self):
        self.write("docs/model/feature-columns.md", "# columns\n")
        self.write(
            "openspec/specs/feature-extraction/spec.md",
            "Use `docs/model/feature-columns.md`.\n"
            "Broken `docs/model/missing.md`.\n"
            "> Historical `docs/old.md`.\n",
        )
        self.assertEqual(len(broken_links(self.root)), 1)
        self.assertIn("docs/model/missing.md", broken_links(self.root)[0])

    def test_docs_check_actual_links_not_historical_inline_examples(self):
        self.write("docs/guide.md", "[current](missing.md)\n`docs/old.md`\n")
        self.assertEqual(len(broken_links(self.root)), 1)
        self.assertIn("missing.md", broken_links(self.root)[0])

    def test_docs_support_source_relative_and_repo_prefixed_links(self):
        self.write("docs/model/feature-columns.md", "# columns\n")
        self.write(
            "docs/guide.md",
            "[local](model/feature-columns.md)\n[root](docs/model/feature-columns.md)\n",
        )
        self.assertEqual(broken_links(self.root), [])

    def test_modified_collision_is_per_capability_and_ignores_archive(self):
        content = "## MODIFIED Requirements\n\n### Requirement: Same title\n"
        self.write("openspec/changes/one/specs/query-api/spec.md", content)
        self.write("openspec/changes/two/specs/query-api/spec.md", content)
        self.write("openspec/changes/three/specs/db-schema/spec.md", content)
        self.write("openspec/changes/archive/old/specs/query-api/spec.md", content)
        self.write(
            "openspec/changes/four/specs/query-api/spec.md",
            "## ADDED Requirements\n\n### Requirement: Same title\n",
        )
        collisions = modified_collisions(self.root)
        self.assertEqual(len(collisions), 1)
        self.assertIn("query-api / same title", collisions[0])
        self.assertIn("one/specs", collisions[0].replace("\\", "/"))
        self.assertIn("two/specs", collisions[0].replace("\\", "/"))


if __name__ == "__main__":
    unittest.main()
