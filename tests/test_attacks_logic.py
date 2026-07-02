"""CPU-only logic tests for the SE/attack machinery.

No real models. Fakes stand in for Llama and DeBERTa so we can verify the
algorithms (entropy, clustering, the optimiser beam search, feasibility,
SRE pooling) without GPU. Run:

    cd "/mnt/i/GITHUBPROJECTS/SE Research"
    source .venv-wsl/bin/activate
    python -m pytest tests/test_attacks_logic.py -v
"""
from __future__ import annotations

import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from se.entropy import discrete_entropy, cluster_samples
from se.nli import NLIResult
from se.attacks import feasibility, optimizer
from se.attacks import proposer as proposer_mod
from se.attacks.proposer import seed_proposer, _instruction


def test_proposer_instruction_is_reproducible_when_seeded():
    # external review B7 (finding 6): seeded instruction RNG -> reproducible
    # candidate prompts. Same seed -> same sequence; different seed -> differs.
    seed_proposer(0)
    a = [_instruction() for _ in range(8)]
    seed_proposer(0)
    b = [_instruction() for _ in range(8)]
    assert a == b
    seed_proposer(1)
    c = [_instruction() for _ in range(8)]
    assert a != c    # a different seed explores different templates


# ---- Fakes -----------------------------------------------------------------

import re as _re
_WORD = _re.compile(r"[a-z0-9]+")


class FakeNLI:
    """Equivalence = identical first alphanumeric word. Deterministic.

    Uses a punctuation-insensitive first token so it stands in for a real
    NLI model that would not care about a trailing comma.
    """

    def _first(self, s: str) -> str:
        m = _WORD.findall(s.lower())
        return m[0] if m else ""

    def _eq(self, a: str, b: str) -> bool:
        return self._first(a) == self._first(b)

    def bidirectional_equivalent(self, a: str, b: str) -> bool:
        return self._eq(a, b)

    def bidirectional_equivalent_batch(self, pairs, batch_size: int = 64):
        return [self._eq(a, b) for a, b in pairs]

    def score_batch(self, pairs, batch_size: int = 64):
        out = []
        for a, b in pairs:
            if self._eq(a, b):
                out.append(NLIResult("entailment", 0.0, 0.0, 1.0))
            else:
                out.append(NLIResult("neutral", 0.1, 0.8, 0.1))
        return out


# ---- discrete_entropy ------------------------------------------------------

def test_entropy_all_same_is_zero():
    assert discrete_entropy([0, 0, 0, 0]) == 0.0


def test_entropy_uniform_is_log_k():
    # Four singleton clusters -> entropy = ln(4).
    h = discrete_entropy([0, 1, 2, 3])
    assert abs(h - math.log(4)) < 1e-9


def test_entropy_bits_base():
    # Two equal clusters -> 1 bit.
    h = discrete_entropy([0, 0, 1, 1], base="bits")
    assert abs(h - 1.0) < 1e-9


# ---- cluster_samples -------------------------------------------------------

def test_cluster_groups_by_first_word():
    nli = FakeNLI()
    samples = ["Paris is nice", "Paris rocks", "London fog", "London bridge", "Berlin wall"]
    assignments = cluster_samples(samples, nli)
    # Paris*2, London*2, Berlin*1 -> 3 clusters
    assert len(set(assignments)) == 3
    assert assignments[0] == assignments[1]      # both Paris
    assert assignments[2] == assignments[3]      # both London
    assert assignments[4] not in (assignments[0], assignments[2])


def test_cluster_singletons_max_entropy():
    nli = FakeNLI()
    samples = ["alpha", "bravo", "charlie", "delta"]
    assignments = cluster_samples(samples, nli)
    assert len(set(assignments)) == 4
    assert abs(discrete_entropy(assignments) - math.log(4)) < 1e-9


# ---- feasibility -----------------------------------------------------------

def test_feasibility_rejects_noop():
    nli = FakeNLI()
    fr = feasibility.check("What is the capital?", "What is the capital?", nli)
    assert not fr.feasible
    assert fr.is_noop


def test_feasibility_rejects_length_outlier():
    nli = FakeNLI()
    long = "What " + "very " * 50 + "long"
    fr = feasibility.check(long, "What short", nli)
    assert not fr.feasible
    assert not fr.length_ok


def test_feasibility_accepts_equivalent_different():
    nli = FakeNLI()
    # Same first word "What" -> FakeNLI calls equivalent; different text; sane length.
    fr = feasibility.check("What is the capital city?", "What is the capital?", nli)
    assert fr.feasible


def test_feasibility_rejects_nonequivalent():
    nli = FakeNLI()
    fr = feasibility.check("Where is the capital?", "What is the capital?", nli)
    assert not fr.feasible


# ---- optimizer -------------------------------------------------------------

def test_optimizer_maximises_feasible_objective(monkeypatch):
    """A scripted proposer + objective; the optimiser must find the best
    feasible candidate and stop at termination."""
    nli = FakeNLI()

    # Objective: longer "What ..." queries score higher. All share first word
    # "What" so FakeNLI treats every candidate as equivalent to the original.
    def objective(q: str) -> float:
        return float(len(q))

    # Scripted proposer: each call appends a word, staying within length gate.
    counter = {"n": 0}
    base = "What is it"
    def fake_propose(query, lm, **kw):
        counter["n"] += 1
        # Keep first word "What", grow modestly so length ratio stays < 2.5.
        return "What is it " + ("x" * (counter["n"] % 5 + 1))

    monkeypatch.setattr(proposer_mod, "propose", fake_propose)

    result = optimizer.optimize(
        base, objective, lm=None, nli=nli,
        max_iteration=3, candidate_size_M=2, top_N=2,
    )
    # Best objective should be at least the base; improvement is possible.
    assert result.best_obj >= result.original_obj
    assert result.n_objective_calls > 1
    assert len(result.trajectory_best_obj) >= 2


def test_optimizer_noimprove_keeps_original(monkeypatch):
    nli = FakeNLI()

    # Objective always worse than base -> nothing beats best -> original kept.
    def objective(q: str) -> float:
        return 0.0 if q != "BASE QUERY" else 100.0

    monkeypatch.setattr(proposer_mod, "propose",
                        lambda query, lm, **kw: "BASE variant text")

    result = optimizer.optimize(
        "BASE QUERY", objective, lm=None, nli=nli,
        max_iteration=2, candidate_size_M=2, top_N=2,
    )
    assert result.best_query == "BASE QUERY"
    assert not result.improved


def test_optimizer_termination_short_circuits(monkeypatch):
    nli = FakeNLI()

    def objective(q: str) -> float:
        return float(len(q))

    # Candidate stays within the feasibility length gate (ratio < 2.5) and
    # keeps the first word, so it is accepted; its objective crosses the
    # termination threshold on the first iteration.
    base = "BASE QUERY HERE"           # len 15
    monkeypatch.setattr(proposer_mod, "propose",
                        lambda query, lm, **kw: "BASE QUERY HERE EXTENDED")  # len 24

    result = optimizer.optimize(
        base, objective, lm=None, nli=nli,
        max_iteration=50, candidate_size_M=1, top_N=1,
        termination_obj=20.0,
    )
    # Should terminate well before 50 iterations once obj crosses 20.
    assert result.n_iterations_run < 50
    assert result.improved


# ---- optimizer keeps the MAX feasible candidate (guard regression) ---------

def test_optimizer_keeps_max_not_last(monkeypatch):
    """Two feasible candidates in one iteration, the second lower than the
    first. best_query must be the higher one. This locks the in-loop guard
    in optimizer.py: removing it would make best_query the LAST candidate."""
    nli = FakeNLI()

    def objective(q: str) -> float:
        return float(len(q))

    # All three share first word "WHAT" (FakeNLI -> equivalent) and both
    # candidates sit inside the feasibility length band [0.4, 2.5] x base.
    base = "WHAT is the capital?"            # len 20
    higher = "WHAT is the capital city here"  # len 29 (ratio 1.45), obj 29
    lower = "WHAT is the capital too"         # len 23 (ratio 1.15), obj 23
    seq = iter([higher, lower])
    monkeypatch.setattr(proposer_mod, "propose",
                        lambda query, lm, **kw: next(seq))

    result = optimizer.optimize(
        base, objective, lm=None, nli=nli,
        max_iteration=1, candidate_size_M=2, top_N=1,
    )
    assert result.best_obj == float(len(higher))   # the MAX, not the last
    assert result.best_query == higher


# ---- proposer label stripping ----------------------------------------------

def test_proposer_strips_known_labels(monkeypatch):
    import se.model as model_mod
    from se.attacks import proposer

    # "New question:" label should be stripped.
    monkeypatch.setattr(model_mod, "generate_one",
                        lambda lm, prompt, gen: 'New question: What is the capital?')
    out = proposer.propose("Where is the capital?", lm=None)
    assert out == "What is the capital?"


def test_proposer_preserves_legitimate_colon(monkeypatch):
    import se.model as model_mod
    from se.attacks import proposer

    # A real question that happens to start "In 1969:" must NOT be stripped.
    q = "In 1969: which mission landed humans on the Moon?"
    monkeypatch.setattr(model_mod, "generate_one", lambda lm, prompt, gen: q)
    out = proposer.propose("What 1969 mission landed on the Moon?", lm=None)
    assert out == q


# ---- SRE pooled clustering -------------------------------------------------

def test_sre_pooled_clustering():
    from se.sre import _cluster_pooled
    nli = FakeNLI()
    pooled = ["Canberra is the capital", "Canberra, yes", "Sydney maybe",
              "Sydney is it", "Melbourne perhaps"]
    assignments = _cluster_pooled(pooled, nli)
    # Canberra*2, Sydney*2, Melbourne*1 -> 3 clusters
    assert len(set(assignments)) == 3
