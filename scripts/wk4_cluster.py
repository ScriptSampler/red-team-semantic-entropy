"""Week 4 phase B: cluster + entropy on the 2000 question sample set.

Loads only DeBERTa-large-MNLI. Llama is not loaded, so peak VRAM stays
around 1.5 GB.

Resumable: on startup, reads entropy.jsonl for question_ids already
clustered and skips them.

Run after wk4_sample.py has produced samples.jsonl:
    cd "/mnt/i/GITHUBPROJECTS/SE Research"
    source .venv-wsl/bin/activate
    python scripts/wk4_cluster.py
"""
from __future__ import annotations

import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from se.entropy import cluster_and_score
from se.nli import NLI
from se.sampling import DEFAULT_SAMPLES_DIR, iter_sample_records


OUT_DIR = DEFAULT_SAMPLES_DIR / "wk4_full_2000q"
PROGRESS_EVERY = 100


def _completed_ids(jsonl_path: Path) -> set[str]:
    done: set[str] = set()
    if not jsonl_path.exists():
        return done
    with jsonl_path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                obj = json.loads(line)
                done.add(obj["question_id"])
            except Exception:
                pass
    return done


def main() -> int:
    samples_path = OUT_DIR / "samples.jsonl"
    entropy_path = OUT_DIR / "entropy.jsonl"

    if not samples_path.exists():
        print(f"no samples.jsonl at {samples_path}. Run wk4_sample.py first.", file=sys.stderr)
        return 1

    already = _completed_ids(entropy_path)
    print(f"resuming: {len(already)} question_ids already in {entropy_path}", flush=True)

    print("loading DeBERTa-large-MNLI...", flush=True)
    t0 = time.perf_counter()
    nli = NLI()
    print(f"loaded in {time.perf_counter()-t0:.1f}s", flush=True)

    records = [r for r in iter_sample_records(OUT_DIR) if r.question_id not in already]
    print(f"to cluster: {len(records)}", flush=True)

    t_start = time.perf_counter()
    with entropy_path.open("a", encoding="utf-8") as f:
        for i, rec in enumerate(records):
            cs = cluster_and_score(rec.samples, nli)
            obj = {
                "question_id": rec.question_id,
                "greedy_correct": rec.greedy_correct,
                "samples_correct": rec.samples_correct,
                "n_clusters": cs.n_clusters,
                "entropy_nats": cs.entropy_nats,
                "entropy_bits": cs.entropy_bits,
                "assignments": cs.assignments,
            }
            f.write(json.dumps(obj) + "\n")
            f.flush()
            if (i + 1) % PROGRESS_EVERY == 0:
                elapsed = time.perf_counter() - t_start
                per_q = elapsed / (i + 1)
                eta_s = per_q * (len(records) - (i + 1))
                print(f"  {i+1}/{len(records)} clustered in {elapsed:.0f}s "
                      f"({per_q:.2f}s/Q), ETA {eta_s/60:.1f} min", flush=True)

    elapsed = time.perf_counter() - t_start
    print(f"phase B done. {len(records)} questions clustered in {elapsed:.0f}s.", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
