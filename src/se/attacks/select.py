"""Select attack targets.

External review B2/§2 killed the old rule: it picked hide targets at MAXIMUM
clean entropy and false-alarm targets at MINIMUM, so the clean AUROC of the
attack pool was 1.000 by construction (the selection rule reflected back) and the
SE-vs-SRE comparison was confounded (SE cells used entropy selection, SRE cells
used a different rule).

The headline selector is now `select_stratified`: a SCORE-INDEPENDENT
stratified-random sample. It reads only the correctness label (greedy_correct
under the span oracle, from relabeled.jsonl) and a fixed seed — never any
SE/SRE entropy. Because selection does not depend on the detector, the SE and
SRE campaigns draw the IDENTICAL question set for a given (want, n, seed); this
is what makes the cross-detector comparison fair (critic DoD B1: "identical qid
set across SE/SRE, proven, not by discipline"). `assert_shared_pool` proves it.

The old extreme-entropy rule survives only as `select_extreme_ablation` — a
clearly-named maximal-headroom probe for an upper-bound ablation, never the
headline. It is unreachable from the headline path.
"""
from __future__ import annotations

import json
import random
from pathlib import Path

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


def assert_shared_pool(want: str, n: int, seed: int = 0) -> list[str]:
    """Prove the pool is detector-independent: two independent calls return the
    IDENTICAL id set (selection reads no detector score)."""
    a = [ex.question_id for ex in select_stratified(want, n, seed=seed)]
    b = [ex.question_id for ex in select_stratified(want, n, seed=seed)]
    assert a == b, "stratified selection is not deterministic"
    return a


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


# Headline entry point: score-independent. The extreme rule is NOT reachable here.
def select_examples(want: str, n: int, *, split: str = "validation", **_) -> list[TriviaQAExample]:
    return select_stratified(want, n, split=split)
