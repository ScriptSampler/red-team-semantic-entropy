"""Preflight: verify the Phase-1 cache exists before any downstream run.

    python scripts/preflight.py

Exit 0 if the cached samples/entropy/relabeled artifacts are present and
non-empty; exit 1 (with a clear message) otherwise. Run this before relabel /
fair-pool / the attack matrix so a missing cache fails loud immediately rather
than deep inside a multi-hour script. See results/OVERNIGHT_2026-07-02.md for the
2026-07-02 cache loss that motivated it.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from se.sampling import DEFAULT_SAMPLES_DIR
from se.cache_check import check_phase1_cache, cache_ok


def main() -> int:
    items = check_phase1_cache(DEFAULT_SAMPLES_DIR)
    print(f"Phase-1 cache preflight - {DEFAULT_SAMPLES_DIR}")
    for i in items:
        print(f"  [{'OK  ' if i.ok else 'FAIL'}] {i.path.name}: {i.note}")
    if not cache_ok(items):
        print("\nPREFLIGHT FAILED: the Phase-1 cache is missing or empty. Target "
              "selection (relabeled.jsonl) and post-attack scoring cannot run. "
              "Regenerate via the Phase-1 sampling pass on the GPU, then relabel. "
              "See results/OVERNIGHT_2026-07-02.md.")
        return 1
    print("\nPreflight OK: Phase-1 cache present.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
