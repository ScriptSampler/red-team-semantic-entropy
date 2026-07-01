"""Preflight integrity check for the cached Phase-1 artifacts.

Motivated by the 2026-07-02 loss of ``~/.cache/se-research``: every downstream
number (clean fair AUROC, relabel report, the attack matrix) was computed from
that cache, and its disappearance was only noticed when a re-run failed deep
inside a script. This makes the dependency explicit and fails loud UP FRONT.

Torch-free on purpose so it can run — and be tested — without the GPU stack.
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass
class CacheItem:
    path: Path
    exists: bool
    n_lines: int          # non-empty lines for .jsonl; 0 otherwise
    expect_lines: int | None
    ok: bool
    note: str


def _count_lines(p: Path) -> int:
    n = 0
    with p.open(encoding="utf-8") as f:
        for line in f:
            if line.strip():
                n += 1
    return n


def check_phase1_cache(samples_dir: Path) -> list[CacheItem]:
    """Check the Phase-1 cache under ``samples_dir`` (DEFAULT_SAMPLES_DIR in
    production). One CacheItem per required artifact. A file is OK if it exists
    and is non-empty; the expected line count is informational, not a hard gate,
    so a legitimately re-sized pool does not false-alarm — but a missing or empty
    (e.g. truncated) file fails."""
    wk4 = samples_dir / "wk4_full_2000q"
    specs = [
        (wk4 / "samples.jsonl", 2000),
        (wk4 / "entropy.jsonl", 2000),
        (wk4 / "relabeled.jsonl", 2000),
    ]
    items: list[CacheItem] = []
    for path, expect in specs:
        exists = path.exists()
        if not exists:
            items.append(CacheItem(path, False, 0, expect, False, "MISSING"))
            continue
        n = _count_lines(path)
        if n == 0:
            items.append(CacheItem(path, True, 0, expect, False, "EMPTY"))
            continue
        note = f"{n} lines" + (f" (expected ~{expect})" if expect and n != expect else "")
        items.append(CacheItem(path, True, n, expect, True, note))
    return items


def cache_ok(items) -> bool:
    return all(i.ok for i in items)
