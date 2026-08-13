"""Fail the build when a population-sensitive number is unlabelled, MISLABELLED, or STALE.

WHY THIS EXISTS. Binding a statistic to the wrong population is this project's most-repeated
error: it has now been found and fixed at SIX separate sites (critique_log 28, 31), each time
by a manual sweep, and each sweep found a site the previous one missed. A manual process that
has failed six times should not be the guard on the seventh.

THREE POPULATIONS, and they are not interchangeable:

  fair pool      200 correct + 200 hallucinating, drawn score-independently.
                 AUROC 0.704 [0.653, 0.753]; separation 0.463 nats, d ~ 0.76.
                 Clean means 1.380 (correct) / 1.843 (wrong), headroom 0.923.
                 The ONLY population on which claims about "the detector" may be made.

  attacked pool  the attack campaign's own targets. TWO STRATA, and only one of them is
                 finished. NAME THE STRATUM, NEVER THE SUM:
                   - false-alarm stratum: COMPLETE and frozen at its pre-registered
                     n = 80 correct answers. A literal `80 correct` is true and stays a
                     valid label.
                   - hide stratum: STILL FILLING against its planned 80. It was 17 when
                     this file was first written, 46 at commit 5d822b9, 52 today. Any
                     literal count of it -- and therefore any total over both strata --
                     is stale at the moment of writing. That is why 5d822b9 purged "97"
                     from every .tex file, and why the guard now carries GROWING_CELLS
                     rather than a list of the particular wrong totals it has seen.
                 AUROC 0.579; separation 0.184 nats, d = 0.28. QUARANTINED for any
                 class-separation claim. The ceiling and granularity statistics (8/80 at
                 the cap, 21/80 in the top tenth, 42/80 = 52.5% at the cap after attack)
                 live HERE -- all of them 80-denominated, all inside the frozen stratum,
                 which is exactly what made the moving total droppable at no cost.

  replication    our own SE replication: one pass over 2000 TriviaQA questions, no attack,
                 no stratified sampler (results/replication_results.md). This is NEITHER
                 of the two above. Its AUROC has no single value -- it depends on which
                 correctness convention labels the run:
                   0.694  greedy alias-aware span  -- OPERATIVE: the convention the rest
                          of the paper runs on, and the one the paper must lead with.
                   0.730  majority-of-samples.
                   0.787  all-samples-correct -- SCORE-COUPLED, and DEMOTED by commit
                          8e54943. All-samples labels a question correct iff all ten
                          samples are correct, and SE is the entropy of the clustering of
                          those same ten, so part of the AUROC it awards is the score
                          scored against itself. It flatters the pipeline (0.787 vs the
                          published 0.828) and it is the one figure this paper may not
                          present as its replication result. Guarded so that it can only
                          appear WITH its convention named.

TWO OF THEM ARE NESTED, NOT DISJOINT. The attacked targets are literally the first 80 of
the fair pool's 200 correct (src/se/attacks/select.py, _stratum_ids + [:n]). So a sentence
may legitimately mention the fair pool *as the provenance* of an attacked-pool number
("the 80 targets are drawn from the fair pool's correct stratum"). Nothing here may assume
disjointness between those two; see NON_BINDING_CUES.

THE REPLICATION POOL IS DISJOINT FROM BOTH -- a different dataset slice, 2000 questions,
scored before any of this. There is no nesting to be tolerant of, so its rules are marked
`exclusive`: a fair-pool or attacked-pool label in the SAME sentence as a replication AUROC
is an error even when the word "replication" sits closer to the number. That is the case
proximity arbitration gets wrong, because "On the fair pool our SE replication reaches
0.694" puts the owning word nearer while the scope adverbial does the actual binding.

THE MARKUP LESSON. The critic's own grep for "fair pool" missed conclusion.tex because the
source reads `\\emph{fair} pool`. Phrase matching does not survive LaTeX. So we strip markup
before matching, and we anchor on NUMBERS, which markup cannot split.

--------------------------------------------------------------------------------------
WHAT THIS CHECKS (and why the first version of it was near-vacuous)

An audit constructed eight genuine population errors and the original rule missed seven.
Every miss had the same shape: the rule asked whether an allowed label was PRESENT within
420 characters, which in a paper that discusses both pools contrastively in one paragraph is
almost always true -- exactly where the error is likeliest. Five defects, all now closed:

  1. PRESENCE, never ATTACHMENT. `requires` was an OR satisfied by any allowed label in the
     window, and no label could ever cause a rejection.
     FIX: negative assertions. Every guarded number carries an OWNING pool; if a FOREIGN
     pool's label binds it more tightly than its own, that is an error. Tightness is
     (sentence boundaries crossed, distance), with a penalty on labels that follow the
     number, because English attaches "on the fair pool ... 0.704" and a label after the
     number usually opens a contrasting clause ("..., whereas the attacked subset gives").

  2. SELF-SATISFYING REQUIREMENTS. The granularity rule accepted the bare token `97` -- also
     satisfied by `0.97` and by the year `1997`; the quarantine rule accepted the bare word
     `attacked`, satisfied by "the detector we attacked".
     FIX: labels are POOL PHRASES ("attack campaign", "attacked subset", "80 correct"), and
     any label whose span lies inside the number's own span cannot label it. Nor may a
     label be built out of another number's DENOMINATOR: "the fair pool's 21/80 correct
     targets" was growing an attacked-pool label ("80 correct") out of the very count it
     was mislabelling. See NOT_A_DENOMINATOR.

  3. GUARDED SET TOO NARROW. 8/80, 21/80, 42/80, 42.5%, 52.5%, 34/80, the 45% retention
     family, 0.93, 0.787, AUROC 1.0 and the fair-pool headroom means were all unguarded.
     FIX: added, each with an owning pool. Plus a RUN-PROVENANCE rule: the checker guards
     which POOL a number belongs to and could not catch a number outliving the RUN it was
     computed on. Three such staleness bugs were found by hand (a stale 39% in the Abstract,
     a stale 39/80 in Methods, stale correlations +0.70/+0.67 that are +0.71/+0.68 under
     `_defb`). SUPERSEDED, below, encodes the retired values.

  4. strip_latex ate from a literal `\\%` to end of line, which blinded the checker to every
     number on Table 1's "Saturation rate (\\% at $\\log N$)" row. Fixed with a negative
     lookbehind; regression-tested.

  5. THE LABELS THEMSELVES WENT STALE, AND HARDENING THE ATTACHMENT LOGIC DID NOT NOTICE.
     Defects 1-4 all improved how a number is BOUND to a label. None of them asked whether
     a label was still TRUE. `97 targets`, `97-target`, `17 wrong` and `17 hide` stayed on
     the attacked pool's label list, and a whole rule ("97-target pool identity") existed to
     legitimise the phrase -- so after the hardening the guard caught 14 of 14 probes and
     still returned GREEN on "Across the 97 targets of the attack campaign (80 correct, 17
     wrong)", a sentence in which BOTH counts are retired. It did worse than miss the error:
     a retired count was a licence to attach anything to it.
     FIX: those four labels are gone, the rule that protected them is deleted, and the class
     is guarded generatively by GROWING_CELLS -- see the growing-denominator note there.
     A label list is an assertion about the world and expires like any other; the standing
     rule is that anything appearing in BOTH `labels` and the paper's numbers must be
     re-derived from an artifact whenever that artifact is rerun.

--------------------------------------------------------------------------------------
WHAT IT STILL CANNOT CATCH (deliberate; false positives gate the suite)

  * A wrong label inside a provenance or contrast clause ("drawn from the fair pool",
    "not the attacked subset", "than the fair pool"). Those labels are deliberately treated
    as NON-BINDING, because the pools are nested and the paper contrasts them constantly.
    A genuine error smuggled into such a clause passes.
  * A number with NO pool label anywhere near and no foreign label either is reported as
    unlabelled, not as mislabelled -- we cannot know which pool was meant.
  * AUROC 1.0 (the circularity artefact) is positive-only: three of its four live sites sit
    one clause away from a fair-pool label by design ("AUROC 1.0 by construction, versus
    0.704 ... on the fair pool"), so a proximity rule there would cry wolf.
  * 0.51 (the embedder's hard-negative AUROC) is NOT guarded: the paper also reports
    simulated power 0.51 at m=30, and a bare-decimal rule cannot tell them apart. Same
    for the Abstract's "20% still pinned" on the 15-target N=20 re-score subset: a bare
    20% is indistinguishable from any other 20%, and an unanchored rule there would fire
    on every future percentage that happens to round to it.
  * 0.698 COLLIDES, and the collision is mis-owned rather than merely unguarded -- the
    hazard the 0.51 entry records, one step worse. It is guarded as the winner's-curse
    selection-time mean intended move, which is 0.698 NATS on the 60 re-scored false-alarm
    targets. It is also 0.6977 -> 0.698, the substring-oracle AUROC of the 2000-question
    replication run (results/replication_auroc.json, greedy_correct) -- the figure commit
    8e54943 refined to the alias-aware 0.694 while leading with it. A bare decimal cannot
    tell a nats mean from an AUROC, so a replication 0.698 written into the paper would be
    reported against the winner's-curse population and would demand a re-scoring label it
    has no business carrying. If 0.698 ever needs to mean the AUROC again, it must be split
    by unit ("0.698 nats" vs "AUROC 0.698") before it can be guarded.
  * The `exclusive` rules (the replication family) fire on ANY same-sentence fair-pool or
    attacked-pool label, so a legitimate cross-population comparison in one sentence trips
    them. The escape hatch is the existing one: NON_BINDING_CUES disarms a label introduced
    by "than", "unlike", "not", "rather than". "0.694, unlike the fair pool's 0.704" passes;
    "0.694 on the fair pool" does not, which is the point.
  * FROZEN_COUNTS is an allow-list of complete cells, so it needs one edit when a cell
    completes -- when the hide arm finishes at its planned 80, its count and the 160 total
    become writable only after being declared here. That edit is the feature: stating a
    total should require asserting that the cell is closed.
  * The oracle-calibrated vs shipped power figures (0.84/0.71 vs 0.77/0.51) are a
    test-variant provenance problem, not a population one, and are not guarded here.
  * Numbers rendered as words ("a tenth", "a quarter", "past half", "nearly two fifths")
    are invisible to a number-anchored check -- for staleness as much as for population,
    and now for growing denominators too: "across the ninety-seven targets of the attack
    campaign" passes. They are the reason prose claims still need a human read.
  * The growing-denominator rule anchors on the NOUN a count quantifies, so a hide count
    written with no stratum noun escapes it: "the hide arm now stands at 52" passes, as
    does "the campaign covers $80 + 52$ targets". A verb-anchored pattern was tried and
    rejected -- Methods legitimately writes "the hide cell is still filling against its
    planned 80", and no cheap rule separates a planned n from a current count. Red-teamed
    and left open on purpose; the constructions that actually carried the bug (a total
    with a pool noun, a count with a stratum noun) are all covered.
  * `exclusive` compares within a sentence-ish unit, and `:` is a unit boundary. "On the
    fair pool: our SE replication reaches 0.694" therefore passes, where the same sentence
    with a comma fails. Splitting on the colon is what keeps the Conclusion's "not a claim
    that the detector fails: on the fair pool ... 0.704" green, so the boundary stays.
  * Table 1's cells are placeholders ("--"). When they are filled, the numbers themselves
    become checkable; the caption already names the population.
  * The guarded set is a LIST. A number this file has never heard of is unguarded, so a new
    run's headline has to be added here as it is added to the paper. That is the standing
    cost of anchoring on numbers rather than on prose, and it is why the fair-pool
    granularity counts (results/fair_pool_granularity.md) are already listed below,
    before they appear in the text.

Run: python scripts/check_population_labels.py    (exit 1 on any problem)
"""
from __future__ import annotations

import re
import sys
from bisect import bisect_left
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
PAPER = REPO / "paper"

# strip_latex preserves the backslash of an ESCAPED percent (`42\%` stays `42\%`), because
# eating it is how the checker went blind to Table 1's saturation row. Every percent pattern
# must therefore tolerate the backslash.
PCT = r"\\?%"

# How far back a negation/provenance cue may sit and still disarm a label. Clipped at the
# previous sentence boundary, so "...fails: on the score-independent fair pool" is NOT
# disarmed by the "not" earlier in that sentence.
CUE_LOOKBACK = 30

# A label that FOLLOWS the number is worth this many characters less than one that precedes
# it. "on the fair pool ... 0.704" binds; "0.463 nats and AUROC 0.704, whereas the attacked
# subset gives 0.184" does not bind 0.704 to the attacked subset. Set generously (a trailing
# label has to be very close to outrank a preceding one) so that the verdict does not flip
# on an unrelated clause being added or removed between a number and its label. A trailing
# foreign label with NO owning label anywhere in range is still an error either way.
TRAILING_PENALTY = 250

# When two labels are equally far in sentences, the foreign one must be this much closer
# before we call it an error. Absorbs comma-level noise.
MARGIN = 16

# A count phrase must not be manufactured out of another number's DENOMINATOR. Without this,
# "the fair pool's 21/80 correct targets" grows an attacked-pool label ("80 correct") out of
# the 21/80 it is mislabelling, and licenses itself -- defect 2 wearing a different hat.
# "$21$ of our $80$ correct targets" keeps its label, because there the 80 stands alone.
NOT_A_DENOMINATOR = r"(?<![/\d])"


# --------------------------------------------------------------------------------------
# Populations, and the phrases that name them. A label is a POOL PHRASE, never a bare token
# or a bare verb -- "the detector we attacked" must not satisfy the attacked-pool rule.
# --------------------------------------------------------------------------------------
POOLS: dict[str, dict] = {
    "fair": {
        "what": "fair pool (200 correct + 200 hallucinating, score-independent)",
        "labels": [
            r"fair pool",                 # survives `\emph{fair} pool` after strip_latex
            r"score-independent pool",
            NOT_A_DENOMINATOR + r"\b200 correct",
            NOT_A_DENOMINATOR + r"\b200 hallucinating",
            r"200\s*\+\s*200",
            r"\b400 questions", r"\bscore-independent 400",
        ],
    },
    "attacked": {
        "what": "attacked pool (the optimiser's own targets: a COMPLETE false-alarm "
                "stratum of 80, plus a hide stratum that is still filling -- no total)",
        # RETIRED as labels, 2026-08-13: `97 targets`, `97-target`, `17 wrong`, `17 hide`.
        # They named a pool identity that stopped being true while they sat here. The FA
        # stratum count is the only literal count of this pool that is frozen, so it is the
        # only one that may license anything; every other count of it is now FLAGGED by
        # GROWING_CELLS, including the ones that used to appear on this list.
        "labels": [
            r"attacked pool", r"attacked subset", r"attacked targets", r"attacked sample",
            r"attack pool", r"attack campaign", r"attack arm", r"attacked stratum",
            r"false-alarm attack pool", r"false-alarm targets", r"false-alarm arm",
            NOT_A_DENOMINATOR + r"\b80 correct",
            NOT_A_DENOMINATOR + r"\b80 false-alarm",
            r"quarantin",
            r"targets the optimiser was run on", r"optimiser'?s own targets",
        ],
    },
    "rescored": {
        "what": "winner's-curse subset (the 60 false-alarm targets re-scored on an "
                "independent sample)",
        "labels": [
            r"re-scor", r"rescor", r"selected paraphrase", r"independent sample",
            r"fresh sample", r"\b60 false-alarm", r"selection-time", r"at selection",
            r"winner'?s.{0,3}curse",
        ],
    },
    "judge_val": {
        "what": "judge-validation strata (domain-matched gold-alias hard negatives, n=300)",
        "labels": [
            r"hard[- ]negative", r"hard negatives", r"hard discrimination",
            r"gold[- ]alias", r"domain-matched", r"adversarial (?:case|discrimination)",
            r"n\s*=?\s*300", r"positive[- ]alias", r"positive-recognition",
        ],
    },
    "circular": {
        "what": "score-DEPENDENT selection (the circularity artefact, not a measured pool)",
        "labels": [
            r"by construction", r"score-dependent", r"extreme selection",
            r"its own scores", r"circularity", r"selection rule reflected",
            r"the extreme one",
        ],
    },
    "replication": {
        "what": "our SE replication run (2000 TriviaQA questions, one pass, no attack and "
                "no stratified sampler -- NEITHER the fair pool NOR the attacked pool)",
        "labels": [
            r"replicat",
            NOT_A_DENOMINATOR + r"\b2000 questions", r"\b2000-question",
            r"greedy alias-aware", r"alias-aware span",
            r"majority-of-samples", r"all[- ]samples[- ]correct",
            r"correctness convention", r"label convention",
        ],
    },
    "published": {
        "what": "a figure reported by prior work, not measured here",
        "labels": [r"published", r"\bpaper'?s?\b", r"prior work", r"originating work"],
    },
}

# A label preceded by one of these does not BIND the number to that pool: it either denies
# the binding, or states provenance. The pools are NESTED (the 80 attacked targets are the
# first 80 of the fair pool's 200 correct), so "drawn from the fair pool" is a legitimate
# thing to say next to an attacked-pool number.
NON_BINDING_CUES = [
    # denial / contrast
    r"\bnot\b", r"\bnever\b", r"\bnor\b", r"\bunlike\b", r"\bthan\b", r"\brather than\b",
    r"\binstead of\b", r"\bas opposed to\b", r"\bdifferent from\b", r"\bdistinct from\b",
    r"\bother than\b",
    # provenance / nesting. The paper states the nesting constantly ("a score-independent
    # sub-sample of the fair pool below", "a prefix of the fair pool's correct stratum"),
    # and every one of those is a provenance mention, not a binding.
    r"\bdrawn from\b", r"\bsampled from\b", r"\bselected from\b", r"\btaken from\b",
    r"\bsubsets? of\b", r"\bsub-?samples? of\b", r"\bsamples? of\b", r"\bprefix of\b",
    r"\bstrat(?:um|a) of\b", r"\bportion of\b", r"\bslice of\b", r"\bsuperset of\b",
    r"\bnested\b", r"\bfirst \d+ of\b", r"\bcome from\b",
]
# NB: "wider" is deliberately NOT a cue. The Abstract reads "on the wider score-independent
# fair pool ... those targets are drawn from, this one separates the two ... (AUROC 0.70)":
# that mention BINDS 0.70 to the fair pool, and disarming it would strip the only label.
_NON_BINDING_RE = re.compile("|".join(NON_BINDING_CUES), re.IGNORECASE)

# Sentence-ish boundaries. `(?=\s)` is load-bearing: it keeps the decimal point of `1.380`
# from being read as the end of a sentence.
_TERM_RE = re.compile(r"[.:;!?](?=\s)")


# --------------------------------------------------------------------------------------
# The guarded numbers. Every one carries an OWNING pool; `foreign` names the pools whose
# labels, if they bind more tightly, constitute an error.
# --------------------------------------------------------------------------------------
RULES: list[dict] = [
    {
        "name": "fair-pool AUROC / separation",
        "owner": "fair",
        "foreign": ["attacked"],
        "numbers": [r"0\.704", r"0\.653", r"0\.753", r"0\.463",
                    r"AUROC 0\.70(?!\d)", r"d\s*=\s*0\.7[56]\d?"],
        "window": 420,
    },
    {
        "name": "fair-pool clean entropy / headroom",
        "owner": "fair",
        "foreign": ["attacked"],
        # commit 4d2aa77: "label the population of every headroom statistic" -- site two.
        "numbers": [r"1\.380", r"1\.843", r"0\.923"],
        "window": 420,
    },
    {
        "name": "QUARANTINED attacked-pool separation",
        "owner": "attacked",
        "foreign": ["fair"],
        "numbers": [r"0\.579", r"0\.184", r"d\s*=\s*0\.28", r"0\.416", r"0\.728"],
        "window": 420,
        "note": "These are the optimiser's own targets -- a selected, partly truncated "
                "sample. They may NEVER be presented as properties of 'the detector'.",
    },
    {
        "name": "ceiling / granularity counts (attacked pool)",
        "owner": "attacked",
        "foreign": ["fair"],
        # `39 attainable` is deliberately NOT guarded: the size of the N=10 lattice is a
        # property of the estimator, true of every population (results/
        # fair_pool_granularity.md derives it from p(10)=42 with no data at all). Only the
        # REALISED count is population-bound, and that is `22 of the 39`.
        # `22 distinct` is handled by SUPERSEDED instead: commit e6e7629 retired the
        # realised-value count from all four sites, so its return is a staleness problem
        # rather than a labelling one, whichever pool it is attached to.
        "numbers": [r"\b8/80", r"\b8 of (?:the )?80", r"\b8 began",
                    r"\b21/80", r"\b21 of (?:our |the )?80", r"those 21 targets"],
        "window": 420,
    },
    {
        # results/fair_pool_granularity.md (2026-08-13) restates the ceiling/granularity
        # finding on the fair pool. Its counts are one nesting-slip away from the attacked
        # pool's: 19/200 = 9.5% at the cap on the fair correct stratum reads almost the same
        # as 8/80 = 10% on the attacked one. Guarded before they land in the text.
        "name": "fair-pool granularity / crowding counts",
        "owner": "fair",
        "foreign": ["attacked"],
        "numbers": [r"31 distinct", r"31 of (?:the )?39", r"\b74/400", r"\b132/400",
                    r"\b19/200", r"\b43/200", r"\b28 of (?:the )?39",
                    r"\b26 of (?:the )?39",
                    # the rates the Abstract actually carries (commit e6e7629 moved the
                    # crowding claim off the attacked subset and onto this population)
                    rf"\b9\.5{PCT}", rf"\b21\.5{PCT}", rf"\b27\.5{PCT}", rf"\b44\.5{PCT}",
                    rf"\b33\.0{PCT}", rf"\b18\.5{PCT}"],
        "window": 420,
    },
    {
        "name": "saturation counts (attacked pool)",
        "owner": "attacked",
        "foreign": ["fair"],
        "numbers": [r"\b42/80", r"\b42 of (?:the )?80", r"\b42 finish", r"\b34/80",
                    rf"42\.5{PCT}", rf"52\.5{PCT}", rf"\b42{PCT}"],
        "window": 420,
    },
    # DELETED 2026-08-13: the "97-target pool identity" rule. Its entire job was to check
    # that a retired phrase was properly attached -- it asked whether "97 targets" named the
    # attack campaign, never whether the attacked pool had 97 targets, which it has not
    # since the hide arm passed 17. There is no pool identity left to state: the total is
    # 80 + a live count. Its three number patterns (`97 targets`, `across 97`, `97-target`)
    # now live in GROWING_CELLS, where 97 is flagged as one instance of a class rather than
    # licensed as a label.
    {
        "name": "winner's-curse retention (re-scored subset)",
        "owner": "rescored",
        "foreign": ["fair"],
        "numbers": [rf"\b45{PCT}", rf"\b25{PCT}", rf"\b65{PCT}", r"0\.383", r"0\.698",
                    r"0\.315", r"0\.529", r"0\.234", r"36 of 60"],
        "window": 700,      # the Limitations paragraph carries its label a long way
        "prox_window": 300,  # but only a NEARBY foreign label is evidence of mislabelling
    },
    {
        "name": "circularity artefact (score-DEPENDENT selection)",
        "owner": "circular",
        "foreign": [],       # positive-only; see the module docstring's limitation list
        "numbers": [r"AUROC (?:of |to |toward )?1\.0(?!\d)", r"\b1\.0 that"],
        "window": 250,
    },
    {
        # The 2000-question replication run is DISJOINT from both pools, so `exclusive`:
        # a fair-pool or attacked-pool label anywhere in the same sentence is an error even
        # when "replication" sits closer to the number. "On the fair pool our SE replication
        # reaches AUROC 0.694" is the shape that defeats proximity arbitration -- the owning
        # word is nearer, and the scope adverbial is what actually binds.
        "name": "our SE replication AUROC (operative conventions)",
        "owner": "replication",
        "foreign": ["fair", "attacked"],
        "numbers": [r"0\.694", r"0\.730"],
        "window": 300,
        "exclusive": True,
        "note": "0.694 (greedy alias-aware span) is the OPERATIVE replication figure and "
                "0.730 the majority-of-samples one. Neither is a fair-pool or an "
                "attacked-pool AUROC: they come from 2000 TriviaQA questions with no "
                "attack and no stratified sampler.",
    },
    {
        # commit 8e54943 DEMOTED 0.787. The coupling is the reason, so the guard demands the
        # coupling be visible: `requires` here is not a pool label but the CONVENTION, and
        # the rule turns red on a bare "our replication reaches 0.787" -- which is exactly
        # how the paper used to present it, against the published 0.828.
        "name": "all-samples replication AUROC (SCORE-COUPLED, never the operative figure)",
        "owner": "replication",
        "foreign": ["fair", "attacked"],
        "numbers": [r"0\.787", r"0\.790"],
        "requires": [r"all[- ]samples", r"all ten sampl", r"nearer[- ]looking",
                     r"(?:mechanically )?coupled", r"score[- ]entangled",
                     r"convention (?:the paper|we) (?:does not|use)"],
        "window": 300,
        "exclusive": True,
        "missing_label": "SCORE-COUPLED FIGURE PRESENTED BARE",
        "note": "0.787 is the all-samples-correct convention: a question counts correct "
                "iff all ten samples are, and SE is the entropy of the clustering of those "
                "same ten, so part of this AUROC is the score scored against itself. It "
                "was demoted by commit 8e54943 and may NEVER be presented as the paper's "
                "operative replication figure -- 0.694 is. Wherever it appears, the "
                "all-samples convention must be named in the same breath.",
    },
    {
        "name": "prior-work figures (not ours)",
        "owner": "published",
        "foreign": [],
        "numbers": [r"0\.828", r"0\.871"],
        "window": 300,
    },
    {
        "name": "judge validation population",
        "owner": "judge_val",
        "foreign": [],
        # 0.51 is deliberately absent: the paper also reports simulated power 0.51 at m=30.
        "numbers": [r"0\.93(?!\d)"],
        "window": 420,
    },
]


# --------------------------------------------------------------------------------------
# Run provenance. The pool rules cannot catch a number that outlived the RUN it came from.
# `wk9_def` was superseded by the instrumented `wk9_defb` cell (results/
# ceiling_saturation_finding.md, results/CORRECTIONS_2026-08-02.md). Ambiguous renderings
# carry a `near` gate so that, e.g., a future "39%" of something else does not cry wolf.
# --------------------------------------------------------------------------------------
_SAT_CTX = [r"satur", r"ceiling", r"\bcap\b", r"pinned", r"log N", r"ln 10", r"2\.30"]
_CORR_CTX = [r"correlat", r"\bcorr\b", r"headroom", r"uncensored", r"\br\s*="]

SUPERSEDED: list[dict] = [
    {"pattern": r"\b39/80", "current": "42/80",
     "quantity": "targets at the log N ceiling after attack"},
    {"pattern": r"\b39 of (?:the )?80", "current": "42 of the 80",
     "quantity": "targets at the log N ceiling after attack"},
    {"pattern": r"\b39 finish", "current": "42 finish",
     "quantity": "targets finishing exactly at the ceiling"},
    {"pattern": r"\b31/80", "current": "34/80",
     "quantity": "ATTACK-INDUCED saturation count"},
    {"pattern": r"\b31 of (?:the )?80", "current": "34 of the 80",
     "quantity": "ATTACK-INDUCED saturation count"},
    {"pattern": r"38\.75", "current": "42.5%",
     "quantity": "ATTACK-INDUCED saturation rate"},
    {"pattern": rf"\b39{PCT}", "current": "42% (42.5%)",
     "quantity": "ATTACK-INDUCED saturation rate", "near": _SAT_CTX},
    {"pattern": rf"\b49{PCT}", "current": "52.5%",
     "quantity": "TOTAL at-ceiling rate", "near": _SAT_CTX},
    {"pattern": r"\+0\.70(?!\d)|r\s*=\s*0\.70(?!\d)", "current": "+0.71",
     "quantity": "corr(headroom, move)", "near": _CORR_CTX},
    {"pattern": r"\+0\.67(?!\d)|r\s*=\s*0\.67(?!\d)", "current": "+0.68",
     "quantity": "corr(headroom, move) within the uncensored subset", "near": _CORR_CTX},
    # Retired outright, not merely recomputed (commit e6e7629). A realised distinct-value
    # count is monotone in targets scored and never converges: the same population gives 22
    # at n=80, 28 at n=200, 35 at n=2000, and the hide cell grew 17 -> 43 mid-session, which
    # falsified the replacement claim before it was committed. Only the LATTICE size is
    # n-invariant. Attaching the right pool to it does not make it true, so it is guarded
    # here rather than by a population rule.
    {"pattern": r"22 distinct|22 attainable|22 of (?:its |the )?39",
     "run": "n=80 FA cell", "quantity": "realised distinct-value count",
     "replacement": "that count is a statement about the sample, not the estimator -- "
                    "report the n-invariant lattice instead ($39$ attainable values at "
                    "$N{=}10$, two of them in the top tenth of the range)"},
    # NB: `97 targets`, `17 wrong` and friends are deliberately NOT listed here. Enumerating
    # the particular stale values is the shape that failed -- see GROWING_CELLS below.
]
SUPERSEDED_RUN = "wk9_def"
CURRENT_RUN = "wk9_defb"
NEAR_WINDOW = 300


# --------------------------------------------------------------------------------------
# GROWING DENOMINATORS. The general form of the bug that inverted this guard.
#
# SUPERSEDED above answers "this number was recomputed and is now that number". It cannot
# answer the hide arm, because the hide arm has no settled value to be superseded BY: it was
# 17, then 41, then 43, then 46, then 52, and it is heading for its planned 80. A literal
# count of a cell that is still filling is wrong at the moment of writing and wrong again at
# every later moment, and so is any total that sums over it. Commit 5d822b9 removed "97" on
# exactly this reasoning ("stale by construction ... would have been wrong again at any
# later value") and the guard then went on blessing it for a day, because the guard was
# looking for values it had been told about.
#
# SO THE POLARITY IS INVERTED. We do not enumerate the stale counts -- that set is open and
# grows by one every time the campaign advances, which is precisely why the enumerated form
# failed. We enumerate the counts that are FROZEN, a closed set that changes only when a cell
# COMPLETES, and flag every other literal count of a campaign stratum or of the pool as a
# whole. 52 is caught today without anyone having written 52 down; so is 61, and so is 132.
#
# Adding to FROZEN_COUNTS is therefore a deliberate assertion that a cell is closed. That is
# the intended cost: stating a total should require saying which run finished.
# --------------------------------------------------------------------------------------
# The registry is keyed by CELL, not by value. Keying it by value alone leaves the worst
# hole open: the hide arm's planned n IS 80, so a global "80 is fine" would bless "80 wrong"
# today -- a count that is false now and will be true later, which is the same
# stale-by-construction bug with the sign flipped. A cell whose entry is an EMPTY set has no
# admissible literal count at all, because it is still filling.
_FA_STRATUM = "the FALSE-ALARM stratum -- COMPLETE at its pre-registered n=80 " \
              "(results/fa_n80_milestone.md, 80/80)"
_FAIR_STRATUM = "a fair-pool correctness stratum -- complete and score-independent"
_WC_SUBSET = "the winner's-curse subset (the FA targets the optimiser found a paraphrase " \
             "for), frozen with the FA cell"
_PILOT = "the N=20 re-score subset (results/pilot_n20_ceiling.md) -- a closed pilot"

FROZEN_COUNTS: dict[int, str] = {          # the union, for reporting only
    15: _PILOT, 60: _WC_SUBSET, 80: _FA_STRATUM, 200: _FAIR_STRATUM,
    300: "each judge-validation stratum -- complete (results/judge_validation.md)",
    400: "the fair pool, 200 + 200 -- complete",
    2000: "the TriviaQA replication run -- complete "
          "(results/replication_results.md, 2000 of 2000)",
}

# HIDE_OPEN is deliberately empty. While the hide arm is filling there is NO literal count
# of it that is true for longer than a session. When it closes at its planned 80, whoever
# closes it puts 80 here, with the artifact that closed it -- and only then may the paper
# write a hide count or a both-strata total.
HIDE_OPEN: frozenset[int] = frozenset()

# (pattern, what it counts, the counts admissible for THAT cell, an optional context gate).
# The gate exists only for patterns loose enough to reach counts outside this campaign.
# NB: `target` is deliberately absent -- the loose pattern below contains the word
# "targets" itself, so including it would make the gate vacuous.
_ATTACK_CTX = [r"attack", r"campaign", r"optimiser", r"hide arm", r"false[- ]alarm",
               r"quarantin"]

_STRATUM_COUNTS: list[tuple[str, str, frozenset, list | None]] = [
    (r"(?<![/\d.])\b(\d+) (?:model-)?wrong\b", "the hide (wrong-answer) stratum",
     HIDE_OPEN, None),
    (r"(?<![/\d.])\b(\d+) wrong-answer\b", "the hide (wrong-answer) stratum",
     HIDE_OPEN, None),
    (r"(?<![/\d.])\b(\d+) hid(?:e|ing)\b", "the hide stratum", HIDE_OPEN, None),
    # `hallucinating` reaches the fair pool's complete wrong stratum, not the hide arm.
    (r"(?<![/\d.])\b(\d+) hallucinating\b", "a hallucinating-answer stratum",
     frozenset({200}), None),
    # `correct`/`false-alarm` reach frozen cells; they are guarded anyway so that a
    # MIS-stated frozen count is caught -- the FA cell being closed is exactly what makes
    # any value but 80 there an error rather than a snapshot.
    (r"(?<![/\d.])\b(\d+) correct\b", "a correct-answer stratum", frozenset({80, 200}),
     None),
    (r"(?<![/\d.])\b(\d+) false-alarm\b", "the false-alarm stratum", frozenset({60, 80}),
     None),
]

# A count predicated of the POOL rather than of a stratum: the sum, which is 80 + a live
# number, and therefore has no admissible value at all. These are CONSTRUCTIONS, not
# proximity: "those 21 targets" and "15 saturated targets" are subset counts and must stay
# green, so a bare "N targets" is never enough -- the pool has to be named, or the
# quantifier has to be a totalising one.
_POOL_NOUN = (r"(?:attack(?:ed)?(?: campaign| pool| subset| arm| cells?)?|campaign"
              r"|optimiser'?s own targets)")
_QUAL = r"(?: [a-z-]+){1,2}"      # "80 CORRECT-ANSWER targets" -- names a stratum
_NUM = r"(?<![/\d.])\b(\d+)"
_STRATUM_OK = frozenset({15, 60, 80})

_POOL_TOTALS: list[tuple[str, str, frozenset, list | None]] = [
    # "the 97 targets of the attack campaign" -- unqualified, so it is the SUM.
    (_NUM + r" targets? (?:of|in|from) (?:the |our |its )?" + _POOL_NOUN,
     "the attacked pool as a whole", HIDE_OPEN, None),
    # "...of our attack campaign" with a stratum named: a stratum count, frozen values only.
    (_NUM + _QUAL + r" targets? (?:of|in|from) (?:the |our |its )?" + _POOL_NOUN,
     "a named stratum of the attacked pool", _STRATUM_OK, None),
    # "the attack campaign's 97 targets", and its stratum-qualified form.
    (_POOL_NOUN + r"'?s? " + _NUM + r" targets?", "the attacked pool as a whole",
     HIDE_OPEN, None),
    (_POOL_NOUN + r"'?s? " + _NUM + _QUAL + r" targets?",
     "a named stratum of the attacked pool", _STRATUM_OK, None),
    # "the 97-target pool". The `\s*` is load-bearing: strip_latex leaves a space where it
    # removed a command, so `$\mathbf{97}$-target` flattens to `97 -target`.
    (_NUM + r"\s*-\s*target\b", "a pool named by its size", HIDE_OPEN, None),
    # "across the 97 targets", "all 97 targets", "a pool of 97". Frozen stratum sizes are
    # tolerated here because "all 80 targets" is far likelier to be the FA cell than a
    # claimed total, and crying wolf on it would cost more than it catches.
    (r"\b(?:across|all|a pool of|pool of|totalling|comprising) (?:the |our |its )?"
     + _NUM + r"\b(?=\s*(?:targets?|attack|campaign|[,.;:]|$))",
     "the attacked pool as a whole", _STRATUM_OK, None),
    (_NUM + r" targets?,? (?:in total|altogether|overall)",
     "the attacked pool as a whole", HIDE_OPEN, None),
    # "97 targets (80 correct, 17 wrong)" -- a total stated with its own strata breakdown,
    # which is the exact sentence commit 5d822b9 deleted.
    (_NUM + r" targets?[^.]{0,20}?\(?\s*(?<![/\d.])\d+ correct",
     "the attacked pool as a whole, stated as a strata sum", HIDE_OPEN, None),
    # Bare "the 97 targets", with no pool noun attached. A DEFINITE determiner is required
    # so that the paper's subset counts stay green: "those 21 targets" and "15 saturated
    # targets" are counts of a slice, not assertions about the pool's size. Context-gated,
    # because "the 500 targets" of something else is none of this rule's business.
    (r"\b(?:the|our|its) " + _NUM + r" targets?\b",
     "the attacked pool as a whole", _STRATUM_OK, _ATTACK_CTX),
]

GROWING_ADVICE = (
    "the hide arm is STILL FILLING against its planned 80 (17 -> 41 -> 46 -> 52 and "
    "counting), so this count -- and every total that sums over it -- is stale at the "
    "moment of writing. Name the stratum that carries the statistic instead: the "
    "false-alarm stratum is complete at 80 and its counts (8/80, 21/80, 42/80) are "
    "stable. If a both-strata figure is wanted, the fair pool supplies one that is "
    "complete and score-independent. If a cell has genuinely COMPLETED, declare it in "
    "FROZEN_COUNTS with the artifact that closed it"
)


def strip_latex(text: str) -> str:
    """Flatten markup so phrase matching works. `\\emph{fair} pool` -> `fair pool`.

    This is the whole point: the manual sweeps failed because \\emph{} split the phrases
    they were grepping for.
    """
    # NB: negative lookbehind is load-bearing. Without it this eats from a LITERAL \%
    # to end of line, which would blind the checker to every number on Table 1's
    # "Saturation rate (\% at $\log N$)" row -- the exact row it exists to guard.
    text = re.sub(r"(?<!\\)%.*?$", "", text, flags=re.MULTILINE)  # comments, not \%
    text = re.sub(r"\\(?:emph|textbf|textit|mathrm|text)\{([^{}]*)\}", r"\1", text)
    text = re.sub(r"\\citep?\{[^{}]*\}", " ", text)                # citations
    text = re.sub(r"\\ref\{[^{}]*\}", " ", text)
    text = re.sub(r"\\[a-zA-Z]+", " ", text)                       # remaining commands
    text = text.replace("{", " ").replace("}", " ").replace("~", " ")
    text = text.replace("$", "")            # math delimiters: $97$ and 97 must match alike
    return re.sub(r"\s+", " ", text)


# --------------------------------------------------------------------------------------
# Label geometry
# --------------------------------------------------------------------------------------
def _terminators(flat: str) -> list[int]:
    return [m.start() for m in _TERM_RE.finditer(flat)]


def _crossings(terms: list[int], lo: int, hi: int) -> int:
    """Sentence-ish boundaries strictly inside [lo, hi)."""
    if hi <= lo:
        return 0
    return bisect_left(terms, hi) - bisect_left(terms, lo)


def _is_non_binding(flat: str, start: int, terms: list[int]) -> bool:
    """True if a denial or provenance cue sits just before this label.

    The lookback stops at the previous sentence boundary, so the Conclusion's
    "This is not a claim that the detector fails: on the ... fair pool" keeps its label.
    """
    lo = max(0, start - CUE_LOOKBACK)
    j = bisect_left(terms, start) - 1
    if j >= 0 and lo <= terms[j] < start:
        lo = terms[j] + 1
    return bool(_NON_BINDING_RE.search(flat[lo:start]))


def _scan_labels(flat: str, patterns: list[str], terms: list[int]) -> list[tuple]:
    spans = []
    for pat in patterns:
        for m in re.finditer(pat, flat, re.IGNORECASE):
            if _is_non_binding(flat, m.start(), terms):
                continue
            spans.append((m.start(), m.end(), m.group(0)))
    return spans


def _closest(num: tuple[int, int], labels: list[tuple], terms: list[int],
             window: int) -> tuple[int, int, str] | None:
    """Tightest-binding label: (sentences crossed, penalised distance, matched text).

    A label whose span lies INSIDE the number's own span is ignored -- the words of the
    flagged phrase cannot be its own licence (defect 2).
    """
    ns, ne = num
    best = None
    for ls, le, text in labels:
        if ls >= ns and le <= ne:
            continue
        if ls >= ne:                       # label after the number
            raw = ls - ne
            cross = _crossings(terms, ne, ls)
            score = raw + TRAILING_PENALTY
        elif le <= ns:                     # label before the number
            raw = ns - le
            cross = _crossings(terms, le, ns)
            score = raw
        else:                              # overlapping
            raw, cross, score = 0, 0, 0
        if raw > window:
            continue
        cand = (cross, score, text)
        if best is None or cand[:2] < best[:2]:
            best = cand
    return best


def _rel(path: Path) -> str:
    try:
        return str(path.relative_to(REPO))
    except ValueError:
        return path.name


def _line_hint(raw: str, matched: str) -> str:
    """Best-effort source line for a token that markup may have split (`$22$ of the $39$`)."""
    parts = [re.escape(p) for p in matched.split() if p]
    if not parts:
        return ""
    pat = re.compile(r"[\s$\\{}~]*".join(parts), re.IGNORECASE)
    for i, line in enumerate(raw.splitlines(), 1):
        if pat.search(line):
            return f":{i}"
    return ""


# --------------------------------------------------------------------------------------
# The checks
# --------------------------------------------------------------------------------------
def _check_pools(raw: str, flat: str, terms: list[int], shown: str) -> list[str]:
    problems: list[str] = []
    pool_labels = {name: _scan_labels(flat, spec["labels"], terms)
                   for name, spec in POOLS.items()}
    custom: dict[tuple, list[tuple]] = {}

    for rule in RULES:
        owner = rule["owner"]
        window = rule["window"]
        prox = rule.get("prox_window", window)
        if "requires" in rule:
            key = tuple(rule["requires"])
            if key not in custom:
                custom[key] = _scan_labels(flat, rule["requires"], terms)
            req_labels = custom[key]
            req_desc = rule["requires"]
        else:
            req_labels = pool_labels[owner]
            req_desc = POOLS[owner]["labels"]

        for num_pat in rule["numbers"]:
            for hit in re.finditer(num_pat, flat, re.IGNORECASE):
                span = (hit.start(), hit.end())
                token = hit.group(0).replace("\\", "")   # `42\%` reads better as `42%`
                own_prox = _closest(span, pool_labels[owner], terms, prox)
                foreign_best = None
                for other in rule["foreign"]:
                    cand = _closest(span, pool_labels[other], terms, prox)
                    if cand is None:
                        continue
                    tagged = (cand[0], cand[1], cand[2], other)
                    if foreign_best is None or tagged[:2] < foreign_best[:2]:
                        foreign_best = tagged

                # (1) NEGATIVE assertion: a foreign pool's label binds more tightly.
                #     ...unless the rule is `exclusive`, in which case the owning pool is
                #     DISJOINT from the foreign ones and same-sentence co-occurrence is
                #     itself the error. Proximity arbitration exists to tolerate NESTING
                #     ("the 80 targets are drawn from the fair pool"); nothing about the
                #     2000-question replication run is nested in either pool, so there is
                #     nothing to tolerate. A label already disarmed by NON_BINDING_CUES
                #     ("unlike the fair pool's 0.704") never reaches here.
                if foreign_best is not None:
                    fc, fs, ftext, fpool = foreign_best
                    exclusive_hit = bool(rule.get("exclusive")) and fc == 0
                    beaten = (exclusive_hit
                              or own_prox is None
                              or fc < own_prox[0]
                              or (fc == own_prox[0] and fs + MARGIN < own_prox[1]))
                    if beaten:
                        if exclusive_hit and own_prox is not None:
                            near = ("its own label "
                                    f"'{own_prox[2]}' is nearer, but these populations are "
                                    "DISJOINT -- they may not share a sentence")
                        elif own_prox is None:
                            near = f"no owning-pool label within {prox} chars"
                        else:
                            near = f"its own label '{own_prox[2]}' binds less tightly"
                        where = f"{shown}{_line_hint(raw, hit.group(0))}"
                        ctx = flat[max(0, hit.start() - 110):hit.end() + 110].strip()
                        problems.append(
                            f"{where}: [{rule['name']}] MISLABELLED POPULATION.\n"
                            f"      '{token}' belongs to the "
                            f"{POOLS[owner]['what']},\n"
                            f"      but the closest binding label is '{ftext}' "
                            f"-> {POOLS[fpool]['what']} ({near}).\n"
                            + (f"      {rule['note']}\n" if rule.get("note") else "")
                            + f"      context: ...{ctx}...")
                        continue

                # (2) POSITIVE assertion: the owning pool must actually be named.
                if _closest(span, req_labels, terms, window) is None:
                    where = f"{shown}{_line_hint(raw, hit.group(0))}"
                    ctx = flat[max(0, hit.start() - 110):hit.end() + 110].strip()
                    problems.append(
                        f"{where}: [{rule['name']}] "
                        f"{rule.get('missing_label', 'UNLABELLED')}.\n"
                        f"      '{token}' belongs to the {POOLS[owner]['what']} "
                        f"but no binding label appears within {window} chars.\n"
                        f"      needs one of: {req_desc}\n"
                        + (f"      {rule['note']}\n" if rule.get("note") else "")
                        + f"      context: ...{ctx}...")
    return problems


def _check_provenance(raw: str, flat: str, shown: str) -> list[str]:
    """Catch a number that outlived the run it was computed on."""
    problems: list[str] = []
    for item in SUPERSEDED:
        for hit in re.finditer(item["pattern"], flat, re.IGNORECASE):
            if "near" in item:
                lo = max(0, hit.start() - NEAR_WINDOW)
                hi = min(len(flat), hit.end() + NEAR_WINDOW)
                ctx = flat[lo:hi]
                if not any(re.search(p, ctx, re.IGNORECASE) for p in item["near"]):
                    continue
            where = f"{shown}{_line_hint(raw, hit.group(0))}"
            snippet = flat[max(0, hit.start() - 110):hit.end() + 110].strip()
            problems.append(
                f"{where}: [run provenance] STALE VALUE.\n"
                f"      '{hit.group(0).replace(chr(92), '')}' is the "
                f"{item.get('run', SUPERSEDED_RUN)} value of {item['quantity']};\n"
                f"      "
                + item.get("replacement",
                           f"{CURRENT_RUN} (definitive) gives {item.get('current')}")
                + f".\n      context: ...{snippet}...")
    return problems


def _check_growing(raw: str, flat: str, shown: str) -> list[str]:
    """Flag a literal count of a cell that is still filling, or a total that sums over one.

    The polarity is the point. A count passes only if it is DECLARED FROZEN in
    FROZEN_COUNTS; the stale values are never enumerated, because that set gains a member
    every time the campaign advances -- which is how `97 targets` and `17 wrong` survived
    as LABELS long after both were false.
    """
    problems: list[str] = []
    seen: set[tuple[int, int]] = set()
    for specs in (_STRATUM_COUNTS, _POOL_TOTALS):
        for pattern, what, allowed, near in specs:
            for hit in re.finditer(pattern, flat, re.IGNORECASE):
                value = int(hit.group(1))
                if value in allowed:
                    continue
                if near is not None:
                    lo = max(0, hit.start() - NEAR_WINDOW)
                    ctx = flat[lo:min(len(flat), hit.end() + NEAR_WINDOW)]
                    if not any(re.search(p, ctx, re.IGNORECASE) for p in near):
                        continue
                if (hit.start(1), hit.end(1)) in seen:   # one report per literal count
                    continue
                seen.add((hit.start(1), hit.end(1)))
                where = f"{shown}{_line_hint(raw, hit.group(0))}"
                snippet = flat[max(0, hit.start() - 110):hit.end() + 110].strip()
                ok = (", ".join(str(v) for v in sorted(allowed)) if allowed
                      else "NONE -- that cell is still filling")
                problems.append(
                    f"{where}: [growing denominator] COUNT OF A CELL THAT IS NOT CLOSED.\n"
                    f"      '{hit.group(0).replace(chr(92), '')}' attaches the literal "
                    f"count {value} to {what};\n"
                    f"      admissible counts there: {ok}.\n"
                    f"      {GROWING_ADVICE}.\n"
                    f"      context: ...{snippet}...")
    return problems


def check_file(path: Path) -> list[str]:
    raw = path.read_text(encoding="utf-8", errors="replace")
    flat = strip_latex(raw)
    terms = _terminators(flat)
    shown = _rel(path)
    return (_check_pools(raw, flat, terms, shown)
            + _check_provenance(raw, flat, shown)
            + _check_growing(raw, flat, shown))


def main() -> int:
    targets = sorted(PAPER.glob("*.tex")) + sorted((PAPER / "sections").glob("*.tex"))
    if not targets:
        print("no .tex files found under paper/", file=sys.stderr)
        return 1
    problems: list[str] = []
    for t in targets:
        problems.extend(check_file(t))
    if problems:
        print(f"POPULATION-LABEL CHECK FAILED - {len(problems)} problem(s):\n")
        for p in problems:
            print("  " + p)
        print("\nEvery population-sensitive number must be BOUND to its pool, not merely "
              "near a mention of one. THREE populations, not interchangeable:\n"
              "  fair pool    200 correct + 200 hallucinating, score-independent. "
              "0.704 lives here, and every correct-versus-hallucinating claim.\n"
              "  attacked     the campaign's own targets: a COMPLETE false-alarm stratum "
              "of 80, plus a hide stratum that is still filling. The ceiling, granularity "
              "and saturation counts live here, all 80-denominated. Name the stratum -- "
              "this pool has no total, and any sum over it is stale before it is read.\n"
              "  replication  2000 TriviaQA questions, no attack. 0.694 is the operative "
              "AUROC; 0.787 is the score-coupled all-samples one and is not the paper's "
              "figure.\n"
              "The first two are nested, not disjoint, so say which one you mean in the "
              "clause that carries the number. The third is disjoint from both.")
        return 1
    n_numbers = sum(len(r["numbers"]) for r in RULES)
    n_growing = len(_STRATUM_COUNTS) + len(_POOL_TOTALS)
    print(f"population-label check: OK ({len(targets)} files, {len(RULES)} rules, "
          f"{n_numbers} number patterns, {len(SUPERSEDED)} superseded-run patterns, "
          f"{n_growing} growing-cell patterns over {len(FROZEN_COUNTS)} frozen counts)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
