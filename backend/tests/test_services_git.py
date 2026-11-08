"""git 服务纯函数的三例单元测试（app/services/git.py）。

`_redact` / `_looks_like_network` / `build_fetch_args` / `pick_hashes_to_predict`
与 `GitError` 均可脱离 git 子进程与网络直接断言，此前无直接覆盖。
"""

from __future__ import annotations

from app.services.git import (
    GitError,
    _looks_like_network,
    _redact,
    build_fetch_args,
    pick_hashes_to_predict,
)


def test_redact_strips_credentials_from_url():
    assert _redact("https://ghp_token@github.com/x/y.git") == "https://***@github.com/x/y.git"


def test_redact_leaves_clean_text_untouched():
    assert _redact("no credentials here") == "no credentials here"


def test_looks_like_network_case_insensitive():
    assert _looks_like_network("Connection Timed Out") is True
    assert _looks_like_network("could not resolve host") is True


def test_looks_like_network_false_for_config_errors():
    assert _looks_like_network("permission denied") is False


def test_build_fetch_args():
    assert build_fetch_args() == ["fetch", "origin", "HEAD"]


def test_pick_hashes_to_predict_filters_predicted():
    assert pick_hashes_to_predict(["a", "b", "c"], {"b"}) == ["a", "c"]


def test_pick_hashes_to_predict_empty_inputs():
    assert pick_hashes_to_predict([], {"a"}) == []
    assert pick_hashes_to_predict(["a"], set()) == ["a"]


def test_pick_hashes_to_predict_preserves_order_and_duplicates():
    assert pick_hashes_to_predict(["a", "a", "b"], set()) == ["a", "a", "b"]


def test_git_error_is_app_error_with_retryable_flag():
    err = GitError(retryable=True)
    assert err.code == 50000
    assert err.retryable is True
    assert GitError(retryable=False).retryable is False
