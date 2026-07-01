"""Select attack targets.

External review B2/§2 killed the old rule: it picked hide targets at MAXIMUM
clean entropy and false-alarm targets at MINIMUM, so the clean AUROC of the
attack pool was 1.000 by construction (the selection rule reflected back) and the
SE-vs-SRE comparison was confounded (SE cells used entropy selection, SRE cells
used a different rule).

The headline selector is now `select_stratified`: a SCORE-INDEPENDENT
stratified-random sample. It reads only the correctness label (greedy_correct
under the span oracle, from relabeled.jsonl) and a fixed seed — never any
SE/SRE entropy.

Cross-detector fairness is ENFORCED, not merely intended. Every campaign cell
routes target selection through `campaign_pool(dataset, want, n, seed)`, which
has NO `detector` parameter — so the SE and SRE cells draw the IDENTICAL id set
BY CONSTRUCTION, not by the discipline of passing matching seeds (critic DoD B1:
"identical qid set across SE/SRE, proven, not by discipline"). `assert_detector_blind`
checks structurally that no selection function can see the detector, and
`assert_shared_pool` confirms two cells consume the same ids. squad (no Week-4
cache) is labelled via a `label_fresh` callback that is likewise detector-blind.

The old extreme-entropy rule survives only as `select_extreme_ablation` — a
clearly-named maximal-headroom probe for an upper-bound ablation, never the
headline. It is unreachable from the headline path.
"""
from __future__ import annotations

import inspect
import json
import random
from pathlib import Path
from typing import Callable

from ..data import TriviaQAExample, load_triviaqa
from ..sampling import DEFAULT_SAMPLES_DIR


WK4_DIR = DEFAULT_SAMPLES_DIR / "wk4_full_2000q"
RELABELED = WK4_DIR / "relabeled.jsonl"          # span-oracle labels (B3 relabel)
ENTROPY = WK4_DIR / "entropy.jsonl"              # for the ablation only


def load_labels(path: Path = RELABELED) -> dict[str, dict]:
    if not path.exists():
        raise FileNotFoundError(
            f"No label file at {path}. Run scripts/relabel_pool.py first."
        )
    out: dict[str, dict] = {}
    for line in path.read_text().splitlines():
        if line.strip():
            obj = json.loads(line)
            out[obj["question_id"]] = obj
    return out


def _stratum_ids(want: str, seed: int, labels: dict) -> list[str]:
    """Score-independent: filter by correctness label only, shuffle by seed.

    Deterministic and detector-independent -> the SE and SRE campaigns get the
    same ids for the same (want, seed)."""
    want_correct = (want == "right")
    ids = sorted(qid for qid, lab in labels.items()
                 if bool(lab["greedy_correct"]) == want_correct)   # NOTE: no entropy read
    rng = random.Random(f"{seed}:{want}")
    rng.shuffle(ids)
    return ids


def select_stratified(
    want: str,                       # "wrong" (Hide) or "right" (False-alarm)
    n: int,
    *,
    seed: int = 0,
    split: str = "validation",
    labels_path: Path = RELABELED,
) -> list[TriviaQAExample]:
    """Score-independent stratified-random sample of the `want` stratum."""
    labels = load_labels(labels_path)
    ids = _stratum_ids(want, seed, labels)[:n]
    by_id = {ex.question_id: ex for ex in load_triviaqa(split=split)}
    examples = [by_id[qid] for qid in ids if qid in by_id]

    # Assert accepted_forms coverage (critic nit): a thin alias set silently
    # under-credits. Fail loud rather than collapse to single-form matching.
    single = sum(1 for ex in examples if len(ex.all_acceptable()) <= 1)
    if single > len(examples) * 0.5:
        raise ValueError(
            f"select_stratified: {single}/{len(examples)} chosen examples have <=1 "
            f"accepted form; alias set looks truncated — refusing to build a pool."
        )
    return examples


# ---- detector-blind campaign pool (external review B1 enforcement) ----------

def campaign_pool(
    dataset: str,                    # "triviaqa" | "squad"
    want: str,                       # "wrong" (Hide) | "right" (False-alarm)
    n: int,
    *,
    seed: int = 0,
    split: str = "validation",
    label_fresh: Callable[[str, int, int], list[TriviaQAExample]] | None = None,
) -> list[TriviaQAExample]:
    """THE selection entry point for a campaign cell — detector-independent.

    This is the enforcement (not the hope) that closes external review B1. The
    pool is a pure function of (dataset, want, n, seed): this function has NO
    `detector` parameter, so the SE cell and the SRE cell of a campaign draw the
    IDENTICAL id set BY CONSTRUCTION, not by discipline. A future re-added
    `if detector == ...` branch cannot live here — there is nothing to branch on.

    triviaqa reads the Week-4 span-oracle cache (CPU, label-free). squad has no
    cache and needs a greedy labelling pass, supplied via `label_fresh(want, n,
    seed)` — itself detector-independent, because greedy correctness under the
    span oracle does not depend on which detector will later score the pool.
    """
    if dataset == "triviaqa":
        return select_stratified(want, n, seed=seed, split=split)
    if dataset == "squad":
        if label_fresh is None:
            raise ValueError(
                "campaign_pool: squad has no Week-4 cache; pass a label_fresh "
                "callback (want, n, seed) -> examples. It MUST NOT read the detector."
            )
        return label_fresh(want, n, seed)
    raise ValueError(f"campaign_pool: unknown dataset {dataset!r}")


def assert_detector_blind() -> None:
    """Enforce structurally that pool selection cannot see the detector: neither
    campaign_pool nor select_stratified may expose a detector-linked parameter.
    Called by tests and by the shared-pool proof so the guarantee is checked, not
    trusted."""
    for fn in (campaign_pool, select_stratified):
        bad = {p for p in inspect.signature(fn).parameters if "detector" in p.lower()}
        if bad:
            raise AssertionError(
                f"{fn.__name__} exposes detector-linked params {bad}; the SE and "
                f"SRE pools could diverge. Selection MUST be detector-independent "
                f"(external review B1)."
            )


def assert_shared_pool(want: str, n: int, seed: int = 0) -> list[str]:
    """Prove the SE and SRE cells consume the IDENTICAL pool.

    Because campaign_pool takes no detector, an "SE cell" and an "SRE cell" are
    the same call for a given (want, n, seed) — identity holds by construction.
    We (1) assert the no-detector property structurally and (2) confirm two cells
    agree on the ids they actually consume."""
    assert_detector_blind()
    se_cell = [ex.question_id for ex in campaign_pool("triviaqa", want, n, seed=seed)]
    sre_cell = [ex.question_id for ex in campaign_pool("triviaqa", want, n, seed=seed)]
    assert se_cell == sre_cell, "SE and SRE cells drew different ids"
    return se_cell


# ---- ablation only: the old maximal-headroom probe (NOT the headline) -------

def select_extreme_ablation(
    want: str, n: int, *, split: str = "validation",
) -> list[TriviaQAExample]:
    """DEPRECATED for the headline. Maximal-headroom probe: hide targets at the
    HIGHEST clean entropy, false-alarm at the LOWEST. Produces the artefactual
    clean AUROC ~1.0 (external review §2). Use ONLY for the labelled upper-bound
    ablation, never the main matrix."""
    labels = load_labels(ENTROPY)  # entropy.jsonl has entropy_nats + greedy_correct
    want_correct = (want == "right")
    rows = [(qid, lab["entropy_nats"]) for qid, lab in labels.items()
            if bool(lab["greedy_correct"]) == want_correct]
    rows.sort(key=lambda r: r[1], reverse=(want == "wrong"))
    by_id = {ex.question_id: ex for ex in load_triviaqa(split=split)}
    return [by_id[qid] for qid, _ in rows[:n] if qid in by_id]


# Single-detector prototype entry point (wk6/wk7). Score-independent; the extreme
# rule is NOT reachable here. `seed` is forwarded EXPLICITLY — no silent **_ drop,
# so a caller can never think it changed the pool while it stayed at the default
# (external review B1: diverging seeds must be visible, not swallowed).
def select_examples(
    want: str, n: int, *, seed: int = 0, split: str = "validation",
) -> list[TriviaQAExample]:
    return select_stratified(want, n, seed=seed, split=split)
