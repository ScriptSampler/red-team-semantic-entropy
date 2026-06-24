"""Self-Reflective / Semantic Reformulation Entropy (Tong et al. 2025).

Reference: arXiv 2509.17445. SRE augments vanilla SE with input-side
reformulation. The procedure we reproduce:

  1. Generate N_reform paraphrases of the question (the original is NOT
     included, per the paper).
  2. For each reformulation, draw K samples at temperature T.
  3. Pool all N_reform * K samples into one set and cluster them jointly
     by semantic equivalence, then compute a single Shannon entropy over
     the cluster sizes.

The paper aggregates by pooling-then-one-entropy, not by averaging the
per-reformulation entropies; we follow that.

Deviations from the paper, documented honestly because SRE is a victim
method in this project, not our contribution:

  - Clustering backend. The paper uses a progressive energy-based hybrid
    clustering (exact match -> embedding similarity > 0.92 -> NLI
    bidirectional entailment -> energy boundary refinement). We use exact
    normalised-string pre-merge followed by NLI bidirectional union-find,
    which is the semantic core of their HSC. The energy refinement stage
    is left as future work. If the Week 8 AUROC lands far from the paper's
    0.871 on TriviaQA, this is the first thing to revisit.
  - Reformulation filter. The paper keeps paraphrases with cosine
    similarity to the original in [0.6, 0.95] using a sentence embedder.
    To avoid a third resident model under the 16 GB VRAM budget, we filter
    with NLI instead: a reformulation is kept if it is not NLI-contradictory
    with the original in either direction. Configurable.
"""
from __future__ import annotations

from dataclasses import dataclass, field

import torch

from . import model as M
from .config import GenConfig
from .entropy import discrete_entropy
from .nli import NLI
from .scoring import normalise


# Few-shot-ish instruction; kept simple and open-ended (no MC choices,
# unlike SECA's MMLU proposer).
_REFORM_SYSTEM = "You rewrite questions while preserving their exact meaning."
_REFORM_INSTRUCTION = (
    "Rewrite the question below as a single, semantically equivalent question. "
    "Keep the meaning and the correct answer identical. Do not answer it. "
    "Return only the rewritten question, nothing else.\n\nQuestion: {q}"
)


@dataclass
class SREResult:
    question: str
    reformulations: list[str]
    entropy_nats: float
    n_clusters: int
    n_pooled_samples: int
    pooled_samples: list[str] = field(default_factory=list)


@torch.no_grad()
def generate_reformulations(
    question: str,
    lm: M.LoadedModel,
    nli: NLI,
    n_reform: int = 3,
    *,
    max_new_tokens: int = 48,
    temperature: float = 1.0,
    keep_non_contradictory: bool = True,
    max_tries: int | None = None,
) -> list[str]:
    """Produce up to n_reform paraphrases of the question.

    Uses Llama itself as the paraphraser. Reformulations equal to the
    original (after normalisation) or duplicates are dropped. If
    keep_non_contradictory, a reformulation is also dropped when NLI calls
    either direction against the original a contradiction.
    """
    max_tries = max_tries or (n_reform * 4)
    prompt = _REFORM_INSTRUCTION.format(q=question)
    gen = GenConfig(max_new_tokens=max_new_tokens, temperature=temperature,
                    top_p=1.0, n_samples=1)

    kept: list[str] = []
    seen = {normalise(question)}
    tries = 0
    while len(kept) < n_reform and tries < max_tries:
        tries += 1
        cand = M.generate_one(lm, prompt, gen).strip().strip('"').strip()
        key = normalise(cand)
        if not key or key in seen:
            continue
        if keep_non_contradictory:
            res = nli.score_batch([(question, cand), (cand, question)])
            if res[0].label == "contradiction" or res[1].label == "contradiction":
                continue
        seen.add(key)
        kept.append(cand)
    return kept


@torch.no_grad()
def self_reflective_entropy(
    question: str,
    lm: M.LoadedModel,
    nli: NLI,
    *,
    n_reform: int = 3,
    k_samples: int = 8,
    temperature: float = 0.8,
    max_new_tokens: int = 48,
    reformulations: list[str] | None = None,
) -> SREResult:
    """Compute SRE for a question.

    If reformulations is given, those are used directly (useful when the
    attack has already chosen the input variants); otherwise they are
    generated. The original question is not included in the reformulation
    set, matching the paper.
    """
    if reformulations is None:
        reformulations = generate_reformulations(
            question, lm, nli, n_reform=n_reform, temperature=1.0
        )
    # If reformulation generation failed entirely, fall back to the
    # original question so SRE still returns a defined score.
    variants = reformulations if reformulations else [question]

    gen = GenConfig(max_new_tokens=max_new_tokens, temperature=temperature,
                    top_p=1.0, n_samples=k_samples)

    pooled: list[str] = []
    for variant in variants:
        pooled.extend(M.generate_samples(lm, variant, gen))

    assignments = _cluster_pooled(pooled, nli)
    return SREResult(
        question=question,
        reformulations=reformulations,
        entropy_nats=discrete_entropy(assignments, "nats"),
        n_clusters=len(set(assignments)),
        n_pooled_samples=len(pooled),
        pooled_samples=pooled,
    )


def _cluster_pooled(samples: list[str], nli: NLI) -> list[int]:
    """Exact normalised-string pre-merge, then NLI bidirectional union-find.

    The pre-merge collapses identical answers cheaply before paying for the
    O(n^2) NLI pass, which matters because pooling N*K samples (24 by
    default) is larger than vanilla SE's N=10.
    """
    from itertools import combinations

    n = len(samples)
    if n <= 1:
        return list(range(n))

    # Pre-merge exact normalised duplicates into representative groups.
    norm = [normalise(s) for s in samples]
    rep_of: dict[str, int] = {}
    group_id = [0] * n
    next_id = 0
    for i, key in enumerate(norm):
        if key not in rep_of:
            rep_of[key] = next_id
            next_id += 1
        group_id[i] = rep_of[key]

    # One representative index per pre-merge group for the NLI pass.
    reps: dict[int, int] = {}
    for i, g in enumerate(group_id):
        reps.setdefault(g, i)
    rep_indices = sorted(reps.values())
    m = len(rep_indices)
    if m <= 1:
        return [0] * n

    pairs = [(samples[rep_indices[a]], samples[rep_indices[b]])
             for a, b in combinations(range(m), 2)]
    equiv = nli.bidirectional_equivalent_batch(pairs)

    parent = list(range(m))

    def find(x: int) -> int:
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    def union(x: int, y: int) -> None:
        rx, ry = find(x), find(y)
        if rx != ry:
            parent[rx] = ry

    for k, (a, b) in enumerate(combinations(range(m), 2)):
        if equiv[k]:
            union(a, b)

    # Map every sample: pre-merge group -> representative position -> cluster.
    pos_of_group = {g: pos for pos, g in enumerate(sorted(reps))}
    cluster_of_pos = [find(p) for p in range(m)]
    remap: dict[int, int] = {}
    out: list[int] = []
    for g in group_id:
        pos = pos_of_group[g]
        root = cluster_of_pos[pos]
        if root not in remap:
            remap[root] = len(remap)
        out.append(remap[root])
    return out
