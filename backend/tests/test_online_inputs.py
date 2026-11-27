# === AI 辅助说明 ===
# 本文件共 2 条测试用例
# [AI生成]：0 条
# [AI生成-人工修改]：2 条（AI 生成骨架，人工补充核心断言）
# [手写]：0 条
# 使用工具：原始生成记录未归档（标注依据代码特征判断，作者于 2026-11-17 确认）
# 提示词见：docs/README.md

import numpy as np
from app import config, semantic_source
from app.services import text_inputs
from git import Repo


def _repo_with_two_commits(tmp_path):
    repo = Repo.init(tmp_path)
    with repo.config_writer() as writer:
        writer.set_value("user", "name", "tester")
        writer.set_value("user", "email", "tester@example.com")
    (tmp_path / "a.txt").write_text("one\n", encoding="utf-8")
    repo.index.add(["a.txt"])
    repo.index.commit("first")
    (tmp_path / "a.txt").write_text("two\n", encoding="utf-8")
    repo.index.add(["a.txt"])
    second = repo.index.commit("second")
    return repo, second.hexsha


def test_commit_text_reuses_pipeline_text_source(tmp_path, monkeypatch):
    repo, second = _repo_with_two_commits(tmp_path)
    monkeypatch.setattr(config, "SOURCE_REPO", tmp_path)
    monkeypatch.setattr(text_inputs, "_cache", {})

    text = text_inputs.commit_text(second)
    assert text.startswith("diff --git a/a.txt b/a.txt")
    assert "two" in text
    assert text_inputs.commit_text("f" * 40) is None


def test_semantic_embedding_falls_back_to_online_encoding(monkeypatch):
    monkeypatch.setattr(semantic_source, "_table", lambda: None)
    monkeypatch.setattr(semantic_source, "_incremental", {})
    calls = {"text": 0, "encode": 0}

    def fake_text(commit_hash):
        calls["text"] += 1
        return "diff --git a/a b/a\n+changed"

    def fake_encode(text):
        calls["encode"] += 1
        return np.ones(semantic_source.DIM, dtype=np.float32)

    monkeypatch.setattr(text_inputs, "commit_text", fake_text)
    monkeypatch.setattr(semantic_source, "_encode_text", fake_encode)

    first = semantic_source.embedding_for("ABC123")
    second = semantic_source.embedding_for("abc123")
    assert first is not None and first.shape == (semantic_source.DIM,)
    assert np.array_equal(first, second)
    assert calls == {"text": 1, "encode": 1}
