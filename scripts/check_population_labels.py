"""Fail the build when a population-sensitive number is unlabelled, MISLABELLED, or STALE.

WHY THIS EXISTS. Binding a statistic to the wrong population is this project's most-repeated
error: it has now been found and fixed at SIX separate sites (critique_log 28, 31), each time
by a manual sweep, and each sweep found a site the previous one missed. A manual process that
has failed six times should not be the guard on the seventh.

FOUR POPULATIONS, and they are not interchangeable:

  (A fifth, smaller population is registered in POOLS below: the winner's-curse
  re-scored subset. It is nested inside the attacked pool's false-alarm stratum and is
  described there, because its whole identity is "the FA targets the optimiser found a
  paraphrase for".)

  fair pool      200 correct + 200 hallucinating, drawn score-independently.
                 AUROC 0.704 [0.653, 0.753]; separation 0.463 nats, d ~ 0.76.
                 Clean means 1.380 (correct) / 1.843 (wrong), headroom 0.923.
                 The ONLY population on which claims about "the detector" may be made.

  attacked pool  the attack campaign's own targets. TWO STRATA, and BOTH ARE NOW CLOSED
                 (2026-08-13). NAME THE STRATUM ANYWAY -- the statistics differ per
                 direction and the sum is rarely the quantity anyone means:
                   - false-alarm stratum: COMPLETE and frozen at its pre-registered
                     n = 80 correct answers. A literal `80 correct` is true and stays a
                     valid label.
                   - hide stratum: COMPLETE at its pre-registered n = 80, as of
                     results/fair_recompute_report.md (07:21, 2026-08-13) and commit
                     9e9347c. It was 17 when this file was first written, 43 at the
                     population-nesting correction, 46 at commit 5d822b9, 52 when
                     GROWING_CELLS was built to catch exactly this, and 60 an hour
                     before it closed. The campaign total is therefore 160, and it is
                     declared in FROZEN_COUNTS. See the HIDE_OPEN note for why the
                     GUARD went on denying this for six days after it became true.
                 AUROC 0.579; separation 0.184 nats, d = 0.28. QUARANTINED for any
                 class-separation claim. The ceiling and granularity statistics (8/80 at
                 the cap, 21/80 in the top tenth, 42/80 = 52.5% at the cap after attack)
                 live HERE -- all of them 80-denominated, all inside the frozen FA
                 stratum, which is exactly what made the moving total droppable at no
                 cost while it was moving.

  full labelled  the 1424 greedy-correct answers of the 2000-question replication pass
  pool, correct  (alias-aware span oracle; 1424 correct + 576 hallucinating = 2000).
  stratum        The achievable-FPR FLOOR lives here: 150/1424 = 10.5% [9.0, 12.2].
                 THE FAIR POOL'S 200-ANSWER CORRECT STRATUM IS A STRICT SUBSET OF IT, so
                 the two estimate the SAME parameter at different precision, and the
                 Discussion uses the 1424 figure as a precision check on the fair pool's
                 9.5% [6.2, 14.4]. That cross-reference is legitimate and load-bearing;
                 see `coexist` for how the guard tells it apart from a mislabelling.

  replication    our own SE replication: one pass over 2000 TriviaQA questions, no attack,
                 no stratified sampler (results/replication_results.md). This is NEITHER
                 of the two above. Its AUROC has no single value -- it depends on which
                 correctness convention labels the run:
                   0.694  greedy alias-aware span  -- OPERATIVE: the convention the rest
                          of the paper runs on, and the one the paper must lead with.
                   0.729  majority-of-samples (0.730 under the substring oracle; the full
                          oracle x convention grid is results/replication_conventions.md).
                   0.787  all-samples-correct -- SCORE-COUPLED, and DEMOTED by commit
                          8e54943. All-samples labels a question correct iff all ten
                          samples are correct, and SE is the entropy of the clustering of
                          those same ten, so part of the AUROC it awards is the score
                          scored against itself. It flatters the pipeline (0.787 vs the
                          published 0.828) and it is the one figure this paper may not
                          present as its replication result. 0.790 is the same cell under
                          the span oracle and carries the same prohibition. Both are
                          guarded so that they can only appear WITH the convention named.

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
almost always true -- exactly where the error is likeliest. Six defects, all now closed:

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

  6. THE GUARDED VALUES WENT STALE TOO, AND THE RULE STAYED GREEN BECAUSE OF IT (2026-08-19).
     Defect 5 fixed the LABELS. It did not ask the same question of `numbers`. When the
     winner's-curse cell was rerun (`_def`, n=60 -> `_defb`, n=69) every figure in it moved,
     and the rule kept listing the OLD ones: 45%/25%/65%, 0.383, 0.698, 0.315, 0.529, 0.234,
     `36 of 60`. Not one live value -- 44%, 23%, 64%, -0.341, -0.469, -0.212, +0.609,
     +0.268, `37 of 69`, r=0.48 -- was guarded, so the paper's entire Limitations winner's-
     curse paragraph, its Abstract sentence and two Introduction sentences were unprotected;
     `\b60 false-alarm` was still a LABEL (defect 5's exact shape, one cell over); and 69 was
     not a frozen count, passing only because the adjacent `80 false-alarm` was the token the
     growing rule happened to capture. A rule pointed at values that no longer exist cannot
     fail, and a check that cannot fail reports success. FIX: the retired nine are moved to
     SUPERSEDED (the existing mechanism for a superseded number), the live ten are registered
     with `rescored` as their owner, 69 and its complement 11 are declared in FROZEN_COUNTS,
     and _WC_OK gives the cell its own admissible set so no neighbouring token can stand in
     for it. THE GENERAL LESSON, and it is the one to carry forward: rerunning a cell
     silently disarms every rule keyed to its old values. `numbers` expires exactly like
     `labels` does. Whoever reruns a cell owns BOTH lists for it.

     AND THERE IS A SECOND WAY TO BE SILENT, found in the same sweep: never keyed at all.
     A rerun disarms an existing rule; a NEW result arrives with no rule at any time. Six
     live values had entered the paper since the guard was last touched -- 5.0% and 2.0%
     (the N=40 achievable grid, fair pool correct stratum), 3.0% (the N=20 floor, and a
     REPLAY rather than a measurement), and 14.8%, 20.0%, 27.8% (Eq.(5) vs discrete
     saturation over the 2000-question pass). Three new rules cover them. Note that the
     `2000 cached sample sets` rendering matched none of the replication pool's labels, so
     registering the values without registering the rendering would only have moved the
     silence -- the two lists have to be extended together.

  7. THE REGISTRY ITSELF EXPIRED, AND THE GUARD BEGAN FLAGGING TRUE STATEMENTS (2026-08-19).
     Defects 5 and 6 are the same bug in `labels` and in `numbers`. This is the third copy
     of it, in FROZEN_COUNTS -- the one list the file explicitly tells you to look at -- and
     it is the only one whose sign is INVERTED. The hide arm closed at its pre-registered
     n=80 on 2026-08-13 (results/fair_recompute_report.md, "SE / hide (n=80)", and its
     AUROC table at n=160; commit 9e9347c, "both arms are now at their pre-registered n for
     the first time ... the true campaign total is 160"). HIDE_OPEN was never updated. So
     for six days the guard reported "80 wrong", "80 hide targets" and "the campaign's 160
     targets" -- all three TRUE -- as growing-denominator errors, and TWO TESTS PINNED THAT
     BEHAVIOUR, which is why nothing broke to say so.
     The reason this is a defect and not a conservative default: critique_log 35 says "a
     check that cannot fail is not a check". A check that fails on true statements has the
     SAME end state by a different route -- its user learns to skip its output -- and it
     gets there faster, because a silent check merely fails to help while a crying one
     actively costs time on every run. Defects 5 and 6 both took a whole audit to find
     precisely because a quiet rule looks exactly like a passing one; this defect announced
     itself daily and was still not fixed, which is the more damning of the two.
     FIX: the hide cell is declared closed, 160 is a frozen count, and -- the part the
     spelled-out edit in the old HIDE_OPEN note got WRONG -- the cell's admissible set and
     the POOL TOTAL's admissible set are now two different constants. See _TOTAL_OK.

  8. A WHOLE POPULATION WAS NEVER REGISTERED, AND THE GUARD WENT RED ON IT (2026-08-19).
     Defect 6's second half was "a new VALUE with no rule". This is a new POPULATION with no
     POOLS entry: the full labelled pool's correct stratum, n=1424, which carries the
     achievable-FPR floor 150/1424 = 10.5% [9.0, 12.2] at four sites including the Abstract
     and the Conclusion. Because 1424 and 576 were not frozen counts, the growing-denominator
     rule was flagging the paper's own "(1424 correct and 576 hallucinating)" in methods.tex
     and limitations.tex -- four false positives, defect 7's shape one population over.
     The interesting part is the NESTING. The fair pool's 200-answer correct stratum is a
     STRICT SUBSET of the 1424, so the two estimate the same parameter and the Discussion
     cross-references them on purpose. Proximity arbitration handles three of the four sites
     unaided, but introduction.tex writes "at 9.5% on the fair pool's correct stratum and at
     10.5% ... on the 1424-answer superset it is a subset of", which puts the FOREIGN label
     26 characters before the number and the OWNING one 25 characters after it -- and a
     trailing label pays TRAILING_PENALTY. That is proximity arbitration losing to a
     perfectly correct sentence. `coexist` is the answer: where owner and foreign are
     NESTED, a foreign label accuses only when the owning label is ABSENT from the sentence.
     Note also that the interval could not be armed as two bare decimals: 9.0 is the LOWER
     bound of [9.0, 12.2] and also the UPPER bound of the N=40 grid's [2.7, 9.0], three
     sites away. It is armed as the PAIR. Same hazard as 0.51, 0.698 and 12.0%.

  9. THE GUARD LICENSED A CLAIM SHAPE THAT SUPERSEDED HAD ALREADY RETIRED (2026-08-19).
     `22 distinct` was retired outright because a realised distinct-value count is a SAMPLE
     statistic wearing a population parameter's clothes: the expected number of distinct
     values among 80 draws is 23.0, so 22 was the 37th percentile of nothing happening. The
     fair-pool granularity rule then listed `31 distinct`, `31 of the 39`, `28 of the 39`
     and `26 of the 39` as LIVE, guarded, fair-pool numbers -- so the guard's answer to the
     retired claim was "correct, once you label it". Attaching the right population to a
     quantity that is not a population parameter does not make it one.
     FIX: the four are struck from the guarded set and the SHAPE is retired GENERATIVELY,
     on the `\\b\\d+/97\\b` precedent -- any "N distinct/attainable values" and any "N of the
     39", with the n-INVARIANT lattice sizes (39 at N=10, 455 at N=20) excluded, because the
     lattice is the one thing here that is a property of the estimator. No numerator is
     enumerated, so 35 at n=2000 and every future rerun's count are caught unwritten.
     THE CONTROL MATTERS MORE THAN THE PROBE HERE. introduction.tex argues the retirement
     explicitly -- "Nothing here rests on a count of distinct values realised ... the same
     population yields 28 at n=200 and 35 at n=2000, and 22 sits at the 37th percentile" --
     and a careless generative rule would go red on the passage that does the retiring. It
     is pinned green by test_the_papers_own_disavowal_of_the_retired_shape_is_not_flagged.

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
  * 0.698 COLLIDES, and the collision USED to be mis-owned -- the hazard the 0.51 entry
    records, one step worse. It was guarded as the winner's-curse selection-time mean
    intended move, 0.698 NATS on the 60 re-scored false-alarm targets. It is also
    0.6977 -> 0.698, the substring-oracle AUROC of the 2000-question replication run
    (results/replication_auroc.json, greedy_correct) -- the figure commit 8e54943 refined to
    the alias-aware 0.694 while leading with it. A bare decimal cannot tell a nats mean from
    an AUROC, so a replication 0.698 was reported against the winner's-curse population and
    made to demand a re-scoring label it had no business carrying. THE `_defb` RERUN
    DISSOLVED THIS: 0.698 is now the RETIRED selection-time mean (+0.609 replaces it), so it
    moved to SUPERSEDED behind a `_WC_CTX` gate. A 0.698 with re-scoring words around it is
    reported as the stale nats mean; a 0.698 in a replication sentence is not reported at
    all, which is the correct silence -- it is unguarded, not mis-owned. If 0.698 ever needs
    to mean the AUROC again it must still be split by unit ("0.698 nats" vs "AUROC 0.698")
    before it can be guarded positively.
  * The `exclusive` rules (the replication family) fire on ANY same-sentence fair-pool or
    attacked-pool label, so a legitimate cross-population comparison in one sentence trips
    them. The escape hatch is the existing one: NON_BINDING_CUES disarms a label introduced
    by "than", "unlike", "not", "rather than". "0.694, unlike the fair pool's 0.704" passes;
    "0.694 on the fair pool" does not, which is the point.
  * FROZEN_COUNTS is an allow-list of complete cells, so it needs one edit when a cell
    completes. That edit is the feature: stating a total should require asserting that the
    cell is closed. IT IS ALSO A LIABILITY, and 2026-08-19 collected the bill -- see
    defect 7. The hide arm closed on 2026-08-13 and nobody made the declaration, so for six
    days the guard reported the TRUE statements "80 wrong" and "the campaign's 160 targets"
    as growing-denominator errors. An allow-list of facts about the world expires exactly
    the way `labels` (defect 5) and `numbers` (defect 6) do; the only difference is the SIGN
    of the failure, and an over-strict guard is not the safe direction to fail in.
  * MEASURED VS DERIVED is a SECOND AXIS, and this file now guards exactly one number on
    it. The oracle-calibrated vs shipped power figures (0.84/0.71 vs 0.77/0.51) are a
    test-variant provenance problem, not a population one, and are still not guarded. The
    N=20 floor is the same shape with a headline attached: only N=40 was measured, every
    smaller budget in results/n_scaling_grid.md is a replay of the recorded verdicts on
    random subsets, and the report's own control shows replay OVERSTATES the floor (12.0%
    median against a directly measured 9.5%, all 20 replicates above). No population label
    can detect that -- 3.0% and 9.5% are the same 200 correct answers -- so the replay rule
    uses `requires` to demand the disclosure instead, the way the 0.787 rule demands its
    convention. Every other derived quantity in the paper is unguarded on this axis.
  * 12.0% COLLIDES: it is the replay median above, and it is also 24/200 = 12.0%, the fair
    pool's correct-stratum rate within 0.01 nats of the top (results/
    fair_pool_granularity.md). Only the first is in the paper. If the second ever lands,
    the replay rule will demand a replay disclosure for a directly measured number, and the
    two must then be split by what they are a rate OF before either can be guarded.
  * THE 2000-QUESTION SATURATION RATES SIT 1400+ CHARACTERS FROM THEIR ONLY LABEL, and the
    rule tolerates it rather than reporting it. In limitations.tex the Eq.(5) paragraph
    declares its population once at the top -- "the 1424 greedy-correct questions ... of
    our 2000-question replication pass" -- and then argues for eleven hundred characters
    before quoting 14.8%, 20.0% and 27.8%. The nearest population label to those three
    rates is a FAIR-POOL one, about 400 characters after them, and they are not fair-pool
    rates: they are 295/2000, 399/2000 and 556/2000. Nothing here is false, but a reader
    arriving at that sentence has no denominator, and the paragraph's own scoping sentence
    names 1424 and 200 while the rates that follow are over 2000. That is a PAPER-side gap;
    the window is set to 1600 so the guard does not go red on it, and the protection that
    remains is proximity: a fair-pool or attacked-pool label written NEXT to one of these
    rates is still reported. Narrowing the window is the right move the moment the
    paragraph restates its denominator closer to the numbers.
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
        # RETIRED as a label, 2026-08-19: `\b60 false-alarm`. The cell was rerun (`_def`
        # n=60 -> `_defb` n=69) and the label went on asserting the old size, which is
        # defect 5 one cell over. 69 is the live size and is DECLARED in FROZEN_COUNTS, so
        # it may be a label; 60 is now caught by the cell-keyed growing rule instead.
        "what": "winner's-curse subset (the 69 false-alarm targets on which the optimiser "
                "found a paraphrase, re-scored on an independent sample)",
        "labels": [
            r"re-scor", r"rescor", r"selected paraphrase", r"independent sample",
            r"fresh sample", NOT_A_DENOMINATOR + r"\b69 false-alarm",
            r"selection-time", r"at selection", r"winner'?s.{0,3}curse",
            r"found a paraphrase",      # the phrase that DEFINES the subset, count-free
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
    "full_correct": {
        # ADDED 2026-08-19 (defect 8). Live at four sites -- Abstract, Introduction,
        # Discussion, Conclusion -- with no POOLS entry at any of them, while the growing
        # rule went red on the paper's own "(1424 correct and 576 hallucinating)".
        #
        # This stratum is the CORRECT half of the replication pass, so it is nested inside
        # `replication`, and the fair pool's 200-answer correct stratum is nested inside IT.
        # All three estimate the same ceiling-atom mass; only the precision differs. The
        # rule that owns 10.5% is therefore `coexist`, never `exclusive`.
        "what": "the full labelled pool's CORRECT stratum (all 1424 greedy-correct answers "
                "of the 2000-question replication pass; the fair pool's 200-answer correct "
                "stratum is a STRICT SUBSET of it, estimating the same parameter less "
                "precisely -- results/achievable_fpr_grid.md)",
        "labels": [
            r"1424-answer", r"\b1424-question",
            NOT_A_DENOMINATOR + r"\b1424 clean correct",
            NOT_A_DENOMINATOR + r"\b1424 greedy-correct",
            NOT_A_DENOMINATOR + r"\b1424 correct",
            NOT_A_DENOMINATOR + r"\b1424 labelled",
            r"full labelled pool", r"full pool", r"labelled superset",
            # the paper's own word for the relation, used at three of the four sites
            r"answer superset", r"\bsuperset puts\b",
        ],
    },
    "replication": {
        "what": "our SE replication run (2000 TriviaQA questions, one pass, no attack and "
                "no stratified sampler -- NEITHER the fair pool NOR the attacked pool)",
        "labels": [
            r"replicat",
            NOT_A_DENOMINATOR + r"\b2000 questions", r"\b2000-question",
            # methods.tex writes "our $2000$ cached sample sets" for the same pass. The
            # three renderings above did not match it, so the Eq.(5) rates below had no
            # reachable label there at all -- registering the values without registering
            # the rendering only moves the silence.
            NOT_A_DENOMINATOR + r"\b2000 cached",
            r"\bcached sample sets", r"\b2000 sample sets",
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
        # 0.703 added 2026-08-19: the SAME fair pool scored under length-normalised
        # Eq.(5) on identical clusterings (results/post_overnight_claim_review.md M4). It
        # is live in limitations.tex, it was unguarded, and it sits one digit from 0.704 in
        # the same clause -- the cheapest possible slip between two estimators on one pool.
        "numbers": [r"0\.704", r"0\.703", r"0\.653", r"0\.753", r"0\.463",
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
        # !! FOUND BY THE 2026-08-19 SWEEP, NOT FIXED HERE: ALL FIVE OF THESE ARE `_def`-ERA
        # VALUES OF A POPULATION THAT NO LONGER EXISTS. results/dynamic_range_finding.md
        # line 66 computes them on "the 80 FA + 17 hide campaign targets" -- the 97-target
        # pool, with the hide arm truncated at n=17. The hide arm was 43, then 52, and
        # closed at 80 on 2026-08-13, so a recomputation today returns different numbers
        # for every one of them. The guard demands an attacked-pool label for five corpses
        # and would say nothing at all about their live replacements. This is defect 6
        # exactly, and it is the SECOND family in that state.
        #
        # It is not rearmed because there is nothing to rearm it WITH: the separation
        # statistic is QUARANTINED (a correct-versus-hallucinating contrast may not be made
        # on a selected sub-sample of one stratum per direction), so no one recomputes it
        # and there is no live value. The correct fix when the quarantine is next revisited
        # is to move all five to SUPERSEDED behind an attacked-pool context gate -- a
        # quarantined number reappearing is a staleness problem as much as a labelling one,
        # and the guard currently reports only the second half of that.
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
        # FOUR PATTERNS STRUCK 2026-08-19 (defect 9): `31 distinct`, `31 of 39`,
        # `28 of 39`, `26 of 39`. They were the SAME CLAIM SHAPE that SUPERSEDED retires as
        # `22 distinct`, and the retirement note there names two of them as instances of the
        # problem: "the same population gives 22 at n=80, 28 at n=200, 35 at n=2000".
        # results/fair_pool_granularity.md agrees with itself on this -- Chao1 from the
        # n=400 sample estimates 35.0 against 39 attainable, "so the realised count has not
        # converged at n=400 either ... a distinct-value count is a statement about the
        # sample, not about the estimator". So this rule was LICENSING, as a
        # properly-labelled fair-pool number, the very claim commit e6e7629 retired from all
        # four sites. A population label cannot rescue a quantity that is not a population
        # parameter, and offering one is worse than silence: it tells the author the number
        # is fine.
        # The shape is now retired GENERATIVELY in SUPERSEDED (see _DISTINCT_COUNT_ADVICE),
        # which also covers the n=2000 rendering (35) that was never guarded at all.
        # The crowding RATES below ARE population statistics and are correctly live.
        "name": "fair-pool granularity / crowding counts",
        "owner": "fair",
        "foreign": ["attacked"],
        "numbers": [r"\b74/400", r"\b132/400",
                    r"\b19/200", r"\b43/200",
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
        # REARMED 2026-08-19 on the `_defb` rerun (n=60 -> n=69). Every number below moved,
        # and until this edit the rule still listed the `_def` set -- 45/25/65%, 0.383,
        # 0.698, 0.315, 0.529, 0.234, `36 of 60` -- none of which appears in the paper any
        # more. The rule therefore matched nothing and could not fail, while the four live
        # sites (Abstract, Introduction x2, Limitations) carried ten unguarded numbers.
        # The retired nine are in SUPERSEDED; see defect 6 in the module docstring.
        "name": "winner's-curse retention (re-scored subset)",
        "owner": "rescored",
        "foreign": ["fair"],
        "numbers": [rf"\b44{PCT}", rf"\b23{PCT}", rf"\b64{PCT}",
                    r"-0\.341", r"-0\.469", r"-0\.212",
                    r"\+0\.609", r"\+0\.268",
                    r"37 of (?:the )?69",
                    r"r\s*=\s*0\.48(?!\d)", r"\+0\.48(?:2)?(?!\d)"],
        "window": 700,      # the Limitations paragraph carries its label a long way
        "prox_window": 300,  # but only a NEARBY foreign label is evidence of mislabelling
        "note": "These are the `_defb` winner's-curse figures on the 69 false-alarm "
                "targets the optimiser found a paraphrase for. They are NOT fair-pool "
                "quantities and not properties of 'the detector'.",
    },
    {
        # ADDED 2026-08-19. THE SECOND FAILURE MODE: never keyed at all. These entered the
        # paper after the guard was last touched, so no rule had ever heard of them -- the
        # standing cost the docstring names, come due. results/rescore_likelihoods.md,
        # 2000 questions: discrete 295/2000 = 14.8% at cap and 556/2000 = 27.8% in the top
        # decile; farquhar_eq5_lennorm 399/2000 = 20.0% in the top decile; Spearman 0.9892.
        #
        # 27.8% COLLIDES with a RETIRED number and the collision is the exact confusion this
        # file exists to prevent: 27/97 = 27.8% is the attacked subset's pooled top-tenth
        # rate from the `_def` era. A value-keyed rule cannot separate them. A POPULATION-
        # keyed one can, and that is the answer: this rate is owned by the replication pass,
        # so an attacked-pool label bound to it is an error, while the retired rendering is
        # caught by its 97 DENOMINATOR in SUPERSEDED. Probe and control both in the tests.
        "name": "Eq.(5) / discrete-estimator saturation rates (2000-question pass)",
        "owner": "replication",
        "foreign": ["fair", "attacked"],
        "numbers": [rf"\b14\.8{PCT}", rf"\b20\.0{PCT}", rf"\b27\.8{PCT}",
                    r"\b295/2000", r"\b556/2000", r"\b399/2000", r"0\.9892"],
        # NOT `exclusive`, unlike the replication AUROCs. Those are headline numbers quoted
        # on their own; these are argued in a paragraph whose SUBJECT is the nesting -- "the
        # 1424 greedy-correct questions of our 2000-question replication pass, and the
        # 200-question correct stratum of the fair pool nested within it" names both
        # populations in one sentence, legitimately, and exclusivity would fire on it.
        "window": 1600,
        "prox_window": 300,
        "note": "These are rates over the 2000-question cached pass, NOT over the fair "
                "pool's 400 and NOT over the attacked pool's 80.",
    },
    {
        # ADDED 2026-08-19, same failure mode: the N=40 budget-scaling numbers landed in the
        # Abstract, Introduction and Discussion in the uncommitted edit and no rule covered
        # them. results/n_scaling_grid.md section 3: at N=40 an `at_most` 5% budget is
        # achieved at 5.0% (10/200), and the smallest non-zero achievable rate is 2.0%
        # (4/200). Both are on the fair pool's CORRECT stratum, n=200 -- the same
        # population as the 9.5% floor they are contrasted with.
        #
        # 2.0% is guarded BEFORE it appears, which is this file's standing practice for a
        # number that is about to land (see the fair-pool granularity rule).
        "name": "achievable-FPR grid at larger sample budgets (fair pool, correct stratum)",
        "owner": "fair",
        "foreign": ["attacked"],
        "numbers": [rf"\b5\.0{PCT}", rf"\b2\.0{PCT}", r"\b10/200", r"\b4/200"],
        "window": 520,       # Discussion carries the label 476 chars back
        "prox_window": 300,
    },
    {
        # ADDED 2026-08-19, defect 8: a FOURTH population, live at four sites and never
        # registered. results/achievable_fpr_grid.md Appendix A: the lowest firing
        # operating point on the full labelled pool's correct stratum is
        # 150/1424 = 10.5% [9.0, 12.2], against 19/200 = 9.5% [6.2, 14.4] on the fair
        # pool's correct stratum -- the SAME parameter, seven times the negatives.
        #
        # THE INTERVAL IS ARMED AS A PAIR, NOT AS TWO DECIMALS, and that is not fussiness:
        # 9.0 is this interval's LOWER bound and also the UPPER bound of the N=40 grid's
        # achieved 5.0% [2.7, 9.0], which is a FAIR-POOL number living three sites away in
        # the same sections. A bare `\b9\.0` rule would demand a 1424 label at every one of
        # them. This is the 0.51 / 0.698 / 12.0% hazard, recognised before it was armed
        # rather than after. 12.2 is unique to this interval and is armed alone; 10.5 is
        # unique to this floor and is armed alone.
        "name": "achievable-FPR floor on the full labelled pool's correct stratum (n=1424)",
        "owner": "full_correct",
        "foreign": ["fair", "attacked", "replication"],
        # NESTED, so `coexist` and never `exclusive`: fair-correct SUBSET full-correct
        # SUBSET replication, and the Discussion's precision check names two of them in one
        # sentence on purpose. A foreign label accuses only where the owner is ABSENT.
        "coexist": True,
        "numbers": [rf"\b10\.5{PCT}", rf"\b10\.53{PCT}", r"\b150/1424",
                    r"\b9\.0\s*,\s*12\.2", rf"\b12\.2(?!\d)"],
        "window": 420,
        "prox_window": 300,
        "note": "This floor is measured on the 1424 greedy-correct answers of the "
                "replication pass, NOT on the fair pool's 200 correct answers (whose "
                "floor is 9.5% [6.2, 14.4]) and NOT over all 2000 questions. The two "
                "correct strata are nested and estimate the same parameter, so name "
                "which one carries the number -- that is the whole content of the "
                "Discussion's precision check.",
    },
    {
        # ADDED 2026-08-19, and it guards a DIFFERENT AXIS from every other rule here.
        #
        # The question these rules ask is "which POPULATION". 3.0% raises a second one that
        # this file has met before and never armed: MEASURED, OR DERIVED? Only N=40 was run.
        # Every smaller budget in results/n_scaling_grid.md is a replay of the recorded
        # pairwise verdicts on random subsets, and the report's own subsetting control shows
        # replay is BIASED: against a directly measured N=10 floor of 9.5%, replay gives a
        # 12.0% median with all 20 replicates above the direct estimate. So a replayed floor
        # quoted as a measurement overstates it, and no population label detects that --
        # 3.0% and 9.5% are the same 200 correct answers.
        #
        # `requires` is therefore the disclosure, not a pool, exactly as the 0.787 rule
        # demands its convention be named. The pre-existing instance of this axis is noted
        # in the docstring (oracle-calibrated vs shipped power, 0.84/0.71 vs 0.77/0.51) and
        # is still unguarded; this is the first time it carries a headline number.
        "name": "REPLAY-derived budget figures (subset replay, not a direct measurement)",
        "owner": "fair",
        "foreign": ["attacked"],
        # 3.1% is the exact subset-averaged value that supersedes the replicate-0 3.0%.
        # Both renderings are guarded, on the 0.729/0.730 precedent: a guard that tracked
        # only the current one would go quiet the moment the estimate was restated.
        "numbers": [rf"\b3\.0{PCT}", rf"\b3\.1{PCT}", rf"\b12\.0{PCT}"],
        "requires": [r"replay", r"replaying", r"replicates?\b", r"subsets?\b",
                     r"recorded (?:pairwise )?(?:equivalence )?verdicts",
                     r"derived by", r"not (?:a )?direct"],
        "window": 420,
        "prox_window": 300,
        "missing_label": "REPLAY-DERIVED FIGURE PRESENTED AS A MEASUREMENT",
        "note": "Only N=40 was measured. Every smaller budget is a replay of the recorded "
                "verdicts on random subsets, and the subsetting control shows replay "
                "OVERSTATES the floor (12.0% median against a directly measured 9.5%, all "
                "20 replicates above). Say that it is a replay wherever it is quoted.",
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
        # Both renderings of the majority cell are guarded. The (oracle x convention) grid
        # in results/replication_conventions.md gives span/majority 0.7292 -> 0.729, which
        # is what the paper now carries, and substring/majority 0.7296 -> 0.730, which it
        # carried until the span oracle was made consistent. A guard that tracked only the
        # current rendering would go quiet the next time the oracle is restated.
        "numbers": [r"0\.694", r"0\.729", r"0\.730"],
        "window": 300,
        "exclusive": True,
        "note": "0.694 (greedy alias-aware span) is the OPERATIVE replication figure; "
                "0.729/0.730 are the majority-of-samples one under the span and substring "
                "oracles. None is a fair-pool or an attacked-pool AUROC: they come from "
                "2000 TriviaQA questions with no attack and no stratified sampler.",
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
# Winner's-curse context. Deliberately NARROW: `paraphrase`, `selection` and `attack` are
# everywhere in this paper, and a gate built from them would reach half the Discussion.
# These are the words that only the re-scoring diagnostic uses.
_WC_CTX = [r"re-scor", r"rescor", r"retention", r"retains", r"shrinkage",
           r"winner'?s.{0,3}curse", r"selection-time", r"at selection",
           r"fresh sample", r"independent sample", r"selected paraphrase"]

# Why every realised distinct-value count is retired, whatever its numerator and whatever
# population it is attached to. Shared by the two generative patterns below so the two
# renderings of one claim cannot drift apart in what they say about it.
_DISTINCT_COUNT_ADVICE = (
    "a realised distinct-value count measures the SAMPLE, not the estimator. It is "
    "monotone in the number of targets scored and it never converges: the same "
    "population gives 22 at n=80, 28 at n=200 and 35 at n=2000, and Chao1 on the n=400 "
    "sample already estimates 35.0 against 39 attainable "
    "(results/fair_pool_granularity.md). 22 was not even low -- the expected number of "
    "distinct values among 80 draws is 23.0, putting 22 at the 37th percentile, so the "
    "original claim reported a coin landing as it was expected to. Commit e6e7629 retired "
    "it from all four sites for that reason, and LABELLING IT DOES NOT REPAIR IT: no "
    "population owns a statistic that is a property of how many draws you took. Report "
    "the n-invariant lattice instead ($39$ attainable values at $N{=}10$, two of them in "
    "the top tenth of the range; $455$ at $N{=}20$)"
)

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
    #
    # GENERATIVE SINCE 2026-08-19 (defect 9), on the `\b\d+/97\b` precedent below. The
    # enumerated form -- `22 distinct|22 attainable|22 of the 39` -- retired ONE numerator
    # while the fair-pool granularity rule went on licensing 31, 28 and 26 as live guarded
    # numbers, and 35 (the n=2000 rendering named in this very note) was covered by neither.
    # Enumerating numerators is the shape that failed for `97` and it failed identically
    # here: what is wrong with the claim is the SHAPE, so the shape is what gets retired,
    # and every future rerun's count is caught without anyone writing it down.
    #
    # THE EXCLUSIONS ARE THE WHOLE DESIGN. 39 (at N=10) and 455 (at N=20) are LATTICE sizes
    # -- derived from p(10)=42 and p(20)=627 with no data at all -- so they are properties
    # of the estimator, they do not move with n, and they are exactly what the paper is told
    # to report INSTEAD. A rule that flagged them would be flagging the replacement.
    {"pattern": r"(?<![/\d.])\b(?!39\b|455\b)\d+ "
                r"(?:distinct|attainable|realised|realized)"
                r"(?: entropy| SE| score)? values?",
     "run": "a finite sample", "quantity": "a REALISED distinct-value count",
     "replacement": _DISTINCT_COUNT_ADVICE},
    # No lattice exclusion on THIS one, deliberately. "39 of the 39" is not the lattice
    # size being reported, it is a claim that a particular sample realised all of it --
    # the retired shape at its upper limit, and the likeliest rendering at n=2000, where
    # Chao1 already estimates 35.0. The exclusion belongs on the pattern that can match a
    # bare lattice statement, and this one cannot.
    {"pattern": r"(?<![/\d.])\b\d+ of (?:its |the |our )?39\b",
     "run": "a finite sample", "quantity": "a REALISED distinct-value count, "
                                           "stated against the lattice size",
     "replacement": _DISTINCT_COUNT_ADVICE},
    # NB: `97 targets`, `17 wrong` and friends are deliberately NOT listed here. Enumerating
    # the particular stale values is the shape that failed -- see GROWING_CELLS below.
    #
    # ANY DENOMINATOR OF 97 IS STALE, generatively, without enumerating the numerators.
    # docs/START_HERE_overnight.md states the rule outright: "Any statistic with 97 in its
    # denominator is stale by construction." 97 was 80 correct + a hide arm truncated at 17;
    # the arm ran on to 43, 52 and finally 80, so 27/97, 12/97 and every sibling describe a
    # pool that existed for one afternoon. This is also half the answer to the 27.8%
    # collision: the RETIRED rendering is caught here by its denominator, and the LIVE
    # 27.8% (556/2000, the replication pass) is caught by its population rule.
    {"pattern": r"(?<![/\d.])\b\d+/97\b", "run": "the 97-target `_def`-era pool",
     "quantity": "a rate over 80 correct + a hide arm truncated at 17",
     "replacement": "that denominator never existed for longer than an afternoon -- the "
                    "hide arm ran 17 -> 43 -> 52 -> 80. Restate the statistic on a closed "
                    "cell: the FA stratum (80) or the fair pool (200 / 400)"},
    #
    # ---- THE WINNER'S-CURSE CELL, `_def` (n=60) -> `_defb` (n=69), 2026-08-19 -----------
    # results/winners_curse_se_false_alarm.md is regenerated from
    # results/winners_curse_ckpt_se_false_alarm_defb.jsonl (69 rows; the `_def` checkpoint
    # has 60). EVERY figure moved, so every one of them is listed: leaving even one off is
    # what let the whole family go quiet. These are VALUES, so they belong here; the cell
    # SIZE (60 -> 69) is a count and is keyed to its cell in _WC_OK instead. Percentages and
    # bare decimals carry a `near` gate, because a future 25% of something else is not this.
    {"pattern": rf"\b45(?:\.2)?{PCT}", "current": "44% (44.0%)",
     "quantity": "retention of the selection-time effect on re-scoring",
     "near": _WC_CTX},
    {"pattern": rf"\b25(?:\.0)?{PCT}", "current": "23%",
     "quantity": "LOWER end of the retention bootstrap interval", "near": _WC_CTX},
    {"pattern": rf"\b65(?:\.0)?{PCT}", "current": "64%",
     "quantity": "UPPER end of the retention bootstrap interval", "near": _WC_CTX},
    {"pattern": r"\+?0\.698(?!\d)", "current": "+0.609 nats",
     "quantity": "mean intended move AT SELECTION",
     # The gate is what keeps the replication's substring-oracle AUROC 0.6977 -> 0.698 out
     # of this rule; see the 0.698 entry in the module docstring's limitation list.
     "near": _WC_CTX},
    {"pattern": r"\+?0\.315(?!\d)", "current": "+0.268 nats",
     "quantity": "mean intended move ON FRESH SAMPLES", "near": _WC_CTX},
    {"pattern": r"-?0\.383(?!\d)", "current": "-0.341 nats",
     "quantity": "shrinkage (fresh - selection)", "near": _WC_CTX},
    {"pattern": r"-?0\.529(?!\d)", "current": "-0.469 nats",
     "quantity": "LOWER end of the shrinkage bootstrap interval", "near": _WC_CTX},
    {"pattern": r"-?0\.234(?!\d)", "current": "-0.212 nats",
     "quantity": "UPPER end of the shrinkage bootstrap interval", "near": _WC_CTX},
    {"pattern": r"\b36 of (?:the |our )?(?:60|69)\b", "current": "37 of the 69",
     "quantity": "re-scored targets keeping a positive move"},
    {"pattern": r"\+0\.456(?!\d)|r\s*=\s*0\.46(?!\d)", "current": "r = 0.48 (+0.482)",
     "quantity": "corr(selection move, fresh move)", "near": _WC_CTX},
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
_FA_STRATUM = "a campaign stratum -- BOTH are COMPLETE at their pre-registered n=80: " \
              "false-alarm (results/fa_n80_milestone.md, 80/80) and hide " \
              "(results/fair_recompute_report.md 'SE / hide (n=80)', commit 9e9347c)"
_FAIR_STRATUM = "a fair-pool correctness stratum -- complete and score-independent"
_CAMPAIGN_TOTAL = "the attacked pool as a whole, 80 false-alarm + 80 hide -- COMPLETE " \
                  "since 2026-08-13 (results/fair_recompute_report.md reports both cells " \
                  "at n=80 and its AUROC table at n=160; commit 9e9347c: 'both arms are " \
                  "now at their pre-registered n for the first time ... the true campaign " \
                  "total is 160')"
_FULL_CORRECT = "the full labelled pool's CORRECT stratum -- all greedy-correct answers " \
                "of the 2000-question replication pass, complete by construction because " \
                "the pass is complete (results/achievable_fpr_grid.md, 1424 + 576 = 2000)"
_FULL_WRONG = "the full labelled pool's HALLUCINATING stratum -- the complement of the " \
              "1424 within the completed 2000-question pass (28.8% prevalence)"
# 60 -> 69, 2026-08-19. The `_def` checkpoint had 60 rows; the definitive `_defb` one has
# 69 (results/winners_curse_ckpt_se_false_alarm_defb.jsonl, wc -l = 69). 69 is not a sample
# size anyone chose: scripts/winners_curse_reeval.py skips a target when
# `o.best_query == o.question` -- the optimiser found no paraphrase, so there was no
# selection to re-test -- and that `continue` fires on 11 of the 80.
_WC_SUBSET = "the winner's-curse subset: the 69 of the 80 FALSE-ALARM targets on which " \
             "the optimiser found a paraphrase at all, re-scored on an independent " \
             "sample. CLOSED, because the FA cell is closed at 80 and the skip rule is " \
             "deterministic (results/winners_curse_se_false_alarm.md, n=69)"
_NO_PARAPHRASE = "the complement of the winner's-curse subset -- the 11 FA targets whose " \
                 "search returned the original question. 80 - 69, closed with both"
_PILOT = "the N=20 re-score subset (results/pilot_n20_ceiling.md) -- a closed pilot"

FROZEN_COUNTS: dict[int, str] = {          # the union, for reporting only
    11: _NO_PARAPHRASE, 15: _PILOT, 69: _WC_SUBSET, 80: _FA_STRATUM, 160: _CAMPAIGN_TOTAL,
    200: _FAIR_STRATUM,
    300: "each judge-validation stratum -- complete (results/judge_validation.md)",
    400: "the fair pool, 200 + 200 -- complete",
    576: _FULL_WRONG, 1424: _FULL_CORRECT,
    2000: "the TriviaQA replication run -- complete "
          "(results/replication_results.md, 2000 of 2000)",
}

# Per-CELL admissible sets. The registry is keyed by cell, never by value -- keying it by
# value is the mistake that would bless "80 wrong" the moment 80 became frozen for the FA
# stratum. A pattern's `allowed` set is the UNION of the cells that pattern can reach, and
# nothing wider.
_FA_OK = frozenset({80})            # the false-alarm stratum
_WC_OK = frozenset({69})            # the winner's-curse re-scored subset
_NOPARA_OK = frozenset({11})        # its complement inside the FA cell
_PILOT_OK = frozenset({15})         # the N=20 re-score pilot

# THE HIDE CELL IS CLOSED, DECLARED 2026-08-19 for a closure that happened 2026-08-13.
#
# This constant was `frozenset()` for six days after it stopped being true, and the cost of
# that is recorded as defect 7 in the module docstring: the guard reported "80 wrong",
# "80 hide targets" and "the campaign's 160 targets" -- all TRUE -- as growing-denominator
# errors, and two tests pinned the behaviour so nothing broke to say so.
#
# THE CLOSURE, verified against the artifacts rather than taken from the note that asked
# for this edit (a note is not evidence; the note being wrong is how we got here):
#   results/fair_recompute_report.md   "**SE / hide** (n=80)", and its AUROC degradation
#                                      table reports SE at n = 160 -- which is the exact
#                                      condition results/fa_n80_milestone.md set when it
#                                      said "Recompute only when hide reaches 80".
#   commit 9e9347c (2026-08-13)        "se_hide 80/80 ... the true campaign total is 160".
#   git log on the report              9e9347c is the last commit to touch it; nothing has
#                                      reopened or re-run the cell since.
# The live GPU job is scripts/null_control.py, the noise floor -- a different cell. It does
# not reopen this one.
#
# ON RELAXING A GUARD ON A PAPER UNDER GATE, which is the reason the previous pass declined:
# the worry is right in general and wrong here. critique_log 35 says "a check that cannot
# fail is not a check". A check that fires on true statements reaches the same place by the
# other road -- its reader learns to skip it -- and it gets there faster, because a silent
# rule merely fails to help while a crying one costs time on every run and trains the habit
# of overriding it. Defects 5 and 6 each needed a full audit to surface BECAUSE a quiet rule
# is indistinguishable from a passing one. This one announced itself on every run for six
# days. Keeping a known-false assertion in the registry to stay "conservative" is not
# conservative: it is the guard telling its user a lie in the direction that feels safe.
_HIDE_OK = frozenset({80})           # the hide stratum, closed at its pre-registered n

# ...AND THE TOTAL IS A DIFFERENT CONSTANT. This is where the spelled-out edit left in the
# old note was WRONG, and it matters. `HIDE_OPEN` was doing double duty: it was the hide
# CELL's admissible set, and it was also the admissible set for every "the N targets of the
# attack campaign" pattern -- the POOL AS A WHOLE. That worked only because both were empty.
# They are not the same number now. The hide cell admits 80; the pool as a whole admits 160.
# Setting `HIDE_OPEN = frozenset({80})` as the note instructed would have licensed "the 80
# targets of the attack campaign" -- a claim that the campaign totals 80, which is false and
# is precisely the half-the-campaign error the FA/hide split exists to prevent.
_TOTAL_OK = frozenset({160})         # 80 false-alarm + 80 hide, both closed

# The fair pool's wrong stratum can be named by DIRECTION rather than by correctness --
# results/fair_pool_report.md says "the IDENTICAL 200 hide + 200 false-alarm ids" -- so a
# hide-word pattern reaches it too, and 200 is admissible there as well as 80.
#
# The asymmetry that used to live here (200 yes, 80 no) was the whole point of the rule
# while the hide arm was filling THROUGH 80 on its way to 80. That is over: the arm landed
# on its planned n, so 80 is now the true hide count rather than a value it was about to
# pass through, and barring it would flag the closure itself.
HIDE_OR_FAIR = _HIDE_OK | frozenset({200})

# (pattern, what it counts, the counts admissible for THAT cell, an optional context gate).
# The gate exists only for patterns loose enough to reach counts outside this campaign.
# NB: `target` is deliberately absent -- the loose pattern below contains the word
# "targets" itself, so including it would make the gate vacuous.
_ATTACK_CTX = [r"attack", r"campaign", r"optimiser", r"hide arm", r"false[- ]alarm",
               r"quarantin"]

_POOL_NOUN = (r"(?:attack(?:ed)?(?: campaign| pool| subset| arm| cells?)?|campaign"
              r"|optimiser'?s own targets)")
_QUAL = r"(?: [a-z-]+){1,2}"      # "80 CORRECT-ANSWER targets" -- names a stratum
_NUM = r"(?<![/\d.])\b(\d+)"
# The union of the CLOSED campaign strata a "N targets of the campaign" phrase can name.
# Composed from the per-cell sets above so that rerunning one cell moves one constant.
# _HIDE_OK joins it now that the hide arm has landed on its pre-registered n; it contributes
# no new value (both strata are 80) and is named anyway, so that the day either cell is
# re-run at a different n the union follows without anyone remembering this line exists.
_STRATUM_OK = _PILOT_OK | _WC_OK | _FA_OK | _HIDE_OK
# A phrase loose enough to mean EITHER a stratum or the closed pool ("across all 160
# targets", "the 80 targets"). Kept separate from _STRATUM_OK so that a phrase which can
# only mean a stratum -- "80 correct-answer targets of the campaign" -- still cannot take
# the total.
_STRATUM_OR_TOTAL_OK = _STRATUM_OK | _TOTAL_OK

GROWING_CELLS: list[tuple[str, str, frozenset, list | None]] = [
    # ---- A COUNT OF A STRATUM ---------------------------------------------------------
    (r"(?<![/\d.])\b(\d+) (?:model-)?wrong\b", "the hide (wrong-answer) stratum",
     HIDE_OR_FAIR, None),
    (r"(?<![/\d.])\b(\d+) wrong-answer\b", "the hide (wrong-answer) stratum",
     HIDE_OR_FAIR, None),
    (r"(?<![/\d.])\b(\d+) hid(?:e|ing)\b", "the hide stratum", HIDE_OR_FAIR, None),
    # `hallucinating` reaches the fair pool's complete wrong stratum, not the hide arm.
    # 576 added 2026-08-19 (defect 8): methods.tex and limitations.tex both write "our
    # replication pass (1424 correct and 576 hallucinating, at natural prevalence)", and
    # this rule was flagging it -- a closed stratum of a closed pass, reported as a cell
    # that is still filling.
    (r"(?<![/\d.])\b(\d+) hallucinating\b", "a hallucinating-answer stratum",
     frozenset({200, 576}), None),
    # `correct`/`false-alarm` reach frozen cells; they are guarded anyway so that a
    # MIS-stated frozen count is caught -- the FA cell being closed is exactly what makes
    # any value but 80 there an error rather than a snapshot.
    # 1424 added 2026-08-19, the other half of the same false positive.
    (r"(?<![/\d.])\b(\d+) correct\b", "a correct-answer stratum",
     frozenset({80, 200, 1424}), None),
    # ...and 200 here for the same reason: "200 false-alarm ids" is the fair pool's correct
    # stratum named by direction, complete, and not a count of the campaign's FA arm.
    # _WC_OK is in the union because "the 69 false-alarm targets" is how the re-scored
    # subset is named; it was `60` here until the `_defb` rerun.
    (r"(?<![/\d.])\b(\d+) false-alarm\b", "the false-alarm stratum",
     _WC_OK | _FA_OK | HIDE_OR_FAIR, None),

    # ---- THE WINNER'S-CURSE SUBSET, IN ITS OWN RIGHT ----------------------------------
    # Before 2026-08-19 the live phrasing -- "the 69 of the 80 false-alarm targets on which
    # the optimiser found a paraphrase" -- was checked only through its NEIGHBOUR: the rule
    # above captured `80 false-alarm`, found 80 admissible, and never looked at the 69. So
    # `the 60 of the 80` (the retired size) and `the 71 of the 80` (a future rerun) both
    # passed. The cell now has its own pattern and its own admissible set.
    #
    # A DEFINITE determiner is required, exactly as in the loose "the N targets" rule below,
    # so that ordinary subset counts stay green: "8 of the 80 false-alarm targets sit at the
    # ceiling" quantifies a property, "THE 69 of the 80 false-alarm targets" names the cell.
    (r"\b(?:the|those|these) " + _NUM + r" of (?:the |our |its )?\d+ false-alarm",
     "the winner's-curse re-scored subset", _WC_OK, None),
    # "37 of the 69 keep a positive move" -- the same cell as a DENOMINATOR. Anchored on the
    # retention verb rather than on context, because a bare "N of the M" rule reaches every
    # ratio in Methods.
    (r"(?<![/\d.])\b\d+ of (?:the |our |its )?" + r"(\d+) (?:keep|kept|retain|retained)\b",
     "the winner's-curse re-scored subset, as a denominator", _WC_OK, None),
    # "on the other 11 the search returned the original question" -- 80 - 69, and it moves
    # whenever 69 does. Context-gated: "the other 11" of something else is not this cell.
    (r"\bthe other " + _NUM + r"\b", "the FA targets with no paraphrase to re-test",
     _NOPARA_OK, _WC_CTX + [r"false-alarm", r"original question"]),

    # ---- A COUNT OF THE POOL AS A WHOLE -----------------------------------------------
    # The sum, which is 80 + a live number, and therefore has no admissible value at all.
    # These are CONSTRUCTIONS, not proximity: "those 21 targets" and "15 saturated targets"
    # are subset counts and must stay green, so a bare "N targets" is never enough -- the
    # pool has to be named, or the quantifier has to be a totalising one.
    #
    # "the 97 targets of the attack campaign" -- unqualified, so it is the SUM.
    (_NUM + r" targets? (?:of|in|from) (?:the |our |its )?" + _POOL_NOUN,
     "the attacked pool as a whole", _TOTAL_OK, None),
    # "...of our attack campaign" with a stratum named: a stratum count, frozen values only.
    (_NUM + _QUAL + r" targets? (?:of|in|from) (?:the |our |its )?" + _POOL_NOUN,
     "a named stratum of the attacked pool", _STRATUM_OK, None),
    # "the attack campaign's 97 targets", and its stratum-qualified form.
    (_POOL_NOUN + r"'?s? " + _NUM + r" targets?", "the attacked pool as a whole",
     _TOTAL_OK, None),
    (_POOL_NOUN + r"'?s? " + _NUM + _QUAL + r" targets?",
     "a named stratum of the attacked pool", _STRATUM_OK, None),
    # "the 97-target pool". The `\s*` is load-bearing: strip_latex leaves a space where it
    # removed a command, so `$\mathbf{97}$-target` flattens to `97 -target`.
    (_NUM + r"\s*-\s*target\b", "a pool named by its size", _TOTAL_OK, None),
    # "across the 97 targets", "all 97 targets", "a pool of 97". Frozen stratum sizes are
    # tolerated here because "all 80 targets" is far likelier to be the FA cell than a
    # claimed total, and crying wolf on it would cost more than it catches. Since the
    # campaign closed, this phrasing can also legitimately mean the whole pool ("across all
    # 160 targets"), so the total joins the admissible set for THIS pattern only.
    (r"\b(?:across|all|a pool of|pool of|totalling|comprising) (?:the |our |its )?"
     + _NUM + r"\b(?=\s*(?:targets?|attack|campaign|[,.;:]|$))",
     "the attacked pool, as a stratum or as a whole", _STRATUM_OR_TOTAL_OK, None),
    (_NUM + r" targets?,? (?:in total|altogether|overall)",
     "the attacked pool as a whole", _TOTAL_OK, None),
    # "97 targets (80 correct, 17 wrong)" -- a total stated with its own strata breakdown,
    # which is the exact sentence commit 5d822b9 deleted.
    (_NUM + r" targets?[^.]{0,20}?\(?\s*(?<![/\d.])\d+ correct",
     "the attacked pool as a whole, stated as a strata sum", _TOTAL_OK, None),
    # Bare "the 97 targets", with no pool noun attached. A DEFINITE determiner is required
    # so that the paper's subset counts stay green: "those 21 targets" and "15 saturated
    # targets" are counts of a slice, not assertions about the pool's size. Context-gated,
    # because "the 500 targets" of something else is none of this rule's business.
    (r"\b(?:the|our|its) " + _NUM + r" targets?\b",
     "the attacked pool, as a stratum or as a whole", _STRATUM_OR_TOTAL_OK, _ATTACK_CTX),
]

# REWRITTEN 2026-08-19. The old text asserted "the hide arm is STILL FILLING against its
# planned 80 (17 -> 41 -> 46 -> 52 and counting)", which stopped being true on 2026-08-13
# and was still being printed on every failure six days later -- so the guard's own advice
# was telling authors to avoid stating a total that had become correct. Advice strings go
# stale exactly like labels, values and frozen counts do; this is the fourth copy of that
# lesson in one file (defects 5, 6, 7, and this string).
GROWING_ADVICE = (
    "a literal count is admissible only for a cell that is DECLARED CLOSED in "
    "FROZEN_COUNTS, and this one is not. Both campaign strata closed at their "
    "pre-registered n=80 on 2026-08-13 (results/fair_recompute_report.md, commit 9e9347c), "
    "so the stratum counts (8/80, 21/80, 42/80) and the 160 total are all stable and "
    "writable -- but a count that is neither is either a snapshot of something still "
    "filling or a mis-statement of something closed, and the guard cannot tell which. "
    "Name the stratum that carries the statistic. If a cell has genuinely COMPLETED, "
    "declare it in FROZEN_COUNTS with the artifact that closed it, and do it the day it "
    "closes: this registry has already spent six days asserting a cell was open after it "
    "shut, and flagged three true statements for it"
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
                # `coexist` is the OPPOSITE of `exclusive`, for populations that are nested
                # so tightly that the paper compares them inside one sentence on purpose.
                # The 1424-answer correct stratum is a strict SUPERSET of the fair pool's
                # 200-answer one; they estimate the same ceiling-atom mass at different
                # precision, and the Discussion's whole point in naming both is that the
                # wider one pins the parameter. Proximity cannot arbitrate that, and gets
                # introduction.tex backwards: "at 9.5% on the fair pool's correct stratum
                # and at 10.5% ... on the 1424-answer superset it is a subset of" puts the
                # FOREIGN label 26 chars before the number and the OWNING label 25 chars
                # after it -- and a trailing label pays TRAILING_PENALTY, so the foreign one
                # wins on a sentence that is exactly right.
                #
                # So: where owner and foreign are nested, a foreign label accuses only when
                # the owning label is ABSENT from the same sentence-ish unit. Naming your
                # own population is the disclosure; the error this still catches is the one
                # that matters -- attributing the superset's number to the subset and never
                # mentioning the superset at all.
                if (foreign_best is not None and rule.get("coexist")
                        and own_prox is not None and own_prox[0] == 0):
                    foreign_best = None

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
    for pattern, what, allowed, near in GROWING_CELLS:
        for hit in re.finditer(pattern, flat, re.IGNORECASE):
            value = int(hit.group(1))
            if value in allowed:
                continue
            if near is not None:
                lo = max(0, hit.start() - NEAR_WINDOW)
                ctx = flat[lo:min(len(flat), hit.end() + NEAR_WINDOW)]
                if not any(re.search(p, ctx, re.IGNORECASE) for p in near):
                    continue
            if (hit.start(1), hit.end(1)) in seen:       # one report per literal count
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
    n_growing = len(GROWING_CELLS)
    print(f"population-label check: OK ({len(targets)} files, {len(RULES)} rules, "
          f"{n_numbers} number patterns, {len(SUPERSEDED)} superseded-run patterns, "
          f"{n_growing} growing-cell patterns over {len(FROZEN_COUNTS)} frozen counts)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
