"""Objective-agnostic zeroth-order beam search.

This is the SECA optimisation loop (src/seca.py) generalised. SECA hard-codes
its objective (target-choice confidence) and its MMLU prompt scaffolding; here
the objective is any callable str -> float that the search MAXIMISES, and the
candidate generator and feasibility gate are injected.

Per iteration, mirroring SECA:
  - for each of the top_N parents, propose M paraphrase children
  - score every child with the objective
  - keep children that beat the running best
  - feasibility-check the survivors (semantic equivalence to the ORIGINAL,
    not to the parent, so drift cannot accumulate across iterations)
  - the next parents are the top feasible candidates, back-filled from the
    previous parents if too few survive
  - stop early if the best objective crosses a threshold

Direction is encoded in the objective sign by the caller: the Hide attack
passes an objective that returns -entropy (so maximising it minimises SE);
the False-alarm attack passes +entropy.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable

from .. import model as M
from ..nli import NLI
from . import feasibility, proposer


# An objective maps a question string to a scalar to be maximised.
Objective = Callable[[str], float]


@dataclass
class Candidate:
    query: str
    obj: float
    parent_index: int
    index: int
    feasible: bool | None = None


@dataclass
class AttackResult:
    original_query: str
    original_obj: float
    best_query: str
    best_obj: float
    improved: bool                 # best_query differs from original and is feasible
    n_iterations_run: int
    n_objective_calls: int
    trajectory_best_obj: list[float] = field(default_factory=list)
    # NOTE: best_is_feasible is True BY CONSTRUCTION — the final best_query is either the
    # original (trivially equivalent to itself) or a candidate that already passed the gate,
    # so this flag can never be False. It is NOT a measurement of gate behaviour; use the
    # per-candidate counters below for that (critique_log 22).
    best_is_feasible: bool = False
    n_feasibility_checks: int = 0     # candidates submitted to the equivalence gate
    n_feasibility_passed: int = 0     # of those, how many the gate admitted
    # TIE MULTIPLICITY AT THE MAXIMUM (critique_log 26). Under the log(N) ceiling the
    # attack's max VALUE is pinned and carries no signal, but the NUMBER of feasible
    # candidates achieving it does: a stronger attack puts more candidates on the ceiling,
    # which shrinks the 1/(b+1) credit each tied benign draw receives in the exceedance
    # test. This count is `b`, and it cannot be estimated from benign data without
    # assuming H0 and destroying the signal — so it must be recorded here.
    n_feasible_at_best: int = 0       # feasible candidates whose objective == best_obj
    feasible_objs: list[float] = field(default_factory=list)   # all feasible objectives


def optimize(
    original_query: str,
    objective: Objective,
    lm: M.LoadedModel,
    nli: NLI,
    *,
    max_iteration: int = 20,
    candidate_size_M: int = 3,
    top_N: int = 3,
    termination_obj: float | None = None,
    feasibility_kwargs: dict | None = None,
    proposer_temperature: float = 1.0,
    verbose: bool = False,
) -> AttackResult:
    feas_kw = feasibility_kwargs or {}

    base_obj = objective(original_query)
    n_calls = 1
    best_query = original_query
    best_obj = base_obj
    best_feasible = True  # the original is trivially equivalent to itself

    # parents: list of (query, obj, OWN_index). The original has no index of its
    # own, so it uses -1 as a sentinel meaning "index 0". new_parents (built below
    # from feasible_candidates) stores each candidate's OWN c.index here, so a
    # child records its PARENT's own index as parent_index — not the grandparent's.
    parents: list[tuple[str, float, int]] = [(original_query, base_obj, -1)] * top_N
    traj = [best_obj]
    self_index = 0
    n_checks = 0
    n_passed = 0
    feasible_objs: list[float] = []

    for it in range(max_iteration):
        children: list[Candidate] = []
        for p_query, _p_obj, parent_own_idx in parents:
            for _ in range(candidate_size_M):
                cand_q = proposer.propose(p_query, lm, temperature=proposer_temperature)
                cand_obj = objective(cand_q)
                n_calls += 1
                self_index += 1
                # parent_index = the parent's OWN index (original -> 0 via sentinel).
                children.append(Candidate(cand_q, cand_obj,
                                          parent_own_idx if parent_own_idx >= 0 else 0,
                                          self_index))

        # Candidates that MATCH the running best are kept, not just those that beat it.
        # Under the log(N) ceiling the best is pinned early and everything afterwards ties
        # it; the old strict `>` discarded those before the feasibility gate, which is why
        # the tie multiplicity `b` was unobservable. Ties cost one extra NLI check each
        # (cheap next to the 10 generations already spent scoring the candidate) and they
        # are the signal-carrying quantity (critique_log 26).
        improved_children = [c for c in children if c.obj >= best_obj]

        # Feasibility-check survivors against the ORIGINAL query.
        feasible_candidates: list[Candidate] = []
        for c in improved_children:
            fr = feasibility.check(c.query, original_query, nli, **feas_kw)
            c.feasible = fr.feasible
            n_checks += 1
            n_passed += int(bool(fr.feasible))
            if fr.feasible:
                feasible_candidates.append(c)
                feasible_objs.append(float(c.obj))
                # This guard is NOT redundant with the improved_children filter
                # above: that filter used best_obj's PRE-LOOP value, but best_obj
                # rises as we accept candidates within this loop. The guard keeps
                # best_query tracking the MAXIMUM feasible candidate, not the last
                # one. Dropping it would let a later, lower-obj feasible candidate
                # overwrite the best.
                if c.obj >= best_obj:
                    best_obj = c.obj
                    best_query = c.query
                    best_feasible = True

        # Next parents: top feasible candidates, back-filled from prior parents.
        feasible_candidates.sort(key=lambda c: c.obj, reverse=True)
        new_parents = [(c.query, c.obj, c.index) for c in feasible_candidates[:top_N]]
        if len(new_parents) < top_N:
            prior_sorted = sorted(parents, key=lambda t: t[1], reverse=True)
            new_parents += prior_sorted[: top_N - len(new_parents)]
        parents = new_parents

        traj.append(best_obj)
        if verbose:
            print(f"iter {it}: best_obj={best_obj:.4f}, "
                  f"feasible_this_iter={len(feasible_candidates)}", flush=True)

        if termination_obj is not None and best_obj >= termination_obj:
            if verbose:
                print(f"termination: best_obj {best_obj:.4f} >= {termination_obj}", flush=True)
            break

    improved = (best_query != original_query) and best_feasible
    return AttackResult(
        original_query=original_query,
        original_obj=base_obj,
        best_query=best_query,
        best_obj=best_obj,
        improved=improved,
        n_iterations_run=it + 1,
        n_objective_calls=n_calls,
        trajectory_best_obj=traj,
        best_is_feasible=best_feasible,
        n_feasibility_checks=n_checks,
        n_feasibility_passed=n_passed,
        n_feasible_at_best=sum(1 for o in feasible_objs if abs(o - best_obj) <= 1e-9),
        feasible_objs=feasible_objs,
    )
