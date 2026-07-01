"""Tests for the Phase-1 cache preflight check. Hermetic (tmp dirs, no torch)."""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from se.cache_check import check_phase1_cache, cache_ok


def _make_cache(base: Path, *, samples=3, entropy=3, relabeled=3):
    wk4 = base / "wk4_full_2000q"
    wk4.mkdir(parents=True)
    for name, n in [("samples.jsonl", samples), ("entropy.jsonl", entropy),
                    ("relabeled.jsonl", relabeled)]:
        if n is None:
            continue   # omit the file entirely
        (wk4 / name).write_text("\n".join('{"x":1}' for _ in range(n)) + "\n")
    return base


def test_all_present_is_ok(tmp_path):
    items = check_phase1_cache(_make_cache(tmp_path))
    assert cache_ok(items)
    assert all(i.exists and i.ok for i in items)


def test_missing_file_fails(tmp_path):
    _make_cache(tmp_path, relabeled=None)   # no relabeled.jsonl
    items = check_phase1_cache(tmp_path)
    assert not cache_ok(items)
    bad = [i for i in items if not i.ok]
    assert len(bad) == 1 and bad[0].path.name == "relabeled.jsonl"
    assert bad[0].note == "MISSING"


def test_empty_file_fails(tmp_path):
    _make_cache(tmp_path, entropy=0)        # entropy.jsonl exists but empty
    items = check_phase1_cache(tmp_path)
    assert not cache_ok(items)
    bad = [i for i in items if not i.ok]
    assert bad[0].path.name == "entropy.jsonl" and bad[0].note == "EMPTY"


def test_missing_dir_fails_all(tmp_path):
    items = check_phase1_cache(tmp_path)    # nothing created
    assert not cache_ok(items)
    assert all(not i.exists for i in items)
    assert len(items) == 3


def test_line_count_mismatch_is_informational_not_fatal(tmp_path):
    _make_cache(tmp_path, samples=5)        # 5 != expected 2000, but non-empty
    items = check_phase1_cache(tmp_path)
    assert cache_ok(items)                  # still OK — soft check, not a hard gate
    s = [i for i in items if i.path.name == "samples.jsonl"][0]
    assert "expected" in s.note
