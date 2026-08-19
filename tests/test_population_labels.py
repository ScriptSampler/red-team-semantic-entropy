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
              "10.5%", "150/1424", "12.2"]
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
        for pat in item.get("near", []):
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
