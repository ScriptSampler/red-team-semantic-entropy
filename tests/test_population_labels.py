"""The population-label guard, and proof that it is not vacuous.

Binding a statistic to the wrong population has been found at six separate sites in this
paper, each by a manual sweep, each sweep missing a site the next one found. This converts
that into a check that runs every time the suite does.

HISTORY THIS FILE HAS TO ANSWER FOR. The first version of the guard, and the first version
of this file, were written by the same person on the same afternoon, and they encoded the
same assumption: that the error looks like a MISSING label. An audit then constructed eight
genuine population errors and the guard missed seven, because every one of them looked like
a WRONG label with a right one somewhere in the window. The eight probes are reconstructed
below as PROBES, and each is paired with a CONTROL -- the same claim written correctly --
so that a rule cannot pass by flagging everything.
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
    """45% is retention on the 60 false-alarm targets the optimiser found a paraphrase for,
    re-scored on an independent sample. It is not a fair-pool quantity."""
    problems = _check(tmp_path, r"""
        On the score-independent \emph{fair} pool ($200$ correct, $200$ hallucinating),
        only $45\%$ of the apparent effect survives re-scoring.
    """)
    assert any("45" in p for p in problems), _say(problems)


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
    """The corrected form must pass, or the check is unusable."""
    problems = _check(tmp_path, r"""
        Across the $97$ targets of the attack campaign, scored clean, a tenth of correct
        answers ($8/80$) already sit at the estimator's maximum. On the score-independent
        \emph{fair} pool ($200$ correct, $200$ hallucinating) it separates correct from
        hallucinating answers at AUROC $0.704$ [$0.653$, $0.753$].
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
    """Introduction: '($80$ correct, $17$ wrong---a score-independent sub-sample of the
    fair pool below...)' -- and then the attacked-pool granularity counts."""
    problems = _check(tmp_path, r"""
        At the standard $N{=}10$, across the $97$ targets of our attack campaign scored
        clean ($80$ correct, $17$ wrong---a score-independent sub-sample of the fair pool
        below, one correctness stratum per attack direction), a quarter of correct answers
        ($21/80$) sit in the top tenth of the score's range.
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
        Across the $97$ targets of the attack campaign we report saturation; AUROC is
        $0.704$ on the score-independent \emph{fair} pool ($200$ correct, $200$
        hallucinating).
        """,
        r"""
        Across the $97$ targets of the attack campaign, scored clean, a quarter sit in the
        top tenth of the range.

        On the score-independent \emph{fair} pool ($200$ correct, $200$ hallucinating) the
        clean detector reaches AUROC $0.704$ [$0.653$, $0.753$].
        """,
    ):
        assert not _check(tmp_path, text), _say(_check(tmp_path, text))


def test_the_winners_curse_paragraph_carries_its_label_a_long_way(tmp_path):
    """Limitations puts 45% some 500 characters after the label that scopes it. The rule's
    window has to reach, without letting a distant fair-pool label accuse it."""
    problems = _check(tmp_path, r"""
        We quantify the resulting inflation directly, by re-scoring each \emph{selected}
        paraphrase on an independent sample. Across the $60$ false-alarm targets on which
        the optimiser found a paraphrase, the mean intended move falls from $+0.698$ nats
        at selection to $+0.315$ nats on fresh samples. The shrinkage is $-0.383$ nats with
        a bootstrap interval of $[-0.529, -0.234]$ that excludes zero. Retention is a ratio
        of means, and its interval is wide at $45\%$ $[25\%, 65\%]$. Signal remains either
        way---$36$ of $60$ targets keep a positive move.
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
        for pat in rule["numbers"] + list(rule.get("requires", [])):
            re.compile(pat)
    for item in SUPERSEDED:
        re.compile(item["pattern"])
        for pat in item.get("near", []):
            re.compile(pat)


def test_the_guard_is_cheap_enough_to_run_in_the_suite():
    import time

    t0 = time.perf_counter()
    main()
    assert time.perf_counter() - t0 < 5.0
