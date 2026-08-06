"""Exchangeable (randomized) tie-breaking — the rule that survives the ceiling."""
from __future__ import annotations

import math
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from se.stats import exceedance_counts, exceedance_counts_randomized

CAP = math.log(10)


def test_tie_credit_shrinks_as_the_attack_puts_more_candidates_on_the_ceiling():
    """THE mechanism: the max VALUE is pinned by the ceiling under any attack strength, so
    the signal is the multiplicity b. More attack candidates at the max => each tied benign
    draw earns less credit => smaller statistic => stronger evidence for the attack."""
    attack = [CAP]
    benign = [[CAP] * 10]                     # every benign draw ties the ceiling
    weak = exceedance_counts_randomized(attack, benign, [1], seed=0)[0][0]
    mid = exceedance_counts_randomized(attack, benign, [9], seed=0)[0][0]
    strong = exceedance_counts_randomized(attack, benign, [99], seed=0)[0][0]
    assert weak == pytest.approx(10 / 2, abs=0.6)      # b=1  -> credit 1/2
    assert mid == pytest.approx(10 / 10, abs=0.4)      # b=9  -> credit 1/10
    assert strong == pytest.approx(10 / 100, abs=0.2)  # b=99 -> credit 1/100
    assert weak > mid > strong


def test_strict_ties_are_recovered_when_nothing_is_tied():
    attack = [0.5]
    benign = [[0.1, 0.6, 0.7]]
    rand = exceedance_counts_randomized(attack, benign, [5], seed=0)
    strict = exceedance_counts(attack, benign, ties="strict")
    assert rand[0][0] == pytest.approx(float(strict[0][0]))
    assert rand[0][1] == strict[0][1] == 3


def test_sits_between_strict_and_conservative():
    """Randomized must never be more extreme than either disqualified rule."""
    attack = [CAP]
    benign = [[CAP, CAP, 0.1]]
    strict = exceedance_counts(attack, benign, ties="strict")[0][0]          # 0
    cons = exceedance_counts(attack, benign, ties="conservative")[0][0]      # 2
    rand = exceedance_counts_randomized(attack, benign, [20], seed=0)[0][0]
    assert strict <= rand <= cons


def test_b_is_clamped_and_empty_benign_skipped():
    attack = [CAP, CAP]
    benign = [[CAP], []]
    got = exceedance_counts_randomized(attack, benign, [0, 5], seed=0)
    assert len(got) == 1                       # empty benign list dropped
    assert got[0][0] <= 1.0                    # b clamped to >=1 -> credit <= 1/2 each
