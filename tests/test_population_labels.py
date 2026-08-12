"""The population-label guard, and proof that it is not vacuous.

Binding a statistic to the wrong population has been found at five separate sites in this
paper, each by a manual sweep, each sweep missing a site the next one found. This converts
that into a check that runs every time the suite does.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "scripts"))

from check_population_labels import check_file, main, strip_latex  # noqa: E402


def test_the_actual_paper_passes():
    """The live paper must have every population-sensitive number labelled."""
    assert main() == 0


def test_strip_latex_defeats_the_markup_that_defeated_the_manual_grep():
    """The critic's own sweep for 'fair pool' MISSED conclusion.tex because the source
    reads `\\emph{fair} pool`. That is the specific failure this guard exists to prevent,
    so it gets its own test."""
    assert "fair pool" in strip_latex(r"on the score-independent \emph{fair} pool it separates")
    assert "attacked pool" in strip_latex(r"the \textbf{attacked} pool")
    # commands that wrap nothing relevant should not glue words together
    assert "97 targets" in strip_latex(r"across the $97$ targets")


def test_catches_an_unlabelled_fair_pool_auroc(tmp_path):
    """A bare 0.704 with no pool named is exactly site four. It must fail."""
    f = tmp_path / "bad.tex"
    f.write_text("The detector separates correct from wrong answers at AUROC $0.704$.\n",
                 encoding="utf-8")
    assert check_file(f), "an unlabelled 0.704 must be reported"


def test_catches_the_real_site_four_construction(tmp_path):
    """Verbatim shape of the Conclusion error: ceiling stats, then 'the same pool', then
    the fair-pool AUROC. The populations differ and this must not pass."""
    f = tmp_path / "site_four.tex"
    f.write_text(
        "the estimator offers only $22$ distinct values across our pool. This is not a "
        "claim that the detector fails: on the same pool it separates correct from "
        "hallucinating answers moderately well, at AUROC $0.704$.\n",
        encoding="utf-8")
    assert check_file(f), "the original site-four construction must be reported"


def test_accepts_a_properly_labelled_pair(tmp_path):
    """The corrected form must pass, or the check is unusable."""
    f = tmp_path / "good.tex"
    f.write_text(
        "Across the $97$ targets of the attack campaign, scored clean, the estimator "
        "offers only $22$ distinct values. On the score-independent \\emph{fair} pool "
        "($200$ correct, $200$ hallucinating) it separates correct from hallucinating "
        "answers at AUROC $0.704$ [$0.653$, $0.753$].\n",
        encoding="utf-8")
    assert not check_file(f), f"correctly labelled text must pass, got: {check_file(f)}"


def test_quarantined_numbers_require_an_attacked_marker(tmp_path):
    """0.579 and 0.184 describe the quarantined attacked subset. Presenting either as a
    property of 'the detector' is the error withdrawn in c92fe2a."""
    f = tmp_path / "quarantined.tex"
    f.write_text("The detector separates the classes by $0.184$ nats (AUROC $0.579$).\n",
                 encoding="utf-8")
    assert check_file(f), "quarantined-population numbers must demand an attacked-pool label"
