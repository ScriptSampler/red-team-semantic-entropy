"""The population-label guard, and proof that it is not vacuous.

Binding a statistic to the wrong population has been found at six separate sites in this
paper, each by a manual sweep, each sweep missing a site the next one found. This converts
that into a check that runs every time the suite does.

HISTORY THIS FILE HAS TO ANSWER FOR, IN TWO ROUNDS.

ROUND ONE. The first version of the guard, and the first version of this file, were written
by the same person on the same afternoon, and they encoded the same assumption: that the
error looks like a MISSING label. An audit then constructed eight genuine population errors
and the guard missed seven, because every one of them looked like a WRONG label with a right
one somewhere in the window. The eight probes are reconstructed below as PROBES, and each is
paired with a CONTROL -- the same claim written correctly -- so that a rule cannot pass by
flagging everything.

ROUND TWO (2026-08-13), and it is the more instructive one. Commit 4448da0 hardened the
attachment logic and the guard went from catching 1 of 14 probes to 14 of 14. It then
returned GREEN on "Across the $97$ targets of the attack campaign ($80$ correct, $17$
wrong)" -- a sentence in which both counts are retired -- because `97 targets` and
`17 wrong` were still LABELS, and a rule existed whose only job was to legitimise the
phrase. The hardening asked how tightly a label binds. It never asked whether the label was
still true, so a retired count became a licence rather than an error.

THIS FILE WAS COMPLICIT. Three of its controls asserted GREEN on the retired framing, one of
them the deleted sentence verbatim, and they went on certifying it after commit 5d822b9
removed it from the paper. They are rewritten below and marked. The lesson generalised into
a structural test -- test_no_pool_label_may_carry_a_count_of_a_cell_that_is_not_closed --
which points the guard's own growing-denominator rule at the guard's own label list: no
label may assert a count unless that cell is declared complete. That test, not the probes,
is what would have caught round two.
"""
from __future__ import annotations

import pathlib
import re
import sys
import textwrap
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "scripts"))

from check_population_labels import check_file, main, strip_latex  # noqa: E402


def _check(tmp_path: Path, text: str, name: str = "probe.tex") -> list[str]:
    f = tmp_path / name
    f.write_text(textwrap.dedent(text).strip() + "\n", encoding="utf-8")
    return check_file(f)


def _say(problems: list[str]) -> str:
    return "\n".join(problems)


# ======================================================================================
# The live paper
# ======================================================================================
def test_the_actual_paper_passes():
    """The live paper must have every population-sensitive number labelled."""
    assert main() == 0


# ======================================================================================
# strip_latex: markup must not defeat phrase matching, and \% must not blind the checker
# ======================================================================================
def test_strip_latex_defeats_the_markup_that_defeated_the_manual_grep():
    """The critic's own sweep for 'fair pool' MISSED conclusion.tex because the source
    reads `\\emph{fair} pool`. That is the specific failure this guard exists to prevent,
    so it gets its own test."""
    assert "fair pool" in strip_latex(r"on the score-independent \emph{fair} pool it separates")
    assert "attacked pool" in strip_latex(r"the \textbf{attacked} pool")
    # commands that wrap nothing relevant should not glue words together
    assert "97 targets" in strip_latex(r"across the $97$ targets")


def test_strip_latex_keeps_numbers_on_a_row_whose_header_contains_an_escaped_percent():
    """Defect 4. `%.*?$` with no negative lookbehind ate from a LITERAL \\% to end of line,
    which would have hidden every number on Table 1's saturation row -- the exact row the
    checker exists to guard."""
    row = r"Saturation rate (\% at $\log N$) & $52.5\%$ & -- \\"
    flat = strip_latex(row)
    assert "52.5" in flat, flat
    # ...while a real LaTeX comment is still removed.
    assert "secret" not in strip_latex("visible text % secret comment\nnext line")


def test_the_saturation_row_is_actually_reachable_end_to_end(tmp_path):
    """The same fix, exercised through check_file rather than through strip_latex."""
    problems = _check(tmp_path, r"""
        \begin{table}
        \caption{Clean detector characteristics on the score-independent \emph{fair} pool
        ($200$ correct, $200$ hallucinating).}
        Saturation rate (\% at $\log N$) & $52.5\%$ \\
        \end{table}
    """)
    assert any("52.5" in p for p in problems), _say(problems)


# ======================================================================================
# THE EIGHT PROBES. Every one of these is a genuine population error. Seven of the eight
# were accepted by the presence-only version of the guard.
# ======================================================================================
PROBES: list[tuple[str, str, str]] = [
    (
        "auroc_0704_bound_to_the_attacked_pool",
        # MISSED by the old rule: `fair pool` is present in the window, so the OR passed --
        # while the sentence actually attaches 0.704 to the attack campaign.
        r"""
        On the $97$ targets of the attack campaign the clean detector reaches AUROC
        $0.704$, and we characterise it there. Numbers for the score-independent
        \emph{fair} pool ($200$ correct, $200$ hallucinating) appear in Methods.
        """,
        "0.704",
    ),
    (
        "ceiling_counts_attributed_to_the_fair_pool",
        # MISSED: `attack campaign` sat in the window, one sentence away, licensing counts
        # that the sentence itself hands to the fair pool. 8/80 was not guarded at all.
        r"""
        On the score-independent \emph{fair} pool ($200$ correct, $200$ hallucinating), a
        tenth of correct answers ($8/80$) already sit at the estimator's maximum and $22$
        of the $39$ attainable values are realised. The attack campaign is described in
        Section 4.
        """,
        "8/80",
    ),
    (
        "quarantined_auroc_sold_as_the_detector",
        # MISSED: the requirement was the bare token `attacked`, and "the questions we
        # attacked" satisfied it.
        r"""
        The detector separates correct from hallucinating answers at AUROC $0.579$; the
        questions we attacked are described in Section 4.
        """,
        "0.579",
    ),
    (
        "quarantined_separation_sold_as_the_detector",
        # MISSED: same trivial satisfaction, on the nats separation.
        r"""
        Semantic entropy separates the two classes by $0.184$ nats overall, a property of
        the detector we attacked.
        """,
        "0.184",
    ),
    (
        "granularity_licensed_by_a_bare_97",
        # MISSED: the requirement was r"97", and `1997` and `0.97` both satisfy it. The
        # claim has since been retired outright, so today it is the provenance rule that
        # answers -- but the self-satisfaction hole it demonstrates is closed generally:
        # labels are pool PHRASES now, never bare tokens.
        r"""
        Across the score-independent \emph{fair} pool the estimator realises only $22$
        distinct values; a similar crowding was reported in $1997$, at a rank correlation
        of $0.97$.
        """,
        "22 distinct",
    ),
    (
        "saturation_rate_attributed_to_the_fair_pool",
        # MISSED: 42.5% and 52.5% were not in the guarded set.
        r"""
        On the score-independent \emph{fair} pool ($200$ correct, $200$ hallucinating),
        $42.5\%$ of targets finish exactly at the ceiling and $52.5\%$ sit there in total.
        """,
        "42.5",
    ),
    (
        "circular_auroc_presented_as_a_fair_pool_result",
        # MISSED: AUROC 1.0 was not in the guarded set. It is the artefact of
        # score-DEPENDENT selection and belongs to no measured pool.
        r"""
        On the score-independent \emph{fair} pool ($200$ correct, $200$ hallucinating) the
        clean detector reaches AUROC $1.0$.
        """,
        "1.0",
    ),
    (
        "abstract_rendering_of_the_fair_auroc_unlabelled",
        # The one the old rule DID catch, once r"AUROC 0.70" was added for the Abstract's
        # two-decimal rendering. Kept as a regression test.
        r"""
        The broader point is that a detector need not be badly calibrated to be fragile:
        this one separates the two moderately well (AUROC $0.70$).
        """,
        "AUROC 0.70",
    ),
]


@pytest.mark.parametrize("name,text,token", PROBES, ids=[p[0] for p in PROBES])
def test_the_eight_audit_probes_are_all_caught(tmp_path, name, text, token):
    problems = _check(tmp_path, text, name=f"{name}.tex")
    assert problems, f"probe {name!r} was accepted -- the check is vacuous on it"
    assert any(token in p for p in problems), _say(problems)


# Three more, for guarded numbers added in the same pass.
def test_judge_accuracy_needs_its_validation_population(tmp_path):
    """0.93 is hard-negative accuracy on domain-matched gold-alias pairs, n=300 -- a proxy
    for the deployed clustering decision. Validation on messy real sampled answers is still
    owed (judge_validation.md), so an unqualified '0.93 accurate' overclaims."""
    problems = _check(tmp_path, r"""
        Our LLM-judge is accurate to $0.93$, so we use it as the adjudicator for the
        confirmatory run.
    """)
    assert any("0.93" in p for p in problems), _say(problems)


def test_replication_auroc_must_not_read_as_a_fair_pool_number(tmp_path):
    """0.787 is our SE replication on TriviaQA, not the fair pool's clean AUROC."""
    problems = _check(tmp_path, r"""
        On the score-independent \emph{fair} pool ($200$ correct, $200$ hallucinating) the
        detector reaches AUROC $0.787$.
    """)
    assert any("0.787" in p for p in problems), _say(problems)


def test_retention_must_not_be_attached_to_the_fair_pool(tmp_path):
    """44% is retention on the 69 false-alarm targets the optimiser found a paraphrase for,
    re-scored on an independent sample. It is not a fair-pool quantity.

    UPDATED 2026-08-19: this probe used to read $45\\%$, the `_def` value. It kept passing
    after the rerun -- but only because 45% is now flagged as STALE, which is a different
    rule answering a different question. A probe that no longer exercises the rule it was
    written for is not a probe, so it now carries the live value and asserts MISLABELLED.
    """
    problems = _check(tmp_path, r"""
        On the score-independent \emph{fair} pool ($200$ correct, $200$ hallucinating),
        only $44\%$ of the apparent effect survives re-scoring.
    """)
    assert any("44" in p and "MISLABELLED" in p for p in problems), _say(problems)


def test_a_denominator_cannot_manufacture_its_own_label(tmp_path):
    """Second-round probe. '21/80 correct targets' contains the string '80 correct', which
    is an attacked-pool label -- so the mislabelled number was licensing itself out of its
    own denominator. Defect 2 wearing a different hat."""
    problems = _check(tmp_path, r"""
        The fair pool's $21/80$ correct targets sit within the top tenth of its range.
    """)
    assert any("21/80" in p for p in problems), _say(problems)


def test_a_trailing_wrong_label_is_caught_too(tmp_path):
    """A label AFTER the number binds more weakly, but when it is the ONLY label it is
    still the binding one -- and it is the wrong pool."""
    problems = _check(
        tmp_path, r"The clean detector reaches AUROC $0.704$ on the attacked pool.")
    assert any("0.704" in p for p in problems), _say(problems)


def test_two_swapped_labels_in_one_sentence_are_both_caught(tmp_path):
    """The contrastive construction with its two pools exchanged. This is the error the
    proximity rule exists for, and it must survive the trailing-label penalty."""
    problems = _check(tmp_path, r"""
        The attacked subset gives a clean separation of $0.463$ nats, whereas the fair
        pool gives $0.184$ nats.
    """)
    assert len(problems) >= 2, _say(problems)
    assert any("0.463" in p for p in problems) and any("0.184" in p for p in problems), \
        _say(problems)


def test_fair_pool_headroom_means_may_not_move_to_the_attacked_pool(tmp_path):
    """Commit 4d2aa77 fixed this exact error once already (site two): the headroom
    statistics are the fair pool's."""
    problems = _check(tmp_path, r"""
        Measured on the $97$ targets of the attack campaign, correctly-answered questions
        have clean mean entropy $1.380$, leaving $0.923$ nats to the ceiling.
    """)
    assert len(problems) >= 2, _say(problems)


def test_the_crowding_rates_may_not_move_back_onto_the_attacked_subset(tmp_path):
    """Commit e6e7629 moved the crowding claim off the attacked subset and onto the
    score-independent 400, precisely because the attacked subset 'is not a description of
    the detector'. Moving it back is the same error in reverse."""
    problems = _check(tmp_path, r"""
        On the $80$ correct-answer targets of our attack campaign, $9.5\%$ of correct
        answers sit at the ceiling and $21.5\%$ in the top decile.
    """)
    assert len(problems) >= 2, _say(problems)


def test_the_live_abstract_wording_for_those_rates_passes(tmp_path):
    """...and the corrected wording, which is what the Abstract now says, must not fire."""
    problems = _check(tmp_path, r"""
        On a score-independent pool of $400$ questions scored clean, $9.5\%$ [$6.2$,
        $14.4$] of \emph{correct} answers already sit exactly at the ceiling before any
        attack and $21.5\%$ [$16.4$, $27.7$] sit on one of those two top-decile points.
        For hallucinating answers it is $27.5\%$ and $44.5\%$. On the $80$ correct-answer
        targets of our attack campaign---a score-independent sub-sample of that pool's
        correct stratum---an optimised paraphrase attack drives a further $42\%$ onto the
        ceiling.
    """)
    assert not problems, _say(problems)


def test_a_mislabelled_number_is_reported_as_mislabelled_not_merely_unlabelled(tmp_path):
    """The distinction is the whole point of the hardening: the old guard could only ever
    say 'no label found', which is why a WRONG label always passed."""
    problems = _check(tmp_path, r"""
        On the $97$ targets of the attack campaign the clean detector reaches AUROC
        $0.704$, and we characterise it there. The score-independent \emph{fair} pool
        ($200$ correct, $200$ hallucinating) is described in Methods.
    """)
    assert any("MISLABELLED" in p for p in problems), _say(problems)


# ======================================================================================
# CONTROLS. The corrected form of every probe must pass, or the rule is unusable.
# ======================================================================================
def test_accepts_a_properly_labelled_pair(tmp_path):
    """The corrected form must pass, or the check is unusable.

    REWRITTEN 2026-08-13. This control used to say "across the $97$ targets of the attack
    campaign" and assert green -- so the test file blessed the retired total just as the
    guard's label list did. The pool is now named by its complete stratum, which is what
    the live paper says.
    """
    problems = _check(tmp_path, r"""
        Across the $80$ correct-answer targets of the attack campaign, scored clean, a
        tenth of correct answers ($8/80$) already sit at the estimator's maximum. On the
        score-independent \emph{fair} pool ($200$ correct, $200$ hallucinating) it
        separates correct from hallucinating answers at AUROC $0.704$ [$0.653$, $0.753$].
    """)
    assert not problems, _say(problems)


def test_the_nested_populations_may_be_stated_without_tripping_the_guard(tmp_path):
    """CRITICAL false-positive case. The attacked targets ARE the first 80 of the fair
    pool's 200 correct (src/se/attacks/select.py). The paper says so constantly, which puts
    a fair-pool label right next to attacked-pool numbers. A provenance mention is not a
    binding."""
    problems = _check(tmp_path, r"""
        The $80$ false-alarm targets are drawn from the fair pool's $200$ correct items;
        $8/80$ of them already sit at the ceiling, and $21/80$ within the top tenth of the
        range.
    """)
    assert not problems, _say(problems)


def test_the_contrastive_sentence_that_names_both_pools_correctly_passes(tmp_path):
    """`A gives x and y, whereas B gives z` puts B's label closer to y than A's is. Binding
    y to B would be wrong, and flagging it would cry wolf on the paper's most common
    construction."""
    problems = _check(tmp_path, r"""
        The fair pool gives a clean correct-versus-wrong separation of $0.463$ nats and
        AUROC $0.704$, whereas the \emph{attacked subset} gives $0.184$ nats and AUROC
        $0.579$.
    """)
    assert not problems, _say(problems)


def test_a_denied_label_does_not_count_as_the_binding_one(tmp_path):
    """Methods: '(the population the detector is characterised on, not the attacked
    subset)'. The denied label must neither satisfy nor accuse."""
    problems = _check(tmp_path, r"""
        Measured on the \emph{score-independent fair pool} (the population the detector is
        characterised on, not the attacked subset), correctly-answered questions have clean
        mean entropy $1.380$, leaving $0.923$ nats to the ceiling, while wrongly-answered
        questions sit at $1.843$, leaving $1.843$ nats to the floor.
    """)
    assert not problems, _say(problems)


def test_a_sub_sample_clause_is_provenance_not_attachment(tmp_path):
    """The Introduction's live wording: the stratum is named, its completeness asserted,
    and the fair pool mentioned only as provenance.

    REWRITTEN 2026-08-13. The old version of this control was the retired sentence verbatim
    -- 'across the $97$ targets of our attack campaign scored clean ($80$ correct, $17$
    wrong---a score-independent sub-sample of the fair pool below)' -- and it asserted
    GREEN. Both counts in that parenthetical are false, and commit 5d822b9 had already
    deleted the sentence from the paper; this test went on certifying it afterwards.
    """
    problems = _check(tmp_path, r"""
        At the standard $N{=}10$, on the $80$ correct-answer targets of our attack campaign
        scored clean---the false-alarm stratum, complete, and a score-independent prefix of
        the fair pool's correct stratum below---a quarter of correct answers ($21/80$) sit
        in the top tenth of the score's range.
    """)
    assert not problems, _say(problems)


def test_the_retired_realised_value_count_is_flagged_wherever_it_reappears(tmp_path):
    """Commit e6e7629 retired '22 distinct values' from all four sites: the count is
    monotone in targets scored (22 at n=80, 28 at n=200, 35 at n=2000) and the hide cell
    grew 17 -> 43 mid-session, falsifying the replacement claim before it was committed.
    Attaching the correct pool to it does not make it true, so the provenance rule -- not a
    population rule -- owns it."""
    for text in (
        r"Across the $97$ targets of the attack campaign the estimator realises only "
        r"$22$ distinct values.",
        r"On the score-independent \emph{fair} pool the estimator realises $22$ of the "
        r"$39$ attainable values.",
    ):
        problems = _check(tmp_path, text)
        assert any("STALE" in p for p in problems), _say(problems)


def test_a_negation_earlier_in_the_sentence_does_not_disarm_a_later_label(tmp_path):
    """Conclusion: 'This is not a claim that the detector fails: on the score-independent
    fair pool ... AUROC 0.704'. The 'not' is 58 chars and one colon away; it denies the
    claim, not the pool."""
    problems = _check(tmp_path, r"""
        This is not a claim that the detector fails: on the score-independent \emph{fair}
        pool ($200$ correct, $200$ hallucinating) it separates correct from hallucinating
        answers moderately well, at AUROC $0.704$ [$0.653$, $0.753$].
    """)
    assert not problems, _say(problems)


def test_a_clause_break_keeps_two_correctly_labelled_claims_apart(tmp_path):
    """A semicolon or a paragraph break is enough to stop one clause's pool label from
    accusing the next clause's number. Without this the paper's normal two-pool paragraph
    would fail on every draft."""
    for text in (
        r"""
        Across the $80$ correct-answer targets of the attack campaign we report saturation;
        AUROC is $0.704$ on the score-independent \emph{fair} pool ($200$ correct, $200$
        hallucinating).
        """,
        r"""
        Across the $80$ correct-answer targets of the attack campaign, scored clean, a
        quarter sit in the top tenth of the range.

        On the score-independent \emph{fair} pool ($200$ correct, $200$ hallucinating) the
        clean detector reaches AUROC $0.704$ [$0.653$, $0.753$].
        """,
    ):
        assert not _check(tmp_path, text), _say(_check(tmp_path, text))


def test_the_winners_curse_paragraph_carries_its_label_a_long_way(tmp_path):
    """Limitations puts the retention figure some 500 characters after the label that
    scopes it. The rule's window has to reach, without letting a distant fair-pool label
    accuse it.

    REWRITTEN 2026-08-19, AND FOR THE SECOND TIME THIS FILE WAS COMPLICIT. The version
    below used to be the `_def` paragraph verbatim -- $60$ false-alarm targets, $+0.698$ to
    $+0.315$, shrinkage $-0.383$ $[-0.529, -0.234]$, retention $45\\%$ $[25\\%, 65\\%]$,
    $36$ of $60$ -- and it asserted GREEN. The cell was rerun to `_defb` (n=69) and every
    one of those ten numbers was superseded; the paper was updated and this control went on
    certifying the retired paragraph, exactly as three controls certified `97 targets`
    after commit 5d822b9 deleted it. The text below is the LIVE Limitations wording. All
    ten retired values are now probes in RETIRED_WINNERS_CURSE.
    """
    problems = _check(tmp_path, r"""
        We quantify the resulting inflation directly, by re-scoring each \emph{selected}
        paraphrase on an independent sample. The re-scored set is the $69$ of the $80$
        false-alarm targets on which the optimiser found a paraphrase at all; on the other
        $11$ the search returned the original question, so there was no selection to
        re-test. Across those, the mean intended move falls from $+0.609$ nats at selection
        to $+0.268$ nats on fresh samples. The shrinkage is $-0.341$ nats with a bootstrap
        interval of $[-0.469, -0.212]$ that excludes zero. Retention is a ratio of means,
        and its interval is wide at $44\%$ $[23\%, 64\%]$. Signal remains either way---$37$
        of the $69$ keep a positive move and the two measurements correlate at $r{=}0.48$.
    """)
    assert not problems, _say(problems)


def test_the_circularity_artefact_reads_cleanly_next_to_the_fair_pool(tmp_path):
    """Introduction contribution (3). AUROC 1.0 sits one clause from a fair-pool label by
    design; 'by construction' is what licenses it."""
    problems = _check(tmp_path, r"""
        Score-independent target selection (without it the clean detector looks
        perfect---AUROC $1.0$ by construction, versus $0.704$ [$0.653$, $0.753$] on the
        fair pool).
    """)
    assert not problems, _say(problems)


def test_temperature_and_simulated_power_are_not_population_statistics(tmp_path):
    """1.0 is also a sampling temperature and 0.51 is also a simulated power at m=30.
    Neither may trip a population rule."""
    problems = _check(tmp_path, r"""
        Semantic entropy draws $N{=}10$ answers at temperature $1.0$ and clusters them by
        bidirectional entailment; the deployed analytic-null test has power $0.77$ at
        $m{=}50$ and $0.51$ at $m{=}30$.
    """)
    assert not problems, _say(problems)


def test_the_lattice_size_is_a_property_of_the_estimator_not_of_a_pool(tmp_path):
    """39 attainable values at N=10 follows from p(10)=42 with no data at all
    (results/fair_pool_granularity.md), so it needs no population label. Only the REALISED
    count does."""
    problems = _check(tmp_path, r"""
        At the standard $N{=}10$ the estimator lives on a lattice of just $39$ attainable
        values, of which only two fall in the top tenth of its range.
    """)
    assert not problems, _say(problems)


# ======================================================================================
# RUN PROVENANCE. A number can be bound to the right pool and still be stale.
# ======================================================================================
def test_stale_saturation_rate_from_the_superseded_run_is_flagged(tmp_path):
    """The Abstract carried the `_def` 39% while `_defb` was mid-flight (critique_log 31)."""
    problems = _check(tmp_path, r"""
        An optimised paraphrase attack drives a further $39\%$ of the attack campaign's
        targets onto the ceiling.
    """)
    assert any("39" in p and "STALE" in p for p in problems), _say(problems)


# --- the withdrawn N=40 floor intervals (2026-08-19) ---------------------------------
@pytest.mark.parametrize("text,want", [
    (r"the floor is an ordinary order statistic, $2.0\%$ [$0.8$, $5.03$]", "5.03"),
    (r"Wilson on a count of four would give [$0.78$, $5.03$]", "0.78"),
    (r"the question bootstrap gives [$0.5$, $4.0$] instead", "0.5"),
    (r"a measured $2.0\%$ [$0.8$, $5.0$] at $N{=}40$", "0.8"),
])
def test_a_withdrawn_n40_floor_interval_is_flagged(tmp_path, text, want):
    r"""PROBE. Both candidate intervals for the N=40 floor were withdrawn because the
    estimand is not identified at n=200 (`results/n40_floor_estimator_ruling.md` sec. 13);
    the coverage pairs often quoted alongside are branch-conditional -- 53.67%/0.00% under
    the calibrated Ewens fit, 95.06%/100% under the zero branch -- and neither pair is the
    reason on its own. Each of the four renderings the paper carried before the ruling
    must come back red.

    `5.03` is the one that matters most: it was live at three sites, the whole concession
    turned on it, and no rule in this file could match it, because the fair-pool rule's
    `\b5\.0\\?%` requires a percent sign immediately after the `5.0`."""
    problems = _check(tmp_path, text)
    stale = [p for p in problems if "STALE" in p]
    assert stale, _say(problems)
    assert any("N=40 floor" in p for p in stale), _say(stale)


def test_the_surviving_n40_numbers_are_not_flagged_as_withdrawn(tmp_path):
    r"""CONTROL, and the four things this arming must not break.

    `0.787` is the score-coupled replication AUROC and merely starts with `0.78`; `0.5`
    and `4.0` are live numbers that are only retired when ADJACENT, which is why the pair
    is armed and not the endpoints; `5.0\\%` is the live achieved operating point; and the
    at-cap interval `[0.0, 1.9]` is the one interval that SURVIVES at N=40."""
    problems = _check(tmp_path, r"""
        On the score-independent \emph{fair} pool ($200$ correct, $200$ hallucinating) the
        cap carries no mass ($0.0\%$ [$0.0$, $1.9$]) and the cheapest alarm costs
        $2.0\%$, while the threshold honouring a $5\%$ budget achieves $5.0\%$
        [$2.7$, $9.0$]. The nearer-looking $0.787$ is the same run scored under an
        all-samples-correct label. Elsewhere the judge separates $0.93$ from $0.5$, and
        the arm moves $4.0$ points.
    """)
    stale = [p for p in problems if "STALE" in p]
    assert not stale, _say(stale)


@pytest.mark.parametrize("text,want", [
    (r"Wilson on the floor count gives [$0.7804$, $5.0287$]", "0.7804"),
    (r"the interval was [$0.780$, $5.029$] before the ruling", "0.780"),
    (r"an upper end of $5.02866\%$ on a count of four", "5.02866"),
    (r"a lower end of $0.78037\%$ on a count of four", "0.78037"),
])
def test_the_full_precision_withdrawn_interval_is_flagged(tmp_path, text, want):
    r"""PROBE, added 2026-08-19. The four rules armed earlier that day matched only the
    ROUNDED renderings the paper happened to be carrying. Wilson on 4/200 is
    [$0.78037$, $5.02866$], and at full precision every one of those rules misses:
    `\b0\.78(?!\d)` is blocked by the next digit, and `\b5\.03` never sees a `5.03` at all
    because the digits read `5.02`.

    This is not a hypothetical rendering. `figures/fig_floor_budget_stats.json` records the
    withdrawn interval as `[0.7804, 5.0287]` -- correctly, that is a sidecar's job -- and
    the paper is one copy-paste away from it."""
    problems = _check(tmp_path, text)
    stale = [p for p in problems if "STALE" in p]
    assert stale, _say(problems)
    assert any("N=40 floor" in p for p in stale), _say(stale)


def test_the_full_precision_arming_does_not_catch_its_neighbours(tmp_path):
    r"""CONTROL for the two new rules, and the reason they are written at three decimals
    rather than two.

    `0.787` is the score-coupled replication AUROC: it starts `0.78` and must stay live,
    which is why the new lower-end rule demands `0.780`. `0.78` unrounded is the OLD rule's
    business and is already covered; `5.0` and `5.03` likewise. What must not happen is the
    new upper-end rule reaching a live `5.0\%`, a `0.5`, or the surviving at-cap interval
    at N=40."""
    problems = _check(tmp_path, r"""
        On the score-independent \emph{fair} pool ($200$ correct, $200$ hallucinating) the
        cap carries no mass ($0.0\%$ [$0.0$, $1.9$]) and the threshold honouring a $5\%$
        budget achieves $5.0\%$ [$2.7$, $9.0$]. Our replication reaches $0.787$ under the
        all-samples-correct label, against a clean fair-pool $0.704$ [$0.653$, $0.753$],
        and the judge agrees at $0.93$.
    """)
    stale = [p for p in problems if "STALE" in p]
    assert not stale, _say(stale)


def test_stale_ceiling_count_and_stale_correlations_are_flagged(tmp_path):
    """Methods carried a stale 39/80; the correlations are +0.71/+0.68 under `_defb`."""
    problems = _check(tmp_path, r"""
        Of the $80$ false-alarm targets of the attack campaign, $39/80$ finish at the
        ceiling; headroom and move correlate at $r{=}0.70$, and at $+0.67$ within the
        uncensored subset.
    """)
    stale = [p for p in problems if "STALE" in p]
    assert len(stale) >= 3, _say(problems)
    assert any("42/80" in p for p in stale), _say(stale)


def test_the_current_run_values_are_not_flagged_as_stale(tmp_path):
    """`_defb` is the definitive cell. Its numbers must pass, and the two-decimal AUROC
    rendering must not be mistaken for the retired +0.70 correlation."""
    problems = _check(tmp_path, r"""
        Of the $80$ false-alarm targets of the attack campaign, $42/80$ finish at the
        ceiling and $34/80$ were driven there by the attack; headroom and move correlate
        at $r{=}0.71$, and at $+0.68$ within the uncensored subset. On the
        score-independent \emph{fair} pool ($200$ correct, $200$ hallucinating) the
        detector reaches AUROC $0.70$.
    """)
    assert not problems, _say(problems)


# ======================================================================================
# THE INVERSION (2026-08-13). Four probes were run through the hardened guard and it
# returned GREEN on three genuine errors -- including one where the guard did not merely
# miss the stale count but BLESSED it, because `97 targets` and `17 wrong` were still on
# the attacked pool's LABEL list and a whole rule existed to legitimise them.
#
# The four are reconstructed verbatim. Each one FAILS without the corresponding change:
# probe 1 needs the label retirement plus GROWING_CELLS, probes 3 and 4 need the
# replication rules and their `exclusive` flag.
# ======================================================================================
INVERSION_PROBES: list[tuple[str, str, str]] = [
    (
        "retired_97_and_17_were_accepted_as_labels",
        r"""
        Across the $97$ targets of the attack campaign ($80$ correct, $17$ wrong), a tenth
        of correct answers ($8/80$) already sit at the estimator's maximum and $21/80$ sit
        in the top tenth of the range.
        """,
        "97",
    ),
    (
        "replication_auroc_sold_as_a_fair_pool_number",
        r"""
        On the \emph{fair} pool ($200$ correct, $200$ hallucinating) our SE replication
        reaches AUROC $0.694$.
        """,
        "0.694",
    ),
    (
        "replication_auroc_sold_as_an_attacked_pool_number",
        r"Measured on the attacked subset the replication AUROC is $0.730$.",
        "0.730",
    ),
]


@pytest.mark.parametrize("name,text,token", INVERSION_PROBES,
                         ids=[p[0] for p in INVERSION_PROBES])
def test_the_inversion_probes_are_caught(tmp_path, name, text, token):
    problems = _check(tmp_path, text, name=f"{name}.tex")
    assert problems, f"probe {name!r} was accepted -- the guard is inverted on it"
    assert any(token in p for p in problems), _say(problems)


def test_the_fourth_probe_the_current_truth_is_also_a_live_count(tmp_path):
    """The audit's fourth probe, and the one place I depart from its expected verdict.

    The audit called '$80$ correct and $52$ wrong' GREEN because 52 is the count TODAY.
    It is flagged. 52 was 46 at commit 5d822b9, 43 six hours before that, and 17 when the
    paper first named it; the FA cell is closed at 80 and the hide cell is not closed at
    all. Commit 5d822b9's own justification for deleting 97 -- 'wrong the moment it was
    committed and wrong again at any later value' -- is a statement about 52 as much as
    about 17, and Methods already refuses to quote the number for that reason ('the hide
    cell is still filling ... any figure we quote for it goes stale between drafts').
    Treating a currently-accurate count as safe is the assumption that produced the bug.
    """
    problems = _check(tmp_path, r"""
        Across the targets of the attack campaign ($80$ correct and $52$ wrong), a tenth
        of correct answers ($8/80$) already sit at the estimator's maximum.
    """)
    assert any("52" in p for p in problems), _say(problems)
    # ...and it is flagged for being a live count, not for being mislabelled.
    assert any("growing denominator" in p for p in problems), _say(problems)


# ======================================================================================
# GROWING DENOMINATORS. The general form: a literal count of a cell that is still filling,
# or any total that sums over one. These must be caught WITHOUT the value ever having been
# written down here -- the enumerated list is what failed.
# ======================================================================================
def test_a_hide_count_no_one_has_ever_enumerated_is_flagged(tmp_path):
    """61 appears nowhere in this repo. The hide arm will pass through it on the way to 80,
    and the guard has to be red on it the day it does, with no edit."""
    problems = _check(tmp_path, r"The attack campaign covers $80$ correct and $61$ wrong.")
    assert any("61" in p for p in problems), _say(problems)


def test_the_registry_is_still_keyed_by_cell_and_not_by_value(tmp_path):
    """REWRITTEN 2026-08-19. This test used to be
    test_the_planned_hide_n_is_not_admissible_while_the_cell_is_open, and it asserted that
    '80 wrong' was an ERROR -- correct while the hide arm was filling THROUGH 80 on its way
    to 80, and false from 2026-08-13, when the arm landed there. It went on asserting it for
    six days, which is half of why nobody noticed the registry had expired: the guard said
    the true sentence was wrong, and the suite said the guard was right. See defect 7.

    The structural point it existed to make is still true and still needs a test, so it is
    made with values that are live. The registry is keyed by CELL, so a count frozen for one
    cell is NOT admissible for another: 69 is the winner's-curse subset, 1424 is the full
    labelled pool's correct stratum, and neither is a number of hide targets.
    """
    for wrong in ("69", "1424", "300"):
        problems = _check(
            tmp_path, rf"The campaign covers $80$ correct and ${wrong}$ wrong targets.")
        assert any(f"{wrong} wrong" in p for p in problems), \
            f"{wrong} is frozen for a DIFFERENT cell and must not be admissible here:\n" \
            + _say(problems)


def test_the_closed_hide_stratum_may_state_its_count_and_its_total(tmp_path):
    """THE control for defect 7, and the reason it is a defect rather than a safe default.

    Both campaign strata closed at their pre-registered n=80 on 2026-08-13
    (results/fair_recompute_report.md, 'SE / hide (n=80)' and an AUROC table at n=160;
    commit 9e9347c, 'the true campaign total is 160'). HIDE_OPEN was not updated, so the
    guard spent six days reporting each of these TRUE sentences as a growing-denominator
    error. A guard that fires on true statements teaches its reader to skip it, which is
    critique_log 35 -- 'a check that cannot fail is not a check' -- reached from the other
    direction and faster, because a silent rule merely fails to help while a crying one
    costs time on every run.
    """
    for true_now in (
        r"The campaign covers $80$ correct and $80$ wrong targets.",
        r"The attack campaign's $80$ hide targets are scored clean.",
        r"Across all $160$ targets of the attack campaign, both strata are complete.",
        r"The campaign covers $80$ hide and $80$ false-alarm targets, $160$ in total.",
        r"""
        Both arms of the attack campaign are now at their pre-registered $n$: the
        false-alarm stratum at $80$ correct-answer targets and the hide stratum at $80$
        wrong-answer targets, for $160$ targets in total.
        """,
    ):
        problems = _check(tmp_path, true_now)
        assert not problems, f"a TRUE statement was flagged:\n{true_now}\n" + _say(problems)


def test_the_campaign_total_is_not_the_same_constant_as_the_hide_cell(tmp_path):
    """The trap in the edit the previous pass left spelled out in a comment, and the reason
    I did not apply it verbatim.

    That note said the fix was `HIDE_OPEN = frozenset({80})`. But HIDE_OPEN was doing double
    duty: it was the hide CELL's admissible set AND the admissible set for every 'the N
    targets of the attack campaign' pattern -- the POOL AS A WHOLE. The two were the same
    constant only because both were empty. Setting it to {80} would have licensed 'the 80
    targets of the attack campaign', which asserts the campaign totals 80 -- half of it --
    and that is the exact stratum/sum confusion the FA-versus-hide split exists to prevent.
    The cell admits 80; the pool as a whole admits 160, and they are now two constants.
    """
    problems = _check(
        tmp_path, r"Across the $80$ targets of the attack campaign we report saturation.")
    assert any("80" in p and "growing denominator" in p for p in problems), \
        "'the 80 targets of the campaign' claims a total of 80; the total is 160:\n" \
        + _say(problems)

    # ...while the same 80 QUALIFIED by its stratum is a stratum count, and correct.
    ok = _check(
        tmp_path,
        r"Across the $80$ correct-answer targets of the attack campaign, a tenth sit at "
        r"the cap.")
    assert not ok, _say(ok)


def test_a_stale_campaign_total_is_still_flagged_after_the_closure(tmp_path):
    """Relaxing the registry must not relax the rule it belongs to. Every count the arm
    passed THROUGH on its way to 80 is still wrong, and so is every total but 160."""
    for text, token in (
        (r"Across the $97$ targets of the attack campaign, a tenth sit at the cap.", "97"),
        (r"The campaign covers $80$ correct and $52$ wrong targets.", "52"),
        (r"The campaign covers $80$ correct and $17$ wrong targets.", "17"),
        (r"The attack campaign's $132$ targets are scored clean.", "132"),
        (r"We report $161$ targets in total for the attack campaign.", "161"),
        (r"The $140$-target pool of the attack campaign is described below.", "140"),
    ):
        problems = _check(tmp_path, text)
        assert any(token in p for p in problems), f"{token}: " + _say(problems)


@pytest.mark.parametrize("text,token", [
    (r"Across the $132$ targets of the attack campaign we report saturation.", "132"),
    (r"The attack campaign's $121$ targets are scored clean.", "121"),
    (r"The $97$-target pool of the attack campaign is described in Section 4.", "97"),
    (r"We report $97$ targets in total for the attack campaign.", "97"),
    (r"We attack a pool of $97$, drawn from the fair pool.", "97"),
    (r"The attack campaign is described below. The $97$ targets were scored clean.", "97"),
    (r"Across $97$ attacked targets, scored clean, a tenth sit at the cap.", "97"),
    (r"The hide arm now covers $52$ hide targets against its planned $80$.", "52"),
    (r"The campaign covers $52$ wrong-answer targets.", "52"),
    (r"Earlier drafts said $41$ wrong, then $46$ wrong, in the hide arm.", "41"),
])
def test_every_rendering_of_a_moving_total_is_flagged(tmp_path, text, token):
    """One construction per row. The bug arrived as 'the 97 targets (80 correct, 17 wrong)',
    but a total can be written a dozen ways and the rule has to reach all of them."""
    problems = _check(tmp_path, text)
    assert any(token in p for p in problems), _say(problems)


def test_latex_cannot_hide_a_moving_total(tmp_path):
    """strip_latex leaves a space where it removed a command, so `$\\mathbf{97}$-target`
    flattens to `97 -target`. The markup lesson, applied to the new rule."""
    for text in (
        r"Across the \emph{97} targets of the attack campaign, a tenth sit at the cap.",
        r"The $\mathbf{97}$-target pool of the attack campaign is described below.",
    ):
        assert any("97" in p for p in _check(tmp_path, text)), text


# --- CONTROLS: the growing rule must not swallow the counts that are actually true ------
def test_the_complete_false_alarm_stratum_is_still_a_valid_label(tmp_path):
    """THE control for this whole change. `80 correct` stays a label -- the FA cell is
    complete at its pre-registered n (results/fa_n80_milestone.md, 80/80) -- while
    `17 wrong` does not. A rule that flagged both would be no better than one that flagged
    neither, and would take the paper's three live sites down with it."""
    good = _check(tmp_path, r"""
        Across the $80$ correct-answer targets of the attack campaign, scored clean, a
        tenth of correct answers ($8/80$) sit at the estimator's maximum and $21/80$ within
        the top tenth of the range.
    """)
    assert not good, _say(good)

    bad = _check(tmp_path, r"""
        Across the $80$ correct and $17$ wrong targets of the attack campaign, scored
        clean, a tenth of correct answers ($8/80$) sit at the estimator's maximum.
    """)
    assert any("17" in p for p in bad), _say(bad)


def test_subset_counts_inside_the_stratum_are_not_pool_totals(tmp_path):
    """Discussion says 'those $21$ targets' and the Abstract '$15$ saturated targets'.
    Both are counts of a slice, not assertions about the pool's size. A bare `N targets`
    rule would fire on both, which is why the pool has to be named or the quantifier has to
    be a totalising one."""
    problems = _check(tmp_path, r"""
        On the attack campaign's $80$ correct-answer targets, a quarter ($21/80$) sit in a
        region containing just two of the estimator's $39$ attainable values, so those
        $21$ targets occupy one of two points; and on $15$ saturated targets re-scored at
        $N{=}20$, lifting the cap by $0.693$ nats left $20\%$ still pinned.
    """)
    assert not problems, _say(problems)


def test_the_fair_pools_wrong_stratum_may_be_named_by_direction(tmp_path):
    """A false positive found by sweeping the rule across results/ before shipping it.

    results/fair_pool_report.md names the fair pool's strata by ATTACK DIRECTION -- 'the
    IDENTICAL 200 hide + 200 false-alarm ids' -- so a hide-word pattern reaches a stratum
    that is complete, and 200 is admissible there.

    REWRITTEN 2026-08-19 (defect 7). The second half of this test used to assert that
    '$80$ hide targets of the attack campaign' was an ERROR, on the reasoning that 'the hide
    arm is planned at 80 and will pass through it, and can never be 200'. The arm stopped
    passing through 80 on 2026-08-13: it LANDED there, at its pre-registered n. So the
    asymmetry this test was built around is gone, and the sentence it called an error is the
    campaign's completion. What remains true, and is what the second half now checks, is
    that a hide-word pattern must not admit a count belonging to some other cell.
    """
    ok = _check(tmp_path, r"""
        The SRE campaigns use the identical $200$ hide and $200$ false-alarm ids from the
        score-independent \emph{fair} pool ($200$ correct, $200$ hallucinating).
    """)
    assert not ok, _say(ok)

    # the closed hide arm, named by direction -- true since 2026-08-13
    closed = _check(tmp_path, r"The campaign covers $80$ hide targets of the attack campaign.")
    assert not closed, _say(closed)

    # ...but a count that belongs to no cell reachable by a hide word is still an error.
    bad = _check(tmp_path, r"The campaign covers $52$ hide targets of the attack campaign.")
    assert any("52" in p for p in bad), _say(bad)


def test_the_frozen_registry_still_matches_the_artifact_that_closed_the_cell():
    """THE TEST THAT WOULD HAVE CAUGHT DEFECT 7, and the reason it is worth more than the
    probes around it.

    Defect 5 retired stale LABELS, defect 6 stale VALUES, defect 7 a stale FROZEN COUNT.
    Each was found by a human sweep, months apart, and each time the standing rule written
    down afterwards was 'whoever reruns a cell owns the lists keyed to it' -- an instruction
    to remember something, which is the control that had just failed. The winner's-curse
    family got a real fix instead (test_the_guard_tracks_the_definitive_winners_curse_
    checkpoint reads the checkpoint and fails if the registry disagrees). This is the same
    fix for the campaign cells: the registry is checked against the artifact, so the next
    time a cell's n moves the suite says so, on the day it moves, without anyone sweeping.
    """
    from check_population_labels import FROZEN_COUNTS, GROWING_CELLS, HIDE_OR_FAIR

    report = (REPO / "results" / "fair_recompute_report.md").read_text(encoding="utf-8")

    # The report writes each closed cell as "**SE / hide** (n=80)".
    cells = dict((name, int(n)) for name, n in
                 re.findall(r"\*\*SE / (\w+)\*\*\s*\(n=(\d+)\)", report))
    assert set(cells) == {"false_alarm", "hide"}, (
        f"the fair-recompute report no longer names both SE cells the way this test reads "
        f"them (found {cells}). Re-derive the registry by hand and re-point this test.")

    for cell, n in cells.items():
        assert n in FROZEN_COUNTS, (
            f"the {cell} cell stands at n={n} and {n} is not a declared frozen count "
            f"(frozen: {sorted(FROZEN_COUNTS)}). If that cell is CLOSED, declare it -- an "
            "undeclared closed cell makes the guard flag true statements, which is how "
            "'80 wrong' was reported as an error for six days after it became correct.")

    total = sum(cells.values())
    assert total in FROZEN_COUNTS, (
        f"both cells are at their n, so the campaign total is {total}, and it is not "
        f"declared (frozen: {sorted(FROZEN_COUNTS)}).")
    assert str(total) in FROZEN_COUNTS[total], FROZEN_COUNTS[total]

    # ...and the hide cell's own count must be reachable by a hide-word pattern, or the
    # declaration is inert: FROZEN_COUNTS is documented as "the union, for reporting only".
    assert cells["hide"] in HIDE_OR_FAIR, (
        f"the hide cell is closed at n={cells['hide']} and FROZEN_COUNTS knows it, but the "
        "hide-word growing patterns still do not admit it, so the guard would go on "
        "flagging '80 wrong'. Declaring a cell in FROZEN_COUNTS is not enough on its own.")

    # The total must NOT leak into the sets that mean "one stratum": a stratum is 80.
    stratum_only = [allowed for pat, what, allowed, _ in GROWING_CELLS
                    if what.startswith("a named stratum")]
    assert stratum_only, "the named-stratum patterns have been renamed"
    for allowed in stratum_only:
        assert total not in allowed, (
            f"{total} is the campaign TOTAL and must not be admissible where a single "
            "stratum is named -- that is the stratum/sum confusion the split exists for.")


def test_target_counts_outside_this_campaign_are_none_of_the_rules_business(tmp_path):
    """The loose 'the N targets' pattern is context-gated. Without the gate it would fire
    on every target count in the paper and the rule would be unusable."""
    problems = _check(
        tmp_path, r"The benign sweep covers the $500$ targets of an unrelated study.")
    assert not problems, _say(problems)


def test_the_papers_refusal_to_quote_a_hide_count_passes(tmp_path):
    """Methods' live wording. Naming the planned n while declining to give a current count
    is the correct behaviour, and the guard must not punish it."""
    problems = _check(tmp_path, r"""
        We deliberately attach no count to that second clause here: the hide cell is still
        filling against its planned $80$, so any figure we quote for it goes stale between
        drafts. We state the hide-side counts once, with their final $n$, when that cell
        completes.
    """)
    assert not problems, _say(problems)


# ======================================================================================
# ROUND THREE (2026-08-19). THE GUARDED VALUES WENT STALE, AND THE RULE WENT QUIET.
#
# Round two retired four LABELS that had stopped being true. It did not ask the same
# question of `numbers`. The winner's-curse cell was then rerun -- `_def` (n=60) to `_defb`
# (n=69) -- and every figure in it moved, while the rule went on listing the old ones. A
# rule pointed at values that no longer occur matches nothing, and a rule that matches
# nothing cannot fail: the checker printed OK on this family while all ten live numbers,
# across four sites in the paper, were unguarded.
#
# Every probe below was GREEN before the rearming. Each is paired with a control.
# ======================================================================================
LIVE_WINNERS_CURSE: list[tuple[str, str, str]] = [
    # Unlabelled first: "unarmed" means the number could be written anywhere, attached to
    # nothing, and the checker would print OK. Each of these was GREEN before the rearming.
    (
        "live_retention_and_its_interval_unlabelled",
        r"Retention is $44\%$, with a bootstrap interval of $[23\%, 64\%]$.",
        "44",
    ),
    (
        "live_shrinkage_and_its_interval_unlabelled",
        r"The shrinkage is $-0.341$ nats, with an interval of $[-0.469, -0.212]$.",
        "0.341",
    ),
    (
        "live_selection_and_fresh_means_unlabelled",
        r"The mean intended move falls from $+0.609$ nats to $+0.268$ nats.",
        "0.609",
    ),
    (
        "live_positive_move_count_unlabelled",
        r"$37$ of the $69$ keep a positive move, and the two correlate at $r{=}0.48$.",
        "37 of the 69",
    ),
    # ...and then mislabelled, which is the error the hardening exists for: the owning
    # label trails, so the fair pool is what actually binds.
    (
        "live_retention_bound_to_the_fair_pool",
        r"""
        On the score-independent \emph{fair} pool ($200$ correct, $200$ hallucinating),
        $44\%$ $[23\%, 64\%]$ of the apparent effect survives re-scoring.
        """,
        "44",
    ),
    (
        "live_positive_move_count_bound_to_the_fair_pool",
        r"""
        On the score-independent \emph{fair} pool ($200$ correct, $200$ hallucinating),
        $37$ of the $69$ keep a positive move after re-scoring.
        """,
        "37 of the 69",
    ),
]


@pytest.mark.parametrize("name,text,token", LIVE_WINNERS_CURSE,
                         ids=[p[0] for p in LIVE_WINNERS_CURSE])
def test_the_live_winners_curse_numbers_are_guarded_at_all(tmp_path, name, text, token):
    """The rule listed `45%`, `0.698`, `0.315`, `36 of 60` and friends -- not one of which
    survives the `_defb` rerun. Every probe here was accepted before 2026-08-19."""
    problems = _check(tmp_path, text, name=f"{name}.tex")
    assert problems, f"probe {name!r} was accepted -- the rule is unarmed on the live cell"
    assert any(token in p for p in problems), _say(problems)


# Each entry: the retired `_def` rendering, and the `_defb` value that replaced it.
RETIRED_WINNERS_CURSE: list[tuple[str, str]] = [
    (r"Re-scoring retains $45\%$ of the effect.", "44"),
    (r"The retention interval on re-scoring is $[25\%, 65\%]$.", "23"),
    (r"On re-scoring, the mean move at selection is $+0.698$ nats.", "0.609"),
    (r"On re-scoring, the mean move on fresh samples is $+0.315$ nats.", "0.268"),
    (r"The shrinkage on re-scoring is $-0.383$ nats.", "0.341"),
    (r"The shrinkage interval on re-scoring is $[-0.529, -0.234]$.", "0.469"),
    (r"On re-scoring, $36$ of $60$ targets keep a positive move.", "37 of the 69"),
    (r"The two re-scored measurements correlate at $r{=}0.46$.", "0.48"),
]


@pytest.mark.parametrize("text,current", RETIRED_WINNERS_CURSE,
                         ids=[t[1] for t in RETIRED_WINNERS_CURSE])
def test_every_retired_winners_curse_value_is_flagged_as_stale(tmp_path, text, current):
    """A superseded number must be reported wherever it reappears -- the mechanism this
    repo already uses for `39/80` and `+0.70`. Before the rearming all eight of these were
    LIVE ENTRIES in the guarded set, so writing one into the paper was not merely
    unreported: it was certified as correctly labelled."""
    problems = _check(tmp_path, text)
    stale = [p for p in problems if "STALE" in p]
    assert stale, _say(problems)
    assert any(current in p for p in stale), _say(stale)


def test_the_stale_winners_curse_gate_does_not_fire_on_the_replication_auroc(tmp_path):
    """THE control for the `_WC_CTX` gate, and the resolution of a hazard the module
    docstring has carried since the guard was written.

    0.698 is two different quantities: the retired selection-time mean move in NATS, and
    0.6977 -> 0.698, the substring-oracle AUROC of the 2000-question replication run. It
    used to be owned by the winner's-curse rule outright, so a replication 0.698 was
    reported against the wrong population and made to demand a re-scoring label. It is now
    retired behind a re-scoring context gate: stale where the diagnostic is being discussed,
    silent where it is not.
    """
    ok = _check(tmp_path, r"""
        Under the substring oracle our SE replication on $2000$ questions reaches AUROC
        $0.698$, which the alias-aware span oracle refines to $0.694$.
    """)
    assert not ok, _say(ok)

    bad = _check(tmp_path, r"""
        Re-scoring each selected paraphrase on an independent sample, the mean intended
        move at selection is $+0.698$ nats.
    """)
    assert any("0.698" in p and "STALE" in p for p in bad), _say(bad)


# --- the CELL, not the values: 69 is now a frozen count in its own right ----------------
def test_the_re_scored_cell_size_cannot_borrow_its_neighbours_licence(tmp_path):
    """THE defect this round of the audit was opened on.

    The live phrasing is "the $69$ of the $80$ false-alarm targets". The only growing-cell
    pattern that reached it captured `80 false-alarm`, found 80 admissible for the FA
    stratum, and never looked at the 69 at all -- so the cell size passed on its
    NEIGHBOUR's licence. The retired 60 and any future rerun's n passed with it.
    """
    for wrong in ("60", "71", "80"):
        problems = _check(
            tmp_path,
            rf"The re-scored set is the ${wrong}$ of the $80$ false-alarm targets on "
            r"which the optimiser found a paraphrase.")
        assert any(wrong in p and "growing denominator" in p for p in problems), \
            f"cell size {wrong} was accepted:\n" + _say(problems)


def test_the_true_re_scored_cell_size_passes(tmp_path):
    """...and the control, or the rule would take the live Limitations paragraph down."""
    problems = _check(tmp_path, r"""
        The re-scored set is the $69$ of the $80$ false-alarm targets on which the
        optimiser found a paraphrase at all; on the other $11$ the search returned the
        original question.
    """)
    assert not problems, _say(problems)


def test_the_re_scored_cell_is_checked_as_a_denominator_too(tmp_path):
    """`37 of the 69 keep a positive move` states the same cell as a denominator. A rerun
    moves it, and the guard has to see it there as well as in the defining phrase."""
    bad = _check(tmp_path, r"On re-scoring, $37$ of the $60$ keep a positive move.")
    assert any("growing denominator" in p for p in bad), _say(bad)

    ok = _check(tmp_path, r"On re-scoring, $37$ of the $69$ keep a positive move.")
    assert not ok, _say(ok)


def test_the_complement_of_the_re_scored_cell_is_guarded(tmp_path):
    """$69 + 11 = 80$ is an identity, so the 11 moves whenever the 69 does. It is
    context-gated: "the other 11" of something unrelated is none of this rule's business."""
    bad = _check(tmp_path, r"""
        Of the false-alarm targets, the optimiser found a paraphrase for most; on the other
        $20$ the search returned the original question, so re-scoring had nothing to test.
    """)
    assert any("20" in p for p in bad), _say(bad)

    unrelated = _check(tmp_path, r"The benign sweep covers the other $20$ questions.")
    assert not unrelated, _say(unrelated)


def test_an_escaped_percent_cannot_hide_the_retention_row(tmp_path):
    """Defect 4, pointed at the newly armed family. `strip_latex` needs `(?<!\\)%`: without
    the negative lookbehind a literal \\% eats to end of line and the whole row escapes
    checking -- so the guard would go quiet on exactly the numbers just rearmed."""
    row = (r"Retention (\% of the effect) & $44\%$ & measured on the "
           r"score-independent \emph{fair} pool \\")
    assert "44" in strip_latex(row), strip_latex(row)
    problems = _check(tmp_path, row)
    assert any("44" in p for p in problems), _say(problems)
    # ...and the mechanism, stated directly: a literal \% survives, a real comment does not.
    assert "44" in strip_latex(r"$44\%$ % secret comment")
    assert "secret" not in strip_latex(r"$44\%$ % secret comment")


# --- structural: the guarded VALUES expire exactly as the LABELS did --------------------
def test_the_guard_tracks_the_definitive_winners_curse_checkpoint():
    """The standing rule from round two -- "anything appearing in BOTH `labels` and the
    paper's numbers must be re-derived from an artifact whenever that artifact is rerun" --
    with the artifact actually read, so the NEXT rerun breaks a test instead of going quiet.

    `_def` has 60 records and `_defb` has 69; the guard must key on the definitive one.
    """
    from check_population_labels import FROZEN_COUNTS, POOLS

    defb = REPO / "results" / "winners_curse_ckpt_se_false_alarm_defb.jsonl"
    n_live = sum(1 for line in defb.read_text(encoding="utf-8").splitlines() if line.strip())
    assert n_live in FROZEN_COUNTS, (
        f"the definitive winner's-curse cell holds {n_live} records and {n_live} is not a "
        f"declared frozen count (frozen: {sorted(FROZEN_COUNTS)}). Whoever reran the cell "
        "owns FROZEN_COUNTS, the rescored labels and the rule's `numbers` for it.")
    assert "winner" in FROZEN_COUNTS[n_live].lower()

    superseded = REPO / "results" / "winners_curse_ckpt_se_false_alarm_def.jsonl"
    n_old = sum(1 for ln in superseded.read_text(encoding="utf-8").splitlines() if ln.strip())
    assert n_old not in FROZEN_COUNTS, f"{n_old} is the SUPERSEDED cell size"
    labels = " ".join(p for spec in POOLS.values() for p in spec["labels"])
    assert str(n_old) not in labels, f"{n_old} is still a pool LABEL"


def test_no_guarded_number_is_also_a_superseded_one():
    """A value cannot be both live and retired. If it is, one of the two rules is keyed to
    a run that no longer exists -- which is defect 6 in whichever direction it points."""
    from check_population_labels import RULES, SUPERSEDED

    probes = ["45%", "25%", "65%", "0.383", "0.698", "0.315", "0.529", "0.234",
              "36 of 60", "39/80", "31/80", "38.75", "22 distinct",
              "44%", "23%", "64%", "-0.341", "-0.469", "-0.212", "+0.609", "+0.268",
              "37 of the 69", "r = 0.48", "42/80", "34/80", "0.704", "0.694",
              # round four: the realised distinct-value shape, retired generatively. Every
              # one of these WAS both guarded and retired before the strike -- guarded by
              # the fair-pool granularity rule, retired by the shape SUPERSEDED already
              # covered for numerator 22. That is exactly the clash this test names.
              "31 distinct values", "31 of the 39", "28 of the 39", "26 of the 39",
              "35 distinct values", "47 distinct values",
              # ...and the fourth population's floor, which must be guarded and NOT retired.
              "10.5%", "150/1424", "12.2",
              # round five: the coverage pair is RETIRED bare and must not also be a
              # guarded number, and its four live neighbours must be neither.
              "53.7%", "0.00%", "53.4%", "53.5%", "53.8%", "53.9%", "0.0%"]
    clashes = []
    for probe in probes:
        guarded = [r["name"] for r in RULES
                   if any(re.search(p, probe, re.IGNORECASE) for p in r["numbers"])]
        retired = [s["quantity"] for s in SUPERSEDED
                   if re.search(s["pattern"], probe, re.IGNORECASE)]
        if guarded and retired:
            clashes.append(f"{probe!r}: guarded by {guarded} AND retired as {retired}")
    assert not clashes, "\n  ".join(clashes)


def test_the_retired_winners_curse_values_are_gone_from_the_guarded_set():
    """Named explicitly, the way round two named its four labels, so that a failure says
    which number came back rather than pointing at a generic invariant."""
    from check_population_labels import RULES

    wc = [r for r in RULES if r["name"].startswith("winner")]
    assert len(wc) == 1
    flat = " ".join(_literal(p) for p in wc[0]["numbers"])

    def names(value: str) -> bool:
        """Is this the whole number, not a fragment of a longer one? `60` must not be
        found inside `+0.609`, which is what a naive substring check does."""
        return bool(re.search(rf"(?<![\d.]){re.escape(value)}(?!\d)", flat))

    for retired in ("45", "25", "65", "0.383", "0.698", "0.315", "0.529", "0.234", "60"):
        assert not names(retired), f"{retired!r} is a retired `_def` value, not a live one"
    for live in ("44", "23", "64", "0.341", "0.469", "0.212", "0.609", "0.268", "69"):
        assert names(live), f"{live!r} is a live `_defb` value and must be guarded"


# ======================================================================================
# ROUND THREE, PART TWO: NEVER KEYED AT ALL.
#
# A rerun disarms a rule that exists. This is the other way to be silent -- a result
# arrives, lands in the paper, and no rule was ever written for it. Six live values were in
# that state on 2026-08-19: the N=40 achievable grid (5.0%, and 2.0% arriving), the N=20
# replay floor (3.0%), and the Eq.(5)-vs-discrete saturation rates over the 2000-question
# pass (14.8%, 20.0%, 27.8%).
# ======================================================================================
def test_the_eq5_saturation_rates_are_guarded_at_all(tmp_path):
    """295/2000 at the cap, 399/2000 and 556/2000 in the top decile
    (results/rescore_likelihoods.md). No rule had ever heard of any of them."""
    for token in ("14.8", "20.0", "27.8"):
        problems = _check(
            tmp_path, rf"The at-cap share under the discrete estimator is ${token}\%$.")
        assert any(token in p for p in problems), f"{token}% is unguarded"


def test_an_eq5_rate_may_not_be_read_as_a_fair_pool_rate(tmp_path):
    """These are rates over 2000 questions, not over the fair pool's 400. The paragraph
    that carries them names the fair pool in its own scoping sentence, which is exactly the
    adjacency that produced six of this project's population errors."""
    problems = _check(tmp_path, r"""
        On the score-independent \emph{fair} pool ($200$ correct, $200$ hallucinating),
        $14.8\%$ of answers sit at the cap under the discrete estimator.
    """)
    assert any("14.8" in p and "MISLABELLED" in p for p in problems), _say(problems)


def test_the_live_eq5_wording_passes(tmp_path):
    """Methods' actual sentence. The label is `2000 cached sample sets`, a rendering none of
    the replication pool's labels matched until this pass -- so this control fails without
    the label edit as surely as without the number edit."""
    problems = _check(tmp_path, r"""
        Re-scoring our $2000$ cached sample sets under Eq.~(5) with the generating model's
        own length-normalised sequence likelihoods---holding the clustering fixed---puts
        $0.0\%$ [$0.0$, $0.2$] of them at the cap, against $14.8\%$ [$13.3$, $16.4$] under
        the discrete estimator.
    """)
    assert not problems, _say(problems)


def test_the_27_8_collision_is_resolved_by_population_not_by_value(tmp_path):
    """THE collision probe. $27.8\\%$ is TWO numbers: 556/2000 in the top decile of the
    replication pass (live), and 27/97 on the attacked subset (retired -- 80 correct plus a
    hide arm truncated at 17). A value-keyed rule must either miss the retired one or cry
    wolf on the live one. Neither rule here is value-keyed: the live rate is owned by the
    replication pass and reports a foreign label bound to it, and the retired rendering is
    caught by its 97 DENOMINATOR, generatively, with no numerator enumerated anywhere.
    """
    live_but_mislabelled = _check(tmp_path, r"""
        Across the $80$ correct-answer targets of our attack campaign, $27.8\%$ fall in the
        top tenth of the range.
    """)
    assert any("27.8" in p and "MISLABELLED" in p for p in live_but_mislabelled), \
        _say(live_but_mislabelled)

    retired = _check(tmp_path, r"""
        Across the targets of the attack campaign, $27/97$ fall in the top tenth of the
        range and $12/97$ sit at the ceiling.
    """)
    stale = [p for p in retired if "STALE" in p]
    assert any("27/97" in p for p in stale), _say(retired)
    assert any("12/97" in p for p in stale), "the rule must be generative, not enumerated"

    # ...and the live rate, correctly attributed, is clean.
    ok = _check(tmp_path, r"""
        Over our $2000$ cached sample sets, $27.8\%$ [$25.9$, $29.8$] fall in the top tenth
        of the range under the discrete estimator.
    """)
    assert not ok, _say(ok)


def test_the_n40_operating_point_is_guarded_and_bound_to_its_stratum(tmp_path):
    """5.0% is 10/200 on the fair pool's CORRECT stratum -- the same 200 answers as the
    9.5% floor it is contrasted with. It appears at three sites and was unguarded at all
    three. 2.0% (4/200) is guarded before it lands, this file's standing practice."""
    for token in ("5.0", "2.0"):
        bare = _check(tmp_path, rf"A $5\%$ budget is honoured at an achieved ${token}\%$.")
        assert any(token in p for p in bare), f"{token}% is unguarded"

    mislabelled = _check(tmp_path, r"""
        Across the $80$ correct-answer targets of the attack campaign, the $5\%$ budget is
        honoured at $N{=}40$ at an achieved $5.0\%$.
    """)
    assert any("5.0" in p and "MISLABELLED" in p for p in mislabelled), _say(mislabelled)

    ok = _check(tmp_path, r"""
        Running the same $200$ correct answers out to $N{=}40$ buys the missing operating
        point---the ceiling atom empties and a $5\%$ budget is honoured at an achieved
        $5.0\%$.
    """)
    assert not ok, _say(ok)


# ======================================================================================
# ROUND FOUR (2026-08-19). A FOURTH POPULATION, NEVER REGISTERED -- AND THE GUARD WENT RED
# ON IT.
#
# Defect 6 found values with no rule. This is a whole POPULATION with no POOLS entry: the
# full labelled pool's correct stratum, n=1424, carrying the achievable-FPR floor
# 150/1424 = 10.5% [9.0, 12.2] at four sites including the Abstract and the Conclusion.
# Because 1424 and 576 were not declared frozen, the growing rule was reporting the paper's
# own "(1424 correct and 576 hallucinating)" as counts of a cell that is still filling --
# four false positives, defect 7's shape one population over.
#
# THE HARD PART IS THE NESTING. The fair pool's 200-answer correct stratum is a STRICT
# SUBSET of the 1424, so the two estimate the same parameter and the Discussion crosses
# between them on purpose. A genuine mislabelling must fire; the cross-reference must not.
# ======================================================================================
def test_the_full_pool_floor_is_guarded_at_all(tmp_path):
    """150/1424 = 10.5% [9.0, 12.2] (results/achievable_fpr_grid.md, Appendix A). Live at
    four sites, and no rule had ever heard of it."""
    for token in ("10.5", "150/1424", "12.2"):
        problems = _check(
            tmp_path, rf"The lowest firing operating point sits at ${token}\%$.")
        assert any(token in p for p in problems), f"{token} is unguarded"


def test_the_full_pool_floor_may_not_be_read_as_the_fair_pools(tmp_path):
    """THE probe. The fair pool's correct stratum has its OWN floor -- 19/200 = 9.5%
    [6.2, 14.4] -- so attaching the superset's 10.5% to the subset is not a rounding
    difference, it is quoting the wrong estimate of the same parameter and claiming the
    wrong precision for it. The subset relation makes this MORE likely, not less."""
    for text in (
        r"""
        On the score-independent \emph{fair} pool ($200$ correct, $200$ hallucinating), the
        lowest firing operating point sits at $10.5\%$ [$9.0$, $12.2$].
        """,
        r"""
        Enumerated on the fair pool's $200$ correct answers, the achievable floor is
        $150/1424$.
        """,
        r"""
        Across the $80$ correct-answer targets of our attack campaign the ceiling atom
        carries $10.5\%$ of the mass.
        """,
    ):
        problems = _check(tmp_path, text)
        assert any("MISLABELLED" in p for p in problems), _say(problems)


def test_the_legitimate_subset_cross_reference_is_not_a_mislabelling(tmp_path):
    """THE control, and the reason the rule is `coexist` rather than `exclusive`.

    The Discussion's precision check is the whole point of having both populations: the
    fair pool's correct stratum is a subset of the 1424, they estimate the same ceiling-atom
    mass, and the wider one pins it. Naming both in one sentence is the argument, not an
    error. Proximity alone gets the Introduction's rendering backwards -- the foreign label
    lands 26 chars before the number and the owning label 25 chars after it, and a trailing
    label pays TRAILING_PENALTY -- so the foreign pool wins on a sentence that is correct.

    Both renderings the paper has carried this session are pinned, because it has already
    swapped between them once while this guard was being written.
    """
    for text in (
        # discussion.tex, live
        r"""
        Nor is the shortfall a property of our sample. The Wilson lower bound on the fair
        pool's correct stratum is $6.2\%$, and the $1424$-answer superset that stratum is a
        subset of estimates the same parameter with seven times the negatives, at $10.5\%$
        [$9.0$, $12.2$].
        """,
        # introduction.tex, live wording (owning label first)
        r"""
        We put that probability at $9.5\%$ on the fair pool's correct stratum and, on the
        $1424$-answer superset that stratum is a subset of, at $10.5\%$ [$9.0$, $12.2$],
        whose lower bound closes off a $5\%$ budget at $95\%$ confidence.
        """,
        # ...and the wording it carried an hour earlier (owning label TRAILING), which is
        # the one proximity arbitration cannot get right on its own.
        r"""
        We put that probability at $9.5\%$ on the fair pool's correct stratum and at
        $10.5\%$ [$9.0$, $12.2$] on the $1424$-answer superset it is a subset of, whose
        lower bound closes off a $5\%$ budget at $95\%$ confidence.
        """,
        # conclusion.tex, live
        r"""
        the probability that a clean correct answer yields $N$ mutually distinct meanings,
        which the $1424$-answer superset puts at $10.5\%$ [$9.0$, $12.2$]. At $N{=}10$ a
        $5\%$ budget is excluded at $95\%$ confidence on both populations.
        """,
        # main.tex, live
        r"""
        the lowest false-alarm rate a firing threshold can have \emph{is} the chance that a
        clean correct answer yields $N$ mutually distinct meanings---$10.5\%$ [$9.0$,
        $12.2$] over $1424$ clean correct answers. At that standard $N{=}10$ an operator
        who specifies a $5\%$ false-alarm budget cannot have one, however well the score
        ranks; the qualifier is load-bearing, since running the fair pool's $200$ correct
        answers out to $N{=}40$ empties the atom.
        """,
    ):
        problems = _check(tmp_path, text)
        assert not problems, _say(problems)


def test_coexist_still_accuses_when_the_owning_population_is_never_named(tmp_path):
    """`coexist` must not become a blanket amnesty. It disarms a foreign label only when
    the OWNING label is in the same sentence -- naming your own population is the
    disclosure. A sentence that names only the fair pool is still a mislabelling, and this
    is the pair that proves the tolerance is not vacuous."""
    disclosed = _check(tmp_path, r"""
        The fair pool's correct stratum puts the floor at $9.5\%$, and the $1424$-answer
        superset puts it at $10.5\%$ [$9.0$, $12.2$].
    """)
    assert not disclosed, _say(disclosed)

    undisclosed = _check(tmp_path, r"""
        The fair pool's correct stratum puts the floor at $10.5\%$ [$9.0$, $12.2$].
    """)
    assert any("MISLABELLED" in p for p in undisclosed), _say(undisclosed)


def test_the_intervals_lower_bound_is_not_armed_as_a_bare_decimal(tmp_path):
    """THE collision control, and it is the reason the interval is armed as a PAIR.

    $9.0$ is the LOWER bound of the 1424 floor's [9.0, 12.2]. It is ALSO the UPPER bound of
    the N=40 grid's achieved $5.0\\%$ [$2.7$, $9.0$] -- a FAIR-POOL number, live in the
    Abstract, the Introduction, the Discussion and the Conclusion. A bare `9.0` rule would
    demand a 1424 label at every one of those sites. Same hazard as 0.51, 0.698 and 12.0%,
    recognised before arming rather than after.
    """
    for text in (
        r"""
        So the $5\%$ budget that $N{=}10$ cannot honour at all is honoured at $N{=}40$, at
        an achieved $5.0\%$ [$2.7$, $9.0$] on the fair pool's $200$ correct answers.
        """,
        r"""
        running the fair pool's $200$ correct answers out to $N{=}40$ empties the atom and
        a $5\%$ operating point then exists, at an achieved $5.0\%$ [$2.7$, $9.0$].
        """,
    ):
        problems = _check(tmp_path, text)
        assert not problems, "a bare 9.0 rule is crying wolf on the N=40 interval:\n" \
            + _say(problems)


def test_the_full_pool_strata_are_declared_and_no_longer_flagged(tmp_path):
    """The four false positives defect 8 was actually reported through. methods.tex and
    limitations.tex both name the replication pass by its split, and the growing rule was
    reporting both halves as counts of a cell that is still filling."""
    for text in (
        r"""
        Re-scoring the $2000$ cached sample sets of our replication pass ($1424$ correct and
        $576$ hallucinating, at natural prevalence) under Eq.~(5) with the generating
        model's own length-normalised sequence likelihoods.
        """,
        r"""
        Over the $2000$ questions of the replication pass ($1424$ correct and $576$
        hallucinating, at natural prevalence), with length-normalised likelihoods the
        at-cap atom is gone.
        """,
    ):
        problems = _check(tmp_path, text)
        assert not problems, _say(problems)

    # ...and a MIS-stated split is still caught, which is what makes the declaration a
    # check rather than an amnesty. 1424 + 576 = 2000, and neither half may drift.
    for wrong in ("1420", "1500", "574"):
        bad = _check(
            tmp_path,
            rf"Our replication pass holds ${wrong}$ correct and $576$ hallucinating."
            if wrong != "574" else
            rf"Our replication pass holds $1424$ correct and ${wrong}$ hallucinating.")
        assert any(wrong in p for p in bad), f"{wrong} was accepted:\n" + _say(bad)


# --- the SECOND AXIS: measured, or derived? --------------------------------------------
def test_a_replayed_floor_may_not_be_presented_as_a_measurement(tmp_path):
    """A different kind of rule, for a different kind of error.

    Only N=40 was run. Every smaller budget in results/n_scaling_grid.md is a replay of the
    recorded pairwise verdicts on random subsets, and the report's own subsetting control
    shows the replay is biased: against a directly measured N=10 floor of 9.5%, replay
    gives a 12.0% median with all 20 replicates above the direct estimate. No POPULATION
    label can catch that -- 3.0% and 9.5% are the same 200 correct answers -- so the rule
    demands the disclosure instead, exactly as the 0.787 rule demands its convention.
    """
    for token in ("3.0", "3.1", "12.0"):
        problems = _check(
            tmp_path,
            rf"On the score-independent \emph{{fair}} pool ($200$ correct, $200$ "
            rf"hallucinating) the floor at $N{{=}}20$ is ${token}\%$.")
        assert any("REPLAY-DERIVED" in p for p in problems), f"{token}%: " + _say(problems)


def test_a_replayed_floor_passes_when_the_replay_is_disclosed(tmp_path):
    """Discussion's live wording. The rule is a disclosure requirement, not a ban -- and
    the paragraph that states the bias most plainly must be the one that passes."""
    for text in (
        r"""
        We have now run the budget out to $N{=}40$, recording the full pairwise equivalence
        verdicts so that any smaller budget is recoverable by replaying them on random
        subsets. On the same $200$ correct answers the ceiling-atom floor falls from
        $9.5\%$ [$6.2$, $14.4$] at $N{=}10$ to $3.0\%$ [$1.4$, $6.4$] at $N{=}20$.
        """,
        r"""
        Replay \emph{over}states the floor, so the true $N{=}20$ floor is probably below
        $3.0\%$ and a $5\%$ budget is more purchasable than we report.
        """,
        r"""
        On the fair pool the floor is $9.5\%$ measured directly at $N{=}10$ against a
        $12.0\%$ median over $20$ subset replays.
        """,
    ):
        problems = _check(tmp_path, text)
        assert not problems, _say(problems)


def test_the_eq5_fair_pool_auroc_is_guarded_beside_its_neighbour(tmp_path):
    """0.703 is the fair pool scored under length-normalised Eq.~(5); 0.704 is the same
    pool under the discrete estimator. They appear in one clause, one digit apart, and only
    0.704 was guarded -- so the cheapest slip in the paper had no check on it."""
    bare = _check(tmp_path, r"The detector reaches AUROC $0.703$ under Eq.~(5).")
    assert any("0.703" in p for p in bare), _say(bare)

    ok = _check(tmp_path, r"""
        On the score-independent \emph{fair} pool ($200$ correct, $200$ hallucinating) it
        scores AUROC $0.703$ against the discrete estimator's $0.704$.
    """)
    assert not ok, _say(ok)


def test_the_replay_rule_covers_the_incoming_correction(tmp_path):
    """3.0% is replicate-0 only; the exact subset-averaged, seed-free value is 3.1%. Both
    renderings are guarded on the 0.729/0.730 precedent, so restating the estimate cannot
    silently un-guard it -- which is defect 6 in miniature."""
    from check_population_labels import RULES

    replay = [r for r in RULES if r["name"].startswith("REPLAY")][0]
    flat = " ".join(replay["numbers"])
    assert "3\\.0" in flat and "3\\.1" in flat


# ======================================================================================
# THE REPLICATION POOL -- a third population, disjoint from both of the others.
# ======================================================================================
def test_the_operative_replication_auroc_is_guarded_at_all(tmp_path):
    """Commit 8e54943 demoted 0.787 and led with 0.694, and the guard kept guarding only
    0.787 -- so the paper's headline replication figure had no protection whatsoever."""
    # 0.729 and 0.730 are the same majority cell under the span and substring oracles
    # (results/replication_conventions.md). Both are guarded, so that restating the oracle
    # -- which the paper did mid-session -- cannot silently un-guard the number.
    for token in ("0.694", "0.729", "0.730"):
        problems = _check(tmp_path, f"The detector reaches AUROC ${token}$.")
        assert any(token in p for p in problems), f"{token} is unguarded"


def test_a_replication_auroc_may_not_share_a_sentence_with_another_pool(tmp_path):
    """`exclusive`. The fair pool and the attacked pool are NESTED, so proximity has to
    arbitrate between them; the 2000-question replication run is DISJOINT from both, so
    there is nothing to arbitrate. This is also the case proximity gets wrong -- 'On the
    fair pool our SE replication reaches 0.694' puts the owning word CLOSER to the number
    than the scope adverbial that actually binds it."""
    for text in (
        r"On the \emph{fair} pool ($200$ correct, $200$ hallucinating) our SE replication "
        r"reaches AUROC $0.694$.",
        r"Our SE replication reaches AUROC $0.694$ on the score-independent fair pool.",
        r"Measured on the attacked subset the replication AUROC is $0.730$.",
    ):
        problems = _check(tmp_path, text)
        assert any("MISLABELLED" in p for p in problems), _say(problems)


def test_a_genuine_contrast_between_the_populations_still_passes(tmp_path):
    """...and `exclusive` must not make cross-population comparison unwritable. The escape
    hatch is the existing one: a label introduced by a denial or contrast cue is disarmed
    before it can accuse anything."""
    problems = _check(tmp_path, r"""
        Our SE replication reaches AUROC $0.694$ under the greedy alias-aware span oracle,
        unlike the fair pool.
    """)
    assert not problems, _say(problems)


def test_the_live_replication_paragraph_passes(tmp_path):
    """Experiments' actual wording, which reports all three conventions and leads with the
    operative one. If the guard cannot accept this, the guard is wrong."""
    problems = _check(tmp_path, r"""
        Our SE replication on TriviaQA does not have one AUROC: on a single run of $2000$
        questions, the number depends on which correctness convention labels it. Under the
        greedy alias-aware span oracle used everywhere else in this paper it is $0.694$;
        under a majority-of-samples label $0.729$; and under an all-samples-correct label
        it reaches $0.790$, against the published SE figure of $0.828$.
    """)
    assert not problems, _say(problems)


def test_the_score_coupled_auroc_may_not_be_presented_bare(tmp_path):
    """0.787 is the all-samples-correct convention: a question counts correct iff all ten
    samples are, and SE is the entropy of the clustering of those same ten -- so part of
    that AUROC is the score scored against itself, in a paper whose third contribution is
    that score-entangled selection invalidates a clean AUROC. Commit 8e54943 demoted it.
    Wherever it appears its convention must appear with it, so that it can never again read
    as the replication result."""
    for text in (
        r"We replicate semantic entropy on TriviaQA at AUROC $0.787$.",
        r"Our SE replication reaches AUROC $0.787$, against the published $0.828$.",
        r"Our SE replication on $2000$ questions reaches AUROC $0.790$.",
    ):
        problems = _check(tmp_path, text)
        assert any("SCORE-COUPLED" in p for p in problems), _say(problems)


def test_the_score_coupled_auroc_passes_when_its_convention_is_named(tmp_path):
    """Limitations' live wording. The demotion is a requirement to disclose, not a ban."""
    problems = _check(tmp_path, r"""
        Our \emph{SE} replication reaches AUROC $0.694$ under the greedy alias-aware span
        oracle this paper operates with, against the paper's SE figure of $0.828$. The
        nearer-looking $0.787$ is the same run scored under an all-samples-correct label, a
        convention mechanically coupled to semantic entropy that we use nowhere else.
    """)
    assert not problems, _say(problems)


# ======================================================================================
# ROUND FOUR, PART TWO: THE GUARD LICENSED A CLAIM IT HAD ALREADY RETIRED.
#
# `22 distinct` was retired outright by commit e6e7629, because a realised distinct-value
# count is a SAMPLE statistic wearing a population parameter's clothes -- monotone in draws
# taken, never converging, and in that instance not even low (the expected number of
# distinct values among 80 draws is 23.0, putting 22 at the 37th percentile).
#
# The fair-pool granularity rule then listed `31 distinct`, `31 of the 39`, `28 of the 39`
# and `26 of the 39` as LIVE guarded fair-pool numbers. So the guard's answer to the retired
# claim was "correct, once you label it" -- which is worse than silence, because silence
# does not tell an author the number is fine. The retirement note itself names two of them.
#
# The shape is now retired GENERATIVELY, on the `\b\d+/97\b` precedent: no numerator is
# enumerated anywhere, and the n-invariant LATTICE sizes are the exclusion.
# ======================================================================================
RETIRED_DISTINCT_SHAPE: list[tuple[str, str]] = [
    ("the enumerated one the rule used to guard",
     r"On the score-independent \emph{fair} pool the estimator realises $31$ distinct "
     r"values."),
    ("the same claim as a fraction of the lattice",
     r"On the score-independent \emph{fair} pool the estimator realises $31$ of the $39$ "
     r"attainable values."),
    ("the n=200 rendering, named in the retirement note",
     r"At $n{=}200$ the estimator realises $28$ of the $39$ attainable values."),
    ("the n=400 rendering",
     r"Across the $400$-question pool the estimator realises $26$ of the $39$ values."),
    ("the n=2000 rendering, which no rule covered at all",
     r"Over the $2000$-question replication pass the estimator realises $35$ distinct "
     r"values."),
    ("a numerator nobody has ever written down",
     r"The estimator realises only $47$ distinct entropy values across the pool."),
    ("the original, still caught",
     r"Across the $97$ targets of the attack campaign the estimator realises only $22$ "
     r"distinct values."),
]


@pytest.mark.parametrize("why,text", RETIRED_DISTINCT_SHAPE,
                         ids=[t[0].replace(" ", "_") for t in RETIRED_DISTINCT_SHAPE])
def test_every_realised_distinct_value_count_is_retired_generatively(tmp_path, why, text):
    """Enumerating numerators is the shape that failed for `97` and it failed identically
    here: one numerator was retired while three more were guarded as live and a fourth was
    not covered at all. The claim's defect is its SHAPE, so the shape is what gets retired,
    and the numerator never has to be known in advance."""
    problems = _check(tmp_path, text)
    stale = [p for p in problems if "STALE" in p]
    assert stale, f"{why}: the retired shape was accepted\n" + _say(problems)
    assert any("sample" in p.lower() for p in stale), _say(stale)


def test_a_fair_pool_label_does_not_license_the_retired_shape(tmp_path):
    """The precise defect. The granularity rule OWNED these numbers, so a correctly
    labelled fair-pool rendering came back green -- the guard certifying, as properly
    attributed, a claim another of its own rules had retired. No population owns a
    statistic that is a property of how many draws you took."""
    problems = _check(tmp_path, r"""
        On the score-independent \emph{fair} pool ($200$ correct, $200$ hallucinating), the
        estimator realises $31$ of the $39$ attainable values.
    """)
    assert any("STALE" in p for p in problems), \
        "attaching the right pool does not repair the claim:\n" + _say(problems)


def test_the_lattice_sizes_are_the_exclusion_and_stay_green(tmp_path):
    """39 at N=10 and 455 at N=20 follow from p(10)=42 and p(20)=627 with no data at all.
    They do not move with n, they are properties of the estimator, and they are precisely
    what the paper is told to report INSTEAD. A rule that flagged them would be flagging
    the replacement."""
    for text in (
        r"""
        At $N{=}10$ the \emph{discrete} estimator is confined to a lattice of $39$
        attainable values with an atom at the maximum.
        """,
        r"""
        Quadrupling the budget puts the top tenth of the range at seven ($455$ attainable
        values at $N{=}20$, against $39$ and two at $N{=}10$).
        """,
        r"""
        At the standard $N{=}10$ the estimator lives on a lattice of just $39$ attainable
        values, of which only two fall in the top tenth of its range.
        """,
    ):
        problems = _check(tmp_path, text)
        assert not problems, _say(problems)


def test_the_papers_own_disavowal_of_the_retired_shape_is_not_flagged(tmp_path):
    """THE CONTROL THAT MATTERS MOST IN THIS ROUND, and the one a careless generative rule
    fails.

    introduction.tex does not make the retired claim -- it ARGUES THE RETIREMENT, and to do
    that it has to quote the counts it is disowning: 28 at n=200, 35 at n=2000, and 22 at
    the 37th percentile of what a random 80 produces. A rule that matched bare numerals near
    the word 'distinct' would go red on the passage that does the retiring, which is the
    defect-7 failure mode (a guard flagging a true statement) planted deliberately by the
    fix for defect 9. The pattern therefore anchors on the QUANTIFIED NOUN -- 'N distinct
    values', 'N of the 39' -- and this passage quantifies nothing.
    """
    problems = _check(tmp_path, r"""
        Nothing here rests on a count of distinct values realised: that quantity is monotone
        in the number of targets scored (the same population yields $28$ at $n{=}200$ and
        $35$ at $n{=}2000$, and $22$ sits at the $37$th percentile of what a random $80$
        produces), so it measures the sample, not the estimator, and the total number of
        operating points inherits the same defect. What does not move with the sample is the
        lattice size, and at the low end the floor.
    """)
    assert not problems, \
        "the guard is red on the passage that RETIRES the claim:\n" + _say(problems)


def test_the_definition_of_the_ceiling_atom_is_not_a_distinct_value_count(tmp_path):
    """'a clean correct answer yields $N$ mutually distinct meanings' is the DEFINITION of
    the ceiling atom's mass, live in the Abstract, the Introduction, the Discussion and the
    Conclusion. It counts meanings in one sample set, not values realised across a pool, and
    the $N$ is a symbol rather than a numeral. It must not be touched."""
    problems = _check(tmp_path, r"""
        Every threshold above that maximum flags nothing, so the lowest false-alarm rate a
        firing threshold can have \emph{is} the chance that a clean correct answer yields
        $N$ mutually distinct meanings---$10.5\%$ [$9.0$, $12.2$] over $1424$ clean correct
        answers.
    """)
    assert not problems, _say(problems)

    # ...and Methods' cluster-count bound, where a decimal exponent sits next to the word.
    ok = _check(tmp_path, r"""
        Reaching the full range $[0, \log N]$ requires $K \geq \lceil N^{0.9} \rceil$
        distinct meanings---at $N{=}10$, nine of them.
    """)
    assert not ok, _say(ok)


def test_the_retired_distinct_patterns_are_gone_from_the_guarded_set():
    """Named explicitly, the way round two named its four labels and round three its nine
    values, so that a regression says which pattern came back rather than pointing at a
    generic invariant."""
    from check_population_labels import RULES

    gran = [r for r in RULES if r["name"].startswith("fair-pool granularity")]
    assert len(gran) == 1, [r["name"] for r in RULES]
    flat = " ".join(_literal(p) for p in gran[0]["numbers"])
    for retired in ("31 distinct", "31 of", "28 of", "26 of"):
        assert retired not in flat, (
            f"{retired!r} is a realised distinct-value count -- a sample statistic. It is "
            "retired in SUPERSEDED and may not be a guarded fair-pool number.")
    # ...and the crowding RATES, which are genuine population statistics, are still there.
    for live in ("9.5", "21.5", "27.5", "44.5", "19/200", "74/400"):
        assert live in flat, f"{live} is a live crowding statistic and must stay guarded"


# ======================================================================================
# ROUND FIVE (2026-08-26): THE RETIRED POSITIONS THAT ARE STATED IN WORDS.
#
# The defect that opened this round had survived FOUR rounds of adversarial review.
# `paper/sections/discussion.tex` said in one place that the measured N=40 floor "takes the
# question bootstrap" -- a position withdrawn on 2026-08-19 -- and in another place, in the
# same file, that it "takes neither". Nothing caught it because IT CONTAINS NO DIGIT: every
# rule above this point in the ledger matches a rendered numeral, and every sweep that went
# looking grepped for numbers. The follow-up sweep then found sixteen more of the same class
# outside paper/ (commit 852e0f7, "sixteen more sites, none of them containing a digit").
#
# WHAT WAS MEASURED BEFORE THESE RULES WERE ACCEPTED. The sixteen prose sites of 852e0f7
# were reconstructed from `852e0f7^` and each was scanned in isolation, so a rule could not
# be credited for firing on a neighbouring paragraph:
#
#     all eight rules together        16 of 16
#     the coverage-pair rules alone   15 of 16
#     the word rules alone            10 of 16
#
# ...on a whitespace-only flattener, each site scanned with NO surrounding context, so a
# rule could not be credited for firing on a neighbouring paragraph. Widening the context
# to six lines either side moves only the word-rule figure, to 11. Through `strip_latex`,
# which is what `check_file` runs today, the same three numbers are 14, 11 and 8. That gap
# is not a rounding difference and it is not tolerable in the next phase; it is pinned as
# a test at the end of this section.
# The 11 is worth noting on its own: it is exactly the figure the sweeping agent predicted
# for the coverage rule, so that estimate was right about the guard AS BUILT and low about
# the rule in the abstract.
#
# THE SHAPE OF EACH RULE, and why it is that shape rather than a phrase match:
#   * `estimand dissolves` and friends are armed FLAT. The ruling withdraws that claim
#     outright (sec. 13), so there is no correct usage for a gate to protect.
#   * `reports a smaller floor` is armed with a CONDITIONAL gate, because there IS a
#     correct usage and it is in the paper right now.
#   * the coverage pair is armed as an ADJACENCY -- the digits are true, and what is
#     retracted is quoting them with no branch named.
#
# WHAT A WIDENED SCOPE WOULD COST TODAY, measured the same way and reported here because
# the next phase has to budget for it rather than discover it: pointed at results/,
# scripts/, tests/, docs/ and figures/ (189 files), these eight rules return 120 hits in
# 11 files. Seventy-two of those are THIS FILE and the ledger itself, which contain the
# retired sentences as data; seven are the ruling, which quotes what it retracts; about
# eighteen are correction notes in already-corrected files ("This banner said ... until
# 2026-08-26"). The genuinely live remainder is small and sits in docs/critique_log.md,
# results/schedule_2026_08_26.md and results/morning_review_2026_08_19.md. None of that
# is fixed here -- widening `main()` is a separate change -- but a phase that widens the
# scope without first deciding what to do about self-reference and correction notes will
# ship a guard that is red on arrival, and a guard that is red on arrival gets switched
# off. Two of the false-positive shapes the dry run found WERE fixed here, because they
# were defects in the rules rather than in the scope: see `_COVERAGE_CTX` and `denial`.
#
# THAT SEPARATE CHANGE LANDED THE SAME DAY. See ROUND SIX at the end of this file: the
# scope IS widened, per-suffix, with a ratchet -- and the paragraph above turned out to be
# right about the shape and wrong about the size. Re-measured through the flattener that
# actually ships (`strip_plain`, not "whitespace-only") and with self-reference, the
# critique log and the ruling excluded BY NAME rather than by hoping, the live remainder is
# 32 findings in 7 files, not "120 hits in 11". The difference is not a better rule; it is
# that four of those eleven files are the ledger, its probes, the log and the ruling, and
# the right answer for all four was a named exclusion with a stated reason.
# ======================================================================================
def _word_rule_hits(problems: list[str]) -> list[str]:
    """Only the problems raised by the retired-position rules armed on 2026-08-26.

    Keyed off the rules' own `quantity` strings rather than a hand-written list, so a rule
    renamed in the ledger cannot quietly drop out of every control in this section.
    """
    from check_population_labels import SUPERSEDED

    quantities = [s["quantity"] for s in SUPERSEDED
                  if str(s.get("run", "")).startswith("pre-sec")]
    assert quantities, "the word rules have vanished from the ledger"
    return [p for p in problems if any(q in p for q in quantities)]


def _word_rule(fragment: str) -> dict:
    """The one word rule whose PATTERN or QUANTITY contains `fragment`.

    It looked in `pattern` only until 2026-08-27, and that coupled every mutation test to
    a regex spelling: widening `smaller (?:floor|one)` into a shape broke four mutation
    tests that had nothing to do with the widening, which is a test suite reporting an
    edit rather than a defect. `quantity` is the rule's identity -- it is what the finding
    prints and what `_word_rule_hits` already keys on -- so mutation tests now name a rule
    the way a reader would.
    """
    from check_population_labels import SUPERSEDED

    hits = [s for s in SUPERSEDED
            if fragment in s["pattern"] or fragment in s.get("quantity", "")]
    assert len(hits) == 1, f"{fragment!r} matched {len(hits)} rules"
    return hits[0]


# --- 1. "the estimand dissolves", in every rendering the repo has actually carried -----
@pytest.mark.parametrize("why,text", [
    ("the plain form, from results/replay_control.md before the fix",
     r"Both candidates fail and the estimand dissolves when the ceiling atom empties."),
    ("with an intensifier, from docs/critique_log.md",
     r"withdrawn, because the estimand itself dissolves once the ceiling atom empties"),
    ("under markup, which is what defeated the manual sweeps",
     r"Neither estimator is broken. The \textbf{estimand} dissolves at the moment the "
     r"atom empties."),
    ("the `stops existing` rendering, from the replay_control provenance banner",
     r"respectively at nominal 95\%, because the estimand stops existing when the "
     r"ceiling atom empties."),
    ("shouted, from scripts/replay_control.py's write_report",
     r"Neither estimator is broken. THE ESTIMAND BREAKS, and it breaks exactly when the "
     r"ceiling atom empties."),
    ("VERB FIRST, which an `estimand <verb>` pattern cannot see at all",
     r"The same event that separates these two columns---the empty atom---also breaks "
     r"the floor as an estimand."),
    ("VERB ELIDED, which neither of the two patterns above can see",
     r"Neither estimator is broken -- the estimand is, once the ceiling atom empties."),
])
def test_the_retracted_estimand_claim_is_flagged_in_every_rendering(tmp_path, why, text):
    r"""PROBE. Ruling sec. 13 retracts "the estimand dissolves when the atom empties" by
    name: it is a statement about ONE BRANCH, and under the other branch (which the data
    does not exclude) Wilson has 95.06% coverage and the estimand is an ordinary binomial
    proportion. Every rendering above was live in this repo on 2026-08-25.

    The last two are the reason this is three rules and not one. The brief that specified
    this ledger proposed `estimand\s+(?:dissolves|stops existing|breaks)`, which is correct
    for the first five and blind to the last two -- and the last two are not hypothetical
    renderings, they are `results/n_scaling_grid.md` and `figures/README.md` as committed.
    """
    problems = _check(tmp_path, text)
    hits = _word_rule_hits(problems)
    assert hits, f"{why}: not flagged\n" + _say(problems)
    assert any("estimand" in h for h in hits), _say(hits)


def test_the_replacement_wording_for_that_claim_is_green(tmp_path):
    """CONTROL, and it carries the whole burden of the rule above being usable.

    Three live, correct sentences. The first is the ruling's own replacement (sec. 13); the
    second is `results/n_scaling_grid.md` as corrected; the third is
    `paper/sections/discussion.tex` line 360, which is about the plug-in entropy estimator
    and has nothing to do with the floor. A rule that reached any of them would be red on
    the text that does the retracting -- the defect-7 failure mode this file already logged
    once, when a generative rule went red on the passage arguing the retirement.
    """
    problems = _check(tmp_path, r"""
        Once the ceiling atom empties the estimand is NOT IDENTIFIED at $n{=}200$: it is
        $2.0\%$ if the population can never produce $39$ mutually inequivalent answers
        out of $40$, and can be arbitrarily smaller if it can. An estimand whose value
        moves by two orders of magnitude across a hypothesis the sample cannot test does
        not have a confidence interval, and that argument needs no population model at
        all. Neither the estimator nor the estimand does what we said it did. Elsewhere,
        a plug-in entropy that rises towards its estimand as the sample grows is that
        estimator's own bias and not a property of any pool.
    """)
    assert not _word_rule_hits(problems), \
        "the guard is red on the wording that REPLACES the retracted claim:\n" \
        + _say(_word_rule_hits(problems))


def test_a_negated_estimand_verb_is_not_the_retracted_claim(tmp_path):
    """CONTROL for the tempered gap. `estimand ... breaks` within a few words is the
    retracted claim; `the estimand does not break` is its denial, and the gap refuses to
    span a negation for exactly that reason. Without the tempering this sentence is red and
    the ledger becomes unusable in any passage that argues against the retracted view."""
    problems = _check(tmp_path, r"""
        The estimand does not break when the atom empties; it stops being identified,
        which is a different and stronger statement.
    """)
    assert not _word_rule_hits(problems), _say(_word_rule_hits(problems))


# --- 2. "reports a smaller floor" -- the conditional-aware rule ------------------------
@pytest.mark.parametrize("why,text", [
    ("the rendering in results/n_scaling_grid.md before the fix",
     r"and that rung is not the top of the population's support: a larger pool reaches a "
     r"higher one and reports a SMALLER floor, so the quantity moves with the pool rather "
     r"than holding still to be estimated."),
    ("the rendering in docs/START_HERE_overnight.md, which says `one` not `floor`",
     r"$4/200$ is the resolution limit of a $200$-answer pool, not an estimate of a "
     r"population floor, and a larger pool reaches a higher rung and reports a smaller "
     r"one."),
    ("the bare assertion, with the dichotomy nowhere in sight",
     r"A larger pool reaches a higher rung and reports a smaller floor. That is why the "
     r"$N{=}40$ row prints no interval."),
])
def test_the_unconditional_smaller_floor_claim_is_flagged(tmp_path, why, text):
    """PROBE. This is the sentence that is TRUE IN ONE BRANCH. Ruling sec. 13: the deep-tail
    misfit "widens the estimand's range in both directions at once", so a directional claim
    -- larger pool, smaller floor -- is precisely what the evidence does not support. The
    third probe is the shape that matters: the claim on its own, with a full stop after it,
    and the next sentence about something else."""
    problems = _check(tmp_path, text)
    hits = _word_rule_hits(problems)
    assert hits, f"{why}: not flagged\n" + _say(problems)
    assert any("UNCONDITIONALLY" in h for h in hits), _say(hits)


def test_the_discussion_conditional_site_is_pinned_green_by_name(tmp_path):
    r"""THE CONTROL THAT MATTERS MOST IN THIS ROUND.

    `paper/sections/discussion.tex`, the sentence beginning "If it is not," is the ONE SITE
    IN THE REPO that states this correctly, and it is verbatim below. It is correct because
    it is an if/else: the clause before the phrase gives the branch in which a larger pool
    reports a smaller floor, and the clause after it gives the branch in which the floor is
    an ordinary population proportion.

    A flat phrase match would fail this site. That is not a cosmetic problem. A guard that
    fires on the one passage that gets the statistics right teaches its user to silence the
    guard, which is this project's "a check that cannot fail is not a check" inverted -- and
    paper/ is verified consistent and not to be edited, so a red here could only be cleared
    by weakening the rule under time pressure.

    Pinned as its own test, named for the file, so that a regression says WHICH site went
    red rather than reporting a count.
    """
    problems = _check(tmp_path, r"""
        Its threshold is not $\ln 40$ or any
        other value fixed in advance but the top score \emph{this} sample attained, and
        once the atom is empty nothing in the sample settles whether that score is the top
        of the population's support. If it is not, a larger pool reaches a higher rung and
        reports a smaller floor, so the quantity being estimated moves with the pool
        instead of holding still to be estimated; if it is, the floor is an ordinary
        population proportion and the count in front of us estimates it. Nothing here
        decides which, and the two readings are far apart.
    """)
    assert not _word_rule_hits(problems), (
        "discussion.tex's if/else -- the one site in the repo that states this correctly "
        "-- is red:\n" + _say(_word_rule_hits(problems)))


@pytest.mark.parametrize("why,text", [
    ("conditional BEHIND the claim, which no lookahead can see",
     r"If the population's support stops where this pool stopped, nothing moves; if it "
     r"does not, a larger pool reports a smaller floor."),
    ("conditional AHEAD of the claim, across a semicolon, as in the figure generator",
     r"A larger pool reaches a higher rung and reports a smaller floor; if it is the top "
     r"of the support, $2.0\%$ is an ordinary population proportion and the count "
     r"estimates it."),
    ("conditional in the NEXT SENTENCE, which a sentence-bounded gate would miss",
     r"A larger pool reaches a higher rung and reports a smaller floor. Whether the "
     r"population's support ends at the rung this pool reached is a question $200$ "
     r"answers cannot settle, and the two readings are far apart."),
    ("the negated form results/n_scaling_grid.md now uses",
     r"If the population can never produce $39$ mutually inequivalent answers out of "
     r"$40$, then $2.0\%$ IS the population quantity and no larger pool reports a "
     r"smaller floor."),
])
def test_the_conditional_gate_reaches_in_both_directions_and_across_a_boundary(
        tmp_path, why, text):
    """CONTROL for the geometry of the gate, one case per thing that could go wrong.

    Cases 1 and 2 are why the gate is not a lookahead: three of the four correct sites in
    this repo put their conditional BEFORE the phrase. Case 3 is why `span` is 1 and not 0
    -- an if/else split across a full stop is still an if/else. Case 4 is the rendering in
    `results/n_scaling_grid.md` today, where the conditional is a `never` clause and the
    claim itself is negated."""
    problems = _check(tmp_path, text)
    assert not _word_rule_hits(problems), f"{why}:\n" + _say(_word_rule_hits(problems))


def test_a_decimal_between_the_claim_and_its_conditional_does_not_break_the_gate(tmp_path):
    r"""CONTROL for the one thing the obvious implementation gets wrong.

    The natural spelling of conditional-awareness is a negative lookahead bounded by
    `[^.]*`. It stops dead at the decimal point of `$2.0\%$`, so this sentence -- correct,
    and the exact wording the figure generator carries -- would fire. `_TERM_RE` ends a
    sentence on `[.:;!?]` only when whitespace follows, which is the machinery the label
    geometry has used since the guard was written, and it is reused here rather than
    reinvented."""
    problems = _check(tmp_path, r"""
        A larger pool reaches a higher rung and reports a smaller floor than $2.0\%$; if
        it is the top of the support, the count in front of us estimates the floor.
    """)
    assert not _word_rule_hits(problems), _say(_word_rule_hits(problems))


# --- 3. the coverage pair, armed as an adjacency --------------------------------------
@pytest.mark.parametrize("why,text", [
    ("Wilson's figure alone, as scripts/n_scaling_grid.py logged it",
     r"Wilson on the first-firing count covers the true floor $53.7\%$ of the time."),
    ("both halves, as the replay_control provenance banner carried them",
     r"Wilson on $4/200$ and the question bootstrap cover the true floor $53.7\%$ and "
     r"$0.00\%$ of the time respectively, at nominal $95\%$."),
    ("at full precision, as the corrected tables render it",
     r"measured coverage at nominal $95\%$ is $53.67\%$ for Wilson and $0.00\%$ for a "
     r"question bootstrap"),
    ("NAMING A MODEL IS NOT NAMING A BRANCH",
     r"Measured coverage at a nominal $95\%$, against a population model validated "
     r"out-of-sample on the two smaller budgets in this table: Wilson on the "
     r"first-firing count $53.7\%$, a question bootstrap over the questions $0.00\%$."),
])
def test_the_coverage_pair_is_flagged_when_no_branch_is_named(tmp_path, why, text):
    """PROBE. `53.67%` and `0.00%` are TRUE -- they are the coverages under the calibrated
    Ewens fit. What ruling sec. 8.4 retracts is quoting them with no population attached,
    because under the zero branch the same two estimators cover 95.06% and 100%, and the
    data excludes neither branch.

    The fourth probe is the discriminating one and it was the actual wording at six of the
    sixteen sites: "against a population model validated out-of-sample" names a model but
    not a branch, and the defect is precisely that. If that phrase were allowed to
    exculpate, all sixteen sites would have been green."""
    problems = _check(tmp_path, text)
    hits = _word_rule_hits(problems)
    assert hits, f"{why}: not flagged\n" + _say(problems)
    assert any("measured under" in h for h in hits), _say(hits)


@pytest.mark.parametrize("why,text", [
    ("the corrected markdown table row, from figures/README.md and n_scaling_grid.md",
     r"| calibrated Ewens (tau\_top = $0.2726\%$) | $53.67\%$ | $0.00\%$ | "
     r"| zero branch (tau$^*$ = $2.0\%$) | $95.06\%$ | $100\%$ |"),
    ("the corrected COLON layout, which is the whole reason the span is 1 and not 0 -- "
     "make_floor_budget_figure.py:71, n_scaling_grid.py:799, "
     "derived_paper_quantities.py:306",
     r"calibrated Ewens (tau\_top = $0.2726\%$): Wilson $53.67\%$, question bootstrap "
     r"$0.00\%$"),
    ("the corrected prose, from results/derived_paper_quantities.md",
     r"Coverage figures for the two candidates use a population model and must be quoted "
     r"with it: under the calibrated Ewens fit, $53.7\%$ (Wilson on $4/200$) and "
     r"$0.00\%$ (question bootstrap) at nominal $95\%$."),
    ("the corrected banner, from results/replay_control.md",
     r"The coverage figures are BRANCH-CONDITIONAL and must never be quoted without "
     r"their population -- under the calibrated Ewens fit Wilson covers $53.67\%$ and "
     r"the question bootstrap $0.00\%$ at nominal $95\%$."),
])
def test_the_coverage_pair_passes_when_its_branch_is_named(tmp_path, why, text):
    """CONTROL. All three are live text in the repo as corrected on 2026-08-26. A rule that
    reddened them would be demanding that the corrected files be un-corrected."""
    problems = _check(tmp_path, text)
    assert not _word_rule_hits(problems), f"{why}:\n" + _say(_word_rule_hits(problems))


def test_the_coverage_rule_does_not_reach_its_neighbours(tmp_path):
    r"""CONTROL, and the reason `53.7` is armed as a digit string rather than as `53.` and
    `0.00` is armed only with a required percent sign.

    `53.4`, `53.5`, `53.8` and `53.9` are live numbers in `achievable_fpr_grid.md`,
    `cluster_count_bound.md` and `null_control_cost_options.md`. `0.000000\%` is the exact
    subset-saturation value $U_{39}$ from ruling section 1 (M3) -- measured, model-free,
    exhaustively enumerated over all $8{,}000$ 39-subsets, and one of the numbers the
    ruling tells the paper to ADD. Flagging it would be flagging the replacement, which is
    the failure mode a generative rule in this file already planted once."""
    problems = _check(tmp_path, r"""
        At $k{=}13$ the full labelled pool's correct stratum gives $766/1424 = 53.8\%$
        and the fair pool $107/200 = 53.5\%$, against $53.4\%$ one rung below and
        $53.9\%$ feasibility checks per target. The exact subset curve reaches
        $0.000000\%$ at $k{=}39$ and $k{=}40$, and the at-cap mass is $0.0\%$
        [$0.0$, $1.9$].
    """)
    assert not _word_rule_hits(problems), _say(_word_rule_hits(problems))


def test_a_zero_rate_with_no_coverage_context_is_not_the_bootstraps_coverage(tmp_path):
    r"""CONTROL for the `near` gate on `0.00\%`. A zero rate is not rare in this repo and
    most of them are nothing to do with the question bootstrap's coverage."""
    problems = _check(tmp_path, r"""
        Of the $80$ false-alarm targets, $0.00\%$ were rejected by the feasibility filter
        before scoring began.
    """)
    assert not _word_rule_hits(problems), _say(_word_rule_hits(problems))


# --- 4. the sentence ruling section 2 forbids by name ----------------------------------
@pytest.mark.parametrize("why,text", [
    ("the Abstract sentence the ruling names and forbids",
     r"The $2.0\%$ is the resolution of the pool and not a property of the detector."),
    ("the docs/START_HERE_overnight.md rendering, with a qualifier in the noun phrase",
     r"the lattice at $N{=}40$ is dense, which is precisely why $4/200$ is a resolution "
     r"limit of the \emph{pool} and not a property of the detector"),
    ("the other START_HERE rendering, where the pool is named by its size",
     r"$4/200$ is the resolution limit of a $200$-answer pool, not an estimate of a "
     r"population floor."),
])
def test_the_resolution_of_the_pool_sentence_is_flagged(tmp_path, why, text):
    """PROBE. Ruling sec. 2 quotes this sentence and says "Do not print that sentence",
    because it is true only in the branch where the population CAN produce 39 mutually
    inequivalent answers out of 40. In the other branch $2.0\\%$ is a genuine estimate of a
    genuine population quantity and Wilson covers it at 95.06%.

    It reached the paper's Abstract and was committed there on 2026-08-26. These two rules
    carry NO `absent` gate, unlike the smaller-floor rule, because the ruling withdraws the
    sentence outright rather than conditioning it -- and the both-branches wording it
    supplies instead contains neither pattern."""
    problems = _check(tmp_path, text)
    hits = _word_rule_hits(problems)
    assert hits, f"{why}: not flagged\n" + _say(problems)
    assert any("2.0%" in h for h in hits), _say(hits)


def test_the_both_branches_wording_the_ruling_supplies_is_green(tmp_path):
    """CONTROL. Ruling sec. 2's replacement sentence, verbatim in substance. It mentions
    both "a property of the detector" and "the pool's size" and is the sentence the paper is
    told to print -- so a rule that matched the phrase rather than the ASSERTION would be
    red on the replacement."""
    problems = _check(tmp_path, r"""
        The cheapest alarm $200$ correct answers can exhibit costs $2.0\%$, but whether
        that is a property of the detector or of the pool's size turns on whether the
        population can ever produce $39$ mutually inequivalent answers out of $40$; $200$
        answers cannot tell, and the two answers differ by more than two orders of
        magnitude. We therefore quote no interval for it.
    """)
    assert not _word_rule_hits(problems), _say(_word_rule_hits(problems))


def test_the_class_separation_may_still_be_not_a_property_of_the_detector(tmp_path):
    """CONTROL, and the reason the detector half carries a `near` gate.

    `results/dynamic_range_finding.md` and `results/CORRECTIONS_2026-08-02.md` both call the
    $+0.184$-nat class separation "not a fixed property of the detector", and both are
    CORRECT: it is a sample statistic from a small stratum, and on the fair pool the same
    quantity is $+0.463$ nats. Neither passage mentions the floor, $4/200$, $2.0\\%$ or
    $N{=}40$, which is what the gate keys on. Named here so a regression says which
    unrelated finding the ledger started flagging."""
    problems = _check(tmp_path, r"""
        The separation is not statistically significant. $+0.184$ nats has a $95\%$ CI of
        [$-0.136$, $+0.488$] and a permutation $p$ of $0.296$, on the attack campaign's
        hide stratum. It is a sample statistic from a small stratum, not a fixed property
        of the detector. On the score-independent \emph{fair} pool ($200$ correct, $200$
        hallucinating) the same quantity is $+0.463$ nats.
    """)
    assert not _word_rule_hits(problems), _say(_word_rule_hits(problems))


def test_a_disowned_retired_claim_stays_green(tmp_path):
    r"""CONTROL for the `denial` gate, and it was found by a dry run rather than by
    imagination: with the first six rules armed and the file scope still at paper/, the
    ledger was pointed at results/, scripts/, docs/ and figures/ to see what a widened
    scope would cost. It flagged `docs/START_HERE_overnight.md` line 190 -- which is the
    CORRECTED text, and which says the retracted thing only in order to disown it.

    Every corrected file in this repo records what it used to say. A ledger that reddens
    the sentence doing the retracting is the defect-7 failure mode, and this file has
    already logged one instance of it.
    Both halves below are live repo text: `docs/START_HERE_overnight.md` line 190
    and `scripts/n_scaling_grid.py` line 793. The smaller-floor rule deliberately
    does NOT get this gate -- see
    test_the_denial_gate_is_armed_on_the_flat_rules_and_on_no_coverage_rule.


    `denial` is `_is_non_binding`, unchanged, the same 30-character lookback clipped at the
    previous sentence boundary that the pool labels have used since the guard was written.
    """
    problems = _check(tmp_path, r"""
        The reason is not data selection, and it is NOT that the estimand dissolves:
        ruling section 13 retracts that sentence as branch-conditional dressed as
        unconditional. Do not restate the old sentence, and do not restate its cousin
        "the estimand dissolves"; both are branch-conditional claims worn as
        unconditional ones.
    """)
    assert not _word_rule_hits(problems), _say(_word_rule_hits(problems))


def test_a_denial_in_the_previous_sentence_does_not_disown_anything(tmp_path):
    r"""PROBE, and the pair to the control above. This is `docs/START_HERE_overnight.md`
    BEFORE the fix: the negation is there, but it is denying something else and a full stop
    stands between it and the claim. `_is_non_binding` clips its lookback at the previous
    sentence boundary precisely so that this stays red -- the same reasoning the Conclusion
    needed when "This is not a claim that the detector fails: on the ... fair pool" had to
    keep its label."""
    problems = _check(tmp_path, r"""
        The reason is not data selection. It is that the estimand dissolves --- $4/200$ is
        the resolution limit of a $200$-answer pool, not an estimate of a population floor.
    """)
    hits = _word_rule_hits(problems)
    assert hits, _say(problems)
    assert any("estimand" in h for h in hits), _say(hits)


def test_mutation_removing_the_denial_gate_reddens_the_corrected_handoff(
        tmp_path, monkeypatch):
    """Remove `denial` and the sentence that disowns the retracted claim goes red."""
    text = r"""
        The reason is not data selection, and it is NOT that the estimand dissolves:
        ruling section 13 retracts that sentence as branch-conditional.
    """
    assert not _word_rule_hits(_check(tmp_path, text)), "control is not green to begin with"

    rule = _word_rule(r"estimand\b(?:(?!")
    monkeypatch.delitem(rule, "denial")
    assert _word_rule_hits(_check(tmp_path, text)), \
        "without `denial` the disowning sentence is still green -- the gate does nothing"


def test_the_denial_gate_is_armed_on_every_position_rule_and_on_no_coverage_rule():
    """A position rule has to survive being quoted in the sentence that disowns it. A
    coverage rule must not: "not 53.7%" is still `53.7%` printed with no branch named, and
    the whole point of that rule is that the digits are TRUE and the attribution is what is
    missing.

    THE LINE MOVED ON 2026-08-27, and the move is a false-positive fix rather than a
    loosening. The invariant used to be "`denial` iff no `absent` gate", which put the
    smaller-floor family on the coverage side, and the note here argued for it: a "not"
    thirty characters back is not evidence that the DICHOTOMY was stated. That argument
    was sound about the gate as it then was -- a proximity test -- and it shipped a plain
    false positive anyway:

        "It does not follow that a larger pool reports a smaller floor"   -> RED

    which is the guard reddening a sentence that says the right thing, on a rule whose own
    comment says a guard that fires on correct usage teaches its user to silence it. The
    premise also changed: `denial` is now `_is_disowned`, a test for named disowning
    CONSTRUCTIONS, and "it does not follow that X" is one of them by construction and not
    by proximity. `absent` still carries the ordinary requirement -- state the dichotomy --
    and `denial` only adds the case where the sentence denies the claim outright.

    SO THE INVARIANT IS NOW A PROPERTY OF WHAT THE RULE RETIRES: a rule whose replacement
    is the POSITION (`_NOT_IDENTIFIED`) gets `denial`; a rule whose replacement is the
    branch-conditional COVERAGE PAIR does not. That is the same value/position distinction
    the `wide` flag uses, applied one level down, and it cannot be satisfied by taste.
    """
    from check_population_labels import _COVERAGE_PAIR, _NOT_IDENTIFIED, SUPERSEDED

    seen = 0
    for s in SUPERSEDED:
        if not str(s.get("run", "")).startswith("pre-sec"):
            continue
        seen += 1
        is_position = s["replacement"] is _NOT_IDENTIFIED
        assert is_position or s["replacement"] is _COVERAGE_PAIR, s["quantity"]
        assert bool(s.get("denial")) is is_position, (
            f"{s['quantity']}: `denial` belongs on exactly the rules that retire a "
            "POSITION. A coverage rule must not have it -- 'not 53.7%' is still 53.7% "
            "printed with no branch named.")
    assert seen == 12, f"{seen} position rules; update this pin deliberately"


def test_the_smaller_floor_rule_no_longer_reddens_a_sentence_that_denies_it(tmp_path):
    """THE FALSE POSITIVE ITSELF, as a probe-and-control pair rather than as a paragraph.

    This is the highest-severity defect class in this guard's threat model: the rule fired
    on correct writing. The control is the denial; the probe beside it is the assertion,
    and they differ by three words, which is why a mechanism and not a special case was
    needed.
    """
    denied = r"It does not follow that a larger pool reports a smaller floor."
    asserted = r"It follows that a larger pool reports a smaller floor."
    assert not _word_rule_hits(_check(tmp_path, denied)), (
        "the guard is RED on a sentence that DENIES the retracted claim\n"
        + _say(_word_rule_hits(_check(tmp_path, denied))))
    assert _word_rule_hits(_check(tmp_path, asserted)), (
        "...and the assertion three words away is green, so the gate is not "
        "discriminating, it is just off")


# --- 5. MUTATION TESTS. Disable each mechanism; a test must break. ---------------------
#
# The guard went from catching 0 of 32 planted probes to 32 of 32 by probe-and-control
# alone, and it was mutation testing that then proved none of the 32 mechanisms was
# vacuous. Each test below removes exactly one gate and asserts that the control it
# protects goes RED -- which is the only evidence that the gate is doing work rather than
# decorating a pattern that never fires anyway.
def test_mutation_removing_the_absent_gate_reddens_the_site_that_gets_it_right(
        tmp_path, monkeypatch):
    """Without `absent`, discussion.tex's if/else is red. That is the proof that the
    conditional gate -- not a lucky non-match in the pattern -- is what keeps the paper
    green, and the proof that the pattern really does reach the correct site."""
    text = r"""
        If it is not, a larger pool reaches a higher rung and reports a smaller floor, so
        the quantity being estimated moves with the pool instead of holding still to be
        estimated; if it is, the floor is an ordinary population proportion.
    """
    assert not _word_rule_hits(_check(tmp_path, text)), "control is not green to begin with"

    rule = _word_rule("reaches a higher rung and reports a smaller floor")
    monkeypatch.delitem(rule, "absent")
    assert _word_rule_hits(_check(tmp_path, text)), (
        "with the `absent` gate removed the conditional site is STILL green -- the gate "
        "is not what is protecting it, so the rule may not be reaching the site at all")


def test_mutation_narrowing_the_span_reddens_a_cross_sentence_conditional(
        tmp_path, monkeypatch):
    """`span=1` is not a free parameter. Set it to 0 and an if/else split across a full
    stop goes red, which is what fixes the width at 1 rather than 0."""
    text = r"""
        A larger pool reaches a higher rung and reports a smaller floor. Whether the
        population's support ends at the rung this pool reached is a question $200$
        answers cannot settle.
    """
    assert not _word_rule_hits(_check(tmp_path, text)), "control is not green to begin with"

    rule = _word_rule("reaches a higher rung and reports a smaller floor")
    monkeypatch.setitem(rule, "span", 0)
    assert _word_rule_hits(_check(tmp_path, text)), \
        "span=0 accepts a conditional a whole sentence away -- the span does nothing"


def test_mutation_removing_the_near_gate_reddens_an_unrelated_zero_rate(
        tmp_path, monkeypatch):
    r"""The `near` gate on `0.00\%` is what stops the rule reaching every zero rate in the
    repo. Remove it and an unrelated one fires."""
    text = r"Of the $80$ false-alarm targets, $0.00\%$ were rejected before scoring."
    assert not _word_rule_hits(_check(tmp_path, text)), "control is not green to begin with"

    rule = _word_rule(r"0\.00")
    monkeypatch.delitem(rule, "near")
    assert _word_rule_hits(_check(tmp_path, text)), \
        "without `near` a bare zero rate is still green -- the gate is doing nothing"


def test_mutation_removing_the_branch_gate_reddens_the_corrected_tables(
        tmp_path, monkeypatch):
    """Remove `absent` from the Wilson-coverage rule and the CORRECTED table row goes red.
    That is the evidence that the adjacency rule is discriminating on the branch name and
    not merely failing to match the digits."""
    text = r"| calibrated Ewens (tau\_top = $0.2726\%$) | $53.67\%$ | $0.00\%$ |"
    assert not _word_rule_hits(_check(tmp_path, text)), "control is not green to begin with"

    rule = _word_rule(r"53\.")
    monkeypatch.delitem(rule, "absent")
    assert _word_rule_hits(_check(tmp_path, text)), \
        "without `absent` the corrected row is still green -- the rule never matched"


def test_mutation_removing_the_negation_tempering_reddens_a_denial(tmp_path, monkeypatch):
    r"""The estimand rule's gap is a TEMPERED one -- `(?:(?!\b(?:not|never|nor|n't)\b)
    [^.;:!?]){0,28}?` -- so `estimand ... breaks` cannot span a negation. Swap in the
    untempered gap and "the estimand does not break" fires, which is the evidence that the
    tempering is load-bearing and not ornament.

    This gate is inside the pattern rather than beside it, so the mutation replaces the
    pattern. Everything else about the rule is left alone."""
    text = r"""
        The estimand does not break when the atom empties; it stops being identified,
        which is a different and stronger statement.
    """
    assert not _word_rule_hits(_check(tmp_path, text)), "control is not green to begin with"

    rule = _word_rule(r"estimand\b(?:(?!")
    monkeypatch.setitem(
        rule, "pattern",
        r"estimand\b[^.;:!?]{0,28}?\b(?:dissolv\w*|breaks?\b|broken\b)")
    assert _word_rule_hits(_check(tmp_path, text)), \
        "the untempered gap still misses the denial -- the tempering is doing nothing"


def test_mutation_removing_the_floor_gate_reddens_an_unrelated_finding(
        tmp_path, monkeypatch):
    """Remove `near` from the detector half and the class-separation finding goes red.
    That is what shows the two claims are being told apart by their subject matter rather
    than by the pattern happening not to reach one of them."""
    text = r"""
        It is a sample statistic from a small stratum, not a fixed property of the
        detector. On the score-independent \emph{fair} pool ($200$ correct, $200$
        hallucinating) the same quantity is $+0.463$ nats.
    """
    assert not _word_rule_hits(_check(tmp_path, text)), "control is not green to begin with"

    rule = _word_rule("property of the detector")
    monkeypatch.delitem(rule, "near")
    assert _word_rule_hits(_check(tmp_path, text)), \
        "without `near` the unrelated finding is still green -- the gate does nothing"


def test_mutation_every_word_rule_fires_on_something(tmp_path):
    """VACUITY. A rule that cannot fire is not a rule, and this file has shipped one before
    (`\\b5\\.0\\\\?%` could never match `5.03`, and the concession turned on that digit).
    One canonical probe per rule, keyed to the rule's own pattern so a rule added later
    without a probe fails here rather than passing silently."""
    from check_population_labels import SUPERSEDED

    probes = {
        r"estimand\b(?:(?!": r"the estimand dissolves once the ceiling atom empties",
        r"break\w*\b[^.;:!?]{0,32}?\bas an estimand\b":
            r"the empty atom also breaks the floor as an estimand",
        r"neither estimator is broken":
            r"Neither estimator is broken -- the estimand is, once the atom empties.",
        r"(?!\s+for (?:the |its )?floor\b)":
            r"A larger pool reaches a higher rung and reports a smaller floor.",
        r"\s+\w+\s+for (?:the |its )?floor\b":
            r"A larger pool gives a smaller number for the floor.",
        r"\bfloor\b[^.;:!?]{0,24}?":
            r"The floor shrinks as the pool grows.",
        r"(?:no longer|not)\s+(?:a\s+|an\s+)?":
            r"Once the atom empties the estimand is no longer well defined.",
        r"cover(?:s|ed|age|ing)?\b[^.;:!?]{0,44}?":
            r"Wilson covers the true floor about $54\%$ of the time, at nominal $95\%$.",
        r"53\.": r"Wilson covers the true floor $53.7\%$ of the time, at nominal $95\%$.",
        r"0\.00": r"the question bootstrap covers it $0.00\%$ of the time, nominal $95\%$",
        r"resolution (?:limit )?of": r"$4/200$ is the resolution of the pool.",
        r"property of the detector":
            r"the $N{=}40$ floor $2.0\%$ is not a property of the detector",
    }
    word_rules = [s for s in SUPERSEDED if str(s.get("run", "")).startswith("pre-sec")]
    assert len(word_rules) == len(probes), (
        f"{len(word_rules)} word rules but {len(probes)} probes -- every rule armed on "
        "this ruling needs one, or it can ship dead")
    for rule in word_rules:
        key = next((k for k in probes if k in rule["pattern"]), None)
        assert key, f"no probe keyed to {rule['pattern']!r}"
        hits = [p for p in _check(tmp_path, probes[key]) if rule["quantity"] in p]
        assert hits, f"VACUOUS: {rule['quantity']} never fires\n  probe: {probes[key]}"


# --- 6. structural pins ----------------------------------------------------------------
def test_every_word_rule_is_a_position_not_a_recomputation(tmp_path):
    """A word rule retires a POSITION, so it must carry a `replacement` telling the author
    what to say instead. `current` -- "the definitive run gives X" -- is the wrong shape:
    there is no rerun that makes "the estimand dissolves" true."""
    from check_population_labels import SUPERSEDED

    for s in SUPERSEDED:
        if not str(s.get("run", "")).startswith("pre-sec"):
            continue
        assert "replacement" in s and "current" not in s, s["quantity"]
        assert "results/n40_floor_estimator_ruling.md" in s["replacement"], s["quantity"]
        for pat in s.get("absent", []) + s.get("near", []):
            re.compile(pat)


def test_every_absent_rule_states_its_own_span():
    """`ABSENT_SPAN` was a module-level DEFAULT that no rule ever took, and it was removed
    on 2026-08-27 for exactly that reason: set it to 9 and the whole suite stayed green,
    which is the definition of a mechanism that is not doing anything. This test is what
    replaces it -- the span is now REQUIRED on any rule with an `absent` gate, so a new
    rule cannot inherit a width nobody chose for it.

    Note what the old structural check actually asserted: `0 <= span <= 2` on a value that
    came from `s.get("span", ABSENT_SPAN)`. It read the constant, so mutating the constant
    broke it -- and it broke on the RANGE CHECK, not on any behaviour. A test that fails
    when a dead constant changes looks like coverage and is not.
    """
    from check_population_labels import SUPERSEDED

    for s in SUPERSEDED:
        if "absent" not in s:
            continue
        assert "span" in s, (
            f"{s['quantity']}: an `absent` gate without a `span`. State the width; there "
            "is no default any more, because the default was never taken.")
        assert isinstance(s["span"], int) and 0 <= s["span"] <= 2, s["quantity"]


def test_the_ledgers_own_advice_passes_the_rules_it_gives(tmp_path):
    r"""A ledger whose advice string would fail its own rule is a ledger nobody can quote
    from -- and this one has to quote `53.67%` and `0.00%` to be useful at all. Both are
    written with their branch named in the same sentence, which is exactly what the rule
    asks of everyone else.

    THE SECOND HALF IS THE POINT. Asserting only that the advice is green proves nothing:
    a string that never matched the pattern at all would also be green, and the first
    draft of this test was exactly that vacuous. So the advice is re-run with every
    `_BRANCH_NAMED` marker blinded, and it must then go RED on both coverage rules --
    which is what shows the advice is protected by NAMING ITS BRANCH rather than by luck.
    Pinned, because the natural way to shorten that string is to drop the branch name.
    """
    from check_population_labels import SUPERSEDED, _BRANCH_NAMED

    advice = " ".join(sorted({s["replacement"] for s in SUPERSEDED
                              if str(s.get("run", "")).startswith("pre-sec")}))
    problems = _check(tmp_path, advice.replace("%", r"\%"))
    assert not _word_rule_hits(problems), \
        "the ledger's own advice trips the ledger:\n" + _say(_word_rule_hits(problems))

    blinded = advice
    for pat in _BRANCH_NAMED:
        blinded = re.sub(pat, "XXX", blinded, flags=re.IGNORECASE)
    hits = _word_rule_hits(_check(tmp_path, blinded.replace("%", r"\%"), name="blind.tex"))
    assert len(hits) >= 2 and all("measured under" in h for h in hits), (
        "with every branch marker blinded the advice is STILL green -- so the green above "
        "is not evidence of anything:\n" + _say(hits))


def test_strip_latex_is_not_safe_for_the_files_this_ledger_is_aimed_at():
    r"""THE KNOWN GAP, AND ITS FIX, PINNED AS ONE TEST because they are one fact.

    `strip_latex` deletes from an unescaped `%` to end of line. That is RIGHT for LaTeX --
    a `%` really does open a comment, and the negative lookbehind that spares `\%` is what
    keeps Table 1's saturation row visible (defect 4) -- and it is catastrophic for
    Markdown and Python, where `53.7% of the time and the` becomes `53.7` and `0.00%`
    becomes `0.00`, which `PCT` (a required percent sign) then refuses to match. That one
    behaviour was the whole of the 16 -> 14 gap measured against the sixteen prose sites of
    852e0f7: eight rules catch 16/16 through a whitespace-only flattener and 14/16 through
    `strip_latex`; the coverage pair alone catches 15/16 and 11/16.

    THE FIRST HALF still asserts the LaTeX behaviour, because paper/ depends on it. THE
    SECOND HALF asserts that `flatten` no longer applies it to the files this ledger is
    aimed at. Neither half is safe to delete: drop the first and a `.tex` comment stops
    being a comment; drop the second and the scope silently un-widens.

    The other consequence stands and is why `_BRANCH_NAMED` carries both spellings:
    `$\tau^*$` reaches the rules as a bare `^*` and `$\tau_{\mathrm{top}}$` as ` top `, so
    in a .tex file only the WORDS "Ewens", "calibrated", "branch-conditional" and "zero
    branch" can exculpate. Outside .tex the symbol entries are live -- that is asserted
    below in test_the_symbol_branch_names_come_alive_outside_tex.
    """
    from check_population_labels import flatten, strip_latex

    md = "Wilson covers the true floor 53.7% of the time and the\nbootstrap 0.00%, at 95%."
    flat = strip_latex(md)
    assert "0.00%" not in flat and "0.00" in flat, flat
    assert "of the time" not in flat, flat
    assert strip_latex(r"under $\tau^*$ the floor is").strip() == "under ^* the floor is"
    assert "tau" not in strip_latex(r"$\tau_{\mathrm{top}}$ is not identified")

    # ...and the phase-2 fix: the same text through the flattener a .md file now gets.
    for suffix in (".md", ".py", ".sh", ".json"):
        plain = flatten(md, suffix)
        assert "0.00%" in plain, (suffix, plain)
        assert "53.7% of the time and the" in plain, (suffix, plain)
    # A LaTeX comment is still a comment in a .tex file, and only there.
    assert "secret" not in flatten("visible % secret\nnext", ".tex")
    assert "secret" in flatten("visible % secret\nnext", ".md")


# ======================================================================================
# Regression: the two original constructions
# ======================================================================================
def test_catches_an_unlabelled_fair_pool_auroc(tmp_path):
    """A bare 0.704 with no pool named is exactly site four. It must fail."""
    problems = _check(
        tmp_path,
        "The detector separates correct from wrong answers at AUROC $0.704$.")
    assert problems, "an unlabelled 0.704 must be reported"


def test_catches_the_real_site_four_construction(tmp_path):
    """Verbatim shape of the Conclusion error: ceiling stats, then 'the same pool', then
    the fair-pool AUROC. The populations differ and this must not pass."""
    problems = _check(tmp_path, r"""
        the estimator offers only $22$ distinct values across our pool. This is not a
        claim that the detector fails: on the same pool it separates correct from
        hallucinating answers moderately well, at AUROC $0.704$.
    """)
    assert problems, "the original site-four construction must be reported"


def test_quarantined_numbers_require_an_attacked_marker(tmp_path):
    """0.579 and 0.184 describe the quarantined attacked subset. Presenting either as a
    property of 'the detector' is the error withdrawn in c92fe2a."""
    problems = _check(
        tmp_path,
        "The detector separates the classes by $0.184$ nats (AUROC $0.579$).")
    assert problems, "quarantined-population numbers must demand an attacked-pool label"


# ======================================================================================
# Housekeeping
# ======================================================================================
def test_every_rule_names_a_known_pool_and_compiles():
    from check_population_labels import POOLS, RULES, SUPERSEDED

    for rule in RULES:
        assert rule["owner"] in POOLS, rule["name"]
        for other in rule["foreign"]:
            assert other in POOLS, rule["name"]
            assert other != rule["owner"], rule["name"]
        # `exclusive` says "a foreign label in this sentence is itself the error", which
        # means nothing without foreign pools to exclude.
        if rule.get("exclusive"):
            assert rule["foreign"], rule["name"]
        # `coexist` says the opposite -- "these populations are NESTED, so a foreign label
        # accuses only where the owner is absent". Same precondition, and the two are
        # contradictory: a rule claiming both would be saying its pools are disjoint and
        # nested at once, and the disjoint branch would silently win.
        if rule.get("coexist"):
            assert rule["foreign"], rule["name"]
            assert not rule.get("exclusive"), (
                f"{rule['name']}: `exclusive` and `coexist` are opposites -- a rule cannot "
                "declare its populations both disjoint and nested.")
        for pat in rule["numbers"] + list(rule.get("requires", [])):
            re.compile(pat)
    for item in SUPERSEDED:
        re.compile(item["pattern"])
        for pat in item.get("near", []) + item.get("absent", []):
            re.compile(pat)


def test_every_growing_cell_pattern_compiles_and_captures_a_count():
    """The growing rule reads group(1) as an integer. A pattern without that group would
    raise at check time, on a file the author is trying to get green."""
    from check_population_labels import GROWING_CELLS

    for pattern, what, allowed, near in GROWING_CELLS:
        rx = re.compile(pattern)
        assert rx.groups >= 1, pattern
        assert what and isinstance(allowed, frozenset), pattern
        for p in (near or []):
            re.compile(p)


def _literal(pattern: str) -> str:
    """Best-effort plain text of a regex, so the guard can be pointed at its own labels."""
    s = re.sub(r"\(\?<![^)]*\)", "", pattern)      # lookbehinds
    s = re.sub(r"\(\?[:=!][^)]*\)", " ", s)        # non-capturing / lookahead groups
    s = re.sub(r"\{\d*(?:,\d*)?\}", "", s)         # repetition counts are not data
    for token, repl in ((r"\b", ""), (r"\s*", " "), (r"\s+", " "), ("\\", "")):
        s = s.replace(token, repl)
    return s


def test_no_pool_label_may_carry_a_count_of_a_cell_that_is_not_closed():
    """THE structural pin for the inversion, and the one rule that would have caught it.

    The guard went wrong because `97 targets`, `97-target`, `17 wrong` and `17 hide` sat on
    the attacked pool's LABEL list. A label is an assertion about the world; those four
    stopped being true and nothing re-checked them, so a retired count became a licence to
    attach anything to it. Hardening the attachment logic could not find that, because the
    attachment logic was working perfectly on a false premise.

    So: every integer that appears anywhere in any label must be a DECLARED-COMPLETE cell
    size. Re-adding `17 wrong` fails here; so does `52 wrong`, and so does the 160 total on
    the day the hide arm closes, until whoever closes it says so in FROZEN_COUNTS.
    """
    from check_population_labels import FROZEN_COUNTS, POOLS

    offenders = []
    for pool, spec in POOLS.items():
        for pat in spec["labels"]:
            for found in re.findall(r"\d+", _literal(pat)):
                if int(found) not in FROZEN_COUNTS:
                    offenders.append(f"{pool}: {pat!r} asserts the count {found}")
    assert not offenders, (
        "a pool label names a count that is not a declared-complete cell size "
        f"(frozen: {sorted(FROZEN_COUNTS)}):\n  " + "\n  ".join(offenders))


def test_the_retired_labels_are_gone_and_stay_gone():
    """Named explicitly, because these four are the ones that inverted the guard and the
    generic test above would not name them in a failure message."""
    from check_population_labels import POOLS, RULES

    flat = " ".join(p for spec in POOLS.values() for p in spec["labels"])
    for retired in ("97 targets", "97-target", "17 wrong", "17 hide"):
        assert retired not in flat, f"{retired!r} is a retired count, not a label"
    # ...and the rule whose only job was to legitimise the phrase.
    assert not any("97" in r["name"] for r in RULES)


def test_the_guard_is_cheap_enough_to_run_in_the_suite():
    import time

    t0 = time.perf_counter()
    main()
    assert time.perf_counter() - t0 < 5.0


# ======================================================================================
# ROUND SIX (2026-08-26): THE SCOPE.
#
# Round five armed eight rules for a defect class whose sixteen known instances all live in
# `results/`, `scripts/`, `tests/` and `figures/` -- and then pointed them at eight files in
# `paper/`. The rules could not reach a single site they were written for. This round moves
# the scope, and almost all of the work is deciding what NOT to move.
#
# THE MEASUREMENT THAT DECIDED IT, over the 201 tier-2 files, one family at a time. It is
# `scope_census()` in the checker, printed by `--dry-run`, and pinned below by
# test_the_scope_census_matches_the_numbers_the_docstring_argues_from -- so the argument
# cannot age quietly, which is the failure mode every earlier round of this file records:
#
#     the pool / attachment rules          736 findings in 52 files
#     the growing-denominator rule          73 findings in 36 files
#     the retired-VALUE half of SUPERSEDED  273 findings in 38 files
#     the retired-POSITION rules (these)     32 findings in  7 files  <- the only one that ports
#
# The first three are not backlogs, they are category errors, and each has its own reason
# (the module docstring's SCOPE section states all three). The short version: the pool and
# growing rules arbitrate by SENTENCE DISTANCE and neither a markdown table row nor a line
# of Python has sentences; and a retired VALUE is legitimately stored, pinned and corrected
# all over this repo, while a retired POSITION is only ever asserted. Those are the two
# controls this section spends most of its length on, because getting either wrong in the
# permissive direction ships a guard nobody can keep green.
#
# THE RATCHET holds the 32 that do port. `check_operational_provenance.py` already had this
# device and it is followed rather than reinvented, in both directions: a file that gains a
# finding fails, and a file that drops below its baseline fails too, so the register cannot
# rot upward. 6 of the 32 are correction notes quoting what they used to say, 21 are a
# coverage figure with no branch named, and 5 are a live unconditional assertion of a
# position section 13 retracts -- pinned, in a register that says which is which, rather
# than silenced.
# ======================================================================================
def _wide(tmp_path, text: str, name: str) -> list[str]:
    """Check `text` as a file of the given name -- i.e. through the tier-2 ruleset."""
    assert not name.endswith(".tex"), "use _check for the LaTeX tier"
    f = tmp_path / name
    f.write_text(textwrap.dedent(text).strip() + "\n", encoding="utf-8")
    return check_file(f)


# --- 1. the flattener, per suffix ------------------------------------------------------
def test_markdown_emphasis_cannot_split_a_guarded_phrase(tmp_path):
    r"""The `\emph{fair} pool` lesson, one markup language over. The pre-fix wording of
    docs/START_HERE_overnight.md is the probe, verbatim: it carries the retired sentence
    with an asterisk pair sitting in the middle of it, which is exactly a phrase rule's
    blind spot."""
    real = ("makes the granularity point without any statistics: the lattice at N=40 is "
            "dense, which is precisely why `4/200` is a resolution limit of the *pool* "
            "and not a property of the detector.")
    hits = _word_rule_hits(_wide(tmp_path, real, "START_HERE_overnight.md"))
    assert len(hits) >= 2, (
        "asterisk emphasis hid the retired sentence from the rules written for it:\n"
        + _say(hits))
    # ...and the backtick around `4/200` did not stop `_FLOOR_RESOLUTION_CTX` gating it.
    assert any("property of the detector" in h for h in hits), _say(hits)


def test_the_plain_flattener_leaves_identifier_underscores_alone(tmp_path):
    """`_` is the word separator in every path and constant this repo cites, so it is NOT
    treated as emphasis -- the same call `check_operational_provenance.py` makes.

    The cost is a REAL blind spot and it is asserted here rather than described: markdown
    underscore emphasis inside a guarded phrase breaks `\\b` and is not seen. Pinned as the
    current behaviour so that anyone who fixes it has to come here and say so.
    """
    from check_population_labels import strip_plain

    flat = strip_plain("see `results/n40_floor_estimator_ruling.md` and `_BRANCH_NAMED`")
    assert "n40_floor_estimator_ruling.md" in flat, flat
    assert "_BRANCH_NAMED" in flat, flat

    seen = _word_rule_hits(_wide(tmp_path, "the _estimand_ dissolves once the atom empties",
                                 "probe.md"))
    assert not seen, (
        "underscore emphasis is now flattened -- good, but the note in `strip_plain` and "
        "the residual list in the module docstring both say it is not. Update them.")
    # the same sentence without the underscores is caught, so the miss is the markup.
    assert _word_rule_hits(_wide(tmp_path, "the estimand dissolves once the atom empties",
                                 "probe.md"))


def test_backticks_cannot_split_a_guarded_phrase(tmp_path):
    """Generated markdown wraps identifiers in backticks constantly, and three of the
    sixteen sites had one inside the phrase."""
    hits = _word_rule_hits(_wide(
        tmp_path,
        "a larger pool reaches a higher rung and `reports a smaller floor`, so the "
        "quantity moves with the pool",
        "n_scaling_grid.md"))
    assert hits, "a backtick split the phrase"


def test_the_symbol_branch_names_come_alive_outside_tex(tmp_path):
    """`_BRANCH_NAMED` carries `tau_top` and `tau *` entries that are DEAD in .tex, because
    `strip_latex` eats `\\tau` with every other command. Outside .tex the corrected tables
    carry a literal `tau_top`, and the entries earn their place -- which the round-five
    note predicted and could not test, because the scope did not reach a .md file yet."""
    from check_population_labels import flatten

    assert "tau" not in flatten(r"$\tau_{\mathrm{top}}$ is not identified", ".tex")
    assert "tau_top" in flatten("tau_top is not identified", ".md")

    bare = "Wilson covers the true floor 53.7% of the time, at nominal 95%."
    assert _word_rule_hits(_wide(tmp_path, bare, "probe.md")), "the bare figure must fire"
    named = ("At tau_top = 0.2726% Wilson covers the true floor 53.7% of the time, "
             "at nominal 95%.")
    assert not _word_rule_hits(_wide(tmp_path, named, "probe.md")), \
        "naming the branch with the symbol must exculpate outside .tex"


# --- 2. a planted defect fires in every newly-scoped file type -------------------------
@pytest.mark.parametrize("name,text", [
    ("a generated report",
     "notes.md::> **WITHDRAWN.** Both candidates fail and the estimand dissolves when "
     "the ceiling atom empties, so the row prints a point."),
    ("a generator's string literal",
     'gen.py::    log("the empty atom -- also breaks the floor as an estimand. Its")'),
    ("a code comment",
     "gen.py::# 4/200 is the resolution of the pool rather than a measurement of anything."),
    ("a docstring",
     'fig.py::"""A larger pool reaches a higher rung and reports a smaller floor."""'),
    ("a test docstring",
     'test_x.py::def t():\n    """Neither estimator is broken -- the estimand is."""'),
    ("an assertion message",
     'test_x.py::assert ok, "the N=40 floor 2.0% is not a property of the detector"'),
    ("a shell wrapper's banner",
     'run.sh::echo "withdrawn: Wilson covers it 53.7% of the time at nominal 95%"'),
    ("a figure sidecar",
     'stats.json::{"note": "question bootstrap coverage 0.00%, nominal 95%"}'),
])
def test_a_planted_position_defect_fires_in_every_newly_scoped_file_type(
        tmp_path, name, text):
    """Every representation the 852e0f7 sweep found, one per file type now in scope.

    The commit message enumerates them: generator string literals, code comments,
    docstrings, a provenance banner, test docstrings, an assertion message, a refusal
    message, doc prose. Not one contained a digit of the quantity in dispute, and not one
    was reachable by a checker that read `paper/*.tex`.
    """
    fname, body = text.split("::", 1)
    hits = _word_rule_hits(_wide(tmp_path, body, fname))
    assert hits, f"{name}: a planted defect in {fname} was not reported"


def test_the_corrected_form_of_each_is_green_in_the_same_file_type(tmp_path):
    """The other half, and the half that decides whether anyone keeps the guard on. Each
    probe above, rewritten the way the ruling says to write it, in the same file type."""
    ok = [
        ("notes.md",
         "> **WITHDRAWN.** tau_top is not identified at n=200: whether 4/200 estimates a "
         "population floor turns on whether the population can yield 39 mutually "
         "inequivalent answers out of 40, and n=200 cannot decide."),
        ("gen.py",
         'log("if the population can never reach the top rung, 4/200 estimates a real")'),
        ("fig.py",
         '"""Under the calibrated Ewens fit Wilson covers 53.7% and the question '
         'bootstrap 0.00%; under the zero branch, 95.06% and 100%."""'),
        ("stats.json",
         '{"note": "zero branch: question bootstrap coverage 100%, nominal 95%"}'),
    ]
    for fname, body in ok:
        hits = _word_rule_hits(_wide(tmp_path, body, fname))
        assert not hits, f"{fname}: the CORRECTED wording was flagged\n" + _say(hits)


# --- 3. what does NOT run outside .tex, and the measurement behind each -----------------
def test_the_pool_rules_do_not_run_outside_tex(tmp_path):
    """1031 findings, and they are a category error rather than a backlog.

    THE SAME TEXT is used twice: as `.tex` it must be reported (the pool rules work, and
    are not being quietly disarmed), and as `.md` and `.py` it must not. The probe is the
    real shape from `scripts/replay_control.py` -- an AUROC inside a `log(...)` whose
    population is named four hundred characters away in a different `log(...)`.
    """
    probe = 'log("Claim 1 -- AUROC 0.704 -> 0.746 (+0.042): DOES NOT SURVIVE.")'
    assert _check(tmp_path, probe), "the pool rules must still fire on .tex"
    for name in ("replay_control.py", "replay_control.md"):
        assert not _wide(tmp_path, probe, name), (
            f"a pool rule reached {name}; a guard that demands a fair-pool label beside "
            "every 0.704 in generated output is one nobody can keep green")


def test_the_generated_table_shape_is_the_reason_and_not_an_excuse(tmp_path):
    """The single worst case, verbatim from results/likelihood_weight_sensitivity.md: one
    table, 64 rows, the same `1.380` on every one of them, the population declared in the
    prose above. `_TERM_RE` needs `[.:;!?]` before whitespace and a table row has none, so
    the whole table is one sentence and every row is unlabelled."""
    row = "| 1e-05 | 1.380 | 9.50% | 21.5% | 9.50% | 9.5% | 9.5% | 21.5% | 170 |"
    table = "\n".join([row] * 6)
    assert not _wide(tmp_path, table, "likelihood_weight_sensitivity.md")
    # ...and in a .tex file the same number is still guarded, which is the point of the
    # scoping rather than of the flattener.
    assert _check(tmp_path, "the clean correct mean is $1.380$ nats")


def test_the_growing_rule_does_not_run_outside_tex(tmp_path):
    """174 findings. A dated snapshot of a filling cell is HISTORY -- results/
    attack_matrix.md's "15 hide" was true the week it was written. The rule exists to stop
    a filling cell being quoted FORWARD, and forward is paper/."""
    probe = "the hide stratum stands at 52 hide targets as of tonight"
    assert _check(tmp_path, probe), "the growing rule must still fire on .tex"
    assert not _wide(tmp_path, probe, "attack_matrix.md")


def test_a_retired_value_is_reported_in_the_paper_and_not_in_a_run_artifact(tmp_path):
    """302 findings, and this is the decision the brief warned could go wrong in either
    direction. The probe is a `_def`-era figure. In `paper/` it is a staleness bug. In
    `results/winners_curse_partial.md` -- the `_def` checkpoint's own report -- it is a
    measurement, correct for the run that produced it."""
    tex = (r"re-scoring retains $45\%$ of the selection-time effect on the "
           r"winner's-curse subset")
    md = "re-scoring retains 45% of the selection-time effect on the winner's-curse subset"
    assert _check(tmp_path, tex), "a retired value must still be caught in .tex"
    assert not _wide(tmp_path, md, "winners_curse_partial.md")
    # ...and the escaping is not what does the work: the .tex rendering is silent there too,
    # so the exemption is the SCOPE and not an accident of `\%`.
    assert not _wide(tmp_path, tex, "winners_curse_partial.md")


def test_a_test_fixture_asserting_a_retired_value_is_correct_usage(tmp_path):
    """The brief's own example, and the shape that decided the value/position line.

    tests/test_derived_paper_quantities.py carries the banned-literal list that keeps the
    withdrawn intervals OUT of the paper. It has to contain them to check for them. A guard
    that flagged it would be flagging the guard -- and it would be doing so at 17 findings
    in that one file.
    """
    fixture = (
        'for banned in (r"2.0\\% [0.8, 5.0]", r"[0.78, 5.03]", r"[0.5, 4.0]",\n'
        '               "0.7804", "5.0287", "0.78037", "5.02866"):\n'
        '    assert " ".join(banned.split()) not in paper, "paper/ has stale intervals"\n')
    assert not _wide(tmp_path, fixture, "test_derived_paper_quantities.py")
    # A POSITION planted in the same fixture file IS reported -- the exemption is the
    # value/position line, not the directory.
    assert _word_rule_hits(_wide(
        tmp_path, fixture + '\n# the estimand dissolves once the atom empties\n',
        "test_derived_paper_quantities.py"))


# --- 4. the control the brief asked for by name: the checker's own patterns -------------
def test_the_checker_does_not_flag_its_own_rule_patterns():
    """A ledger of retired sentences contains every retired sentence. Twice, in fact: once
    as a regex and once in the `quantity` prose that explains it ("...described as 'the
    resolution of the pool'").

    BOTH HALVES MATTER. That the ledger and its probes are out of scope is the first half;
    the second is that the exclusion is LOAD-BEARING rather than decorative, which is shown
    by scanning them anyway and finding that they would report. An exclusion nobody has
    checked is indistinguishable from a rule that never fired.
    """
    from check_population_labels import OUT_OF_SCOPE, check_file as cf, wide_files

    scoped = {p.relative_to(REPO).as_posix() for p in wide_files()}
    for name in ("scripts/check_population_labels.py", "tests/test_population_labels.py"):
        assert name in OUT_OF_SCOPE, f"{name} must be excluded BY NAME, with a reason"
        assert name not in scoped, f"{name} is being scanned"
        n = len(cf(REPO / name))
        assert n > 0, (
            f"{name} reports nothing, so its exclusion protects nothing -- either the "
            "rules stopped matching their own patterns (check them) or the exclusion is "
            "dead weight and should go")


def test_every_out_of_scope_entry_is_real_and_says_why():
    """An exclusion list is an assertion about the world and expires like `labels` did
    (defect 5). Three failure modes, all cheap to catch: an entry naming a file that no
    longer exists, an entry with no stated reason, and an entry that would be picked up by
    no glob anyway -- which means it is decoration rather than an exclusion."""
    from check_population_labels import OUT_OF_SCOPE, WIDE_GLOBS

    reachable = {p.relative_to(REPO).as_posix()
                 for g in WIDE_GLOBS for p in REPO.glob(g) if p.is_file()}
    for name, reason in OUT_OF_SCOPE.items():
        assert (REPO / name).exists(), f"{name} is excluded but does not exist"
        assert len(reason) > 40, f"{name} is excluded without a stated reason"
        assert name in reachable, (
            f"{name} is in OUT_OF_SCOPE but no glob reaches it -- the entry is decoration, "
            "and a reader will believe it is doing work")


def test_the_ledgers_own_prose_is_still_guarded_despite_the_exclusion():
    """Excluding the ledger from the scan does not leave its prose unguarded: the advice
    strings are re-run through the rules by
    test_the_ledgers_own_advice_passes_the_rules_it_gives, and blinded to prove it. This
    test only pins that the two arrangements are connected, so removing one is visible."""
    from check_population_labels import OUT_OF_SCOPE, SUPERSEDED

    assert "scripts/check_population_labels.py" in OUT_OF_SCOPE
    advice = {s["replacement"] for s in SUPERSEDED if s.get("wide")}
    assert advice, "no wide rule carries a replacement, so there is no prose to guard"
    assert all("n40_floor_estimator_ruling.md" in a for a in advice)


# --- 5. the tier-2 ledger is exactly the position rules --------------------------------
def test_the_wide_set_is_exactly_the_position_rules():
    """The `wide` flag decides scope, so it must not be settable by taste.

    THREE DEFINITIONS OF THE SAME SET, held together here: the flag, the `pre-sec` run
    marker round five used, and the PROPERTY -- a wide rule retires a POSITION, so it
    carries a `replacement` and never a `current`. That is the whole argument for the
    tier-2 line (a value is stored all over this repo; a position is only ever asserted),
    and if a future entry can get the wider scope while carrying a `current`, the argument
    is gone and 302 findings come with it.
    """
    from check_population_labels import (SUPERSEDED, WIDE_SUPERSEDED,
                                         _COVERAGE_PAIR, _NOT_IDENTIFIED)

    by_flag = {s["quantity"] for s in SUPERSEDED if s.get("wide")}
    by_marker = {s["quantity"] for s in SUPERSEDED
                 if str(s.get("run", "")).startswith("pre-sec")}
    by_property = {s["quantity"] for s in SUPERSEDED
                   if s.get("replacement") in (_NOT_IDENTIFIED, _COVERAGE_PAIR)}
    assert by_flag == by_marker == by_property, (
        "the three definitions of the tier-2 set disagree:\n"
        f"  flag only     : {sorted(by_flag - by_property)}\n"
        f"  property only : {sorted(by_property - by_flag)}")
    assert len(WIDE_SUPERSEDED) == len(by_flag) == 12
    for s in WIDE_SUPERSEDED:
        assert "current" not in s, (
            f"{s['quantity']}: a wide rule may not carry a recomputed value -- there is no "
            "rerun that makes a retracted position true")


def test_no_retired_value_rule_leaks_into_the_wider_scope(tmp_path):
    """The complement, stated as behaviour rather than as data. Every SUPERSEDED entry that
    is NOT wide must be silent on a .md file, or the 302-finding backlog is back."""
    from check_population_labels import SUPERSEDED

    narrow = [s for s in SUPERSEDED if not s.get("wide")]
    assert len(narrow) == 29
    quantities = [s["quantity"] for s in narrow]
    body = "\n".join([
        "39/80 targets finish at the ln N ceiling; 31/80 of that is attack-induced.",
        "corr(headroom, move) is +0.70 within the uncensored subset after re-scoring.",
        "Wilson on 4/200 gives [0.78, 5.03]; the question bootstrap [0.5, 4.0].",
        "the estimator offers 22 distinct values, 22 of the 39 attainable, and 27/97.",
        "re-scoring retains 45% of the effect, bootstrap [25%, 65%], 36 of the 69.",
    ])
    found = [p for p in _wide(tmp_path, body, "old_run.md")
             if any(q in p for q in quantities)]
    assert not found, "a retired-VALUE rule ran outside .tex:\n" + _say(found)
    # ...and every one of them still fires in the paper.
    assert len([p for p in _check(tmp_path, body) if any(q in p for q in quantities)]) >= 8


# --- 6. THE RATCHET --------------------------------------------------------------------
def test_the_register_matches_the_repo_today():
    """The ratchet is only worth anything if its numbers are true when it is struck. This
    is the test that would have failed on the day someone raised a pin to clear a red."""
    from check_population_labels import KNOWN_OPEN, check_file as cf, wide_files

    live = {p.relative_to(REPO).as_posix(): len(cf(p)) for p in wide_files()}
    open_now = {k: v for k, v in live.items() if v}
    assert open_now == KNOWN_OPEN, (
        "KNOWN_OPEN and the repo disagree.\n"
        f"  found but not pinned : { {k: v for k, v in open_now.items() if KNOWN_OPEN.get(k) != v} }\n"
        f"  pinned but not found : { {k: v for k, v in KNOWN_OPEN.items() if open_now.get(k) != v} }")
    assert sum(KNOWN_OPEN.values()) == 26 and len(KNOWN_OPEN) == 5


def test_a_new_defect_in_a_pinned_file_still_fails(tmp_path):
    """PINNED, NOT SILENCED -- the property the whole device exists for. Take the most
    heavily pinned file in the register, add one sentence, and the ratchet must notice."""
    from check_population_labels import KNOWN_OPEN, _ratchet, check_file as cf, wide_files

    worst = max(KNOWN_OPEN, key=KNOWN_OPEN.get)
    baseline = KNOWN_OPEN[worst]
    assert not _ratchet({p.relative_to(REPO).as_posix(): len(cf(p)) for p in wide_files()})

    copy = tmp_path / worst.rsplit("/", 1)[-1]
    copy.write_text((REPO / worst).read_text(encoding="utf-8")
                    + "\n\nThe estimand dissolves once the ceiling atom empties.\n",
                    encoding="utf-8")
    assert len(cf(copy)) == baseline + 1, "the planted sentence was not reported"
    live = {f.relative_to(REPO).as_posix(): len(cf(f)) for f in wide_files()}
    problems = _ratchet({**live, worst: baseline + 1})
    assert len(problems) == 1, _say(problems)
    assert problems[0].startswith(f"{worst}: ratchet:")
    assert "1 NEW one(s)" in problems[0], problems[0]


def test_the_ratchet_fails_in_both_directions_and_on_an_orphan():
    """A file that GAINS one fails; a file that LOSES one fails too, so the register cannot
    be raised and left to rot (defect 7's shape, third copy); and an entry naming a file
    that has left the scope is itself reported, so the map cannot outlive its subject."""
    from check_population_labels import KNOWN_OPEN, _ratchet

    name = "results/replay_control.md"
    base = KNOWN_OPEN[name]

    gained = _ratchet({**{k: v for k, v in KNOWN_OPEN.items()}, name: base + 2})
    assert len(gained) == 1 and "ratchet:" in gained[0] and "2 NEW" in gained[0]

    dropped = _ratchet({**{k: v for k, v in KNOWN_OPEN.items()}, name: base - 1})
    assert len(dropped) == 1 and "ratchet-stale" in dropped[0]
    assert f"lower KNOWN_OPEN['{name}'] to {base - 1}" in dropped[0]

    orphan = _ratchet({k: v for k, v in KNOWN_OPEN.items() if k != name})
    assert len(orphan) == 1 and "ratchet-orphan" in orphan[0]

    # a file with no entry has an implied baseline of 0, so its first finding fails
    fresh = _ratchet({**KNOWN_OPEN, "results/brand_new.md": 1})
    assert len(fresh) == 1 and "baseline of 0" in fresh[0]


def test_the_failure_message_says_how_to_lower_a_baseline_honestly_and_dishonestly():
    """Required of this change explicitly, and it is not decoration: the pressure to raise
    a pin arrives at the exact moment the suite is red and someone is in a hurry. The
    message has to name the dishonest moves, including the one that does not look like a
    baseline edit at all -- widening a gate until the finding disappears."""
    from check_population_labels import KNOWN_OPEN, RATCHET_ADVICE, _ratchet

    msg = _ratchet({**KNOWN_OPEN, "figures/README.md": 99})[0]
    assert RATCHET_ADVICE in msg
    low = msg.lower()
    for honest in ("fix the site", "same commit"):
        assert honest in low, f"the message never says to {honest!r}"
    for dishonest in ("raising the pin", "out_of_scope", "widening a gate",
                      "deleting the file's entry"):
        assert dishonest in low, f"the message never names {dishonest!r} as dishonest"
    assert "n40_floor_estimator_ruling.md" in msg, (
        "the message should name the ruling a widened gate would quietly repeal")


def test_the_pinned_findings_are_not_printed_on_an_unrelated_failure(capsys):
    """A red run must show the NEW finding, not thirty-two pinned ones with it buried
    inside. This file's own docstring says a guard whose output stops being read has the
    same end state as a guard that cannot fail."""
    import check_population_labels as C

    C.main()
    out = capsys.readouterr().out
    assert "OK (" in out and "26 finding(s) pinned in 5" in out
    assert "STALE VALUE" not in out, "a green run printed the pinned backlog"


def test_dry_run_prints_the_register_and_never_fails(capsys):
    """The honest way to re-strike the register: what IS, printed beside what is PINNED,
    with no red suite applying pressure to the comparison."""
    import check_population_labels as C

    assert C.main(["--dry-run"]) == 0
    out = capsys.readouterr().out
    for name in C.KNOWN_OPEN:
        assert name in out, f"{name} missing from --dry-run"
    assert "found" in out and "pinned" in out


# --- 7. scope plumbing -----------------------------------------------------------------
def test_the_scope_reaches_the_four_directories_the_sweep_found(tmp_path):
    """`results/`, `scripts/`, `tests/` and `figures/` carried all sixteen sites, and
    `tests/` is the one a previous post-mortem named as unreachable by name."""
    from check_population_labels import wide_files

    scoped = {p.relative_to(REPO).as_posix() for p in wide_files()}
    for d in ("results/", "scripts/", "tests/", "figures/", "docs/"):
        assert any(s.startswith(d) for s in scoped), f"{d} is not in scope"
    for f in ("tests/test_replay_control.py", "scripts/n_scaling_grid.py",
              "results/n_scaling_grid.md", "figures/README.md"):
        assert f in scoped, f"{f} carried one of the sixteen sites and is not scanned"
    assert len(scoped) > 150


def test_the_scope_is_not_recursive_by_accident():
    """A glob that grows on its own cannot have a ratchet: the baseline would move without
    anyone editing anything.

    THE INVARIANT IS "NAMES ONE DIRECTORY", NOT "IS ONE DEEP". It was written as
    `g.count("/") == 1` and that was the right test for a scope that happened to be flat;
    when `src/se/attacks/*.py` and the root `README.md` were added on 2026-08-27 it would
    have rejected both for depth rather than for growth, which is not what it is for. What
    actually matters is that no component before the filename contains a wildcard: then the
    set of directories scanned is fixed by this tuple and a new subdirectory cannot join it
    without someone editing this file.
    """
    from check_population_labels import WIDE_GLOBS

    for g in WIDE_GLOBS:
        assert "**" not in g, f"{g} is recursive; a new subdirectory would move the register"
        head, _, tail = g.rpartition("/")
        assert "*" not in head and "?" not in head, (
            f"{g} wildcards a DIRECTORY component; the set of directories scanned must be "
            "fixed by WIDE_GLOBS, or the register moves without anyone editing anything")
        assert tail, g


def test_the_paper_tier_is_untouched_by_the_widening():
    """paper/ still gets every rule. The widening is additive or it is a regression."""
    from check_population_labels import GROWING_CELLS, RULES, SUPERSEDED, paper_files

    assert len(paper_files()) == 8
    assert (len(RULES), len(SUPERSEDED), len(GROWING_CELLS)) == (16, 41, 18)
    assert main() == 0


def test_the_flattener_dispatches_on_suffix_and_not_on_directory(tmp_path):
    """Load-bearing for this whole file: the hundred-odd probes above write `probe.tex`
    into a tmp_path nowhere near paper/, and they must keep getting the LaTeX flattener and
    the full ruleset."""
    from check_population_labels import flatten, strip_latex, strip_plain

    for suffix in (".tex",):
        assert flatten("a % b", suffix) == strip_latex("a % b")
    for suffix in (".md", ".py", ".sh", ".json", ".txt", ""):
        assert flatten("a % b", suffix) == strip_plain("a % b")
    # the probe convention itself
    assert _check(tmp_path, "The detector separates at AUROC $0.704$.")


def test_the_widened_guard_is_still_cheap_enough_for_the_suite():
    """201 more files, read on every run of the suite. Measured at ~0.6 s."""
    import time

    t0 = time.perf_counter()
    assert main() == 0
    assert time.perf_counter() - t0 < 5.0


# --- 8. the sixteen sites themselves, verbatim -----------------------------------------
# Not paraphrases. These are lines DELETED by commit 852e0f7 ("sixteen more sites, none of
# them containing a digit"), one per file it touched, each replayed into a file of the same
# name and suffix. A rule that fires on a rewording of a defect and not on the defect is a
# rule that was written after the fact; this is the section that says otherwise.
@pytest.mark.parametrize("fname,removed", [
    ("START_HERE_overnight.md",
     "bootstrap **0.00%**, at nominal 95%. The reason is not data selection. It is that "
     "the estimand\ndissolves — `4/200` is the **resolution limit of a 200-answer "
     "pool**, not an estimate of a\npopulation floor, and a larger pool reaches a higher "
     "rung and reports a smaller one."),
    ("n_scaling_grid.md",
     "the empty atom -- also breaks the floor as an estimand. Its threshold is no\n"
     "and that rung is not the top of the population's support: a larger pool\n"
     "reaches a higher one and reports a SMALLER floor, so the quantity moves with\n"
     "the pool rather than holding still to be estimated. Measured coverage at a\n"
     "nominal 95%, against a population model validated out-of-sample on the two\n"
     "smaller budgets in this table: Wilson on the first-firing count 53.7%, a\n"
     "question bootstrap over the questions 0.00%."),
    ("replay_control.md",
     "> **WITHDRAWN, 2026-08-19.** The N=40 floor's interval -- BOTH candidates. Wilson "
     "on\n> 4/200 and the question bootstrap cover the true floor 53.7% and 0.00% of the "
     "time\n> respectively at nominal 95%, because the estimand stops existing when the "
     "ceiling atom\n> empties."),
    ("derived_paper_quantities.py",
     "    # atoms: Wilson [0.78, 5.03] covers the true floor 53.7% of the time at "
     "nominal 95%,\n    # the question bootstrap [0.50, 4.00] covers it 0.00% of the "
     "time, and neither is\n    # broken -- the ESTIMAND breaks, because once the ceiling "
     "atom empties \"the floor\" is\n    # the multiplicity of whichever rung this pool "
     "happened to reach and moves with the\n    # pool size."),
    ("make_floor_budget_figure.py",
     "                 \"results/n40_floor_estimator_ruling.md withdrew both candidates "
     "-- \"\n                 \"Wilson on 4/200 covers the true floor 53.7% of the time "
     "and the \"\n                 \"question bootstrap 0.00%, at nominal 95%. If that "
     "ruling has been \"\n                 \"overturned, change it there first and say so "
     "here.\")"),
    ("n_scaling_grid.py",
     "    # floor, so the estimand moves with the pool instead of holding still to be "
     "estimated.\n    # `results/n40_floor_estimator_ruling.md` measured what that costs, "
     "against a\n    # population model validated out-of-sample on the N=20 and N=10 "
     "atoms: at nominal 95%,\n    # Wilson on the first-firing count covers the true "
     "floor 53.7% of the time and a\n    # question bootstrap 0.00%."),
    # CORRECTED 2026-08-27, after an audit found these two attributed to the wrong file --
    # which, in the one section whose whole claim is "the rules were not written after the
    # fact", is the error it can least afford. The `replay_control.py` entry replayed two
    # `log(...)` lines that 852e0f7 deleted from scripts/n_scaling_grid.py, so
    # scripts/replay_control.py -- a file the commit DID touch -- had no entry of its own
    # while appearing to have one. The `test_n_scaling_grid.py` entry replayed a sentence
    # that is in no version of any file in the commit: a fair paraphrase of the docstring
    # actually deleted, and a paraphrase is precisely what this section exists to rule out.
    # Both are now verbatim, and test_every_replayed_line_is_really_in_that_commit checks
    # all eight against `git show 852e0f7` so this cannot happen a third time.
    ("replay_control.py",
     "    log(\"Neither estimator is broken. THE ESTIMAND BREAKS, and it breaks exactly "
     "when the\")\n    log(\"ceiling atom empties. While the atom carries mass the floor "
     "is a fixed population\")"),
    ("test_n_scaling_grid.py",
     "    threshold becomes the top score this pool happened to reach, which is not the "
     "top of\n    the population's support -- a larger pool reaches a higher rung and "
     "reports a smaller\n    floor -- so the estimand moves with the pool."),
])
def test_the_removed_lines_of_852e0f7_all_go_red(tmp_path, fname, removed):
    """Every file the sixteen-site sweep touched, in the representation it used."""
    hits = _word_rule_hits(_wide(tmp_path, removed, fname))
    assert hits, f"{fname}: the text 852e0f7 DELETED is not reported"


def test_every_replayed_line_is_really_in_that_commit():
    """THE GUARD ON THE SECTION ABOVE, added 2026-08-27 after an audit found 2 of its 8
    entries attributed to the wrong file.

    That section makes the strongest claim in this file: "a rule that fires on a rewording
    of a defect and not on the defect is a rule that was written after the fact; this is
    the section that says otherwise". A replay that is a paraphrase, or that is filed under
    a file it never came from, cannot support that claim -- it supports the opposite one.
    So the entries are checked against the commit now instead of trusted.

    What was wrong, measured against `git show 852e0f7` rather than recalled:
      * `replay_control.py` replayed two `log(...)` lines deleted from n_scaling_grid.py,
        leaving scripts/replay_control.py -- one of the eight files the commit touched --
        with no entry of its own while appearing to have one.
      * `test_n_scaling_grid.py` replayed a sentence in no version of any file in the
        commit. It is a fair paraphrase of the deleted docstring, and this section exists
        to rule out paraphrase.
      * `make_floor_budget_figure.py` closed its string early, inventing `.")` where the
        source continues, and the START_HERE entry rewrote an em dash as `--`. Neither
        changes which file it came from, and both make "verbatim" false.

    SKIPPED rather than failed where git is unavailable: the assertion is about repository
    history, and a checkout without it should not go red for that reason alone.
    """
    import subprocess

    try:
        diff = subprocess.run(["git", "show", "852e0f7"], cwd=str(REPO),
                              capture_output=True, text=True, encoding="utf-8",
                              errors="replace", timeout=60)
    except (OSError, subprocess.SubprocessError):          # pragma: no cover
        pytest.skip("git is not available here")
    if diff.returncode != 0:                               # pragma: no cover
        pytest.skip("commit 852e0f7 is not in this checkout")

    deleted: dict[str, list[str]] = {}
    current = None
    for line in diff.stdout.splitlines():
        if line.startswith("--- a/") or line.startswith("+++ b/"):
            current = line[6:]
        elif line.startswith("-") and not line.startswith("---") and current:
            deleted.setdefault(current, []).append(line[1:])

    def norm(s: str) -> str:
        return re.sub(r"\s+", " ", s).strip()

    cases = test_the_removed_lines_of_852e0f7_all_go_red.pytestmark[0].args[1]
    assert len(cases) == 8, "one entry per file the commit touched"
    for fname, removed in cases:
        owners = [path for path in deleted
                  if pathlib.PurePosixPath(path).name == fname]
        assert owners, f"{fname} is not a file commit 852e0f7 touched"
        for chunk in (ln for ln in removed.split("\n") if ln.strip()):
            assert any(norm(chunk) in norm(d) for path in owners for d in deleted[path]), (
                f"{fname}: the replayed line\n    {chunk!r}\n"
                "is not a line commit 852e0f7 deleted from that file. Either it came from "
                "a different file -- which is how this section acquired two wrong "
                "attributions -- or it is a paraphrase, which is the thing this section "
                "exists to rule out. Copy the line out of `git show 852e0f7` verbatim.")


def test_the_replacements_852e0f7_wrote_are_all_green(tmp_path):
    """The other half, taken from the same commit's ADDED lines. If the corrected wording
    were flagged, the guard would be reddening the fix -- which is the failure the round-
    five note records for `span: 0`, one mechanism over."""
    for fname, added in [
        ("replay_control.md",
         "> **WITHDRAWN, 2026-08-19.** Under the calibrated Ewens fit Wilson covers "
         "53.67% and the question bootstrap 0.00% at nominal 95%; under the zero branch, "
         "95.06% and 100%."),
        ("n_scaling_grid.md",
         "Whether that rung is the population's top rung is not decidable at n=200: if "
         "the population can never yield 39 mutually inequivalent answers out of 40, "
         "4/200 estimates a real quantity."),
        ("derived_paper_quantities.py",
         "    # calibrated Ewens (tau_top = 0.2726%): Wilson 53.67%, question bootstrap "
         "0.00%\n    # zero branch (tau_top = 2.0%): Wilson 95.06%, bootstrap 100%"),
    ]:
        hits = _word_rule_hits(_wide(tmp_path, added, fname))
        assert not hits, f"{fname}: the CORRECTED wording is flagged\n" + _say(hits)


# --- 9. mutation tests for the scope itself --------------------------------------------
def test_mutation_running_the_latex_flattener_on_markdown_loses_sites(tmp_path,
                                                                      monkeypatch):
    """THE PHASE-2 BLOCKER, as a mutation rather than as a description.

    Point `flatten` at `strip_latex` for every suffix -- the state this file was in before
    today -- and the damage is ASYMMETRIC, which is more interesting than "it breaks" and
    is the shape the round-five measurement actually recorded (16 -> 14 for all eight
    rules, 15 -> 11 for the coverage pair alone). `strip_latex` eats from an unescaped `%`
    to end of line, so `0.00%, at nominal 95%.` collapses to `0.00`, and the `0.00%` rule
    requires a percent sign (PCT) because a bare `0.00` would reach the exhaustively
    enumerated `U_39 = 0.000000%` of ruling section 1. That rule goes silent. The `53.7`
    rule has no PCT -- 53.7 is unique in this repo and is armed on the digits -- so it
    survives, and a reader who tested only that one would conclude the flattener was fine.
    """
    import check_population_labels as C

    probe = ("Wilson covers the true floor 53.7% of the time and the question bootstrap "
             "0.00%, at nominal 95%.")
    before = _word_rule_hits(_wide(tmp_path, probe, "probe.md"))
    assert {"53.7", "0.00%"} <= {h.split("'")[1] for h in before}, _say(before)

    monkeypatch.setattr(C, "flatten", lambda text, suffix: C.strip_latex(text))
    after = {h.split("'")[1] for h in _word_rule_hits(_wide(tmp_path, probe, "probe2.md"))}
    assert "0.00%" not in after, (
        "the LaTeX flattener no longer loses the bootstrap coverage, so the per-suffix "
        "split has stopped being load-bearing -- delete it, or find out what changed")
    assert "53.7" in after, (
        "53.7 was lost too, which the round-five measurement says it should not be. If "
        "that rule has grown a PCT requirement, the 16 -> 14 figure in this file is stale")


def test_mutation_widening_tier_two_to_every_superseded_entry_reddens_the_repo():
    """The 1083-finding measurement, as a live assertion instead of a comment. Run the FULL
    ledger over the tier-2 files and the backlog explodes across the run artifacts, the
    absence-pins and the correction records -- which is the whole argument for the
    value/position line, and it stops being an argument the day it stops being true."""
    import check_population_labels as C

    wide_now = sum(len(C.check_file(f)) for f in C.wide_files())
    assert wide_now == 26

    census = C.scope_census()
    value_findings, value_files = census["retired-value"]
    assert value_findings > 200 and value_files > 25, (
        f"the full ledger now returns only {value_findings} findings in {value_files} "
        "files outside paper/. If the retired VALUES have genuinely stopped appearing in "
        "run artifacts and absence-pins, the tier-2 line can move -- but move it "
        "deliberately, with the new count in the commit message, not by noticing that "
        "this test went quiet")


def test_mutation_a_pinned_file_that_is_excluded_instead_is_visible():
    """The dishonest fix the failure message names third: silence a red by adding the file
    to OUT_OF_SCOPE. It works -- and it leaves a KNOWN_OPEN entry pointing at a file no
    longer scanned, which `_ratchet` reports as an orphan. That is the trap closing."""
    import check_population_labels as C

    name = "results/schedule_2026_08_26.md"
    live = {f.relative_to(REPO).as_posix(): len(C.check_file(f)) for f in C.wide_files()}
    assert not C._ratchet(live)

    silenced = {k: v for k, v in live.items() if k != name}     # as if OUT_OF_SCOPE'd
    problems = C._ratchet(silenced)
    assert len(problems) == 1 and "ratchet-orphan" in problems[0] and name in problems[0]


# --- 10. the self-reference control, in detail -----------------------------------------
def test_the_checkers_own_findings_never_land_on_executable_code():
    """`test_the_checker_does_not_flag_its_own_rule_patterns` shows the exclusion is
    load-bearing. This shows what it is hiding, mechanically rather than by assurance:
    every self-finding sits on a COMMENT or a STRING CONSTANT -- a rule pattern, a
    `quantity`, an advice string, a ratchet note, a paragraph of the docstring -- and never
    on a line that decides anything. So the exclusion cannot be concealing a change in
    behaviour; at worst it conceals prose, and the prose that matters (the advice strings
    the rest of the repo is told to quote) is re-checked by
    test_the_ledgers_own_advice_passes_the_rules_it_gives.

    `tokenize` is the arbiter rather than a regex, because "is this line a comment" is
    exactly the question a regex gets wrong on a file that is mostly regexes.
    """
    import tokenize
    from check_population_labels import check_file as cf

    src = REPO / "scripts/check_population_labels.py"
    prose_lines: set[int] = set()
    with tokenize.open(src) as fh:
        for tok in tokenize.generate_tokens(fh.readline):
            if tok.type in (tokenize.COMMENT, tokenize.STRING):
                prose_lines.update(range(tok.start[0], tok.end[0] + 1))

    own = cf(src)
    assert own, "the ledger no longer matches itself; check the rules still compile"
    located = 0
    for problem in own:
        head = problem.split(":")[0:2]
        if len(head) < 2 or not head[1].isdigit():
            continue                       # `_line_hint` found no single source line
        located += 1
        line = int(head[1])
        assert line in prose_lines, (
            f"a self-finding lands on EXECUTABLE line {line} of the ledger, which is not "
            "self-reference and may be real:\n" + problem)
    assert located >= 30, f"only {located} of {len(own)} findings could be located"


def test_a_third_party_file_quoting_a_rule_pattern_is_reported():
    """The exclusion is BY NAME, not by content, and that is on purpose: it protects the
    two files that are the ledger, not any file that mentions it. A doc explaining the
    guard by quoting a retracted sentence WILL be reported, and will need a pin with a
    reason like everything else. Stated as a test so nobody expands the exclusion by
    analogy when that day comes."""
    import tempfile
    from check_population_labels import check_file as cf

    with tempfile.TemporaryDirectory() as d:
        f = pathlib.Path(d) / "guard_explainer.md"
        f.write_text("The ledger retires the sentence: the estimand dissolves once the "
                     "ceiling atom empties.\n", encoding="utf-8")
        assert _word_rule_hits(cf(f)), (
            "a third-party file quoting the retracted sentence went unreported")


# --- 11. a red run shows the NEW finding, not the pinned backlog ------------------------
def test_a_breach_prints_its_own_file_and_not_the_other_pinned_ones(capsys,
                                                                    monkeypatch):
    """Twenty-six pinned findings printed alongside one new one is a report nobody reads,
    and this file's docstring is explicit that a guard whose output is skipped has the same
    end state as one that cannot fail. So `main` prints findings only for files that BREACH
    the ratchet."""
    import check_population_labels as C

    monkeypatch.setitem(C.KNOWN_OPEN, "docs/START_HERE_overnight.md", 0)
    assert C.main([]) == 1
    out = capsys.readouterr().out
    assert "docs/START_HERE_overnight.md" in out
    assert "STALE VALUE" in out, "the breaching file's finding itself must be shown"
    for quiet in ("results/replay_control.md", "scripts/replay_control.py",
                  "results/schedule_2026_08_26.md"):
        assert f"{quiet}: [run provenance]" not in out, (
            f"{quiet} is at its baseline and its findings were printed anyway")


def test_the_scope_census_matches_the_numbers_the_docstring_argues_from():
    """THE SCOPE ARGUMENT IS A MEASUREMENT, so it expires like every other list in this
    ledger -- `labels` (defect 5), `numbers` (defect 6), FROZEN_COUNTS (defect 7). The
    docstring says the pool rules would return 736 findings outside paper/ and that this
    is why they stay scoped. If that becomes 40, the argument is gone and nobody would
    know. Bands rather than exact equality, because these move when the repo does; a band
    breach is a prompt to re-read the SCOPE section, not necessarily a defect.
    """
    from check_population_labels import scope_census

    census = scope_census()
    bands = {                       # (low, high) for findings; the docstring's figure
        "pools": (600, 900),                    # 736
        "growing": (50, 120),                   # 73
        "retired-value": (200, 380),            # 274
        "retired-position": (26, 26),           # 26 -- pinned exactly; it is the ratchet
    }
    for name, (low, high) in bands.items():
        found, _ = census[name]
        assert low <= found <= high, (
            f"{name}: {found} findings, outside the band [{low}, {high}] the SCOPE section "
            "of scripts/check_population_labels.py argues from. Re-read that section and "
            "restate the number, or move the tier line -- but do not leave the docstring "
            "quoting a figure the code no longer produces")
    assert census["retired-position"][1] == 5


# ======================================================================================
# ROUND SEVEN (2026-08-27): THE INDEX CASE, AND A GATE THAT ANSWERS THE RIGHT QUESTION.
#
# Round five armed eight rules after `paper/sections/discussion.tex:306` said the measured
# N=40 floor "takes the question bootstrap". Round six widened their scope. A verifier then
# ran the PRE-FIX TEXT OF :306 through all 37 rules in both tiers and it PASSED -- along
# with three rewordings and with the same assertion made in Wilson's favour. The ledger
# caught the sixteen follow-on sites of 852e0f7 and not the sentence it was built after,
# which makes it fitted to the sweep rather than to the class. That is what section 1 below
# closes, with the estimator-ownership rule the original design note proposed.
#
# Four other things were wrong and are fixed here, in the order the threat model ranks
# them -- a false positive on correct writing outranks every miss, because a guard that
# fires on correct usage gets silenced and a silenced guard is worse than none:
#
#   * THE SMALLER-FLOOR RULE REDDENED A DENIAL. "It does not follow that a larger pool
#     reports a smaller floor" was RED. Section 2.
#   * THE DENIAL GATE WAS A PROXIMITY TEST and it failed in both directions -- green on
#     "The reason is not obvious, but the estimand dissolves", red on "doesn't dissolve"
#     while green on "does not dissolve", because `\bn't\b` cannot match a contraction.
#     Section 3.
#   * TWO EXCULPATION LISTS WERE MAGIC WORDS. `\bcalibrated\b` (36 of the 228 tier-2 files
#     mean embedding or judge calibration by it -- measured here, not taken from the brief,
#     which said 53) and bare `\bwhether\b` / `\bunless\b`. Section 4.
#   * THE RULES MATCHED ONE SPELLING WHERE THEIR OWN COMMENTS SAY TO ENUMERATE THE SHAPE.
#     30 of 56 evasion probes got through. Section 5, which also records what was DECLINED
#     and why -- the threat model is a careless writer, not an evader, so a rewording no
#     real writer would produce is not a defect worth a rule.
# ======================================================================================


# --- 1. ESTIMATOR OWNERSHIP: the index case ---------------------------------------------
def _own(problems: list[str]) -> list[str]:
    return [p for p in problems if "estimator ownership" in p]


@pytest.mark.parametrize("why,text", [
    ("THE INDEX CASE. paper/sections/discussion.tex:306 as committed, and as deleted by "
     "commit c19c356. Every guard in this repo watching the N=40 floor matched a rendered "
     "numeral; this sentence contains no digit of the quantity at all.",
     r"row is a count of independent indicators at the fixed threshold $\ln 10$ and takes "
     r"Wilson;" "\n"
     r"the measured $N{=}40$ floor is a count at no fixed threshold at all and takes the "
     r"question" "\n" r"bootstrap for the reason given above."),
    ("the same claim with the clause trimmed, which is how it would be re-introduced",
     r"the measured $N{=}40$ floor is a count at no fixed threshold at all and takes the "
     r"question bootstrap"),
    ("the estimator named by what it resamples rather than by its name",
     r"The measured $N{=}40$ floor takes a bootstrap over the $200$ questions."),
    ("the ownership stated from the estimator's end, with the row after `for`",
     r"We quote a question bootstrap interval for the measured $N{=}40$ floor."),
    ("THE INVERTED FORM. docs/START_HERE_overnight.md section 2 says in terms that "
     "'the paper should reinstate Wilson there' and 'the paper should switch to the "
     "bootstrap there' are the same dead claim wearing opposite signs.",
     r"The measured $N{=}40$ floor takes Wilson."),
    ("belongs-to, one of the predicates the design note listed",
     r"The measured $N{=}40$ floor belongs to the question bootstrap."),
    ("is-priced-by, ditto -- and `prices` is the verb the paper itself uses",
     r"The measured $N{=}40$ floor is priced by Wilson."),
    ("row 2 run backwards. The achieved 5% budget point takes Wilson; giving it the "
     "bootstrap is the retired [2.5, 5.0], and it is the OPPOSITE direction to row 1.",
     r"The achieved $5\%$-budget point takes the question bootstrap."),
    ("the at-cap mass given no estimator, when it is the one row whose Wilson interval is "
     "valid in BOTH branches and the quantity the ruling says to print instead",
     r"The at-cap mass at $\ln 40$ takes neither."),
    ("the replayed rows given Wilson, when their point estimate is an average over subset "
     "draws and no count exists",
     r"The replayed rows take Wilson."),
])
def test_the_estimator_ownership_defect_is_flagged(tmp_path, why, text):
    """PROBE. The vocabulary is closed -- three estimators crossed with five rows -- and
    every answer is a RULING (results/n40_floor_estimator_ruling.md sections 1, 2, 8.4,
    13), so the rule is a TABLE LOOKUP and a re-ruling changes one cell rather than a
    regex. This is the rule the round-five design note proposed and nobody built."""
    hits = _own(_check(tmp_path, text))
    assert hits, f"{why}: not flagged\n" + _say(_check(tmp_path, text))


@pytest.mark.parametrize("why,text", [
    ("discussion.tex:310-311 AS CORRECTED. Two rows, two answers, either side of a "
     "semicolon -- and a rule whose window crossed that semicolon would flag the sentence "
     "that fixed the defect.",
     r"The direct $N{=}10$ row is a count of independent indicators at the fixed threshold "
     r"$\ln 10$ and takes Wilson;" "\n"
     r"the measured $N{=}40$ floor is a count at no fixed threshold at all and takes "
     r"neither, for the reason given above."),
    ("discussion.tex:158-166, the paragraph that STATES the mapping. It names three rows "
     "and two estimators in one sentence, with an em-dash aside between them, and it is "
     "right about all of it.",
     r"Which interval a row takes is decided by the estimator and not by whether the row "
     r"was replayed: Wilson prices a count of independent indicators at a threshold fixed "
     r"\emph{before} the data, so it belongs to the two rows that are exactly "
     r"that---the direct $N{=}10$ floor, $19$ of $200$ at $\ln 10$, and the empty at-cap "
     r"mass at $\ln 40$---while the replayed rows take a bootstrap over the $200$ "
     r"questions, because their point estimate is an average over subset draws rather "
     r"than a count. The measured $N{=}40$ floor takes neither, for the reason below."),
    ("discussion.tex:180, where the estimator PRECEDES the predicate",
     r"Neither prices the floor, so we report $2.0\%$ as the cheapest alarm $200$ answers "
     r"can exhibit and leave it without an interval."),
    ("the achieved 5%-budget point with the estimator the ruling gives it",
     r"The achieved $5\%$-budget operating point takes Wilson, $5.0\%$ [$2.7$, $9.0$]."),
    ("the direct N=10 row with the estimator the ruling gives it",
     r"The direct $N{=}10$ floor is $19$ of $200$ at $\ln 10$ and takes Wilson."),
    ("the at-cap mass with the estimator the ruling gives it",
     r"The at-cap mass at $\ln 40$ takes Wilson, $0.0\%$ [$0.0$, $1.9$]."),
    ("the replayed rows with theirs",
     r"The replayed rows take a bootstrap over the $200$ questions."),
    ("AN AMBIGUOUS ROW NAME IS LEFT ALONE. A bare `N=20 floor` names two different rows -- "
     "the direct count and the subset-averaged replay -- and the paper quotes the replayed "
     "one. A rule that guessed would be wrong half the time, and being wrong here means "
     "reddening correct prose.",
     r"The $N{=}20$ floor takes Wilson."),
    ("...and the same at N=10",
     r"The $N{=}10$ floor takes a bootstrap over the questions."),
    ("A PREDICATE WITH NO ROW THIS TABLE KNOWS IS SILENT. results/replay_control.md:18.",
     r"The `achieved FPR, B\% budget` brackets are the range of the estimator and not "
     r"confidence intervals; the paper takes Wilson on the count for those rows."),
    ("the claim DENIED",
     r"The measured $N{=}40$ floor does not take the question bootstrap."),
])
def test_correct_estimator_ownership_is_not_flagged(tmp_path, why, text):
    """CONTROL, and it carries the whole weight of the rule being usable. Two of these are
    the live paper. One -- the :158-166 paragraph -- names three rows and two estimators
    with an aside in the middle, and it is the reason arbitration is NEAREST-NAME rather
    than any-name-in-window: read the other way it binds "a bootstrap" to the at-cap mass
    forty characters further back and reddens the passage that gets it right."""
    hits = _own(_check(tmp_path, text))
    assert not hits, f"{why}: FLAGGED, and it is correct as written\n" + _say(hits)


def test_the_index_case_is_reported_at_its_own_line_number(tmp_path):
    """LOCATABILITY, which is not a nicety here: the round-five docstring already lists
    `_line_hint` returning the wrong place as one of the reasons the pool rules stay out of
    tier 2.

    The flatteners collapse newlines, so a matched phrase routinely straddles a line break
    in the source -- and the index case does exactly that, `takes the` ending one line and
    `question bootstrap` starting the next. A per-line search can never find it, so the
    finding printed with no line number at all, on the one sentence this round exists for.
    `_line_hint` now falls back to adjacent pairs.
    """
    src = ("The direct $N{=}10$ row is a count of independent indicators at the fixed\n"
           "threshold $\\ln 10$ and takes Wilson;\n"
           "the measured $N{=}40$ floor is a count at no fixed threshold at all and "
           "takes the\n"
           "question bootstrap for the reason given above.\n")
    hits = _own(_check(tmp_path, src))
    assert hits, _say(_check(tmp_path, src))
    assert hits[0].startswith("probe.tex:3:"), (
        "the finding does not name the line the sentence starts on:\n" + hits[0])


def test_the_ownership_rule_reaches_the_file_types_the_sweep_found(tmp_path):
    """The defect class had sixteen instances outside paper/ and none of them was .tex.
    Ownership runs in tier 2 for the same reason the position rules do: its finding is a
    POSITION ("this row takes neither"), never a recomputed value."""
    for name in ("probe.md", "probe.py", "probe.sh", "probe.json"):
        assert _own(_wide(tmp_path, "the measured N=40 floor takes the question bootstrap",
                          name)), name


def test_the_ownership_verdicts_are_data_and_the_repo_agrees_with_them():
    """STRUCTURAL. The point of a table is that a re-ruling edits one cell. So the table has
    to be readable as a table: three estimators, a `why` that cites the ruling, and no row
    whose name patterns can match another row's name."""
    from check_population_labels import _EST_PATTERNS, OWNERSHIP_ROWS

    assert set(_EST_PATTERNS) == {"wilson", "bootstrap", "neither"}
    seen = set()
    for spec in OWNERSHIP_ROWS:
        assert spec["takes"] in _EST_PATTERNS, spec["row"]
        assert spec["why"] and spec["names"], spec["row"]
        assert spec["row"] not in seen
        seen.add(spec["row"])
        for pat in spec["names"]:
            re.compile(pat)
    # The ruling's own answers, restated here so a silent edit to the table fails.
    answers = {s["row"].split(" (")[0]: s["takes"] for s in OWNERSHIP_ROWS}
    assert answers == {
        "the measured N=40 floor": "neither",
        "the at-cap mass at ln 40": "wilson",
        "the direct N=10 floor": "wilson",
        "the achieved 5%-budget operating point": "wilson",
        "the replayed / subset-averaged rows": "bootstrap",
    }, ("the ownership table no longer matches results/n40_floor_estimator_ruling.md "
        "sections 1, 2 and 13. If the ruling changed, change this pin in the same commit "
        "and say which section did it.")


def test_mutation_removing_the_ownership_rule_loses_the_index_case(tmp_path, monkeypatch):
    """Disable the rule and the sentence this whole round exists for goes green again."""
    import check_population_labels as C

    text = (r"the measured $N{=}40$ floor is a count at no fixed threshold at all and "
            r"takes the question bootstrap")
    assert _own(_check(tmp_path, text)), "the probe is not red to begin with"
    monkeypatch.setattr(C, "OWNERSHIP_ROWS", [])
    assert not _own(_check(tmp_path, text)), (
        "the index case is still reported with the ownership table emptied -- something "
        "else is catching it and this rule may be doing nothing")


def test_mutation_widening_the_object_gap_binds_a_row_it_has_no_business_binding(
        tmp_path, monkeypatch):
    """`OWNERSHIP_OBJECT_GAP` ALONE, on a sentence where nothing else protects it.

    The obvious probe for this constant is scripts/replay_control.py:1131 -- "takes Wilson,
    as everywhere else in the paper, and only the replayed rows ... take the bootstrap" --
    and it is the wrong probe, because the `, and` in that gap is ALSO a clause break, so
    two mechanisms independently refuse the binding and mutating either one changes
    nothing. A mutation test on a redundantly-protected text proves nothing about the
    mechanism it names. This sentence has no clause break in its gap at all; only the
    distance stops the guard reading "the measured N=40 floor" as the object of a predicate
    fifty characters earlier, which it is not."""
    import check_population_labels as C

    text = (r"Every count of independent indicators takes Wilson, including the row "
            r"printed immediately above the measured $N{=}40$ floor.")
    assert not _own(_check(tmp_path, text)), "control is not green to begin with"
    monkeypatch.setattr(C, "OWNERSHIP_OBJECT_GAP", 400)
    assert _own(_check(tmp_path, text)), (
        "with the object gap widened to 400 the guard is STILL green -- the gap is not "
        "what is holding this binding off, and the constant is decoration")


def test_mutation_removing_the_cell_wall_lets_one_column_negate_another(
        tmp_path, monkeypatch):
    """`|` AS A CLAUSE BREAK, isolated. Outside paper/ this repo is mostly tables, and
    `strip_plain` collapses a whole table into one line. Without a cell wall, a word in one
    column reaches a claim in another: here a `not identified` in the first cell disowns a
    flat assertion in the second, which is D2 exculpating on text that has nothing to do
    with the claim beside it."""
    import check_population_labels as C

    row = "| not identified | the estimand dissolves once the atom empties |\n"
    assert _word_rule_hits(_wide(tmp_path, row, "probe.md")), "probe is not red to begin with"
    monkeypatch.setattr(
        C, "_CLAUSE_BREAK_RE",
        re.compile(C._CLAUSE_BREAK_RE.pattern.replace(r"|\|", "", 1), re.IGNORECASE))
    assert not _word_rule_hits(_wide(tmp_path, row, "probe.md")), (
        "the row is still reported with the cell wall removed -- `|` is not what keeps "
        "one column's words out of another column's clause")


def test_mutation_shrinking_the_char_cap_loses_a_row_named_a_sentence_earlier(
        tmp_path, monkeypatch):
    """`OWNERSHIP_CHAR_CAP` is the other end of the same window. A row named early in a long
    clause still owns the predicate at the end of it; shrink the cap and the rule goes
    quiet, which is what shows the cap is a width and not decoration."""
    import check_population_labels as C

    text = (r"the measured $N{=}40$ floor, which is a count at no fixed threshold at all "
            r"and whose value is the top score this particular sample happened to attain, "
            r"takes the question bootstrap")
    assert _own(_check(tmp_path, text)), "the probe is not red to begin with"
    monkeypatch.setattr(C, "OWNERSHIP_CHAR_CAP", 5)
    assert not _own(_check(tmp_path, text)), (
        "the row is still found with the window shrunk to 5 characters -- the cap is not "
        "the thing bounding the search")


def test_a_table_cell_wall_stops_the_ownership_rule(tmp_path):
    """results/replay_control.md's own summary table, verbatim in shape. Three columns, two
    rows, and the estimator in one row's third column sits 28 characters from the NEXT
    row's name. Without `|` as a clause break the guard reads them as one clause and
    reddens a correct table."""
    text = ("| the subset-averaged replayed floor (what this report and the paper quote) "
            "| the questions only | a bootstrap over questions only |\n"
            "| the measured N=40 floor | the questions only, but the ESTIMAND moves with "
            "them | none -- withdrawn |\n")
    assert not _own(_wide(tmp_path, text, "probe.md")), _say(_own(
        _wide(tmp_path, text, "probe.md")))


# --- 2. THE FALSE POSITIVE THE THREAT MODEL RANKS FIRST ---------------------------------
# (the probe/control pair lives beside the invariant it changed, in section 4 of round
# five: test_the_smaller_floor_rule_no_longer_reddens_a_sentence_that_denies_it)


# --- 3. THE DISOWNING GATE ---------------------------------------------------------------
@pytest.mark.parametrize("why,text", [
    ("A NEGATION ABOUT SOMETHING ELSE, in a clause the claim does not share. The `not` "
     "denies the obviousness of the reason; the clause after `but` asserts the retracted "
     "position flatly. Green under the 30-character lookback.",
     r"The reason is not obvious, but the estimand dissolves once the ceiling atom empties."),
    ("...and on a comparative, which `_is_non_binding` also treated as a denial cue",
     r"It is worse than that -- the estimand dissolves once the ceiling atom empties."),
    ("...and across a bare coordinating conjunction",
     r"The atom is not full and the estimand dissolves once it empties."),
    ("A PAST ATTRIBUTION WITH NO DISAVOWAL is a claim being repeated, not withdrawn. This "
     "is the failure mode the round-six note predicted for any gate built on `said X`, and "
     "it is why D3 needs two keys.",
     'This banner said "the estimand stops existing when the ceiling atom empties".'),
    ("THE PRE-FIX WORDING OF docs/START_HERE_overnight.md, which must stay red: the "
     "negation is real and a full stop stands between it and the claim.",
     r"The reason is not data selection. It is that the estimand dissolves --- $4/200$ is "
     r"the resolution limit of a $200$-answer pool."),
    ("A PRESENT-TENSE CITATION buys nothing. A stale brief asserts in the present; a "
     "correction note reports in the past, which is the half that discriminates.",
     r"The ruling states that the estimand dissolves once the ceiling atom empties, and "
     r"that supersedes the earlier note."),
])
def test_the_disowning_gate_still_fires_where_the_claim_is_made(tmp_path, why, text):
    """PROBE. Three of these were GREEN under the proximity gate. Measured, not imagined."""
    hits = _word_rule_hits(_check(tmp_path, text))
    assert hits, f"{why}: not flagged\n" + _say(_check(tmp_path, text))


@pytest.mark.parametrize("why,text", [
    ("the negated claim verb, spelled out",
     r"The estimand does not dissolve when the atom empties."),
    ("THE SAME SENTENCE CONTRACTED. This was RED while the line above was green, because "
     "`\\bn't\\b` cannot match a contraction -- the `n` of `doesn't` is preceded by a word "
     "character, so there is no boundary there -- and NON_BINDING_CUES carried no "
     "contraction at all. A guard that reddens a denial over an apostrophe is the false "
     "positive this file's threat model ranks above every miss.",
     r"The estimand doesn't dissolve when the atom empties."),
    ("the negated matrix",
     r"It is not that the estimand dissolves; it is that tau is not identified at n=200."),
    ("docs/START_HERE_overnight.md:190 as corrected",
     r"The reason is not data selection, and it is NOT that the estimand dissolves: "
     r"ruling section 13 retracts that sentence."),
    ("QUOTED AND DATED. figures/README.md's correction note, in shape. The disavowal "
     "FOLLOWS the quotation, which is where the old backward lookback could never see it "
     "-- six pinned findings' worth.",
     'This section said "Neither estimator is broken -- the estimand is" until 2026-08-26; '
     'ruling sec. 13 retracts that.'),
    ("ATTRIBUTED WITHOUT QUOTATION MARKS. scripts/make_floor_budget_figure.py's note: the "
     "paraphrase of the old claim is the author's own words, so a containment test on "
     "quotes sees nothing.",
     'This paragraph said "Wilson on the count for the two directly measured rows" until '
     '2026-08-26, which named the measured N=40 floor as taking Wilson.'),
    ("the same shape in a generator comment, where the quotation opens in the MIDDLE of "
     "the matched phrase -- scripts/replay_control.py:796",
     'The "Which interval goes with which estimator" table -- the one table in this repo '
     'whose entire job is to state that mapping -- went on saying the measured N=40 floor '
     'takes "Wilson on the count" for a whole round after the floor table thirteen lines '
     'below it had been changed to "none -- withdrawn".'),
])
def test_the_disowning_gate_is_green_where_the_claim_is_withdrawn(tmp_path, why, text):
    """CONTROL. Every one of these is live repo text or one word from it, and every one is
    correct writing. Two were RED before this round."""
    hits = _word_rule_hits(_check(tmp_path, text)) + _own(_check(tmp_path, text))
    assert not hits, f"{why}: FLAGGED, and it is correct as written\n" + _say(hits)


def test_mutation_removing_the_clause_break_restores_the_old_false_negatives(
        tmp_path, monkeypatch):
    """D2's whole content is that a CLAUSE and not a character count decides whether a
    negation reaches a claim. Disable the clause breaks -- which makes the scope run back
    to the start of the text, the way a pure `not-is-nearby` test effectively does -- and
    the two sentences the old gate missed go green again."""
    import check_population_labels as C

    text = r"The reason is not obvious, but the estimand dissolves once the atom empties."
    assert _word_rule_hits(_check(tmp_path, text)), "probe is not red to begin with"
    monkeypatch.setattr(C, "_CLAUSE_BREAK_RE", re.compile(r"(?!x)x"))
    assert not _word_rule_hits(_check(tmp_path, text)), (
        "with clause breaks disabled the sentence is still reported -- the clause "
        "boundary is not what is doing the work")


def test_mutation_dropping_the_disavowal_key_would_exculpate_a_bare_attribution(
        tmp_path, monkeypatch):
    """D3 needs TWO keys and this is the evidence. Make every text look disavowed and a
    bare `said X` -- a claim being repeated -- goes green, which is precisely the failure
    the round-six note warned this gate would have if it were built on attribution alone."""
    import check_population_labels as C

    text = 'This banner said "the estimand stops existing when the ceiling atom empties".'
    assert _word_rule_hits(_check(tmp_path, text)), "probe is not red to begin with"
    monkeypatch.setattr(C, "_DISAVOWAL_RE", re.compile(r""))
    assert not _word_rule_hits(_check(tmp_path, text)), (
        "the bare attribution is still reported with the disavowal key satisfied -- so "
        "the second key is not what is holding the gate shut")


def test_mutation_raising_the_char_cap_licenses_a_distant_exculpation(
        tmp_path, monkeypatch):
    """ABSENT_CHAR_CAP, which the previous round left with no assertion at all: setting it
    to 100000 left the entire suite green. It matters exactly where this repo is hardest --
    a generated table or a `log(...)` block with no sentence terminator in it, where the
    sentence-span search would otherwise run to the end of the file and let one `Ewens`
    somewhere on the page exculpate every coverage figure below it."""
    import check_population_labels as C

    row = "| N=40 (atom empty) | 0.27% | 53.7% | 0.00% |\n"
    text = "calibrated Ewens fit, tau_top = 0.2726%\n" + ("| pad | 1.1% | 2.2% |\n" * 40)
    text += row
    assert _word_rule_hits(_wide(tmp_path, text, "probe.md")), (
        "the branch name is over 600 characters away through unpunctuated table rows and "
        "the row is NOT reported -- the cap is not clipping anything")
    monkeypatch.setattr(C, "ABSENT_CHAR_CAP", 100000)
    assert not _word_rule_hits(_wide(tmp_path, text, "probe.md")), (
        "with the cap raised the distant branch name STILL does not exculpate -- something "
        "other than the cap is bounding the search, and the constant is decoration")


# --- 4. THE EXCULPATION LISTS WERE MAGIC WORDS -------------------------------------------
@pytest.mark.parametrize("why,text", [
    ("`calibrated` means embedding calibration, judge-threshold calibration and "
     "probability calibration in 36 of the 228 tier-2 files. Admitted bare, it "
     "exculpated a coverage figure on a neighbouring subfield's vocabulary.",
     "The judge threshold was calibrated on the pilot; Wilson covers 53.7% at nominal 95%."),
    ("...and on the embedder",
     "The paraphrase embedder was calibrated on held-out pairs. Wilson covers the floor "
     "53.7% of the time at nominal 95%."),
    ("a bare `whether` is a conditional about anything at all",
     "A larger pool reaches a higher rung and reports a smaller floor, whether or not "
     "anyone bothers to check."),
    ("...and so is a bare `unless`",
     "A larger pool reaches a higher rung and reports a smaller floor, unless the run "
     "crashes first."),
])
def test_a_magic_word_no_longer_exculpates(tmp_path, why, text):
    """PROBE. Each of these passed. The fix is the one the `if` entry of `_BOTH_BRANCHES`
    has always followed: the conditional has to be ABOUT THE THING IN DISPUTE, so it names
    its subject, and `calibrated` has to be calibrating the fit rather than a judge."""
    hits = _word_rule_hits(_wide(tmp_path, text, "probe.md"))
    assert hits, f"{why}: not flagged\n" + _say(_wide(tmp_path, text, "probe.md"))


@pytest.mark.parametrize("why,text", [
    ("the corrected table header every generator in this repo now writes",
     "calibrated Ewens (tau_top = 0.2726%): Wilson 53.67%, question bootstrap 0.00%"),
    ("the same with the noun spelled out",
     "Under the calibrated Ewens fit Wilson covers 53.67% and the question bootstrap "
     "0.00%; under the zero branch, 95.06% and 100%."),
    ("`whether` naming its subject, which is what results/n_scaling_grid.md writes",
     "A larger pool reaches a higher rung and reports a smaller floor, but whether the "
     "population's support ends at the rung this pool reached is a question 200 answers "
     "cannot settle."),
    ("`unless` naming its subject",
     "A larger pool reaches a higher rung and reports a smaller floor, unless the "
     "population can never yield 39 mutually inequivalent answers out of 40."),
])
def test_tightening_the_lists_did_not_redden_a_corrected_site(tmp_path, why, text):
    """CONTROL, and the one that decides whether the tightening was worth doing. The
    module comment claims all five passages in this repo that state the dichotomy
    correctly are exculpated by the FIRST `_BOTH_BRANCHES` entry, so narrowing `whether`
    and `unless` should cost nothing. Measured, not assumed."""
    hits = _word_rule_hits(_wide(tmp_path, text, "probe.md"))
    assert not hits, f"{why}: FLAGGED, and it is the corrected wording\n" + _say(hits)


def test_the_five_correct_dichotomy_passages_in_this_repo_are_all_still_green():
    """The claim the `_BOTH_BRANCHES` comment makes, as an assertion over the real files.
    If one of these ever goes red, the tightening reached too far and the comment is
    wrong -- and this is the test that says which."""
    import check_population_labels as C

    for rel in ("results/n_scaling_grid.md", "scripts/make_floor_budget_figure.py",
                "scripts/n_scaling_grid.py", "tests/test_n_scaling_grid.py"):
        f = C.REPO / rel
        assert f.is_file(), rel
        assert not C.check_file(f), (
            f"{rel} states the dichotomy correctly and is now FLAGGED:\n"
            + _say(C.check_file(f)))
    assert main() == 0


# --- 5. SHAPES, NOT SPELLINGS -- and what was declined -----------------------------------
@pytest.mark.parametrize("why,text", [
    ("vanishes", "Once the ceiling atom empties the estimand vanishes."),
    ("evaporates", "Once the ceiling atom empties the estimand evaporates."),
    ("disappears", "Once the ceiling atom empties the estimand disappears."),
    ("is undefined", "Once the ceiling atom empties the estimand is undefined."),
    ("has no referent", "Once the atom empties the estimand has no referent."),
    ("NEGATION INSIDE THE CLAIM. 'is no longer well defined' IS the retracted position; "
     "the negator belongs to the claim, not to a denial of it, which is why this is armed "
     "as its own rule rather than folded into the tempered one.",
     "Once the ceiling atom empties the estimand is no longer well defined."),
    ("reports a LOWER floor", "A larger pool reaches a higher rung and reports a lower "
     "floor."),
    ("yields a smaller one", "A larger pool reaches a higher rung and yields a smaller "
     "one."),
    ("the noun displaced: a smaller NUMBER for the floor",
     "A larger pool gives a smaller number for the floor."),
    ("THE INTRANSITIVE GRAMMAR, which has no reporting verb for any widening to reach",
     "The floor shrinks as the pool grows, so the quantity moves with the pool."),
    ("...and its other verb", "The floor falls as the pool gets larger."),
])
def test_the_widened_shapes_catch_what_a_paraphraser_writes(tmp_path, why, text):
    """PROBE. 30 of 56 evasion probes got through the single-spelling rules. These eleven
    are the ones a real writer produces -- ordinary English for "dissolves" and for
    "reports a smaller floor" -- which is the test for admitting a rendering at all."""
    hits = _word_rule_hits(_check(tmp_path, text))
    assert hits, f"{why}: not flagged\n" + _say(_check(tmp_path, text))


@pytest.mark.parametrize("why,text", [
    ("THE ESTIMAND WIDENING MUST NOT REACH THE ESTIMATOR HALF. 'both estimators fail' is "
     "a phrase six correct passages use, always under attribution.",
     r"Both estimators fail on the first row, which is a statement about that row only."),
    ("the replacement wording the ruling supplies",
     r"Once the ceiling atom empties the estimand is NOT IDENTIFIED at $n{=}200$: it is "
     r"$2.0\%$ if the population can never produce $39$ mutually inequivalent answers out "
     r"of $40$, and can be arbitrarily smaller if it can."),
    ("a plug-in estimator rising towards its estimand -- discussion.tex:360, and nothing "
     "to do with this floor",
     r"A plug-in entropy that rises towards its estimand as the sample grows is that "
     r"estimator's own bias and not a property of any pool."),
    ("A FLOOR THAT FALLS FOR ANOTHER REASON is not this claim. The intransitive rule is "
     "gated on the POOL GROWING, because the retracted content is specifically that the "
     "quantity moves with the pool.",
     r"The floor falls when the judge threshold is loosened, which is a different "
     r"mechanism entirely."),
    ("the conditional site in the paper, with the widened verbs in it",
     r"If it is not, a larger pool reaches a higher rung and reports a lower floor, so "
     r"the quantity being estimated moves with the pool instead of holding still to be "
     r"estimated; if it is, the floor is an ordinary population proportion."),
])
def test_the_widened_shapes_do_not_reach_correct_writing(tmp_path, why, text):
    """CONTROL. Widening a rule is only worth doing if the widening keeps its precision,
    and the fifth entry is the one that matters: the paper's own conditional site, rewritten
    with the newly admitted verb in it, still green."""
    hits = _word_rule_hits(_check(tmp_path, text))
    assert not hits, f"{why}: FLAGGED\n" + _say(hits)


@pytest.mark.parametrize("why,text", [
    ("A COUNT OF REPLICATE POOLS. Declined: this is a MEASUREMENT of the branch, not an "
     "assertion of it, and the ruling's own section 8 prints figures of exactly this "
     "shape on purpose. A writer restating a coverage quotes the percentage.",
     "The floor was reached in 537 of 1000 replicate pools."),
    ("A MONOTONICITY STATEMENT IN ACADEMIC REGISTER. Declined: nobody in this repo writes "
     "like this, and a rule for it would reach every monotonicity claim in Methods.",
     "The floor is a decreasing function of pool size."),
    ("THE CLAIM WITH THE NOUN `estimand` DROPPED ENTIRELY. Declined, and this one is the "
     "closest call: the ceiling-atom argument the paper makes CORRECTLY uses this "
     "vocabulary, and an anchor-free rule would have to arbitrate a topic it cannot see. "
     "The noun is what makes the claim about the estimand rather than about the estimator, "
     "and the estimator half is what six correct passages say.",
     "Once the atom empties there is nothing left to estimate."),
])
def test_the_declined_evasions_are_declined_on_purpose(tmp_path, why, text):
    """NOT A PROBE -- a record of what this ledger deliberately does NOT catch, in the form
    that fails if someone quietly widens a rule to cover it. Each entry names the writer
    who would have to produce the sentence, because "an evasion no real writer would
    produce is not a defect worth fixing" is only a defensible line if the line is written
    down and held."""
    hits = _word_rule_hits(_check(tmp_path, text))
    assert not hits, (
        f"{why}\n...but the guard now FLAGS it. That may be right -- but it is a widening, "
        "and a widening is a decision: move this case into the probe list above with the "
        "reason, do not leave it here as a declined evasion that is quietly no longer "
        "declined.\n" + _say(hits))


# --- 6. COVERAGE FIGURES IN ORDINARY NUMBER FORMS ----------------------------------------
@pytest.mark.parametrize("why,text", [
    ("0% with no decimals", "Wilson covers the true floor 0% of the time at nominal 95%."),
    ("rounded to 54%", "Wilson covers about 54% of the time at nominal 95%."),
    ("the noun form, after the number",
     "| Wilson 53.7% / bootstrap 0.00% coverage, 40,000 pools | MEASURED |"),
    ("53.7 with no percent sign, which the exact rule already reached",
     "Wilson's coverage of the floor is 53.7 at nominal 95%."),
])
def test_an_ordinary_rendering_of_a_withdrawn_coverage_is_flagged(tmp_path, why, text):
    hits = _word_rule_hits(_wide(tmp_path, text, "probe.md"))
    assert hits, f"{why}: not flagged\n" + _say(_wide(tmp_path, text, "probe.md"))


@pytest.mark.parametrize("why,text", [
    ("THE AT-CAP MASS, which is the quantity the ruling says to print INSTEAD, and which "
     "renders as `0.0%` one sentence from the word `covers` in every corrected banner. "
     "This is why the new rule is an adjacency to the covering verb and not a `near` "
     "window: a 300-character gate cannot tell these apart.",
     "Under the zero branch Wilson covers 95.06%; quote the at-cap mass 0/200 = 0.0% "
     "[0.0%, 1.9%] beside it."),
    ("AN INTERVAL CONTAINING A VALUE. results/n_scaling_plan.md's budget table says "
     "`no -- interval covers 5%` on twenty rows of correct arithmetic. The verb is the "
     "containment sense, and without the lookbehind `\\b0` also matched the trailing zero "
     "of `4.0%`.",
     "| 4.0% | 2.0%-7.7% | 2.5%-6.4% | 3.1%-5.2% | no -- interval covers 5% |"),
    ("counts out of a replicate pool, declined above and still declined here",
     "The bootstrap covers in 0 of 1000 replicate pools at nominal 95%."),
    ("the exhaustively enumerated zero of ruling section 1 (M3), which is a MEASURED "
     "model-free value and the most quotable number in that section",
     "Exhaustive enumeration gives U_39 = 0.000000% at N=40."),
])
def test_the_new_coverage_renderings_do_not_reach_their_neighbours(tmp_path, why, text):
    hits = _word_rule_hits(_wide(tmp_path, text, "probe.md"))
    assert not hits, f"{why}: FLAGGED\n" + _say(hits)


def test_mutation_dropping_the_digit_lookbehind_reddens_a_hundred_percent(
        tmp_path, monkeypatch):
    """`(?<![\\d.%])` on the rounded-coverage rule, which is the least obvious thing in it.

    It replaced a `\\b`, and `\\b` is the wrong boundary for a number: it matches between
    the `.` and the `0` of `4.0%`, which is how twenty rows of results/n_scaling_plan.md's
    budget table (`| 4.0% | ... | no -- interval covers 5% |`) came back as withdrawn
    coverage figures on the first dry run. The lookbehind refuses ANY digit, dot or percent
    before the number, and the sentence below is why that matters more than the table did:
    the at-cap mass's one-sided Wilson bound has 100% coverage across the whole plausible
    range, it is CORRECT and valid in both branches, and it contains a `0` followed by `%`.
    """
    import check_population_labels as C

    text = ("Its threshold is ln 40, fixed before the data, and its one-sided upper bound "
            "has 100% coverage across the whole plausible range.")
    assert not _word_rule_hits(_wide(tmp_path, text, "probe.md")), \
        "control is not green to begin with"
    rule = _word_rule("rounded or decimal-free rendering")
    monkeypatch.setitem(rule, "pattern", rule["pattern"].replace(r"(?<![\d.%])", ""))
    assert _word_rule_hits(_wide(tmp_path, text, "probe.md")), (
        "without the lookbehind `100% coverage` is STILL green -- the lookbehind is not "
        "what is keeping the rule out of the middle of a number")


def test_mutation_loosening_the_coverage_noun_reddens_a_containment_claim(
        tmp_path, monkeypatch):
    """The REVERSE arm of the same rule requires the noun `coverage` and not any `cover*`,
    and this is the sentence that decides it. "the interval covers it" is the CONTAINMENT
    sense -- an interval containing a value -- and it has nothing to do with a coverage
    probability. A verb after the number is nearly always containment; the noun is nearly
    always the probabilistic sense. The two mechanisms in this rule are not redundant:
    the lookbehind protects `100% coverage`, this protects `0% ... covers it`."""
    import check_population_labels as C

    text = "The at-cap rate is 0% and the Wilson interval covers it comfortably."
    assert not _word_rule_hits(_wide(tmp_path, text, "probe.md")), \
        "control is not green to begin with"
    rule = _word_rule("rounded or decimal-free rendering")
    monkeypatch.setitem(
        rule, "pattern",
        rule["pattern"].replace(r"[^.;:!?]{0,26}?\bcoverage\b",
                                r"[^.;:!?]{0,26}?\bcover(?:s|ed|age|ing)?\b"))
    assert _word_rule_hits(_wide(tmp_path, text, "probe.md")), (
        "with any `cover*` accepted after the number the containment sentence is STILL "
        "green -- the noun requirement is not what tells the two senses apart")


# --- 7. SCOPE: what the widening reaches, and what the exclusions still cost ---------------
def test_the_scope_reaches_the_directories_added_this_round(tmp_path):
    """`README.md`, `results/figures/*.json` and `src/` were unreachable: WIDE_GLOBS is
    non-recursive by design and nobody had listed them. Measured before adding -- all three
    report zero findings today -- so this is reach bought at no ratchet cost, on the same
    read-FORWARD argument that put `scripts/` in scope."""
    from check_population_labels import WIDE_GLOBS, wide_files

    reached = {p.relative_to(__import__("check_population_labels").REPO).as_posix()
               for p in wide_files()}
    assert "README.md" in reached
    assert any(r.startswith("src/") for r in reached), "src/ is still unreachable"
    assert any(r.startswith("results/figures/") for r in reached)
    # ...and the globs still name every directory explicitly.
    assert all("**" not in g for g in WIDE_GLOBS)


def test_the_self_excluded_files_have_not_gained_a_retired_position():
    """THE COMPENSATING CONTROL FOR SELF-EXCLUSION, and it is a ratchet rather than a scan.

    Two of the sixteen sites of 852e0f7 lived in files excluded from tier 2 BY NAME -- this
    file and the ledger it tests -- so file-level reach is 14 of 16. The exclusion is right:
    both files contain every retired sentence as DATA (a regex, a `quantity` string, a
    probe), and scanning them reports findings manufactured entirely out of their own
    rules. But "excluded" must not also mean "unguarded", and the control that was there --
    running the ledger's advice STRINGS through the rules -- covers the advice and nothing
    else. Neither of the two 852e0f7 sites was an advice string; one was a code comment and
    one was a test docstring.

    A COMMENTS-ONLY SCAN WAS TRIED AND REJECTED, measured: the comments of the ledger yield
    49 findings, every one of them a rule being explained by quoting what it retires
    ("one line said the measured N=40 floor `takes the question bootstrap`"). There is no
    subset of these two files that can be scanned to zero, because their subject matter IS
    the retired sentences.

    So the control is the device this repo already uses for a backlog it cannot clear: pin
    the count, and fail when it moves. A NEW assertion added to either file's prose gains a
    finding and fails the suite exactly as it would in any other file. It counts and does
    not identify -- the same limitation the main ratchet records for itself -- and when it
    fires the answer is `--dry-run` beside `git diff`.
    """
    import check_population_labels as C

    pinned = {"scripts/check_population_labels.py": 59,
              "tests/test_population_labels.py": 106}
    for rel, want in pinned.items():
        found = len(C.check_file(C.REPO / rel))
        assert found == want, (
            f"{rel}: {found} retired-position findings against a pin of {want}.\n"
            "      If you ADDED a rule or a probe, that is expected -- update this number "
            "in the same commit and say so in the message.\n"
            "      If you did not, one of them is a NEW assertion of a retracted position "
            "in a file the tier-2 scan cannot see. Run\n"
            "        python scripts/check_population_labels.py --dry-run\n"
            "      which prints the live count for every file excluded by name.")


def test_the_exclusions_publish_their_own_cost(capsys):
    """The OUT_OF_SCOPE reasons used to carry hand-written counts and four of the eight had
    gone stale within a day of being written -- 39 against a true 41, 53 against 101, 91
    against 86. That is defect 5, 6 and 7 committed a fourth time, in the one list whose
    whole job is to justify not looking. The counts are gone from the prose; `--dry-run`
    prints them live, where they cannot age."""
    from check_population_labels import OUT_OF_SCOPE, _dry_run

    _dry_run()
    out = capsys.readouterr().out
    assert "Excluded by name" in out
    for rel in OUT_OF_SCOPE:
        assert rel in out, f"{rel} is excluded and its live cost is not printed"
        assert "finding(s)" in out
    # ...and no reason quotes a bare finding count any more.
    for rel, reason in OUT_OF_SCOPE.items():
        assert "tier-2 findings" not in reason, (
            f"{rel}: the reason quotes a finding count again. A count is a function of the "
            "RULES as much as of the file, and this list has already gone stale once for "
            "exactly that. State the argument; let --dry-run state the number.")
