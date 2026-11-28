from __future__ import annotations

import shutil
from datetime import datetime, timedelta
from pathlib import Path

from git import Actor, Repo

from app import config
from app.constants import EXPERT_FEATURES
from data_model import features as feature_lib
from data_model import gitops, szz


def _prepare_repo() -> tuple[Repo, Path]:
    path = Path(config.TEMP_ROOT) / "tests" / "collect_repo"
    shutil.rmtree(path, ignore_errors=True)
    path.mkdir(parents=True, exist_ok=True)
    repo = Repo.init(path)
    actor = Actor("dev", "dev@example.com")
    base = datetime(2024, 1, 1, 10, 0, 0)

    def commit(content: str, message: str, day: int, name: str = "parser.py"):
        (path / name).write_text(content, encoding="utf-8")
        repo.index.add([name])
        when = (base + timedelta(days=day)).isoformat()
        return repo.index.commit(
            message, author=actor, committer=actor, author_date=when, commit_date=when
        )

    lines = "\n".join(f"line{i}" for i in range(1, 11)) + "\n"
    commit(lines, "init parser", 0)
    commit(lines.replace("line5", "line5_bug"), "change parser body", 1)
    commit("helper\n", "add helper", 2, name="helper.py")
    commit(lines.replace("line5", "line5_fixed"), "fix: correct parser body", 3)
    return repo, path


def test_szz_marks_introducing_commit():
    repo, _ = _prepare_repo()
    commits = list(reversed(list(repo.iter_commits(no_merges=True))))
    hashes = [commit.hexsha for commit in commits]
    labels = szz.label_commits(repo, hashes, [hashes[-1]])
    assert labels[hashes[-3]]["is_bug_inducing"] == 1
    assert labels[hashes[-1]]["is_bug_inducing"] == 0


def test_kamei_features_shape():
    repo, _ = _prepare_repo()
    commits = list(reversed(list(repo.iter_commits(no_merges=True))))
    computed = feature_lib.compute_features_batch(repo, commits)
    assert set(computed[commits[-2].hexsha]) == set(EXPERT_FEATURES)
    bug_commit = computed[commits[-2].hexsha]
    assert bug_commit["nf"] == 1
    assert bug_commit["ns"] == 1
    assert bug_commit["la"] >= 1
    assert isinstance(bug_commit["exp"], float)
    single = feature_lib.compute_features(repo, commits[-2].hexsha)
    assert set(single) == set(EXPERT_FEATURES)


def test_parse_repo_url():
    info = gitops.parse_repo_url("https://github.com/owner/repo.git")
    assert info["platform"] == "github"
    assert info["repo_name"] == "owner/repo"
    assert gitops.parse_repo_url("gitee.com/a/b")["platform"] == "gitee"
