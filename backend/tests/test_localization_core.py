"""AI-generated DB-free localization tests; not human-reviewed."""

import importlib
import importlib.util
import json
import subprocess

import pytest
from app.errors import AppError


def test_localization_core_exists():
    assert importlib.util.find_spec("app.localization_core") is not None, (
        "W9 requires the standalone localization core"
    )


@pytest.fixture
def core():
    return importlib.import_module("app.localization_core")


def git(repo, *args):
    return (
        subprocess.check_output(["git", "-C", str(repo), *args], stderr=subprocess.PIPE)
        .decode("utf-8")
        .strip()
    )


@pytest.fixture
def repository(tmp_path):
    repo = tmp_path / "checkout"
    repo.mkdir()
    git(repo, "init", "-q")
    src = repo / "src"
    src.mkdir()
    (src / "代码 space.java").write_text("class Example {\nint value = 1;\n}\n")
    (repo / "guide.md").write_text("original guide\n")
    (repo / "binary.bin").write_bytes(b"abc\x00def")
    (repo / "invalid.bin").write_bytes(b"\xff\xfe")
    (repo / "oversized.txt").write_text("x" * 4096)
    (repo / "empty.txt").write_text("")
    (repo / "link.java").symlink_to("src/代码 space.java")

    def commit(message, empty=False):
        git(repo, "add", "--all")
        args = ["-c", "user.name=Fixture", "-c", "user.email=fixture@example.test", "commit", "-q"]
        if empty:
            args.append("--allow-empty")
        git(repo, *args, "-m", message)
        return git(repo, "rev-parse", "HEAD")

    first = commit("fix CAMEL-123 boundary")
    (src / "代码 space.java").write_text(
        "class Example {\nif (value == null) return;\nint value = 2;\n}\n"
    )
    (repo / "guide.md").write_text("updated guide\nreview behavior\n")
    changed = commit("change behavior")
    empty = commit("empty followup", empty=True)
    (src / "代码 space.java").write_text("DIRTY WORKTREE IS NOT SOURCE\n")
    return repo, first, changed, empty


def reader(core, repository, **kwargs):
    return core.SourceReader(
        str(repository[0]), allow_roots=[str(repository[0].parent)], protocol_whitelist=[], **kwargs
    )


def prediction(commit_hash, **kwargs):
    return {
        "commit_hash": commit_hash,
        "model_name": "model-A",
        "model_version": "v1",
        "feature_version": "features-v1",
        "risk_score": 0.6,
        **kwargs,
    }


def test_immutable_source_tree_unicode_search_and_statuses(core, repository):
    repo, first, changed, _ = repository
    before = (
        git(repo, "status", "--porcelain"),
        git(repo, "rev-parse", "HEAD"),
        git(repo, "rev-list", "--count", "HEAD"),
    )
    with reader(core, repository, file_size_max=1024) as source:
        assert source.resolve(first.upper()) == first
        root = source.tree(first)
        assert any(e["path"] == "src" and e["type"] == "tree" for e in root["entries"])
        tree = source.tree(first, "src")
        assert tree["entries"][0]["path"] == "src/代码 space.java"
        assert (
            source.tree(first, search="代码 space")["entries"][0]["path"] == "src/代码 space.java"
        )
        old = source.file(first, "src/代码 space.java")
        assert old["content"] == "class Example {\nint value = 1;\n}\n"
        assert old["total_lines"] == 3 and old["encoding"] == "utf-8"
        assert (
            source.file(changed, "src/代码 space.java", 2, 2)["content"]
            == "if (value == null) return;\n"
        )
        for path, status in [
            ("binary.bin", "binary"),
            ("invalid.bin", "binary"),
            ("oversized.txt", "too_large"),
            ("absent", "not_found"),
            ("link.java", "not_found"),
            ("src", "not_found"),
        ]:
            payload = source.file(first, path)
            assert payload["status"] == status and payload["content"] is None
            assert payload["reason"]
        assert source.file(first, "empty.txt")["content"] == ""
        assert source.file(first, "empty.txt")["total_lines"] == 0
    assert before == (
        git(repo, "status", "--porcelain"),
        git(repo, "rev-parse", "HEAD"),
        git(repo, "rev-list", "--count", "HEAD"),
    )


@pytest.mark.parametrize("path", ["../x", "/tmp/x", "a/../x", "a\\b", "a\x00b", "a\nb"])
def test_path_boundary(core, repository, path):
    with reader(core, repository) as source, pytest.raises(AppError):
        source.file(repository[1], path)


@pytest.mark.parametrize("value", ["HEAD", "a" * 39, "z" * 40, "--help", None])
def test_hash_boundary(core, repository, value):
    with reader(core, repository) as source, pytest.raises(AppError):
        source.resolve(value)


def test_missing_commit_and_tree_path_errors(core, repository):
    with reader(core, repository) as source:
        with pytest.raises(AppError) as missing:
            source.resolve("0" * 40)
        assert missing.value.code == 40400
        with pytest.raises(AppError):
            source.tree(repository[1], "guide.md")
        with pytest.raises(AppError):
            source.tree(repository[1], "missing")
        for start, end in [(0, None), (True, None), (2, 1), (1, False), (9, None)]:
            with pytest.raises(AppError):
                source.file(repository[1], "guide.md", start, end)


def test_rejects_repository_and_remote_boundaries(core, repository, tmp_path):
    for source in [
        "relative",
        "https://user:secret@example.org/repo",
        "https://127.0.0.1/repo",
        "ext::something",
        str(tmp_path.parent / "not-allowed"),
    ]:
        with pytest.raises(AppError):
            with core.SourceReader(
                source, allow_roots=[str(tmp_path)], protocol_whitelist=["https"]
            ):
                pass
    gitdir = repository[0] / ".git"
    (gitdir / "shallow").write_text(repository[1] + "\n")
    with pytest.raises(AppError):
        with reader(core, repository):
            pass


def test_partial_config_merges_without_mutating_defaults(core):
    config = core.validate_config(
        {"weights": {"file_types": {"source": 0}, "hunk": 0}, "top_n": {"files": 1}}
    )
    assert config["weights"]["file_types"]["source"] == 0
    assert (
        config["weights"]["file_types"]["document"]
        == core.DEFAULT_WEIGHTS["file_types"]["document"]
    )
    assert config["top_n"] == {"files": 1, "lines": 30}
    config["weights"]["mix"]["base"] = 88
    assert core.DEFAULT_WEIGHTS["mix"]["base"] == 0.45


@pytest.mark.parametrize(
    "raw",
    [
        None,
        [],
        {"unknown": 1},
        {"weights": {"new": 1}},
        {"weights": {"mix": {"extra": 1}}},
        {"weights": {"hunk": -1}},
        {"weights": {"hunk": float("nan")}},
        {"weights": {"hunk": float("inf")}},
        {"weights": {"hunk": True}},
        {"top_n": {"lines": 0}},
        {"top_n": {"files": True}},
        {"file_size_max": 17 * 1024**2},
        {"file_size_max": 0},
        {"format": "json"},
        {"suggestion_sources": []},
        {"suggestion_sources": ["template", "template"]},
        {"suggestion_sources": ["network"]},
        {"patch_preview": 1},
        {"commit_hash": "HEAD"},
        {"model_name": ""},
    ],
)
def test_invalid_config(core, raw):
    with pytest.raises(AppError):
        core.validate_config(raw)


def test_real_localization_evidence_weights_topn_and_no_patch(core, repository):
    pred = prediction(repository[2])
    with reader(core, repository) as source:
        result = core.localize(
            source, [pred], {"top_n": {"files": 1, "lines": 1}, "patch_preview": True}
        )
        assert len(result["rows"]) == 1
        row = result["rows"][0]
        assert row["file_path"] == "src/代码 space.java" and row["line_number"] == 2
        assert row["rank"] == 1 and row["level"] == "line"
        data = json.loads(row["evidence_json"])
        assert data["prediction"]["risk_score"] == 0.6
        assert data["line"]["content"] == "if (value == null) return;"
        assert "missing_explanation" in data["insufficiencies"]
        assert data["context"] and data["signal_weights"]
        assert result["summary"]["truncated"]
        assert result["summary"]["patch_reason"] == "no_reliable_patch"
        assert "patch" not in result
        assert result["evidence"][repository[2]]["diff"] == source.diff(repository[2])
        assert result["summary"]["insufficient_count"] == 1
        changed = core.localize(
            source,
            [pred],
            {
                "top_n": {"files": 1, "lines": 1},
                "weights": {"file_types": {"source": 0, "document": 100}},
            },
        )
        assert changed["rows"][0]["file_path"] == "guide.md"
        zero = core.localize(
            source, [pred], {"weights": {"mix": {"base": 0, "file": 0, "hunk": 0}}}
        )
        assert all(row["suspicion"] == 0 for row in zero["rows"])
        content_zero = core.localize(
            source, [pred], {"weights": {"line_content": {"suspicious": 0}}}
        )
        assert (
            next(
                row
                for row in content_zero["rows"]
                if row["line_number"] == 2 and row["file_path"].endswith("java")
            )["suspicion"]
            == 0
        )


def test_empty_commit_preserves_prediction_risk_and_multiple_models(core, repository):
    preds = [
        prediction(repository[2]),
        prediction(repository[3]),
        prediction(repository[2], model_name="model-B", risk_score=0.2),
    ]
    with reader(core, repository) as source:
        result = core.localize(source, preds, {})
    commit_rows = [row for row in result["rows"] if row["level"] == "commit"]
    assert len(commit_rows) == 1
    assert commit_rows[0]["suspicion"] == 0.6
    assert commit_rows[0]["file_path"] is None and commit_rows[0]["line_number"] is None
    assert "no_added_text_lines" in json.loads(commit_rows[0]["evidence_json"])["insufficiencies"]
    assert {
        json.loads(row["evidence_json"])["prediction"]["model_name"] for row in result["rows"]
    } == {"model-A", "model-B"}
    assert len(result["evidence"][repository[2]]["predictions"]) == 2


def test_git_lf_positions_preserve_unicode_separators(core, repository):
    repo = repository[0]
    path = 'src/代码 space.java'
    (repo/path).write_text('class Example {\nString text = "a\u2028b";\nif (value == null) throw new RuntimeException();\n}\n', encoding='utf-8')
    git(repo, 'add', path)
    git(repo, '-c', 'user.name=Fixture', '-c', 'user.email=fixture@example.test', 'commit', '-qm', 'LF positions')
    commit = git(repo, 'rev-parse', 'HEAD')
    with reader(core, repository) as source:
        file = source.file(commit, path)
        assert file['total_lines'] == 4
        result = core.localize(source, [prediction(commit)], {})
        line = next(row for row in result['rows'] if row['line_number'] == 3)
        assert json.loads(line['evidence_json'])['line']['content'] == 'if (value == null) throw new RuntimeException();'


def test_w8_canonical_explanation_columns_and_default_patch(core, repository):
    pred = prediction(repository[2])
    with reader(core, repository) as source:
        result = core.localize(source, [pred], {}, explanations=[{**pred, 'technique': 'shap', 'feature': 'la',
            'raw_value': 2.0, 'contribution': .3, 'direction': 'increase', 'rank': 1, 'label': '新增代码', 'reason_code': None}])
        data = json.loads(result['rows'][0]['evidence_json'])
        assert data['explanation']['contributions'][0]['feature'] == 'la'
        assert result['summary']['patch_reason'] == 'no_reliable_patch'
        reason = core.localize(source, [pred], {}, explanations=[{**pred, 'reason_code': 'unsupported_model_family'}])
        assert 'missing_explanation' in json.loads(reason['rows'][0]['evidence_json'])['insufficiencies']


@pytest.mark.parametrize('changed_lines', [(2001,), (2001, 3999)])
def test_paged_candidate_cache_excludes_trailing_lf(core, repository, changed_lines):
    repo, path = repository[0], 'src/代码 space.java'
    lines = [f'int value{i} = {i};' for i in range(1, max(changed_lines) + 1)]
    (repo / path).write_text('\n'.join(lines) + '\n')
    git(repo, 'add', path)
    git(repo, '-c', 'user.name=Fixture', '-c', 'user.email=fixture@example.test', 'commit', '-qm', 'AI-generated paging baseline')
    for number in changed_lines:
        lines[number - 1] = f'if (value{number} == null) throw new RuntimeException();'
    (repo / path).write_text('\n'.join(lines) + '\n')
    git(repo, 'add', path)
    git(repo, '-c', 'user.name=Fixture', '-c', 'user.email=fixture@example.test', 'commit', '-qm', 'AI-generated page boundary changes')
    commit = git(repo, 'rev-parse', 'HEAD')
    with reader(core, repository) as source:
        result = core.localize(source, [prediction(commit)], {})
    assert {row['line_number'] for row in result['rows']} == set(changed_lines)
    assert 'blob_line_mismatch' not in json.dumps(result['evidence'])
    for row in result['rows']:
        detail = json.loads(row['evidence_json'])['line']
        assert detail['content'] == lines[row['line_number'] - 1]


def test_requested_file_end_is_clamped(core, repository):
    with reader(core, repository) as source:
        data = source.file(repository[1], 'src/代码 space.java', 1, 200)
        assert data['end_line'] == data['total_lines'] == 3


def test_explanation_context_signed_rows_reason_rows_and_versions(core, repository):
    pred = prediction(repository[2])
    rows = [
        {**pred, "feature": "la", "raw_value": 2, "contribution": 0.3},
        {**pred, "feature": "ld", "raw_value": 1, "contribution": -0.1},
    ]
    with reader(core, repository) as source:
        result = core.localize(source, [pred], {}, explanations=rows)
        info = json.loads(result["rows"][0]["evidence_json"])
        assert [item["contribution"] for item in info["explanation"]["contributions"]] == [
            0.3,
            -0.1,
        ]
        assert info["explanation"]["mapping_note"]
        assert "missing_explanation" not in info["insufficiencies"]
        reasons = core.localize(
            source, [pred], {}, explanations=[{**pred, "reason_code": "unavailable"}]
        )
        assert (
            "missing_explanation"
            in json.loads(reasons["rows"][0]["evidence_json"])["insufficiencies"]
        )
        zeros = core.localize(source, [pred], {}, explanations=[{**rows[0], "contribution": 0}])
        assert (
            "zero_explanation" in json.loads(zeros["rows"][0]["evidence_json"])["insufficiencies"]
        )
        for bad in [
            {**rows[0], "model_version": "v2"},
            {**rows[0], "commit_hash": "0" * 40},
            {**rows[0], "feature_version": "v2"},
        ]:
            with pytest.raises(AppError) as error:
                core.localize(source, [pred], {}, explanations=[bad])
            assert error.value.code == 40001


@pytest.mark.parametrize("risk", [None, True, -0.1, 1.1, float("nan"), float("inf")])
def test_invalid_prediction_risk(core, repository, risk):
    with reader(core, repository) as source, pytest.raises(AppError):
        core.localize(source, [prediction(repository[2], risk_score=risk)], {})


def test_empty_input_and_filters_reject(core, repository):
    with reader(core, repository) as source:
        for preds, cfg in [
            ([], {}),
            ([prediction(repository[2])], {"model_name": "missing"}),
            ([prediction(repository[2])], {"commit_hash": repository[1]}),
        ]:
            with pytest.raises(AppError):
                core.localize(source, preds, cfg)


def test_history_ancestry_and_llm_failure_bounded_facts(core, repository):
    with reader(core, repository) as source:
        history = source.history(repository[2])
        assert len(history) == 1 and history[0]["commit_hash"] == repository[1]
        assert history[0]["message"] == "fix CAMEL-123 boundary" and history[0]["committed_at"]
        calls = []

        def unavailable(facts):
            calls.append(facts)
            raise RuntimeError("private diagnostic")

        result = core.localize(
            source,
            [prediction(repository[2])],
            {"suggestion_sources": ["llm", "history"]},
            llm=unavailable,
        )
        assert calls and calls[0]["top_files"][0]["lines"]
        assert "template_fallback" in result["summary"]["suggestion_sources"]
        assert "private diagnostic" not in result["suggestions"]
        for title in ["## 问题说明", "## 建议修改", "## 风险提示", "## 参考依据"]:
            assert title in result["suggestions"]
        assert "src/代码 space.java:2" in result["suggestions"]
        assert repository[1] in result["suggestions"]
        source.history = lambda _: pytest.fail("history must be opt-in")
        core.localize(source, [prediction(repository[2])], {})


def test_localization_skips_large_and_binary_and_checks_blob_content(core, repository):
    with reader(core, repository, file_size_max=16) as source:
        result = core.localize(source, [prediction(repository[2])], {"file_size_max": 16})
        assert all(row["level"] == "commit" for row in result["rows"])
        assert "too_large" in json.dumps(result["evidence"])
    with reader(core, repository) as source:
        original = source.file

        def mismatched(*args, **kwargs):
            output = original(*args, **kwargs)
            if output["status"] == "ok":
                output["content"] = "not matching\n" * output["total_lines"]
            return output

        source.file = mismatched
        result = core.localize(source, [prediction(repository[2])], {})
        assert all(row["level"] == "commit" for row in result["rows"])
        assert "blob_line_mismatch" in json.dumps(result["evidence"])
