"""Tests for scripts/prepare_equivalence_audit.py — synthetic outcomes, no models.

The properties under test are the ones that make the audit *mean* something:
stratification matches the harness's own success definition, the annotator's sheet
carries no provenance cue, the draw is reproducible under a seed, and the key can be
joined back to reconstruct every pair.
"""
from __future__ import annotations

import csv
import importlib.util
import json
from pathlib import Path

_spec = importlib.util.spec_from_file_location(
    "prepare_equivalence_audit",
    Path(__file__).resolve().parent.parent / "scripts" / "prepare_equivalence_audit.py")
pea = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(pea)


# ---------------------------------------------------------------------------
# Synthetic pool. Mirrors se/attacks/harness.py:
#   success == entropy_and_feasible and status_held
#   status_held / correct_under_q_prime are only MEASURED when entropy_and_feasible
# Counts are deliberately uneven so proportional bugs show up.
# ---------------------------------------------------------------------------
_TOPICS = ["the capital of Peru", "the boiling point of mercury", "who wrote Ulysses",
           "the longest river in Asia", "the atomic number of tin", "Wimbledon 1987",
           "the currency of Ghana", "the tallest building in Chicago",
           "the composer of Nabucco", "the depth of the Mariana Trench",
           "the first man on the Moon", "the flag of Nepal"]


def _rec(qid, attack, *, idx=0, ef, held, noop=False, feasible=True):
    """One synthetic outcome.

    `idx` (not the qid) drives the question text: varied topics so catch trials, which
    reject overlapping pairs, are not starved; unique so no question repeats; and free
    of the question_id, because a real question never contains one and the blinding
    test asserts none reaches the sheet.
    """
    topic = _TOPICS[idx % len(_TOPICS)]
    q = f"What is {topic}, variant {idx}?"
    return {
        "question_id": qid, "attack": attack, "detector": "se",
        "question": q,
        "best_query": q if noop else f"Concerning {topic}, which variant {idx} applies?",
        "feasible": feasible, "improved": True,
        "entropy_and_feasible": ef,
        "status_held": held if ef else True,
        "correct_under_q_prime": (held if attack == "false_alarm" else not held) if ef else False,
        "frac_correct_under_q_prime": 0.7 if ef else -1.0,
        "success": bool(ef and held),
        "answer_under_q_prime": f"Answer for {qid}",
        "entropy_before": 1.0, "entropy_after": 1.5, "delta": 0.5,
    }


def _pool():
    """Fixed construction order, so `idx` — and therefore the whole fixture — is
    deterministic across calls."""
    spec = ([("fw", "false_alarm", True, True, False, True)] * 14
            + [("hw", "hide", True, True, False, True)] * 9
            + [("ff", "false_alarm", True, False, False, True)] * 3
            + [("hf", "hide", True, False, False, True)] * 5
            + [("fs", "false_alarm", False, True, False, True)] * 7
            + [("hs", "hide", False, True, False, True)] * 4
            # unauditable -> catch-trial material: no-ops and a never-feasible record
            + [("no", "false_alarm", False, True, True, True)] * 10
            + [("nf", "hide", False, True, False, False)])
    recs, seen = [], {}
    for idx, (pre, attack, ef, held, noop, feasible) in enumerate(spec):
        n = seen[pre] = seen.get(pre, -1) + 1
        recs.append(_rec(f"{pre}{n}", attack, idx=idx, ef=ef, held=held,
                         noop=noop, feasible=feasible))
    return recs


# distinct topics so catch trials clear the overlap filter
def _distinct_unauditable(n):
    out = []
    for i in range(n):
        q = f"What is {_TOPICS[i % len(_TOPICS)]}, variant {i}?"
        out.append({"question_id": f"u{i}", "attack": "hide", "detector": "se",
                    "question": q, "best_query": q, "feasible": True,
                    "entropy_and_feasible": False, "status_held": True,
                    "correct_under_q_prime": False, "success": False,
                    "source_file": "s.jsonl"})
    return out


def _write_pool(tmp_path, recs, name="triviaqa_se_all.jsonl"):
    p = tmp_path / name
    p.write_text("\n".join(json.dumps(r) for r in recs), encoding="utf-8")
    return p


def _built(seed=0, alloc=None, n_catch=4):
    recs = _pool()
    for r in recs:
        r["source_file"] = "s.jsonl"
    groups = pea.partition(recs)
    catch = pea.make_catch_pairs(pea.excluded_records(recs), n_catch,
                                 __import__("random").Random(seed + 977))
    alloc = alloc or {"win": -1, "flip": -1, "subthreshold": -1, "catch": n_catch}
    return groups, catch, pea.build_round1(groups, catch, alloc, seed)


# ---------------------------------------------------------------------------
# Classification: the stratification must match the harness, not the old
# `success == True` filter that made the interesting stratum unreachable.
# ---------------------------------------------------------------------------
def test_classify_matches_harness_success_definition():
    for attack in ("false_alarm", "hide"):
        win = _rec("a", attack, ef=True, held=True)
        flip = _rec("b", attack, ef=True, held=False)
        sub = _rec("c", attack, ef=False, held=True)
        assert pea.classify(win) == "win" and win["success"] is True
        assert pea.classify(flip) == "flip" and flip["success"] is False
        assert pea.classify(sub) == "subthreshold" and sub["success"] is False


def test_flip_stratum_is_nonempty_and_would_be_lost_by_a_success_filter():
    """Regression on the original bug: `success == True` drops every flip, which is
    exactly the disclosed lower bound on gate leakage."""
    recs = _pool()
    groups = pea.partition(recs)
    assert len(groups["flip"]) == 8
    # the old sampler kept exactly `success == True`, i.e. precisely the win stratum
    old_sampler_would_keep = [r for r in recs if r["success"]]
    assert {r["question_id"] for r in old_sampler_would_keep} == \
           {r["question_id"] for r in groups["win"]}
    # so every flip and subthreshold pair was invisible to it
    assert not any(r["success"] for r in groups["flip"] + groups["subthreshold"])
    assert len(groups["flip"]) + len(groups["subthreshold"]) == 19


def test_noop_and_infeasible_records_are_not_auditable():
    assert pea.classify(_rec("x", "hide", ef=True, held=True, noop=True)) is None
    assert pea.classify(_rec("y", "hide", ef=True, held=True, feasible=False)) is None
    assert pea.classify(_rec("z", "hide", ef=True, held=True)) == "win"


def test_stratum_sizes_and_census_default():
    groups, _, (ann, key) = _built()
    assert (len(groups["win"]), len(groups["flip"]), len(groups["subthreshold"])) == (23, 8, 11)
    from collections import Counter
    c = Counter(k["stratum"] for k in key)
    assert c["win"] == 23 and c["flip"] == 8 and c["subthreshold"] == 11  # -1 == census
    assert c["catch"] == 4
    assert len(ann) == len(key) == 46


def test_subsampling_respects_requested_n():
    _, _, (ann, key) = _built(alloc={"win": 5, "flip": 2, "subthreshold": 3, "catch": 4})
    from collections import Counter
    c = Counter(k["stratum"] for k in key)
    assert (c["win"], c["flip"], c["subthreshold"]) == (5, 2, 3)
    assert len(ann) == 14


def test_requesting_more_than_available_caps_at_the_pool():
    _, _, (_, key) = _built(alloc={"win": 999, "flip": 999, "subthreshold": 999, "catch": 4})
    from collections import Counter
    c = Counter(k["stratum"] for k in key)
    assert (c["win"], c["flip"], c["subthreshold"]) == (23, 8, 11)


# ---------------------------------------------------------------------------
# Blinding. The annotator's sheet must carry no cue to the stratum.
# ---------------------------------------------------------------------------
def test_annotator_columns_are_exactly_the_blind_contract():
    _, _, (ann, _) = _built()
    assert list(ann[0]) == list(pea.ANNOTATOR_COLS)
    leaky = {"stratum", "attack", "detector", "success", "status_held", "delta",
             "entropy_and_feasible", "correct_under_q_prime", "answer_under_q_prime",
             "question_id", "orientation", "entropy_before", "entropy_after"}
    assert leaky.isdisjoint(set(pea.ANNOTATOR_COLS))


def test_no_stratum_or_provenance_value_leaks_into_annotator_cells(tmp_path):
    _, _, (ann, _) = _built()
    out = tmp_path / "a.csv"
    pea.write_rows(ann, pea.ANNOTATOR_COLS, out)
    blob = out.read_text(encoding="utf-8")
    # tokens that cannot occur in natural question text, so a hit is a genuine leak
    for token in ("subthreshold", "false_alarm", "status_held", "qprime_first",
                  "entropy_and_feasible", "correct_under_q_prime"):
        assert token not in blob, f"{token!r} leaked into the annotator sheet"
    # stratum labels must not appear as a cell VALUE anywhere (substring matching would
    # false-positive on real questions containing "win" or "hide")
    cells = {v for row in pea.read_rows(out) for v in row.values()}
    assert cells.isdisjoint(set(pea.ALL_STRATA))
    assert cells.isdisjoint({"q_first", "qprime_first", "false_alarm", "hide", "se"})
    # and no question_id from the pool appears anywhere in the sheet
    for qid in {r["question_id"] for r in _pool()}:
        assert qid not in blob, f"question_id {qid!r} leaked into the annotator sheet"


def test_pair_ids_are_assigned_after_the_shuffle():
    """If ids were assigned per stratum before shuffling, the sheet order would be
    blocked by stratum and the id would be an index into those blocks."""
    _, _, (ann, key) = _built()
    assert [a["pair_id"] for a in ann] == [f"P{i:03d}" for i in range(1, len(ann) + 1)]
    seq = [k["stratum"] for k in key]
    blocked = sorted(seq, key=lambda s: pea.ALL_STRATA.index(s))
    assert seq != blocked, "strata appear in contiguous blocks — the shuffle did not run"
    # first and last thirds should both contain wins and non-wins
    third = max(1, len(seq) // 3)
    for chunk in (seq[:third], seq[-third:]):
        assert "win" in chunk and len(set(chunk)) > 1


def test_response_columns_start_blank():
    _, _, (ann, _) = _built()
    for row in ann:
        assert all(row[c] == "" for c in pea.RESPONSE_COLS)


# ---------------------------------------------------------------------------
# Orientation: which side of the pair holds the original is randomised, balanced,
# and recoverable only from the key.
# ---------------------------------------------------------------------------
def test_orientation_is_balanced_and_both_values_occur():
    _, _, (_, key) = _built()
    vals = [k["orientation"] for k in key]
    assert set(vals) == {"q_first", "qprime_first"}
    assert abs(vals.count("q_first") - vals.count("qprime_first")) <= 1


def test_orientation_determines_ab_placement():
    _, _, (ann, key) = _built()
    by_id = {k["pair_id"]: k for k in key}
    for row in ann:
        k = by_id[row["pair_id"]]
        expect = ((k["question"], k["best_query"]) if k["orientation"] == "q_first"
                  else (k["best_query"], k["question"]))
        assert (row["question_A"], row["question_B"]) == expect


# ---------------------------------------------------------------------------
# Determinism
# ---------------------------------------------------------------------------
def test_same_seed_reproduces_the_sheet_exactly():
    a = _built(seed=3)[2]
    b = _built(seed=3)[2]
    assert a == b


def test_different_seed_changes_the_draw():
    (_, k0), (_, k3) = _built(seed=0)[2], _built(seed=3)[2]
    order0 = [(k["question_id"], k["orientation"]) for k in k0]
    order3 = [(k["question_id"], k["orientation"]) for k in k3]
    assert order0 != order3


def test_input_record_order_does_not_change_the_draw():
    """`partition` sorts each stratum before sampling, so a differently-ordered JSONL
    (e.g. a resumed run appending out of order) yields the same sheet."""
    import random
    recs = _pool()
    for r in recs:
        r["source_file"] = "s.jsonl"
    shuffled = list(recs)
    random.Random(11).shuffle(shuffled)
    alloc = {"win": 5, "flip": 3, "subthreshold": 4, "catch": 0}
    a = pea.build_round1(pea.partition(recs), [], alloc, 0)[1]
    b = pea.build_round1(pea.partition(shuffled), [], alloc, 0)[1]
    assert [k["question_id"] for k in a] == [k["question_id"] for k in b]


# ---------------------------------------------------------------------------
# Catch trials
# ---------------------------------------------------------------------------
def test_catch_pairs_are_unrelated_distinct_and_consume_each_record_once():
    import random
    pool = _distinct_unauditable(12)
    pairs = pea.make_catch_pairs(pool, 5, random.Random(0))
    assert len(pairs) == 5
    used = []
    for p in pairs:
        assert p["question"] != p["best_query"]
        assert pea.overlap(p["question"], p["best_query"]) <= 0.25
        used += p["question_id"].replace("catch:", "").split("|")
    assert len(used) == len(set(used)) == 10   # 5 pairs, no record reused


def test_catch_pairs_degrade_gracefully_when_material_runs_out():
    import random
    assert pea.make_catch_pairs(_distinct_unauditable(3), 5, random.Random(0)).__len__() == 1
    assert pea.make_catch_pairs([], 5, random.Random(0)) == []
    assert pea.make_catch_pairs(_distinct_unauditable(9), 0, random.Random(0)) == []


def test_no_question_text_appears_twice_across_the_sheet():
    """A question the annotator has already read in another pair is itself a cue."""
    _, _, (ann, _) = _built()
    seen = [row[c] for row in ann for c in ("question_A", "question_B")]
    assert len(seen) == len(set(seen))


# ---------------------------------------------------------------------------
# Round 2 / re-annotation
# ---------------------------------------------------------------------------
def test_round2_is_a_flipped_reshuffled_relabelled_subset():
    _, _, (_, key1) = _built()
    ann2, key2 = pea.build_round2(key1, 0.30, seed=0)
    assert len(ann2) == len(key2) == round(0.30 * len(key1))
    by1 = {k["pair_id"]: k for k in key1}
    assert [a["pair_id"] for a in ann2] == [f"R{i:03d}" for i in range(1, len(ann2) + 1)]
    for k in key2:
        src = by1[k["round1_pair_id"]]
        assert k["round"] == 2 and k["stratum"] == src["stratum"]
        assert k["orientation"] != src["orientation"]        # flipped
        assert (k["question"], k["best_query"]) == (src["question"], src["best_query"])
    # order is not the round-1 order
    assert [k["round1_pair_id"] for k in key2] != sorted(k["round1_pair_id"] for k in key2)


def test_round2_pairs_show_the_original_on_the_other_side():
    _, _, (ann1, key1) = _built()
    ann2, key2 = pea.build_round2(key1, 0.30, seed=0)
    a1 = {a["pair_id"]: a for a in ann1}
    a2 = {k["pair_id"]: a for k, a in zip(key2, ann2)}
    for k in key2:
        first, second = a1[k["round1_pair_id"]], a2[k["pair_id"]]
        assert (second["question_A"], second["question_B"]) == \
               (first["question_B"], first["question_A"])


def test_round2_fraction_zero_and_one():
    _, _, (_, key1) = _built()
    assert pea.build_round2(key1, 0.0, seed=0) == ([], [])
    assert len(pea.build_round2(key1, 1.0, seed=0)[0]) == len(key1)


# ---------------------------------------------------------------------------
# Key round-trip
# ---------------------------------------------------------------------------
def test_key_round_trips_through_csv_and_rejoins_the_sheet(tmp_path):
    _, _, (ann, key1) = _built()
    ann2, key2 = pea.build_round2(key1, 0.30, seed=0)
    kp, ap = tmp_path / "k.csv", tmp_path / "a.csv"
    pea.write_rows([*key1, *key2], pea.KEY_COLS, kp)
    pea.write_rows(ann, pea.ANNOTATOR_COLS, ap)

    back = pea.read_rows(kp)
    assert len(back) == len(key1) + len(key2)
    assert list(back[0]) == list(pea.KEY_COLS)
    # every field survives, comparing as strings (csv is untyped)
    for orig, got in zip([*key1, *key2], back):
        for c in pea.KEY_COLS:
            assert str(orig.get(c, "")) == got[c], c
    # the join that §5 of the protocol relies on
    joined = {k["pair_id"]: k for k in back if k["round"] == "1"}
    for row in pea.read_rows(ap):
        k = joined[row["pair_id"]]
        assert {row["question_A"], row["question_B"]} == {k["question"], k["best_query"]}
    assert len({k["pair_id"] for k in back}) == len(back)   # ids unique across rounds


# ---------------------------------------------------------------------------
# Interval arithmetic used by the sizing table
# ---------------------------------------------------------------------------
def test_wilson_is_sane_at_the_extremes_and_brackets_p_hat():
    lo, hi = pea.wilson(0, 40)
    assert lo == 0.0 and 0.0 < hi < 0.15          # non-degenerate at zero events
    lo, hi = pea.wilson(4, 40)
    assert lo < 0.10 < hi and 0.15 < (hi - lo) < 0.25
    assert pea.wilson(0, 0) == (0.0, 1.0)
    for n in (10, 50, 200):
        for k in range(0, n + 1, max(1, n // 5)):
            lo, hi = pea.wilson(k, n)
            assert 0.0 <= lo <= k / n <= hi <= 1.0


def test_wilson_narrows_as_n_grows():
    widths = [pea.wilson(round(0.1 * n), n)[1] - pea.wilson(round(0.1 * n), n)[0]
              for n in (20, 40, 80, 160)]
    assert widths == sorted(widths, reverse=True)


def test_fpc_collapses_at_a_census_and_is_never_wider_than_the_superpopulation():
    assert pea.wilson_fpc(7, 72, 72) == (7 / 72, 7 / 72)      # census -> no sampling error
    for n in (10, 30, 60, 71):
        flo, fhi = pea.wilson_fpc(round(0.1 * n), n, 72)
        lo, hi = pea.wilson(round(0.1 * n), n)
        assert (fhi - flo) <= (hi - lo) + 1e-12
    # and it tightens monotonically as the sample approaches the population
    ws = [pea.wilson_fpc(round(0.1 * n), n, 72)[1] - pea.wilson_fpc(round(0.1 * n), n, 72)[0]
          for n in (10, 30, 50, 70)]
    assert ws == sorted(ws, reverse=True)


def test_sizing_table_shape():
    rows = pea.sizing_table(72, [20, 72], [0.0, 0.1])
    assert len(rows) == 4
    assert {r["n"] for r in rows} == {20, 72}
    assert all(r["wilson_width"] >= r["fpc_width"] for r in rows)


# ---------------------------------------------------------------------------
# End to end
# ---------------------------------------------------------------------------
def test_main_writes_all_four_artefacts(tmp_path):
    src = _write_pool(tmp_path, _pool())
    stem = str(tmp_path / "aud")
    assert pea.main([str(src), "--out", stem, "--seed", "0", "--n_catch", "3"]) == 0
    for suffix in (".csv", "_round2.csv", "_key.csv", "_design.md"):
        assert Path(stem + suffix).exists(), suffix
    ann = pea.read_rows(Path(stem + ".csv"))
    key = pea.read_rows(Path(stem + "_key.csv"))
    assert list(ann[0]) == list(pea.ANNOTATOR_COLS)
    assert len(ann) == 23 + 8 + 11 + 3
    assert {k["round"] for k in key} == {"1", "2"}
    md = Path(stem + "_design.md").read_text(encoding="utf-8")
    assert "sha256" in md and "win" in md and "n audited" in md


def test_main_key_out_can_be_redirected(tmp_path):
    src = _write_pool(tmp_path, _pool())
    stem, key = str(tmp_path / "aud"), tmp_path / "elsewhere" / "k.csv"
    assert pea.main([str(src), "--out", stem, "--key_out", str(key)]) == 0
    assert key.exists() and not Path(stem + "_key.csv").exists()


def test_main_exclude_audited_yields_a_disjoint_topup(tmp_path):
    src = _write_pool(tmp_path, _pool())
    a, b = str(tmp_path / "a"), str(tmp_path / "b")
    assert pea.main([str(src), "--out", a, "--n_win", "5", "--n_flip", "2",
                     "--n_subthreshold", "2", "--n_catch", "0"]) == 0
    assert pea.main([str(src), "--out", b, "--exclude_audited", a + "_key.csv",
                     "--n_catch", "0"]) == 0
    first = {k["question_id"] for k in pea.read_rows(Path(a + "_key.csv"))}
    second = {k["question_id"] for k in pea.read_rows(Path(b + "_key.csv"))}
    assert first and second and first.isdisjoint(second)


def test_main_refuses_a_fabricated_benign_arm(tmp_path):
    src = _write_pool(tmp_path, _pool())
    assert pea.main([str(src), "--out", str(tmp_path / "x"),
                     "--benign_jsonl", str(src)]) == 2


def test_main_errors_on_missing_input_and_on_an_unauditable_pool(tmp_path):
    assert pea.main([str(tmp_path / "nope.jsonl"), "--out", str(tmp_path / "x")]) == 2
    only_noop = _write_pool(tmp_path, [_rec(f"n{i}", "hide", ef=False, held=True, noop=True)
                                       for i in range(4)], name="noop.jsonl")
    assert pea.main([str(only_noop), "--out", str(tmp_path / "y")]) == 1


def test_sheet_is_bom_prefixed_utf8_and_preserves_typography(tmp_path):
    """TriviaQA questions carry curly quotes, en dashes and ellipses. The sheet is opened
    in a spreadsheet by hand, and Excel mis-decodes BOM-less UTF-8, so the file must be
    utf-8-sig and the characters must survive the round trip byte-for-byte."""
    recs = _pool()
    recs[0]["question"] = "Who wrote ‘The Waste Land’ — and when, exactly…?"
    recs[0]["best_query"] = "Which author produced ‘The Waste Land’, and in what year…?"
    src = _write_pool(tmp_path, recs)
    stem = str(tmp_path / "aud")
    assert pea.main([str(src), "--out", stem]) == 0

    assert Path(stem + ".csv").read_bytes().startswith(b"\xef\xbb\xbf")  # BOM for Excel
    rows = pea.read_rows(Path(stem + ".csv"))
    assert list(rows[0])[0] == "pair_id"          # BOM did not contaminate the header
    cells = [c for r in rows for c in (r["question_A"], r["question_B"])]
    assert any("‘The Waste Land’" in c and "—" in c and "…" in c for c in cells)
    assert not any("�" in c or "â€" in c for c in cells)   # no mojibake introduced


def test_key_written_by_us_is_readable_back_with_or_without_a_bom(tmp_path):
    """`--exclude_audited` consumes a key that may have been re-saved by a spreadsheet."""
    _, _, (_, key) = _built()
    with_bom, without = tmp_path / "b.csv", tmp_path / "n.csv"
    pea.write_rows(key, pea.KEY_COLS, with_bom)
    without.write_bytes(with_bom.read_bytes()[3:])          # strip the BOM
    a, b = pea.read_rows(with_bom), pea.read_rows(without)
    assert a == b and list(a[0])[0] == "pair_id"
