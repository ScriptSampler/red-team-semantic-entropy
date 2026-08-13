"""The operational-provenance guard, and proof that it is neither vacuous nor over-eager.

WHAT THIS FILE HAS TO ANSWER FOR.

`check_population_labels.py`'s first version caught 1 of 14 constructed errors, and its test
file was complicit: it had been written by the same person on the same afternoon, encoding
the same wrong assumption about what the error looks like. So every probe here is paired
with a CONTROL -- the same claim written correctly -- because a rule that flags everything is
not a rule, and a test suite that only supplies probes cannot tell the difference.

The second thing that file learned is subtler and is the reason for
`test_the_paragraph_window_does_not_launder_the_papers_dead_anchor`. A retirement marker is
searched over the enclosing PARAGRAPH, not the sentence, because a correction reads across
two sentences. That widening nearly cost the most important catch in the repo: an early draft
counted "correction" as a retirement marker, and `paper/sections/experiments.tex:173` sits in
a paragraph containing "the budget correction then moved ..." -- so the one dead anchor that
reached the paper was silently laundered by a word in an adjacent clause. That regression is
pinned below.

WHY THERE IS NO test_the_repo_is_green. There isn't one, and there should not be. The repo is
NOT green: 23 sites currently restate a superseded operational anchor, including one in the
paper and two in a shell script that is running on the GPU right now and must not be edited.
Asserting green would require either lying or editing files that are in flight. This project
already has the rule -- "A green test suite next to a known-broken statistic reads as
validation of it. Pin the failure or delete the test." So the failures are PINNED, in
KNOWN_SITES, and the test fails when a NEW one appears or a pinned one is fixed without
updating the register. That is a debt ledger, not a passing grade.
"""
from __future__ import annotations

import datetime as dt
import re
import sys
import textwrap
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "scripts"))

from check_operational_provenance import (  # noqa: E402
    DEAD_ANCHORS, KNOWN_OPEN, OUT_OF_SCOPE, check_file, main, scoped_files, strip_markup,
)

TODAY = dt.date(2026, 8, 14)


def _check(tmp_path: Path, text: str, name: str = "probe_plan.md", **kw) -> list[str]:
    f = tmp_path / name
    f.write_text(textwrap.dedent(text).strip() + "\n", encoding="utf-8")
    return check_file(f, today=kw.pop("today", TODAY), repo=kw.pop("repo", tmp_path))


def _say(problems: list[str]) -> str:
    return "\n".join(problems)


def _rules(problems: list[str]) -> set[str]:
    out = set()
    for p in problems:
        m = re.search(r"(dead-anchor|untagged|anchorless-model|supersede-trigger|"
                      r"stale-countdown|ratchet-stale)", p)
        if m:
            out.add(m.group(1))
    return out


# ======================================================================================
# Rule 1 -- dead anchors. The chain that cost the scheduling decision.
# ======================================================================================
DEAD_PROBES = [
    ("the 55 s clustering probe, restated as an anchor",
     "The judge arm is ~(2+m+n_seeds) clusterings per target, ~55 s each.",
     "dead-anchor"),
    ("the 228 GPU-h price tag, in the paper's own phrasing",
     "the matched design pricing out at $228$ GPU-hours, about nine and a half GPU-days.",
     "dead-anchor"),
    ("the 67 GPU-h null control, as the pre-registration wrote it",
     "Cost: 55 clusterings per target => ~50 min/target => ~67 GPU-hours for n=80.",
     "dead-anchor"),
    ("the 60 GPU-h restatement that scheduled the queue",
     "It has ~60 GPU-h left against a ~10 h night, so it yields nothing by morning.",
     "dead-anchor"),
    ("the 73.9 s/eval N=40 figure",
     "the recommended buy: ONE pass at N=40, both strata: n=400 evals -> 8.22 GPU-h "
     "[73.9 s/eval].",
     "dead-anchor"),
    ("the 2.8 s SE-eval token split",
     "Splitting it by generated tokens gives s_SE ~ 2.8 s per SE eval.",
     "dead-anchor"),
    ("the 6.1 s cheap-arm figure",
     "and the cheap arms alone are ~6.1 s per eval, so 25 GPU-h covers n=80.",
     "dead-anchor"),
    ("the 67 s judge clustering",
     "At the deployed setting a judge clustering is 67 s, so J1 is 3.11 GPU-h.",
     "dead-anchor"),
]


@pytest.mark.parametrize("name,text,rule", DEAD_PROBES, ids=[p[0] for p in DEAD_PROBES])
def test_every_dead_anchor_is_caught_when_restated_as_live(tmp_path, name, text, rule):
    problems = _check(tmp_path, text)
    assert rule in _rules(problems), f"{name}: not caught.\n{_say(problems)}"


@pytest.mark.parametrize("name,text,rule", DEAD_PROBES, ids=[p[0] for p in DEAD_PROBES])
def test_the_same_anchors_pass_when_the_paragraph_says_they_are_dead(tmp_path, name, text, rule):
    """The CONTROL half. A register of superseded numbers has to be able to name them."""
    problems = _check(tmp_path, text + " That figure is superseded; the deployed run "
                                       "refutes it.")
    assert "dead-anchor" not in _rules(problems), (
        f"{name}: flagged even though the paragraph retires it.\n{_say(problems)}")


@pytest.mark.parametrize("name,text,rule", DEAD_PROBES, ids=[p[0] for p in DEAD_PROBES])
def test_a_retirement_in_the_NEXT_paragraph_does_not_excuse_the_restatement(tmp_path, name,
                                                                            text, rule):
    """The window is the paragraph and stops there, deliberately.

    Widening it to the whole section would let a "superseded" in a summary at the bottom of
    a 400-line plan bless every live restatement above it -- the precise shape of the
    presence-in-a-window defect that made `check_population_labels.py`'s first version
    near-vacuous.
    """
    problems = _check(tmp_path, text + "\n\nSeparately, that figure is superseded.")
    assert "dead-anchor" in _rules(problems), (
        f"{name}: a retirement one paragraph away laundered it.\n{_say(problems)}")


def test_the_dead_anchor_message_carries_the_replacement_not_just_the_complaint():
    """A guard that says 'wrong' without saying 'use this instead' gets worked around."""
    for _pattern, _context, name, replacement in DEAD_ANCHORS:
        assert len(replacement) > 40, f"{name} has no useful replacement text"
        assert re.search(r"\d", replacement), f"{name}'s replacement names no number"


def test_the_paragraph_window_does_not_launder_the_papers_dead_anchor(tmp_path):
    """REGRESSION, and the most important test in this file.

    An early draft counted 'correction' as a retirement marker. The paragraph in
    `experiments.tex` that carries the 228 GPU-h figure also contains 'The budget correction
    then moved ...', so the widening silently blessed the one dead anchor that reached the
    paper. Words that are merely common in adjacent prose cannot be retirement markers.
    """
    problems = _check(tmp_path, r"""
        The benign floor moved from individual draws to a budget-corrected comparison,
        triggered by the winner's-curse mismatch surfaced in adversarial review. The budget
        correction then moved from brute-force matching to the analytic exceedance null,
        triggered by the matched design pricing out at $228$ GPU-hours, about nine and a
        half GPU-days.
        """, name="probe.tex")
    assert "dead-anchor" in _rules(problems), (
        "a 'correction' three clauses away laundered the paper's dead anchor:\n"
        + _say(problems))


def test_markup_cannot_hide_a_dead_anchor(tmp_path):
    """The markup lesson, inherited: a grep for a phrase does not survive LaTeX."""
    assert "228" in strip_markup(r"pricing out at $228$ GPU-hours")
    assert "8.22 GPU-h" in strip_markup("**8.22 GPU-h** [MODELLED]")
    assert len(strip_markup(r"\emph{fair} pool")) == len(r"\emph{fair} pool")
    problems = _check(tmp_path, r"the design prices out at \textbf{$228$~GPU-hours} today.",
                      name="probe.tex")
    assert "dead-anchor" in _rules(problems), _say(problems)


# ======================================================================================
# Rule 2 -- tags, and the ratchet
# ======================================================================================
def test_an_untagged_gpu_hour_figure_is_caught(tmp_path):
    problems = _check(tmp_path, "The extension is 30 further negatives: 0.62 GPU-h.")
    assert "untagged" in _rules(problems), _say(problems)


def test_a_tagged_figure_passes(tmp_path):
    problems = _check(
        tmp_path,
        "The extension is 30 further negatives: 0.38 GPU-h [MEASURED from "
        "`results/n_scaling_ckpt.jsonl`, 43 evals at N=40].")
    assert not problems, _say(problems)


@pytest.mark.parametrize("unit", [
    "8.2 GPU-h", "4.1 GPU-days", "12.87 s/eval", "586 s/target", "24.0 s/clustering",
    "0.42 s/Q", "50 min/target", "2.6 nights",
])
def test_every_operational_unit_shape_is_recognised(tmp_path, unit):
    """A rule that only knows about GPU-hours misses the per-unit rates they are built from
    -- and every failure in the audit was a per-unit rate, not an hours figure."""
    problems = _check(tmp_path, f"The remainder is {unit}.")
    assert "untagged" in _rules(problems), f"{unit} not recognised as operational"


def test_a_plain_number_is_not_mistaken_for_a_cost(tmp_path):
    """Non-vacuity in the other direction: the guard must not chase every digit."""
    problems = _check(tmp_path, """
        The lattice has 39 attainable values at N=10, of which 2 lie in the top tenth, and
        the gap between the top two points is 0.1386 nats. AUROC 0.704 [0.653, 0.753] on
        n=400 targets at m=50.
        """)
    assert not problems, _say(problems)


def test_the_ratchet_fires_on_a_new_untagged_figure_not_on_the_existing_ones(tmp_path):
    """KNOWN_OPEN is a debt ledger. Adding to a file's debt must fail even though the file
    already carries some."""
    import check_operational_provenance as C
    f = tmp_path / "ratchet_plan.md"
    key = C._rel(f)
    f.write_text("Item one costs 3.0 GPU-h. Item two costs 4.0 GPU-h.\n", encoding="utf-8")
    C.KNOWN_OPEN[key] = 2
    try:
        assert not check_file(f, today=TODAY, repo=tmp_path), "baseline should be clean"
        f.write_text("Item one costs 3.0 GPU-h. Item two costs 4.0 GPU-h. "
                     "Item three costs 5.0 GPU-h.\n", encoding="utf-8")
        problems = check_file(f, today=TODAY, repo=tmp_path)
        assert "untagged" in _rules(problems), _say(problems)
    finally:
        C.KNOWN_OPEN.pop(key, None)


def test_the_ratchet_also_fires_when_debt_is_paid_without_updating_the_register(tmp_path):
    """Otherwise the register rots upward: a file that has been cleaned still licenses new
    untagged figures up to its stale baseline."""
    import check_operational_provenance as C
    f = tmp_path / "ratchet_plan.md"
    key = C._rel(f)
    f.write_text("Item one costs 3.0 GPU-h.\n", encoding="utf-8")
    C.KNOWN_OPEN[key] = 2
    try:
        problems = check_file(f, today=TODAY, repo=tmp_path)
        assert "ratchet-stale" in _rules(problems), _say(problems)
    finally:
        C.KNOWN_OPEN.pop(key, None)


# ======================================================================================
# Rule 3 -- a MODELLED figure has to name its anchor
# ======================================================================================
def test_a_modelled_figure_that_names_no_anchor_is_caught(tmp_path):
    problems = _check(tmp_path, "The gate is about 4 GPU-h [MODELLED].")
    assert "anchorless-model" in _rules(problems), _say(problems)


@pytest.mark.parametrize("named", [
    "[MODELLED from critique_log 22's K=8 probe at judge_batch_size 12]",
    "[MODELLED from `results/null_control_cost_options.md` section 1]",
    "[MODELLED via the token split in null_objective_ablation_plan.md]",
    "[MODELLED, based on the hide cell's 568-607 s/target]",
])
def test_a_modelled_figure_passes_once_the_anchor_is_written_down(tmp_path, named):
    problems = _check(tmp_path, f"The gate is about 4 GPU-h {named}.")
    assert "anchorless-model" not in _rules(problems), _say(problems)


def test_naming_the_anchor_is_all_the_rule_can_do_and_the_docstring_says_so():
    """Type (d): no checker can tell that a K=8 probe is the wrong anchor for a K=50 run.
    The rule buys legibility, not correctness, and the module must not pretend otherwise."""
    import check_operational_provenance as C
    doc = C.__doc__ or ""
    assert "NOT MECHANISABLE" in doc
    assert "K=8" in doc


# ======================================================================================
# Rule 4 -- re-derive once the work has run
# ======================================================================================
def test_a_declared_supersede_trigger_fires_when_the_artifact_appears(tmp_path):
    (tmp_path / "results").mkdir()
    text = ("The remainder is ~50 GPU-h [MODELLED from critique_log 22; "
            "supersede-when: results/ckpt.jsonl].")
    problems = _check(tmp_path, text)
    assert "supersede-trigger" not in _rules(problems), (
        "fired before the artifact existed:\n" + _say(problems))
    (tmp_path / "results" / "ckpt.jsonl").write_text("{}\n", encoding="utf-8")
    problems = _check(tmp_path, text)
    assert "supersede-trigger" in _rules(problems), (
        "did not fire once the artifact existed:\n" + _say(problems))


def test_the_supersede_trigger_is_the_rule_that_would_have_caught_the_null_control(tmp_path):
    """The concrete case. The 67 GPU-h figure was modelled from a K=8 probe; the deployed
    run's checkpoint had been on disk for hours. Declared, the guard fires the moment the
    first target is written."""
    (tmp_path / "results").mkdir()
    (tmp_path / "results" / "null_control_ckpt_defb.jsonl").write_text("{}\n", encoding="utf-8")
    problems = _check(tmp_path, (
        "Null control remaining: 50 GPU-h [MODELLED from critique_log 22's 55 s/clustering "
        "K=8 probe; supersede-when: results/null_control_ckpt_defb.jsonl]."))
    assert "supersede-trigger" in _rules(problems), _say(problems)


# ======================================================================================
# Rule 5 -- countdowns are monotone in time
# ======================================================================================
def test_a_stale_countdown_is_caught(tmp_path):
    problems = _check(tmp_path, "33 days remain to the 2026-09-15 target.")
    assert "stale-countdown" in _rules(problems), _say(problems)


def test_a_correct_countdown_passes(tmp_path):
    problems = _check(tmp_path, "32 days remain to the 2026-09-15 target.")
    assert not problems, _say(problems)


def test_the_countdown_rule_needs_no_judgement_at_all():
    """The one rule with a provably empty false-positive set: it is arithmetic on two
    literals in the text. Recomputed against a different 'today', the same sentence flips."""
    import check_operational_provenance as C
    p = Path(__file__).parent / "__cd.md"
    p.write_text("33 days remain to the 2026-09-15 target.\n", encoding="utf-8")
    try:
        assert not check_file(p, today=dt.date(2026, 8, 13), repo=REPO)
        assert check_file(p, today=dt.date(2026, 8, 14), repo=REPO)
    finally:
        p.unlink()


# ======================================================================================
# Scope
# ======================================================================================
def test_the_append_only_history_is_out_of_scope_and_stays_that_way():
    """critique_log.md is full of dead anchors -- correctly, they were true when written.
    Scanning it would produce noise that buries the forward quotations that matter."""
    scanned = {p.as_posix() for p in scoped_files()}
    for excluded in OUT_OF_SCOPE:
        assert not any(s.endswith(excluded) for s in scanned), f"{excluded} is in scope"
    assert (REPO / "docs" / "critique_log.md").exists(), "the exclusion is not vacuous"


def test_the_audit_itself_is_excluded_for_a_stated_reason_not_by_omission():
    """It is the register of dead anchors; it must be able to name them. That is the same
    argument as the critique log's, and it is written in the module, not just here."""
    import check_operational_provenance as C
    assert "results/operational_number_audit.md" in OUT_OF_SCOPE
    assert "operational_number_audit.md" in (C.__doc__ or "") or \
        "operational_number_audit.md" in Path(C.__file__).read_text(encoding="utf-8")


def test_the_live_planning_documents_are_actually_in_scope():
    """Non-vacuity: the guard must be pointed at the files where the failure happened."""
    scanned = {p.as_posix() for p in scoped_files()}
    for required in ("docs/START_HERE_overnight.md", "docs/definitive_run_plan.md",
                     "results/n_scaling_plan.md", "results/null_control_cost_options.md",
                     "results/null_objective_ablation_plan.md",
                     "results/judge_owed_conditions.md",
                     "paper/sections/experiments.tex",
                     "scripts/overnight_2026_08_13.sh"):
        assert any(s.endswith(required) for s in scanned), f"{required} is NOT scanned"


# ======================================================================================
# The debt ledger. NOT a passing grade -- see the module docstring.
# ======================================================================================
# (file, rule, anchor-or-empty) -> count, as of 2026-08-14.
#
# Every entry is a real finding from results/operational_number_audit.md. None of them can
# be fixed here: the .md files are script-generated, `overnight_2026_08_13.sh` is running on
# the GPU and is under a no-edit rule, and `experiments.tex` is a paper claim whose fix is a
# rewrite ("the measured figure is ~99 GPU-h; the decision was taken on a modelled 228"),
# not a substitution.
KNOWN_SITES: dict[tuple[str, str, str], int] = {
    ("docs/START_HERE_overnight.md", "dead-anchor", "~67 GPU-h null control"): 1,
    ("docs/START_HERE_overnight.md", "stale-countdown", ""): 1,
    ("docs/definitive_run_plan.md", "dead-anchor", "~67 GPU-h null control"): 1,
    # THE ONE IN THE PAPER. experiments.tex discloses a pre-registration deviation as
    # triggered by a 228 GPU-h price tag; the measured figure is ~99. The deviation stands;
    # the stated trigger is 2.3x too large, in the paragraph whose whole job is to let a
    # reviewer check the rule was not tuned to the result.
    ("paper/sections/experiments.tex", "dead-anchor", "228 GPU-h"): 1,
    ("results/derived_paper_quantities.md", "dead-anchor", "228 GPU-h"): 2,
    ("results/judge_owed_conditions.md", "dead-anchor", "55 s / clustering"): 1,
    ("results/judge_owed_conditions.md", "dead-anchor", "6.1 s cheap-arm eval"): 1,
    ("results/judge_owed_conditions.md", "dead-anchor", "~67 GPU-h null control"): 1,
    ("results/judge_owed_conditions.md", "stale-countdown", ""): 1,
    ("results/n_scaling_plan.md", "dead-anchor", "73.9 s/eval at N=40"): 6,
    ("results/n_scaling_plan.md", "dead-anchor", "~67 GPU-h null control"): 2,
    ("results/n_scaling_plan.md", "stale-countdown", ""): 1,
    # The sharpest one. null_control_cost_options.md is the document that CORRECTED the
    # 67 GPU-h figure -- and section 6F imports the discredited 2.8 s/eval from the very
    # file it was correcting, three sections further down, to conclude that the judge is
    # 88% of a clustering. Measured, it is at most 46%.
    ("results/null_control_cost_options.md", "dead-anchor", "2.8 s per SE eval"): 1,
    ("results/null_objective_ablation_plan.md", "dead-anchor", "2.8 s per SE eval"): 3,
    ("results/null_objective_ablation_plan.md", "dead-anchor", "~67 GPU-h null control"): 2,
    ("results/power_under_ceiling.md", "dead-anchor", "228 GPU-h"): 1,
    ("scripts/overnight_2026_08_13.sh", "dead-anchor", "~60 GPU-h null control"): 2,
}


def _live_sites() -> dict[tuple[str, str, str], int]:
    out: dict[tuple[str, str, str], int] = {}
    for path in scoped_files():
        for p in check_file(path, today=TODAY):
            head = p.split("\n", 1)[0]
            file_part = head.split(":", 1)[0]
            rule = re.search(r"(dead-anchor|untagged|anchorless-model|supersede-trigger|"
                             r"stale-countdown|ratchet-stale)", head)
            anchor = re.search(r"dead-anchor: '([^']+)'", head)
            key = (file_part, rule.group(1) if rule else "?",
                   anchor.group(1) if anchor else "")
            out[key] = out.get(key, 0) + 1
    return out


def test_the_open_sites_are_exactly_the_pinned_ones():
    """A NEW site fails here. A FIXED site also fails here, so the ledger cannot rot.

    If this test fails with an addition, someone has quoted a superseded operational number
    forward -- which is precisely the failure that cost a scheduling decision on 2026-08-13.
    Do not raise the pin to make it pass. Re-derive the figure, or say in the sentence that
    the anchor is dead.
    """
    live = _live_sites()
    added = {k: v for k, v in live.items() if KNOWN_SITES.get(k, 0) < v}
    fixed = {k: v for k, v in KNOWN_SITES.items() if live.get(k, 0) < v}
    assert not added and not fixed, (
        f"NEW sites (a superseded figure has been quoted forward): {added}\n"
        f"FIXED sites (good -- now update KNOWN_SITES in this file): {fixed}")


def test_the_guard_is_currently_red_and_that_is_the_finding():
    """`main()` returns non-zero today, on purpose. If this ever starts passing, the debt in
    KNOWN_SITES has been paid and this test should be replaced by a plain green assertion --
    deliberately, in a commit that says so, not by accident."""
    assert main(today=TODAY) == 1
    assert sum(KNOWN_SITES.values()) == sum(_live_sites().values())


def test_the_ratchet_baselines_match_the_repo_today():
    """KNOWN_OPEN is only meaningful if it is accurate. Any drift shows up as an `untagged`
    or `ratchet-stale` finding, neither of which is in KNOWN_SITES."""
    live = _live_sites()
    assert not [k for k in live if k[1] in ("untagged", "ratchet-stale")], (
        f"ratchet drift: {[k for k in live if k[1] in ('untagged', 'ratchet-stale')]}\n"
        f"KNOWN_OPEN needs updating in scripts/check_operational_provenance.py")
    assert KNOWN_OPEN, "the ratchet register is empty -- the rule would be vacuous"
