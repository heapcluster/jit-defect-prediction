"""Regression tests for documentation references and concurrent OpenSpec deltas."""

import tempfile
import unittest
from pathlib import Path

from infra.check_spec_references import (
    active_change_format,
    broken_links,
    modified_collisions,
    modified_missing_targets,
)


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
            "[local](model/feature-columns.md)\n"
            "[root](docs/model/feature-columns.md)\n",
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

    def test_modified_title_must_match_live_requirement(self):
        self.write(
            "openspec/specs/model-training/spec.md",
            "## Requirements\n### Requirement: Train eight\n",
        )
        source = "openspec/changes/scope/specs/model-training/spec.md"
        self.write(source, "## MODIFIED Requirements\n### Requirement: Train three\n")
        self.assertEqual(len(modified_missing_targets(self.root)), 1)
        self.write(source, "## MODIFIED Requirements\n### Requirement: Train eight\n")
        self.assertEqual(modified_missing_targets(self.root), [])

    def test_active_change_requires_template_header_manifest_and_five_sections(self):
        folder = "openspec/changes/example"
        self.write(f"{folder}/.openspec.yaml", "schema: spec-driven\ncreated: 2026-10-31\n")
        self.write(
            f"{folder}/proposal.md",
            "# Example\n## Why\n## What Changes\n## Capabilities\n## Impact\n",
        )
        self.write(f"{folder}/specs/example/spec.md", "## ADDED Requirements\n")
        task = f"{folder}/tasks.md"
        valid = (
            "# example — 任务清单\n\n"
            "> 提案：proposal.md ｜ 设计决策：无 ｜ 规格：specs/example/spec.md\n"
            "> 负责人：甲 ｜ 创建：2026-10-31 ｜ 状态：进行中\n"
            "> 关联需求：无（工程化）\n"
            "> 统一格式：docs/common/openspec-task-template.md\n\n"
            "## 1. 交付\n- [ ] 1.1 完成实现\n\n## 测试与验证（强制板块）\n"
            "### 1. 单元测试\n### 2. 集成测试\n### 3. 验收测试\n"
            "### 4. 非功能验证\n### 5. 已知缺口与后续计划\n"
        )
        self.write(task, valid)
        self.assertEqual(active_change_format(self.root), [])
        self.write(task, valid.replace("关联需求：", "用户故事："))
        self.assertTrue(any("header" in error for error in active_change_format(self.root)))

    def test_checked_task_cannot_claim_deleted_current_artifact(self):
        folder = "openspec/changes/example"
        self.write(f"{folder}/.openspec.yaml", "schema: spec-driven\ncreated: 2026-10-31\n")
        self.write(f"{folder}/proposal.md", "## Why\n## What Changes\n## Capabilities\n## Impact\n")
        self.write(f"{folder}/specs/example/spec.md", "## ADDED Requirements\n")
        task = f"{folder}/tasks.md"
        self.write(
            task,
            "# example\n\n> 提案：proposal.md ｜ 设计决策：无 ｜ 规格：specs/example/spec.md\n"
            "> 负责人：甲 ｜ 创建：2026-10-31 ｜ 状态：进行中\n"
            "> 关联需求：无（工程化）\n> 统一格式：docs/common/openspec-task-template.md\n"
            "## 1. 交付\n- [x] 1.1 已实现 `docs/missing.md`\n"
            "## 测试与验证（强制板块）\n### 1. 单元测试\n### 2. 集成测试\n"
            "### 3. 验收测试\n### 4. 非功能验证\n### 5. 已知缺口与后续计划\n",
        )
        self.assertTrue(any("checked task cites missing" in error for error in active_change_format(self.root)))


if __name__ == "__main__":
    unittest.main()
