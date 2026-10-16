"""Regression: the Effort-aware quota must spend a LOC budget, not count rows.

The reviewer's minimal counter-example: 5 commits, scores descending 5..1,
LOC = [10, 10, 10, 10, 60], labels = [0, 1, 0, 0, 1].

  * count-based quota (old behaviour): 20% of 5 rows = 1 commit -> recall 0
  * LOC budget (correct): 20% of 100 LOC = 20 -> two 10-LOC commits -> recall 0.5

The two metrics differ by half the recall on the same input, so the label
"Effort-aware" only holds if the budget is actually effort.
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from data_model.pipelines.expert.significance import top_by_effort  # noqa: E402

FRACTION = 0.20

# score order is 0,1,2,3,4 (descending scores 5,4,3,2,1)
LOC = np.array([10.0, 10.0, 10.0, 10.0, 60.0])
LABELS = np.array([0, 1, 0, 0, 1])


def test_counter_example_uses_effort_not_row_count():
    scores = np.array([5.0, 4.0, 3.0, 2.0, 1.0])
    top = top_by_effort(scores, LOC, FRACTION)
    # budget = 100 * 0.20 = 20 LOC -> commits 0 and 1 (10 + 10)
    assert sorted(top.tolist()) == [0, 1]
    recall = LABELS[top].sum() / LABELS.sum()
    assert recall == pytest.approx(0.5)


def test_count_based_would_have_returned_one_commit():
    """Documents what the old (wrong) quota produced on the same input."""
    scores = np.array([5.0, 4.0, 3.0, 2.0, 1.0])
    n = len(scores)
    old_quota = max(1, int(round(n * FRACTION)))
    assert old_quota == 1
    assert LABELS[:old_quota].sum() / LABELS.sum() == pytest.approx(0.0)


def test_single_huge_commit_is_still_reviewed():
    """A commit whose LOC alone exceeds the budget must not empty the set."""
    scores = np.array([9.0, 1.0])
    loc = np.array([1000.0, 1.0])   # budget = 200.4 -> only commit 0 fits
    top = top_by_effort(scores, loc, FRACTION)
    assert top.tolist() == [0]


def test_budget_selects_in_score_order_not_loc_order():
    """Selection follows the model score, spending effort as it goes."""
    scores = np.array([5.0, 1.0, 4.0, 3.0, 2.0])
    loc = np.array([1.0, 50.0, 1.0, 1.0, 1.0])   # total 54, budget 10.8
    top = top_by_effort(scores, loc, FRACTION)
    # order by score = [0, 2, 3, 4, 1]; cumulative LOC 1, 2, 3, 4 -> first four
    assert sorted(top.tolist()) == [0, 2, 3, 4]


def test_effort_is_never_zero_so_budget_is_never_zero():
    """The pipeline floors effort at 1 upstream; the set must stay non-empty."""
    loc = np.array([0.0, 0.0, 0.0, 0.0, 0.0])
    scores = np.array([5.0, 4.0, 3.0, 2.0, 1.0])
    effort = np.maximum(loc, 1.0)
    top = top_by_effort(scores, effort, FRACTION)
    assert top.size >= 1
