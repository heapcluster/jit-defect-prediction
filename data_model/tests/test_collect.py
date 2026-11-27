# AI-generated/unreviewed: all tests and fixture builders in this file.
"""W3.1 real Git acceptance tests; no database or Camel baseline writes."""
from __future__ import annotations

import hashlib
import importlib
import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
DATA_MODEL = ROOT / "data_model"
FIXTURE = DATA_MODEL / "tests/fixtures/files/collect/history.json"
sys.path.insert(0, str(DATA_MODEL))


def collect():
    assert (DATA_MODEL / "preparation/collect.py").is_file(), "W3.1 collect implementation missing"
    return importlib.import_module("preparation.collect")


def git(repo, *args, when=None):
    source = json.loads(FIXTURE.read_text(encoding="utf-8"))
    env = {key: value for key, value in os.environ.items() if not key.startswith("GIT_")}
    env.update(GIT_CONFIG_NOSYSTEM="1", GIT_CONFIG_GLOBAL=os.devnull,
               GIT_AUTHOR_NAME=source["author_name"], GIT_COMMITTER_NAME=source["author_name"],
               GIT_AUTHOR_EMAIL=source["author_email"], GIT_COMMITTER_EMAIL=source["author_email"])
    if when:
        env.update(GIT_AUTHOR_DATE=when, GIT_COMMITTER_DATE=when)
    return subprocess.run(["git", "-C", str(repo), *args], env=env, check=True,
                          capture_output=True).stdout.decode("utf-8").strip()


def make_repo(parent, *, count=4, same_second=False, root_fix=False):
    repo = parent / "repository"
    repo.mkdir()
    git(repo, "init", "--initial-branch=main")
    source = json.loads(FIXTURE.read_text(encoding="utf-8"))
    hashes = []
    (repo / "src").mkdir()
    for i, row in enumerate(source["commits"][:count]):
        (repo / "src/中文 file.txt").write_text(row["content"], encoding="utf-8")
        git(repo, "add", "src")
        message = "CAMEL-1 fix 根提交" if root_fix and i == 0 else row["message"]
        git(repo, "commit", "-m", message,
            when=source["commits"][0]["when"] if same_second else row["when"])
        hashes.append(git(repo, "rev-parse", "HEAD"))
    return repo, hashes


@pytest.fixture
def repository(tmp_path):
    return make_repo(tmp_path)


def config(repo, **changes):
    # 新契约：采集必须显式选择分支。
    return {"repo_source": str(repo), "dataset_name": "中文数据集", "fetch_remote": False,
            "branch": "main", **changes}


def run(repo, **kwargs):
    return collect().run(config(repo, **kwargs), allow_roots=[str(repo.parent)], protocol_whitelist=["https", "git"])


@pytest.mark.parametrize("method,positive", [("szz_v1", 0), ("szz_lite", 1)])
def test_full_history_labels_and_v1(repository, method, positive):
    repo, hashes = repository
    before = (git(repo, "rev-parse", "HEAD"), (repo / ".git/index").read_bytes(), git(repo, "status", "--porcelain"))
    events = []
    result = collect().run(config(repo, szz_method=method), allow_roots=[str(repo.parent)],
                           protocol_whitelist=["https"], progress=lambda *event: events.append(event))
    rows = result["rows"]
    assert [row["commit_hash"] for row in rows] == hashes
    labels = [row["is_bug_inducing"] for row in rows]
    assert labels[-1] is None
    assert labels.count(1) == 1 and labels.count(0) == 2
    contracts, _ = collect()._file_services()
    columns, exported = contracts.read_table("collected_commits.csv", collect().encode_rows(rows, "csv"))
    assert tuple(columns) == contracts.COLLECTED_COMMITS_COLUMNS
    assert all("is_test" not in row and not set(row) & set(contracts.FEATURE_COLUMNS) for row in exported)
    assert result["summary"]["rows"] == 4
    assert result["summary"]["labeled_rows"] == 3
    assert result["summary"]["positive_rows"] == 1
    assert result["summary"]["negative_rows"] == 2
    assert result["summary"]["unlabeled_rows"] == 1
    assert result["summary"]["head_hash"] == hashes[-1]
    assert result["audit"]["szz"]["unresolved_hashes"] == [hashes[-1]]
    assert result["audit"]["szz"]["unresolved_reasons"] == {hashes[-1]: "no_old_lines"}
    assert result["config"]["feature_version"] == "v1"
    assert result["config"]["resolvedHEAD"] == hashes[-1]
    assert result["config"]["labeled_at"] == "2026-01-04T12:00:00Z"
    assert rows[-1]["labeled_at"] is None
    assert rows[-1]["label_method"] is None
    assert [event[1] for event in events] == sorted(event[1] for event in events)
    assert {event[1] for event in events} == set(range(6))
    assert all(event[2] == 5 for event in events)
    assert before == (git(repo, "rev-parse", "HEAD"), (repo / ".git/index").read_bytes(), git(repo, "status", "--porcelain"))
    item = result["inputs"][0]
    snapshot = Path(item["path"])
    assert snapshot.name == "repository_snapshot.json" and snapshot.is_file()
    assert hashlib.sha256(snapshot.read_bytes()).hexdigest() == item["sha256"]
    assert item["rows"] == 4
    assert json.loads(snapshot.read_text(encoding="utf-8"))["head_hash"] == hashes[-1]


def test_no_fix_and_singleton_keep_null(tmp_path):
    repo, hashes = make_repo(tmp_path, count=1)
    result = run(repo)
    assert result["rows"][0]["is_bug_inducing"] is None
    assert result["rows"][0]["is_test"] == 0
    assert result["summary"]["labeled_rows"] == 0
    assert result["audit"]["boundary"]["reason"] == "single_commit_no_two_sided_split"
    assert result["audit"]["szz"]["fix_total"] == 0


def test_all_unresolved_no_fake_negatives(tmp_path):
    repo, _ = make_repo(tmp_path, count=2, root_fix=True)
    result = run(repo)
    assert [r["is_bug_inducing"] for r in result["rows"]] == [None, None]
    assert result["audit"]["szz"]["no_parent"] == 1


def test_range_only_filters_output_not_feature_or_szz_history(repository):
    repo, hashes = repository
    full = run(repo)
    selected = run(repo, start_commit=hashes[1], end_commit=hashes[2],
                   start_time="2026-01-02T12:00:00Z", end_time="2026-01-03T12:00:00+00:00")
    assert selected["rows"] == full["rows"][1:3]
    assert selected["config"]["resolvedHEAD"] == hashes[-1]


def test_future_commit_with_old_author_date_cannot_change_prior_features(repository):
    repo, hashes = repository
    before = run(repo, start_commit=hashes[2], end_commit=hashes[2])['rows'][0]
    fixture = json.loads(FIXTURE.read_text(encoding='utf-8'))
    for day in (5, 6):
        env = {**os.environ, 'GIT_CONFIG_GLOBAL': os.devnull, 'GIT_CONFIG_NOSYSTEM': '1',
               'GIT_AUTHOR_NAME': fixture['author_name'], 'GIT_COMMITTER_NAME': fixture['author_name'],
               'GIT_AUTHOR_EMAIL': fixture['author_email'], 'GIT_COMMITTER_EMAIL': fixture['author_email'],
               'GIT_AUTHOR_DATE': '2026-01-01T12:00:00Z', 'GIT_COMMITTER_DATE': f'2026-01-0{day}T12:00:00Z'}
        subprocess.run(['git', '-C', str(repo), 'commit', '--allow-empty', '-qm', 'future timestamp fixture'],
                       env=env, check=True)
    after = run(repo, start_commit=hashes[2], end_commit=hashes[2])['rows'][0]
    assert {name: before[name] for name in ('exp', 'rexp', 'ndev', 'age', 'nuc')} == {
        name: after[name] for name in ('exp', 'rexp', 'ndev', 'age', 'nuc')}


def test_selected_ref_does_not_use_user_head_history(repository):
    repo, hashes = repository
    result = run(repo, branch=hashes[1])
    assert len(result["rows"]) == 2 and result["summary"]["head_hash"] == hashes[1]
    assert result["summary"]["labeled_rows"] == 0
    assert git(repo, "rev-parse", "HEAD") == hashes[-1]


def test_list_dedup_and_unreachable_rejected(repository):
    repo, hashes = repository
    module = collect()
    result = module.run(config(repo), allow_roots=[str(repo.parent)], protocol_whitelist=[],
                        commit_hashes=[hashes[2], hashes[1], hashes[2]])
    assert [r["commit_hash"] for r in result["rows"]] == hashes[1:3]
    assert result["audit"]["deduplicated"] == 1
    with pytest.raises(module.CollectError) as error:
        module.run(config(repo), allow_roots=[str(repo.parent)], protocol_whitelist=[], commit_hashes=["f" * 40])
    assert error.value.code == 40001


@pytest.mark.parametrize("changes", [
    {"unknown": 1}, {"dataset_id": 1}, {"fetch_remote": "false"}, {"fetch_remote": 0},
    {"split_ratio": True}, {"split_ratio": "0.7"}, {"split_ratio": float("nan")},
    {"split_ratio": 0}, {"split_ratio": 1}, {"mode": "random"}, {"dedup": "none"},
    {"format": "xls"}, {"szz_method": "other"}, {"branch": "--all"},
    {"branch": "main;touch x"}, {"branch": "HEAD@{1}"}, {"branch": "main\n--all"},
    {"head_expect": "abcd"}, {"start_time": "2026-01-01"},
    {"start_time": "2026-02-01T00:00:00Z", "end_time": "2026-01-01T00:00:00Z"},
])
def test_strict_config(repository, changes):
    repo, _ = repository
    module = collect()
    with pytest.raises(module.CollectError) as error:
        module.validate_config(config(repo, **changes), allow_roots=[str(repo.parent)], protocol_whitelist=[])
    assert error.value.code == 40001 and error.value.message


def test_path_symlink_escape_and_missing(tmp_path):
    module = collect()
    allowed = tmp_path / "allowed"
    allowed.mkdir()
    outside = tmp_path / "outside"
    outside.mkdir()
    (allowed / "link").symlink_to(outside, target_is_directory=True)
    for path, code in [(allowed / "link", 40001), (allowed / "missing", 40400)]:
        with pytest.raises(module.CollectError) as error:
            module.validate_config(config(path), allow_roots=[str(allowed)], protocol_whitelist=[])
        assert error.value.code == code


@pytest.mark.parametrize("source", [
    "file:///tmp/repo", "ssh://example.org/repo", "ext::command", "git@github.com:owner/repo", 
    "https://user:secret@example.org/repo", "https://example.org/repo?x=1",
    "https://example.org/repo#HEAD", "https://localhost/repo", "https://127.0.0.1/repo",
    "https://10.1.2.3/repo", "git://192.168.0.1/repo", "https://[::1]/repo",
    "https://169.254.169.254/repo", "https://192.0.2.1/repo", "https://224.0.0.1/repo",
])
def test_url_security(tmp_path, source):
    module = collect()
    with pytest.raises(module.CollectError) as error:
        module.validate_config(config(source), allow_roots=[str(tmp_path)], protocol_whitelist=["https", "git"])
    assert error.value.code == 40001


def test_dns_private_target_rejected(tmp_path, monkeypatch):
    module = collect()
    monkeypatch.setattr(module.socket, "getaddrinfo", lambda *a, **k: [(2, 1, 6, "", ("10.0.0.1", 443))])
    with pytest.raises(module.CollectError, match="网络"):
        module.validate_config(config("https://example.org/repo"), allow_roots=[str(tmp_path)], protocol_whitelist=["https"])


def test_empty_same_second_head_and_missing_ref(tmp_path):
    repo, hashes = make_repo(tmp_path, same_second=True)
    module = collect()
    for changes in [{}, {"head_expect": "f" * 40}, {"branch": "absent"},
                    {"start_time": "2027-01-01T00:00:00Z"}, {"start_commit": hashes[3], "end_commit": hashes[0]}]:
        with pytest.raises(module.CollectError) as error:
            run(repo, **changes)
        assert error.value.code == 40001


@pytest.mark.parametrize("phase", range(6))
def test_cancellation_callback_never_swallowed(repository, phase):
    repo, _ = repository
    module = collect()
    class Cancelled(RuntimeError):
        pass
    def progress(name, done, total):
        if done == phase:
            raise Cancelled("cancelled by main thread")
    with pytest.raises(Cancelled):
        module.run(config(repo), allow_roots=[str(repo.parent)], protocol_whitelist=[], progress=progress)


def test_incremental_cache_checksum_head_and_config(repository, tmp_path):
    repo, hashes = repository
    module = collect()
    cache = tmp_path / "controlled-cache"
    args = dict(allow_roots=[str(repo.parent)], protocol_whitelist=[], cache_dir=cache)
    first = module.run(config(repo), **args)
    second = module.run(config(repo), **args)
    assert first["rows"] == second["rows"]
    assert second["audit"]["cache"]["hit"] is True
    files = list(cache.glob("*.json"))
    assert files
    files[0].write_text('{"corrupt":true}', encoding="utf-8")
    assert module.run(config(repo), **args)["audit"]["cache"]["hit"] is False
    assert module.run(config(repo, szz_method="szz_lite"), **args)["audit"]["cache"]["hit"] is False
    git(repo, "commit", "--allow-empty", "-m", "追加中文提交", when="2026-01-05T12:00:00+0000")
    newer = module.run(config(repo), **args)
    assert newer["audit"]["cache"]["hit"] is False and newer["summary"]["rows"] == 5
    assert newer["config"]["resolvedHEAD"] != hashes[-1]


def test_readonly_safety_external_tools_and_git_environment(repository, tmp_path, monkeypatch):
    repo, _ = repository
    marker = tmp_path / "SHOULD_NOT_EXIST"
    git(repo, "config", "core.fsmonitor", f"touch {marker}")
    git(repo, "config", "diff.external", f"touch {marker}")
    git(repo, "config", "diff.evil.textconv", f"touch {marker}")
    (repo / ".gitattributes").write_text("*.txt diff=evil\n")
    monkeypatch.setenv("GIT_EXTERNAL_DIFF", f"touch {marker}")
    monkeypatch.setenv("GIT_CONFIG_COUNT", "1")
    monkeypatch.setenv("GIT_CONFIG_KEY_0", "core.fsmonitor")
    monkeypatch.setenv("GIT_CONFIG_VALUE_0", f"touch {marker}")
    assert run(repo)["summary"]["rows"] == 4
    assert not marker.exists()


def test_limits_and_git_failure_codes(repository, monkeypatch):
    repo, _ = repository
    module = collect()
    monkeypatch.setattr(module, "MAX_REPO_BYTES", 1)
    with pytest.raises(module.CollectError) as error:
        run(repo)
    assert error.value.code == 40001
    monkeypatch.setattr(module, "MAX_REPO_BYTES", 2 * 1024**3)
    monkeypatch.setattr(module, "MAX_ROWS", 2)
    with pytest.raises(module.CollectError) as error:
        run(repo)
    assert error.value.code == 40001
    with pytest.raises(module.CollectError) as error:
        module.GitRunner([], None)(repo, "not-a-command")
    assert error.value.code == 50000


def test_encoded_features_have_database_precision_without_changing_math(repository):
    module = collect()
    repo, _ = repository
    result = run(repo)
    contracts, _ = module._file_services()
    csv = module.encode_rows(result['rows'], 'csv')
    xlsx = module.encode_rows(result['rows'], 'xlsx')
    csv_rows = contracts.read_table('collected_commits.csv', csv)[1]
    xlsx_rows = contracts.read_table('collected_commits.xlsx', xlsx)[1]
    assert csv_rows == xlsx_rows
    for row in csv_rows:
        assert not set(row) & set(contracts.FEATURE_COLUMNS)
        assert "is_test" not in row
        assert set(row) == set(contracts.COLLECTED_COMMITS_COLUMNS)


def test_direct_cli_script_works_without_external_pythonpath(repository, tmp_path):
    repo, _ = repository
    process = subprocess.run([sys.executable, '-I', str(DATA_MODEL / 'preparation/collect.py'),
        'run', '--repo', str(repo), '--branch', 'main', '--name', 'standalone fixture', '--fetch-remote', 'false',
        '--allow-root', str(repo.parent), '--out', str(tmp_path / 'direct-cli')],
        capture_output=True, text=True)
    assert process.returncode == 0, process.stderr
    assert list((tmp_path / 'direct-cli').glob('*/collected_commits_*.csv'))


def test_cli_run_export_verified_manifest_and_bom(repository, tmp_path):
    repo, _ = repository
    module = collect()
    env = {**os.environ, "PYTHONPATH": str(DATA_MODEL), "DATABASE_URL": "", "DB_HOST": ""}
    out = tmp_path / "output"
    command = [sys.executable, "-m", "preparation.collect"]
    process = subprocess.run(command + ["run", "--repo", str(repo), "--branch", "main", "--name", "中文数据集",
        "--mode", "incremental", "--fetch-remote", "false", "--out", str(out), "--allow-root", str(repo.parent)],
        env=env, capture_output=True, text=True)
    assert process.returncode == 0, process.stderr
    table = next(out.glob("*/collected_commits_*.csv"))
    assert table.read_bytes().startswith(b"\xef\xbb\xbf")
    sys.path.insert(0, str(ROOT / "backend"))
    from app.services import file_contracts
    columns, rows = file_contracts.read_table(table.name, table.read_bytes())
    assert tuple(columns) == file_contracts.COLLECTED_COMMITS_COLUMNS
    expected = run(repo)["rows"]
    assert rows[0]["message"] == expected[0]["message"]
    assert rows[-1]["is_bug_inducing"] == ""
    manifest = file_contracts.verify_manifest(table.name, table.read_bytes(), table.with_suffix(".manifest.json").read_bytes())
    assert "+preparation." in manifest["code_version"]
    assert module.code_version().split("+preparation.")[1] in manifest["code_version"]
    result = subprocess.run(command + ["export", "--input", str(table), "--format", "xlsx", "--out", str(out)],
                            env=env, capture_output=True, text=True)
    assert result.returncode == 0, result.stderr
    xlsx = next(out.glob("*/collected_commits_*.xlsx"))
    assert file_contracts.read_table(xlsx.name, xlsx.read_bytes())[1] == rows
    table.write_bytes(table.read_bytes() + b"tampered")
    result = subprocess.run(command + ["export", "--input", str(table), "--format", "xlsx", "--out", str(out)],
                            env=env, capture_output=True, text=True)
    assert result.returncode != 0
    assert json.loads(result.stderr)["code"] == 40001


def test_user_worktree_attributes_cannot_change_snapshot_features(repository):
    repo, _ = repository
    before = run(repo)["rows"]
    (repo / ".gitattributes").write_text("*.txt binary\n", encoding="utf-8")
    after = run(repo)["rows"]
    assert after == before


def test_cache_cannot_be_inside_checkout_and_snapshot_root_is_not_checkout(repository):
    repo, _ = repository
    module = collect()
    with pytest.raises(module.CollectError):
        module.run(config(repo), allow_roots=[str(repo.parent)], protocol_whitelist=[], cache_dir=repo / "cache")
    with pytest.raises(module.CollectError):
        module.run(config(repo), allow_roots=[str(repo)], protocol_whitelist=[])
    assert not list(repo.glob(".collect-*"))


def test_clone_transport_validated_controlled_and_cleanup(repository, tmp_path, monkeypatch):
    repo, _ = repository
    module = collect()
    monkeypatch.setattr(module.socket, "getaddrinfo", lambda *a, **k: [(2, 1, 6, "", ("93.184.216.34", 443))])
    original = module.GitRunner.__call__
    seen = []
    def fixture_transport(self, directory, *args, **kwargs):
        if args[0] == "clone":
            seen.append((Path(directory), args, tuple(self.network_config)))
            # Only transport is replaced: real bare Git clone + real history/SZZ.
            local = module.GitRunner(["file"], self.progress)
            return original(local, directory, "clone", "--bare", "--no-hardlinks", "--template=", "--", str(repo), args[-1])
        return original(self, directory, *args, **kwargs)
    monkeypatch.setattr(module.GitRunner, "__call__", fixture_transport)
    result = module.run(config("https://example.org/snapshot.git"), allow_roots=[str(tmp_path)], protocol_whitelist=["https"])
    assert result["summary"]["rows"] == 4
    assert result["audit"]["fetch"] == "new_controlled_clone"
    assert seen and "--bare" in seen[0][1] and "--no-local" in seen[0][1]
    assert seen[0][2][0].startswith("http.curloptResolve=example.org:443:")
    assert not seen[0][0].exists()
    existing = tmp_path / "unrelated"
    existing.mkdir()
    def broken_clone(self, directory, *args, **kwargs):
        if args[0] == "clone":
            (Path(directory) / "partial").write_text("only owned staging")
            raise module.CollectError(50000, "Git clone failed")
        return original(self, directory, *args, **kwargs)
    monkeypatch.setattr(module.GitRunner, "__call__", broken_clone)
    with pytest.raises(module.CollectError) as error:
        module.run(config("https://example.org/snapshot.git"), allow_roots=[str(tmp_path)], protocol_whitelist=["https"])
    assert error.value.code == 50000
    assert existing.is_dir() and not list(tmp_path.glob(".collect-clone-*"))


def test_git_failure_has_stage_audit_and_cancel_during_same_stage(repository, monkeypatch):
    repo, _ = repository
    module = collect()
    original = module.GitRunner.__call__
    def failing(self, directory, *args, **kwargs):
        if args[0] == "show":
            raise module.CollectError(50000, "Git show failed")
        return original(self, directory, *args, **kwargs)
    monkeypatch.setattr(module.GitRunner, "__call__", failing)
    with pytest.raises(module.CollectError) as error:
        run(repo)
    assert error.value.audit["stage_errors"][0]["phase"] == "commits"
    monkeypatch.setattr(module.GitRunner, "__call__", original)
    class Cancelled(ValueError):
        pass
    repeats = 0
    def progress(phase, done, total):
        nonlocal repeats
        if done == 3:
            repeats += 1
            if repeats == 5:
                raise Cancelled("cancel during backtracking")
    with pytest.raises(Cancelled):
        module.run(config(repo), allow_roots=[str(repo.parent)], protocol_whitelist=[], progress=progress)


def test_runner_timeout_and_cancellation_kill_owned_process(repository, monkeypatch):
    repo, _ = repository
    module = collect()
    popen = module.subprocess.Popen
    processes = []
    def slow_git(argv, **kwargs):
        process = popen([sys.executable, "-c", "import time; time.sleep(30)"], **kwargs)
        processes.append(process)
        return process
    monkeypatch.setattr(module.subprocess, "Popen", slow_git)
    monkeypatch.setattr(module, "GIT_TIMEOUT", 0.03)
    with pytest.raises(module.CollectError) as error:
        module.GitRunner([], None)(repo, "rev-parse", "HEAD")
    assert error.value.code == 50000 and processes[-1].poll() is not None
    checks = 0
    class Cancelled(RuntimeError):
        pass
    def check():
        nonlocal checks
        checks += 1
        if checks == 2:
            raise Cancelled("cancel running process")
    with pytest.raises(Cancelled):
        module.GitRunner([], check)(repo, "rev-parse", "HEAD")
    assert processes[-1].poll() is not None


def test_history_and_batch_feature_optional_callbacks(repository):
    repo, hashes = repository
    module = collect()
    extract = importlib.import_module("preparation.03_extract_features")
    class Cancelled(ValueError):
        pass
    def cancel():
        raise Cancelled("cancel history index")
    with pytest.raises(Cancelled):
        extract.HistoryIndex(extract.scan_history(repo), progress=cancel)
    runner = module.GitRunner([], None)
    batch = extract.extract_commits(repo, list(reversed(hashes[:3])), ref=hashes[2], runner=runner)
    # Same injected runner: legacy default Git quotes non-ASCII paths, whereas
    # collect deliberately requests literal UTF-8 paths for correct blob specs.
    expected = extract.extract_commits(repo, hashes[:3], runner=runner)
    assert [r["features"] for r in batch] == [r["features"] for r in reversed(expected)]
    with pytest.raises(Cancelled):
        extract.extract_commits(repo, hashes, runner=runner, progress=cancel)


def test_partial_szz_diff_never_claims_complete_backtracking():
    szz = importlib.import_module("preparation.02_szz_labeling")
    text = ('diff --git a/good.txt b/good.txt\n--- a/good.txt\n+++ b/good.txt\n@@ -1 +1 @@\n-old\n+new\n'
            'diff --git "a/unsupported\\tname" "b/unsupported\\tname"\n--- "a/unsupported\\tname"\n'
            '+++ "b/unsupported\\tname"\n@@ -1 +1 @@\n-old\n+new\n')
    sha = "a" * 40
    memo = {szz.blame_cache_key("p", "good.txt", ((1, 1),)): {1: sha}}
    assert szz.backtrack_szz(Path("/unused"), "f", "p", text, memo, strict=True) == set()


def test_snapshot_cleanup_on_cancel_after_final_materialization(repository):
    repo, _ = repository
    module = collect()
    class Cancelled(RuntimeError):
        pass
    def progress(phase, done, total):
        if list(repo.parent.glob(".collect-snapshot-*/repository_snapshot.json")):
            raise Cancelled("cancel final result")
    with pytest.raises(Cancelled):
        module.run(config(repo), allow_roots=[str(repo.parent)], protocol_whitelist=[], progress=progress)
    assert not list(repo.parent.glob(".collect-clone-*"))
    assert not list(repo.parent.glob(".collect-snapshot-*"))


@pytest.mark.parametrize("value", [10**1000, -10**1000])
def test_oversized_numeric_config_still_returns_40001(repository, value):
    repo, _ = repository
    module = collect()
    with pytest.raises(module.CollectError) as error:
        module.validate_config(config(repo, split_ratio=value), allow_roots=[str(repo.parent)], protocol_whitelist=[])
    assert error.value.code == 40001


def test_cache_hit_never_reexecutes_szz_or_features_and_list_key(repository, tmp_path, monkeypatch):
    repo, hashes = repository
    module = collect()
    cache = tmp_path / "cache"
    args = dict(allow_roots=[str(repo.parent)], protocol_whitelist=[], cache_dir=cache)
    first = module.run(config(repo), commit_hashes=hashes[:3], **args)
    szz = importlib.import_module("preparation.02_szz_labeling")
    features = importlib.import_module("preparation.03_extract_features")
    def forbidden(*args, **kwargs):
        pytest.fail("exact cache hit re-executed expensive labeling/features")
    monkeypatch.setattr(szz, "run_method", forbidden)
    monkeypatch.setattr(features, "compute_raw", forbidden)
    cached = module.run(config(repo), commit_hashes=list(reversed(hashes[:3])), **args)
    assert cached["audit"]["cache"]["hit"] is True and cached["rows"] == first["rows"]
    assert module._cache_read(next(cache.glob("*.json")), "wrong-key", module.code_version()) is None
    monkeypatch.undo()
    # Different selection cannot read labels from this list's cached payload.
    changed = module.run(config(repo), commit_hashes=hashes[1:3], **args)
    assert changed["audit"]["cache"]["hit"] is False
    assert changed["config"]["commit_list_sha256"] != first["config"]["commit_list_sha256"]


def test_bare_input_and_merge_selection_audit(repository, tmp_path):
    repo, hashes = repository
    bare = tmp_path / "source.git"
    git(tmp_path, "clone", "--bare", "--no-hardlinks", str(repo), str(bare))
    assert run(bare)["rows"][0]["repo_name"] == "source.git"
    git(repo, "checkout", "-b", "side", hashes[1])
    (repo / "side.txt").write_text("branch-only\n")
    git(repo, "add", "side.txt")
    git(repo, "commit", "-m", "侧分支中文提交", when="2026-01-05T12:00:00+0000")
    side = git(repo, "rev-parse", "HEAD")
    git(repo, "checkout", "main")
    git(repo, "merge", "--no-ff", "side", "-m", "合并中文样例", when="2026-01-06T12:00:00+0000")
    merge = git(repo, "rev-parse", "HEAD")
    full = run(repo)
    assert full["summary"]["head_hash"] == merge and full["summary"]["rows"] == 5
    assert full["audit"]["skipped"]["merges"] == 1
    selected = run(repo, start_commit=hashes[2])
    assert side not in {row["commit_hash"] for row in selected["rows"]}
    assert [row["commit_hash"] for row in selected["rows"]] == hashes[2:]


def test_runtime_repository_git_error_not_misreported_as_missing(repository, monkeypatch):
    repo, _ = repository
    module = collect()
    original = module.GitRunner.__call__
    def failed_read(self, directory, *args, **kwargs):
        if args[:2] == ("rev-parse", "--absolute-git-dir"):
            raise module.CollectError(50000, "Git read timed out")
        return original(self, directory, *args, **kwargs)
    monkeypatch.setattr(module.GitRunner, "__call__", failed_read)
    with pytest.raises(module.CollectError) as error:
        run(repo)
    assert error.value.code == 50000


def test_csv_formula_escape_without_database(repository):
    repo, _ = repository
    result = run(repo)
    contracts, _ = collect()._file_services()
    assert "app.db" not in sys.modules
    result["rows"][0]["message"] = "=1+2 中文"
    for format in ("csv", "xlsx"):
        content = collect().encode_rows(result["rows"], format)
        columns, rows = contracts.read_table(f"collect_commits_test.{format}", content)
        assert tuple(columns) == contracts.COLLECTED_COMMITS_COLUMNS
        assert rows[0]["message"] == "'=1+2 中文"
        assert rows[-1]["is_bug_inducing"] == ""


def test_cli_direct_xlsx_retains_full_width_nullable_rows(repository, tmp_path):
    repo, _ = repository
    env = {**os.environ, "PYTHONPATH": str(DATA_MODEL), "DATABASE_URL": "", "DB_HOST": ""}
    output = tmp_path / "xlsx-output"
    process = subprocess.run([sys.executable, "-m", "preparation.collect", "run", "--repo", str(repo),
        "--branch", "main", "--name", "中文", "--fetch-remote", "false", "--format", "xlsx", "--out", str(output),
        "--allow-root", str(repo.parent)], env=env, capture_output=True, text=True)
    assert process.returncode == 0, process.stderr
    path = next(output.glob("*/collected_commits_*.xlsx"))
    contracts, _ = collect()._file_services()
    columns, rows = contracts.read_table(path.name, path.read_bytes())
    assert tuple(columns) == contracts.COLLECTED_COMMITS_COLUMNS and rows[-1]["is_bug_inducing"] == ""
