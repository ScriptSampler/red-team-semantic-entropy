"""The batched judge path must produce IDENTICAL clusters to the unbatched path for a
deterministic judge (the only remaining difference is batched-generation numerics, which
scripts/probe_batched_judge.py checks on the GPU). Pure CPU, mock judges — no models."""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from se.entropy import (cluster_samples_judge, cluster_samples_judge_batched,
                        cluster_and_score_judge, cluster_and_score_judge_batched)
from se.judge import make_judge_fn, make_batched_judge_fn, _PROMPT


def _rule(a: str, b: str) -> bool:
    """Mock ground-truth equivalence: same team-token => same answer."""
    def team(x):
        x = x.lower()
        return "broncos" if "broncos" in x else "nuggets" if "nuggets" in x else x
    return team(a) == team(b)


SAMPLES = ["Denver Broncos", "the Broncos", "Broncos", "Denver Nuggets", "Nuggets", "Broncos"]


def test_batched_clusters_equal_unbatched():
    judge_fn = lambda a, b: _rule(a, b)                       # noqa: E731
    judge_pairs = lambda pairs: [_rule(a, b) for a, b in pairs]  # noqa: E731
    assert (cluster_samples_judge_batched(SAMPLES, judge_pairs)
            == cluster_samples_judge(SAMPLES, judge_fn))
    # and the derived entropy matches exactly
    a = cluster_and_score_judge(SAMPLES, judge_fn)
    b = cluster_and_score_judge_batched(SAMPLES, judge_pairs)
    assert a.n_clusters == b.n_clusters
    assert abs(a.entropy_nats - b.entropy_nats) < 1e-12


def test_singletons_and_all_equal_edge_cases():
    alldiff = ["a", "b", "c", "d"]
    assert cluster_samples_judge_batched(alldiff, lambda ps: [False] * len(ps)) == [0, 1, 2, 3]
    allsame = ["x", "x", "x"]
    got = cluster_samples_judge_batched(allsame, lambda ps: [True] * len(ps))
    assert len(set(got)) == 1
    assert cluster_samples_judge_batched(["only"], lambda ps: []) == [0]  # n<=1: no pairs


def _extract(prompt: str):
    seg = prompt.rsplit("Answer 1: ", 1)[1]
    a, rest = seg.split(" | Answer 2: ", 1)
    return a.strip(), rest.split(" ->", 1)[0].strip()


def test_batched_judge_fn_matches_unbatched_and_is_symmetric():
    # A generate_fn that says "yes" only for the ordered pair (X, Y) — asymmetric on purpose.
    def gen_one(prompt: str) -> str:
        a, b = _extract(prompt)
        return "yes" if (a, b) == ("X", "Y") else "no"

    def gen_batch(prompts):
        return [gen_one(p) for p in prompts]

    pairs = [("X", "Y"), ("P", "P")]
    # unbatched symmetric judge: (X,Y) fails because (Y,X) says no; (P,P) also asymmetric-> no
    jf = make_judge_fn(gen_one, symmetric=True)
    jp = make_batched_judge_fn(gen_batch, symmetric=True)
    unb = [jf(a, b) for a, b in pairs]
    bat = jp(pairs)
    assert bat == unb == [False, False]        # symmetric AND-logic drops the asymmetric yes

    # asymmetric mode keeps the single-direction yes, and batched == unbatched
    jf_a = make_judge_fn(gen_one, symmetric=False)
    jp_a = make_batched_judge_fn(gen_batch, symmetric=False)
    assert jp_a(pairs) == [jf_a(a, b) for a, b in pairs] == [True, False]
    assert jp([]) == []                        # empty pair list
