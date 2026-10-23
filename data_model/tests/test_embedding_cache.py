"""Regression: the encoding cache must be readable by both allow_pickle=False loaders.

``pandas`` string columns yield ``object`` arrays; ``np.savez_compressed`` then
stores them as pickled object arrays, which ``np.load(allow_pickle=False)``
rejects. The cache is produced once by the semantic line and consumed by both
the semantic and the fused line, so a save/load round-trip is the contract.
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from data_model.pipelines.semantic.data import (
    _as_str_array,
    load_embeddings,
    save_embeddings,
)


@pytest.fixture()
def sample():
    hashes = ["a" * 40, "b" * 40, "c" * 40]
    df = pd.DataFrame({
        "commit_hash": hashes,
        "label": [1, 0, 1],
        "feature_version": ["v2", "v2", "v3"],
    })
    # the fused loader validates that the semantic cache is N x 768
    emb = np.arange(3 * 768, dtype=np.float32).reshape(3, 768)
    return df, emb, hashes


def test_as_str_array_is_unicode_not_object():
    arr = _as_str_array(["x" * 40, "y" * 40])
    assert arr.dtype.kind == "U"
    assert arr.dtype != np.dtype("O")


def test_as_str_array_handles_empty():
    arr = _as_str_array([])
    assert arr.dtype.kind == "U"
    assert arr.size == 0


def test_saved_arrays_are_not_object_dtype(tmp_path, sample):
    df, emb, _ = sample
    path = tmp_path / "emb.npz"
    save_embeddings(path, df, emb)
    with np.load(path, allow_pickle=False) as z:
        assert z["commit_hash"].dtype.kind != "O"
        assert z["feature_version"].dtype.kind != "O"
        assert z["commit_hash"].dtype.kind == "U"


def test_round_trip_semantic_loader(tmp_path, sample):
    df, emb, hashes = sample
    path = tmp_path / "emb.npz"
    save_embeddings(path, df, emb)
    got_hashes, got_emb, labels, versions = load_embeddings(path)
    assert got_hashes == hashes
    np.testing.assert_allclose(got_emb, emb)
    assert labels is not None and labels.tolist() == [1, 0, 1]
    assert sorted(versions) == ["v2", "v3"]


def test_round_trip_fused_loader(tmp_path, sample):
    """The fused line reads the same file with allow_pickle=False."""
    from data_model.pipelines.fused.data import load_embeddings as fused_load

    df, emb, hashes = sample
    path = tmp_path / "emb.npz"
    save_embeddings(path, df, emb)
    index, matrix = fused_load(path)
    assert sorted(index.keys()) == sorted(hashes)
    assert matrix.shape[0] == 3


def test_round_trip_survives_nan_free_float_and_reload(tmp_path, sample):
    """A second training pass re-reads the cache written by the first."""
    df, emb, hashes = sample
    path = tmp_path / "emb.npz"
    save_embeddings(path, df, emb)
    first = load_embeddings(path)
    second = load_embeddings(path)
    assert first[0] == second[0] == hashes
    np.testing.assert_allclose(first[1], second[1])
