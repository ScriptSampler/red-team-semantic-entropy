"""Week 3 Wednesday session.

Load DeBERTa-large-MNLI, run a battery of hand-crafted equivalence
pairs to confirm the bidirectional check behaves sensibly, then walk
five real questions from Monday's sample collection and report how the
N=10 samples cluster under NLI.

Hand-crafted pairs cover the standard sanity cases the plan calls for
plus a handful of failure modes I want to know about up front: scoped
quantifiers, dates, negations, partial information.

Output: results/wk3_wed_nli_check.md.
"""
from __future__ import annotations

import sys
import time
from itertools import combinations
from pathlib import Path

import torch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from se.config import RESULTS_DIR
from se.nli import NLI
from se.sampling import DEFAULT_SAMPLES_DIR, iter_sample_records


# (a, b, expected_equivalent, label)
HAND_PAIRS = [
    ("Paris", "the capital of France", True, "synonym/definition"),
    ("Paris", "London", False, "different cities"),
    ("Paris is the capital of France.", "France's capital is Paris.", True, "syntactic paraphrase"),
    ("It is hot today.", "It is not hot today.", False, "negation"),
    ("Albert Einstein", "the physicist who developed relativity", True, "person/description"),
    ("Albert Einstein", "Isaac Newton", False, "different people"),
    ("The book has 200 pages.", "The book has many pages.", False, "specific vs vague"),
    ("World War II ended in 1945.", "World War II ended in the 1940s.", True, "specific implies general"),
    ("World War II ended in the 1940s.", "World War II ended in 1945.", False, "general does not imply specific"),
    ("Cats are mammals.", "All cats are mammals.", True, "scope"),
    ("Some cats are black.", "All cats are black.", False, "scope, existential vs universal"),
    ("The Eiffel Tower is in Paris.", "Paris contains the Eiffel Tower.", True, "active/passive"),
    ("Mount Everest is the tallest mountain.", "Mount Everest is the tallest mountain in the world.", True, "implicit context"),
    ("Canberra is the capital of Australia.", "Sydney is the capital of Australia.", False, "common misconception"),
    ("Sunset Boulevard premiered in 1993.", "Sunset Boulevard, the Lloyd Webber musical, premiered in the US in 1993.", True, "additional consistent detail"),
    # Edge case: NLI may struggle here
    ("The answer is Octopussy.", "Rita Coolidge sang the title song for Octopussy.", False, "premise lacks the artist; expected to fall short of full equivalence"),
]


def main() -> int:
    report: list[str] = []

    def log(line: str = "") -> None:
        print(line, flush=True)
        report.append(line)

    log(f"# Week 3 Wed: NLI bidirectional entailment (DeBERTa-large-MNLI)")
    log(f"GPU: {torch.cuda.get_device_name(0) if torch.cuda.is_available() else 'CPU'}")
    log("")

    log("## Load")
    t0 = time.perf_counter()
    nli = NLI()
    t_load = time.perf_counter() - t0
    vram_mb = torch.cuda.memory_allocated() / 1024**2 if torch.cuda.is_available() else 0.0
    log(f"NLI loaded in {t_load:.1f}s, VRAM {vram_mb:.0f} MB")
    log("")

    log("## Hand-crafted pairs")
    log("Expected column is the human judgement, EQ column is what NLI says, OK if they match.")
    log("")
    log(f"| # | expected | EQ | a -> b (entail prob) | b -> a (entail prob) | category | a / b |")
    log(f"| - | -------- | -- | -------------------- | -------------------- | -------- | ----- |")
    flat_pairs: list[tuple[str, str]] = []
    for a, b, _, _ in HAND_PAIRS:
        flat_pairs.append((a, b))
        flat_pairs.append((b, a))
    flat_results = nli.score_batch(flat_pairs)
    n_correct_hand = 0
    for i, (a, b, expected, category) in enumerate(HAND_PAIRS):
        fwd = flat_results[2 * i]
        rev = flat_results[2 * i + 1]
        eq = (fwd.label == "entailment") and (rev.label == "entailment")
        ok = "ok" if eq == expected else "no"
        if eq == expected:
            n_correct_hand += 1
        log(f"| {i:>2} | {str(expected):>5} | {str(eq):>5} | "
            f"{fwd.label[:5]} {fwd.entail_prob:.2f} | "
            f"{rev.label[:5]} {rev.entail_prob:.2f} | "
            f"{category} | "
            f"{a[:40]} / {b[:40]} |")
    log("")
    log(f"hand-crafted accuracy: {n_correct_hand}/{len(HAND_PAIRS)}")
    log("")

    log("## NLI clustering on five Monday questions")
    log("Picks five from results/wk3_mon_samples_inspect.md to look at, mixing right and wrong cases.")
    log("")
    samples_dir = DEFAULT_SAMPLES_DIR / "wk3_mon_50q"
    records = list(iter_sample_records(samples_dir))
    # Pick: the tc_69 Octopussy case (greedy hallucinated, samples agree) plus four others
    # we want to study: a confident-correct, a confident-wrong, a high-variance, a numeric-answer.
    target_ids = {"tc_69", "tc_2", "tc_79", "tc_149", "tc_165"}
    picked = [r for r in records if r.question_id in target_ids]
    # Stable order by appearance in records.
    log(f"selected {len(picked)} of the 5 target ids found")
    log("")

    for rec in picked:
        log(f"### {rec.question_id}")
        log(f"Q: {rec.question}")
        log(f"canonical: {rec.canonical_answer}")
        log(f"greedy:    {rec.greedy[:120]}{'...' if len(rec.greedy) > 120 else ''}")
        log(f"sample correctness: {sum(rec.samples_correct)}/{len(rec.samples_correct)}")
        log("")

        # Cluster samples by single-link bidirectional equivalence.
        n = len(rec.samples)
        # Pre-compute pairwise equivalence on upper triangle.
        upper_pairs = [(rec.samples[i], rec.samples[j]) for i, j in combinations(range(n), 2)]
        equiv_flags = nli.bidirectional_equivalent_batch(upper_pairs)
        adj = [[False] * n for _ in range(n)]
        for k, (i, j) in enumerate(combinations(range(n), 2)):
            adj[i][j] = adj[j][i] = equiv_flags[k]
        # Union-find clustering.
        parent = list(range(n))
        def find(x):
            while parent[x] != x:
                parent[x] = parent[parent[x]]
                x = parent[x]
            return x
        def union(x, y):
            rx, ry = find(x), find(y)
            if rx != ry:
                parent[rx] = ry
        for i in range(n):
            for j in range(i + 1, n):
                if adj[i][j]:
                    union(i, j)
        clusters: dict[int, list[int]] = {}
        for i in range(n):
            clusters.setdefault(find(i), []).append(i)

        log(f"NLI clusters: {len(clusters)}")
        for cid, members in clusters.items():
            log(f"  cluster of size {len(members)}:")
            for m in members:
                tag = "ok" if rec.samples_correct[m] else "no"
                snippet = rec.samples[m][:100].replace("\n", " ")
                log(f"    [{m}] {tag} {snippet}{'...' if len(rec.samples[m]) > 100 else ''}")
        log("")

    out_path = RESULTS_DIR / "wk3_wed_nli_check.md"
    out_path.write_text("\n".join(report) + "\n")
    print(f"\nWritten to {out_path}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
