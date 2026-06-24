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
    best_is_feasible: bool = False


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

    # parents: list of (query, obj, parent_index)
    parents: list[tuple[str, float, int]] = [(original_query, base_obj, -1)] * top_N
    traj = [best_obj]
    self_index = 0

    for it in range(max_iteration):
        children: list[Candidate] = []
        for p_query, _p_obj, _p_idx in parents:
            for _ in range(candidate_size_M):
                cand_q = proposer.propose(p_query, lm, temperature=proposer_temperature)
                cand_obj = objective(cand_q)
                n_calls += 1
                self_index += 1
                children.append(Candidate(cand_q, cand_obj, _p_idx if _p_idx >= 0 else 0, self_index))

        # Keep only children that beat the running best objective.
        improved_children = [c for c in children if c.obj > best_obj]

        # Feasibility-check survivors against the ORIGINAL query.
        feasible_candidates: list[Candidate] = []
        for c in improved_children:
            fr = feasibility.check(c.query, original_query, nli, **feas_kw)
            c.feasible = fr.feasible
            if fr.feasible:
                feasible_candidates.append(c)
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
    )
