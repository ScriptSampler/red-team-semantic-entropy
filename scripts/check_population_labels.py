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

  * NEW WITH TIER 2 (2026-08-26), and the last three are the ones to watch:
  * OUTSIDE paper/, A MISLABELLED POPULATION IS INVISIBLE. `results/` and `scripts/` are
    checked ONLY for the retired positions. `0.704` attributed to the attacked pool in a
    generated report passes, and so does a growing hide count. That is not an oversight; it
    is the (a)/(b) argument above. It does mean a defect can be authored in a generator,
    survive there, and be caught only when it reaches the paper -- one step later than a
    reader of this file might assume.
  * `_` IS NOT FLATTENED (see `strip_plain`), so markdown underscore emphasis inside a
    guarded phrase -- `the _estimand_ dissolves` -- breaks `\\b` and is not seen. `*` is
    flattened, which is the marker the sixteen sites actually used. Cheap to add `_` and
    expensive to be wrong about it: it is the word separator in every path and identifier
    this repo cites.
  * SENTENCE GEOMETRY IS LOOSER IN A TABLE THAN IN PROSE, and it cuts the other way from
    everything else here. `_TERM_RE` finds no boundary in `| N=40 | 0.27% | 53.7% |`, so
    the `absent` window is bounded only by ABSENT_CHAR_CAP -- 600 characters each side
    instead of one sentence. A stray "calibrated" 500 characters up the page therefore
    EXCULPATES a bare coverage figure in a table that has nothing to do with it. A false
    negative, not a false positive, and it is why the tier-2 tests plant their probes in
    tables as well as in prose.
  * THE RATCHET COUNTS, IT DOES NOT IDENTIFY. A file at its baseline that fixes one site
    and introduces another stays green. `check_operational_provenance.py` has the same
    hole and it is inherent to a count; `--dry-run` beside `git diff` is the only answer,
    and it is worth the two minutes on any commit that touches a pinned file.

--------------------------------------------------------------------------------------
SCOPE (2026-08-26, widened 2026-08-27). WHY IT IS NOT THE SAME RULES EVERYWHERE.

Until today this file read eight `paper/*.tex` files and nothing else. Every one of the
SIXTEEN sites found by the 2026-08-26 sweep -- the ones that carry no digit -- was in
`results/`, `scripts/`, `tests/` or `figures/` (commit 852e0f7). So the ledger could not
see the places the defect actually lives -- the same gap `docs/critique_log.md` line 2441
and `results/morning_review_2026_08_19.md` line 316 both name in the same words: "the
linter's scope is eight `.tex` files, so it cannot reach `tests/`". Checked, not recalled. Scope is now two tiers, and the split is
MEASURED, not asserted. Every count below comes from `scope_census()` over the 228 tier-2
files (234 reached by WIDE_GLOBS, 6 excluded by name) and is REPRODUCIBLE: run the script
with `--dry-run` and it prints the same table. Numbers that cannot be re-derived are how
this project got here; a figure quoted from a session nobody can replay is a figure on
trust, and this file has spent two rounds paying for that.

  TIER 1, `paper/*.tex` and `paper/sections/*.tex`: EVERY rule. Unchanged, byte for byte.

  TIER 2, `README.md` and `results/ scripts/ tests/ figures/ docs/ src/` (.md .py .sh
  .json): the RETIRED POSITIONS ONLY -- the twelve rules armed on the 2026-08-26 ruling,
  whose `replacement` is a position (`_NOT_IDENTIFIED`, `_COVERAGE_PAIR`) rather than a
  recomputed value, PLUS the estimator-ownership table. Selected by the `wide` flag on a
  SUPERSEDED entry, pinned to the position/recomputation distinction by
  test_the_wide_set_is_exactly_the_position_rules. Ownership qualifies by the same
  property -- its finding is "this row takes neither", never "the definitive run gives X"
  -- and is counted inside the `retired-position` census row so the census and the ratchet
  cannot disagree.

WHAT STAYS SCOPED TO .tex, AND WHY. Three families, three separate reasons, all three
measured before they were decided:

  (a) THE POOL / ATTACHMENT RULES (`_check_pools`, 16 rules, 78 number patterns) --
      736 findings in 52 files. NOT a backlog: a category error. These rules arbitrate
      between a number's OWN label and a FOREIGN one by counting SENTENCE BOUNDARIES and
      characters. A markdown table row has no sentences (`_TERM_RE` needs `[.:;!?]` before
      whitespace, and `| 1e-05 | 1.380 | 9.50% |` has none), so a whole generated table is
      one sentence; Python source has no sentences at all.
      `results/likelihood_weight_sensitivity.md` alone yields 65 findings off one table --
      12 copies of `9.5%`, 11 of `21.5%`, 4 of `1.380` -- whose population is declared in
      the prose above it and nowhere a proximity rule can reach.
      `scripts/replay_control.py` yields 30, mostly inside `log(...)` calls whose
      population is named hundreds of characters away in a DIFFERENT `log(...)`.
      They are also barely locatable: `_line_hint` returns the FIRST source line carrying
      the token, and a generated table repeats its values on every row, so 30 of that
      file's 65 findings point at line 59 and 27 more at line 30. Running these outside
      .tex is the permissive-direction failure -- a guard nobody can keep green.

  (b) THE GROWING-DENOMINATOR RULE (`_check_growing`) -- 73 findings in 36 files.
      Table-hostile for the same reason, plus a second: outside the paper the repo
      legitimately RECORDS open cells. `results/attack_matrix.md` (4) is a week-6 snapshot
      whose "15 hide" was true when written; `results/schedule_2026_08_19.md` (7) yields
      "12-target" and "40-target", which are BUDGETS (N=40) and not campaign cells at all,
      matched by the `-target` noun. A dated snapshot of a filling cell is history; the
      rule exists to stop a filling cell being quoted FORWARD, and forward is `paper/`.

  (c) THE RETIRED-VALUE HALF OF SUPERSEDED (29 of the 41 entries) -- 274 findings across
      39 files, and this is the one worth reading twice, because the temptation is to
      widen it. A retired VALUE is a fact about a run, and outside `paper/` this repo
      legitimately restates one in three distinct ways, which are the top offenders in the
      census:
        - it STORES the superseded run's own output. `results/winners_curse_partial.md`
          (18 findings) is the `_def` checkpoint's report. Its numbers are correct FOR
          THAT RUN. Flagging it is flagging a measurement for having been measured.
        - it PINS the value in order to assert its ABSENCE. `tests/
          test_derived_paper_quantities.py` (11) carries the banned-literal list
          `(r"2.0\\% [0.8, 5.0]", r"[0.78, 5.03]", ...)` -- the check that keeps those
          numbers out of the paper. Widening here means the guard flags the guard.
        - it RECORDS the correction. `results/morning_review_2026_08_19.md` (35),
          `results/ceiling_saturation_finding.md` (20),
          `results/post_overnight_claim_review.md` (19).
      A retired POSITION has no such legitimate use: no file has any reason to ASSERT that
      the estimand dissolves. The innocent restatements are quoting-to-disown and the
      ledger / ruling / history files, which are named in OUT_OF_SCOPE below. That
      asymmetry -- values are stored, positions are only ever claimed -- is the whole of
      the tier-2 line, and it is exactly the distinction today's defect demonstrated.

      THIS PARAGRAPH USED TO SAY quoting-to-disown was handled by "the `denial` gate
      already", and it was not: the register this file shipped with pinned SIX findings
      and classified all six as quoting-to-disown that the gate could not reach. A
      docstring asserting a capability its own register records as absent is the same
      object as an untagged operational number -- a claim with no evidence behind it,
      standing where a reader will trust it. The gate was rebuilt on 2026-08-27 to make
      the sentence true rather than the sentence softened to make the gate excusable, and
      all six went green with no file but this one changing. See the block above
      `_is_disowned` for the three constructions and their costs.

--------------------------------------------------------------------------------------
THE RATCHET (2026-08-26), and why widening could not simply go green.

Widening scope surfaces a BACKLOG that has nothing to do with whoever widened it. This
repo has already decided how to hold one: `scripts/check_operational_provenance.py`
records a per-file count of known-open findings in `KNOWN_OPEN`, and fails when a file
GAINS one -- so the arriving backlog is PINNED rather than SILENCED, and any new defect
still fails the build. That device is followed here rather than reinvented, down to the
failure in the other direction: a file that drops BELOW its baseline also fails, because a
register that can only be raised rots upward. The counts, and what each one is, are in
KNOWN_OPEN below; there are 26 across 5 files -- 736 + 73 + 274 findings avoided by the
scoping above, and 26 held. It was 32 across 7 on 2026-08-26; the six that left were false
positives on correct writing, cleared by rebuilding the disowning gate rather than by
lowering a pin, and KNOWN_OPEN says so per file.

WHAT A BASELINE IS NOT. It is not an opinion that the site is fine. Two of the five files
carry a LIVE, uncorrected assertion of a position section 13 retracts, and the ratchet
records exactly that rather than hiding it. The honest way to lower an entry is to fix the
site and lower the number in the same commit. The dishonest way is to raise the number,
and the failure message says so in those words, because the pressure to do it arrives at
exactly the moment the suite goes red.

Run: python scripts/check_population_labels.py             (exit 1 on any problem)
     python scripts/check_population_labels.py --dry-run   (per-file counts, exit 0)
"""
from __future__ import annotations

import re
import sys
from bisect import bisect_left
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
PAPER = REPO / "paper"

# --------------------------------------------------------------------------------------
# TIER 2 SCOPE. Globs relative to the repo root; order is display order. Only the RETIRED
# POSITIONS run here -- see the SCOPE section of the module docstring for the measurement
# behind every one of these choices.
#
# NOT RECURSIVE, deliberately. `results/**/*.md` would pull in whatever a future run drops
# in a subdirectory, and a guard whose scope grows on its own cannot have a ratchet: the
# baseline would move without anyone editing anything. A new subdirectory is a decision and
# gets a line here.
#
# THE SUFFIXES ARE THE PROSE-BEARING ONES. .md, .py, .sh and .json are where all sixteen of
# the 852e0f7 sites lived -- reports, generators, wrappers and figure sidecars. Deliberately
# absent: .jsonl and .csv (run checkpoints and audit tables; machine records that no one
# reads a claim out of), .log, and .txt (`results/env_check.txt` is captured tool output).
# Add one when a claim is found in it, not in advance.
# (This paragraph appeared TWICE here, verbatim, until 2026-08-27. Nothing turned on it and
# nothing caught it, which is a small argument for reading a comment block through once
# before adding to it.)
#
# THE GAPS CLOSED ON 2026-08-27, each decided by measurement rather than by symmetry:
#   `README.md`             the repo's front door. Nothing in it today, but it is the most
#                           read-FORWARD file here, and forward is the whole of the scope
#                           test. In scope on the principle, at zero cost.
#   `results/figures/*.json` `figures/*.json` was in scope and this sibling directory was
#                           not, for no reason anyone recorded. Sidecars are exactly where
#                           a withdrawn interval gets stored next to a plot.
#   `src/*.py`, `src/se/*.py`, `src/se/attacks/*.py`
#                           the library, 25 files, listed one directory at a time because
#                           `src/**/*.py` is the recursive form this comment refuses. It
#                           reports 0 findings today; it is in scope because a claim
#                           authored in the library reaches the paper the same way a claim
#                           authored in a generator does, and `scripts/` is already here on
#                           that argument. Measured before adding, so this is a decision
#                           and not an enthusiasm.
# Still deliberately absent: `notebooks/` (scratch, not read forward), `configs/*.json`
# (settings, no prose), `dashboard/` and `vendor/` (not ours).
WIDE_GLOBS = (
    "README.md",
    "docs/*.md",
    "figures/*.md", "figures/*.json",
    "results/*.md", "results/*.json",
    "results/figures/*.json",
    "scripts/*.py", "scripts/*.sh",
    "src/*.py", "src/se/*.py", "src/se/attacks/*.py",
    "tests/*.py",
)

# Out of scope BY NAME, each for a stated reason. Every one of these files contains the
# retired positions on purpose; none of them asserts one.
#
# The first two are the SELF-REFERENCE pair. This file holds every retracted sentence as a
# regex AND as prose in `quantity` ("...described as 'the resolution of the pool'"), so
# scanning it reports findings manufactured entirely out of its own rules; its test file
# plants each defect deliberately, once per probe. Neither is left unguarded by the
# exclusion: the ledger's advice strings -- the part other files are told to quote -- are
# re-run through the rules by test_the_ledgers_own_advice_passes_the_rules_it_gives, and
# blinded to prove that green is not luck; the exclusion itself is proved load-bearing by
# test_the_checker_does_not_flag_its_own_rule_patterns, and shown to conceal nothing
# executable by test_the_checkers_own_findings_never_land_on_executable_code.
#
# The other three follow `check_operational_provenance.py`'s precedent verbatim, including
# its wording: rewriting history to satisfy a linter is worse than the disease, and the
# danger from a log was never that it CONTAINS a dead claim but that the claim gets quoted
# FORWARD. Forward is where the scope is.
#
# NO COUNTS IN THESE REASONS, AND THAT IS THE 2026-08-27 FIX. Every one of them carried a
# figure -- "39 tier-2 findings", "53", "9", "under all 37 they are 85, 145, 91 and 31" --
# and four of the eight had gone stale within a day of being written: measured on the same
# files, the true numbers were 41 and 101 and 86. They went stale for the reason every
# hand-maintained number in this file goes stale, which the module docstring calls defect 5,
# 6 and 7 and then committed a fourth time here. A count of findings is a function of the
# RULES, and the rules change more often than the prose does.
# So the reasons state the ARGUMENT, which does not expire, and `--dry-run` prints the live
# count beside each excluded file, which cannot.
OUT_OF_SCOPE: dict[str, str] = {
    "scripts/check_population_labels.py":
        "this ledger. It holds every retired sentence as a pattern AND restates each one "
        "in prose in its own `quantity` field -- \"...described as 'the resolution of the "
        "pool'\" -- so it matches itself by construction, and every finding it yields is "
        "manufactured out of its own rules. TWO COMPENSATING CONTROLS, because the "
        "exclusion is real and so is the hole in it: "
        "test_the_ledgers_own_advice_passes_the_rules_it_gives re-runs the advice strings "
        "through the rules and then re-runs them BLINDED to prove the green is not luck; "
        "and test_the_self_excluded_files_have_not_gained_a_retired_position pins the "
        "whole-file count, so a NEW assertion added to this file's prose fails the suite "
        "the way it would in any other file. A count does not identify -- the same "
        "limitation the main ratchet records -- and it is what an exclusion can afford.",
    "tests/test_population_labels.py":
        "this ledger's probes: every defect planted on purpose, once per rule. A probe that "
        "stopped matching would be a dead test, not a clean file. Same count pin as above, "
        "and for the same reason: the exclusion must not also excuse a new claim.",
    "docs/critique_log.md":
        "append-only history -- the same call, and the same reason, as "
        "check_operational_provenance.py's. Its findings are all in dated entries. "
        "Commit 852e0f7, which fixed the sixteen live sites, left these alone in those "
        "words: rewriting a timestamped record to match today's understanding destroys the "
        "audit trail. The danger from a log was never that it CONTAINS a retracted claim "
        "but that the claim gets quoted FORWARD, and forward is paper/ and the live "
        "generators, both of which are in scope.",
    "results/n40_floor_estimator_ruling.md":
        "the adjudication that DID the retracting. Its findings are the withdrawn "
        "positions being quoted in order to withdraw them, plus the branch table "
        "the rest of the repo is told to cite. Scoping it in would mean the guard's own "
        "evidence file may not cite its own evidence -- the call "
        "check_operational_provenance.py makes for results/operational_number_audit.md.",
    "results/OVERNIGHT_2026-07-02.md":
        "append-only run log -- a timestamped record of what a night produced, the same "
        "class as the critique log and excluded by name in check_operational_provenance.py "
        "too. It reports nothing today, so this entry buys nothing NOW and is "
        "here on the principle rather than on the count: a log that later quotes a "
        "retracted position is recording history, and rewriting it to satisfy a linter "
        "destroys the audit trail.",
    "results/OVERNIGHT_2026-07-05.md":
        "append-only run log; identical reasoning to the 07-02 entry above.",
}

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
# IS THIS SENTENCE DISOWNING THE CLAIM?  (2026-08-27, replacing a proximity test)
#
# WHAT WAS THERE AND WHY IT WAS THE WRONG QUESTION. `denial` used to be `_is_non_binding`
# unchanged: "does any of not / never / nor / than / rather than / drawn from sit in the
# 30 characters before this?" That is the right question for a POOL LABEL, where the cue
# genuinely modifies the label ("unlike the fair pool's 0.704"). It is the wrong question
# for a retired POSITION, because a position is disowned by a CONSTRUCTION and not by the
# presence of a negative word, and the two come apart in both directions. Measured on the
# guard as it shipped:
#
#   FALSE NEGATIVE  "The reason is not obvious, but the estimand dissolves once the
#                   ceiling atom empties."            -> GREEN. The `not` denies the
#                   obviousness of the reason; the clause after `but` asserts the
#                   retracted position flatly, and the gate cannot tell.
#   FALSE NEGATIVE  "It is worse than that -- the estimand dissolves..."  -> GREEN, on the
#                   `than` of a comparison that has nothing to do with the claim.
#   FALSE POSITIVE  "The estimand doesn't dissolve."  -> RED, while "does not dissolve" is
#                   green. NON_BINDING_CUES carries no contraction at all, and the
#                   `\bn't\b` written into the estimand rule's tempered gap was DEAD: the
#                   `n` of `doesn't` is preceded by a word character, so `\b` cannot match
#                   there. A guard that reddens a denial because of an apostrophe is the
#                   false positive this file's own threat model ranks above every miss.
#
# SO ASK THE QUESTION DIRECTLY. Three constructions disown a proposition in the prose this
# repo actually contains, and the gate tests for those three rather than for a word:
#
#   D1  THE CLAIM'S OWN VERB IS NEGATED. The negator sits INSIDE the matched span:
#       "the estimand does not dissolve", "doesn't dissolve", "never dissolves". This is
#       the case the tempered gap was reaching for, done where it can see a contraction.
#
#   D2  THE MATRIX IS NEGATED, IN THE SAME CLAUSE. "It is not that the estimand
#       dissolves", "It does not follow that a larger pool reports a smaller floor",
#       "nothing here says the estimand dissolves". The scope runs back to the nearest
#       CLAUSE break rather than a fixed 30 characters -- and clause is the whole of the
#       fix, because `, but`, ` -- ` and a bare coordinating conjunction all START a new
#       clause, which is exactly where the two false negatives above put the assertion.
#
#   D3  THE CLAIM IS ATTRIBUTED TO A PAST STATE OF THE TEXT, IN ORDER TO BE WITHDRAWN.
#       `This banner said "the estimand stops existing when the ceiling atom empties"
#       until 2026-08-26; sec. 13 retracts that`. Every corrected file in this repo
#       records what it used to say in that shape, and the previous gate could not reach
#       ANY of them -- its lookback ran backwards and the disavowal follows the
#       quotation. Six of the 32 findings the ratchet pinned on 2026-08-26 were exactly
#       this, pinned because the gate could not see them; the module docstring meanwhile
#       asserted the gate "already handles" quoting-to-disown. It does now.
#
# D3 REQUIRES TWO KEYS, and that is deliberate. The note the previous round left says a
# gate that read "said X ... retracts that" would also read "said X" alone, and it would:
# a bare attribution is how a claim gets repeated, not how it gets withdrawn. So D3 needs
#   (i)  the claim to sit inside a QUOTATION, or to follow a PAST-TENSE attribution in the
#        same sentence ("said", "carried", "used to give", "went on saying") -- and past
#        tense is the discriminating half. A correction note reports what the text USED to
#        say; a stale brief asserts in the present. `says`, `states` and `asserts` are
#        deliberately absent for that reason, so "The ruling states that the N=40 floor
#        takes the question bootstrap" gets no exculpation from the citation.
#   (ii) a DISAVOWAL marker within a sentence either side -- a retraction, a withdrawal,
#        a supersession, or a dated "until YYYY-MM-DD".
# `This banner said "the estimand stops existing"` with nothing else in the paragraph
# stays RED, and there is a control on it.
#
# THE QUOTATION TEST IS OVERLAP, NOT CONTAINMENT, and that was measured rather than
# guessed: the three correction notes in this repo that record a WRONG-ESTIMATOR defect
# write it as `... said the measured N=40 floor takes "Wilson on the count" for a whole
# round after the ruling withdrew both candidates`, where the quotation opens in the
# middle of the matched phrase. Containment sees no quotation there at all.
#
# WHAT IT COSTS, stated rather than discovered:
#   * A disowning spread across two clauses is now flagged. "This is not our position. We
#     hold that the estimand dissolves" was green under the old gate only by accident (the
#     full stop already clipped it); "It is not our position, but the estimand dissolves"
#     is now RED and a human would call that a fair reading of the sentence.
#   * `\bno\b` is NOT a negator here, and the omission is load-bearing rather than an
#     oversight: the index case reads "a count at NO FIXED THRESHOLD at all and takes the
#     question bootstrap", and a gate that treated bare `no` as a denial would exculpate
#     the one sentence this whole round exists to catch. `nothing`, `no longer` and
#     `neither` are in, because each of them negates a proposition rather than a noun.
#   * D3 can be bought with a quotation plus an unrelated "correction" in the next
#     sentence. Narrow, and cheaper than the six false positives it removes.
# --------------------------------------------------------------------------------------
# A negator that negates a PROPOSITION. See the note above for why bare `no` is absent.
_NEGATOR = (r"(?:\bnot\b|\bnever\b|\bnor\b|\bno longer\b|\bnothing\b|\bneither\b"
            r"|\bnone\b|n['’]t\b|\bfails? to\b|\bdenies\b|\bdeny\b|\brefus\w+\b)")
# ...and a contrastive frame, which disowns without negating.
_CONTRAST = (r"(?:\brather than\b|\binstead of\b|\bas opposed to\b|\bfar from\b"
             r"|\bother than\b|\bunlike\b|\bmistaken\w*\b|\bwrongly\b)")
_DISOWN_RE = re.compile(_NEGATOR + "|" + _CONTRAST, re.IGNORECASE)

# Where a clause starts. Sentence terminators (the same set `_TERM_RE` uses, so the two
# cannot drift), a dash aside, a bracket, and a coordinating conjunction with or without
# its comma. `and` is in the list: "The atom is not full and the estimand dissolves"
# asserts the position in its second clause, and the first clause's `not` is about the
# atom.
_CLAUSE_BREAK_RE = re.compile(
    r"[.:;!?](?=\s)"
    r"|\s(?:--+|[–—])\s?"
    r"|,\s*(?=(?:but|yet|and|so|though|although|however|while|whereas|because|since)\b)"
    r"|\s(?=(?:but|yet|however|whereas|although|though)\b)"
    r"|\s(?<=\s)and(?=\s)"
    # A TABLE CELL WALL IS A CLAUSE BOUNDARY, and this repo is mostly tables outside
    # paper/. Without it, `| the subset-averaged replayed floor (...) | the questions only
    # | a bootstrap over questions only | | the measured N=40 floor | ... |` reads as one
    # clause, and the estimator-ownership rule binds a phrase in one cell to a row name in
    # the NEXT ROW -- measured, on results/replay_control.md's own summary table, which is
    # correct as written.
    r"|\|"
    # ...and so is a code-comment marker. `strip_plain` collapses newlines, so a `.py` file
    # arrives here as one unbroken line and a comment inherits the clause of whatever
    # statement precedes it. Measured: `assert " ".join(b.split()) NOT in paper, "..."`
    # followed by `# the estimand dissolves` exculpated the comment on the `not` of the
    # assertion above it.
    r"|#+"
    r"|[()\[\]]",
    re.IGNORECASE)

# The claim is being withdrawn, not repeated. One of these must accompany a quotation
# before D3 exculpates it.
_DISAVOWAL = [
    r"\buntil \d{4}-\d{2}-\d{2}\b", r"\bretract\w*", r"\bwithdraw\w*", r"\bwithdrew\b",
    r"\bwithdrawn\b", r"\bused to\b", r"\bpreviously\b", r"\bformerly\b",
    r"\bno longer\b", r"\bsupersede\w*", r"\bretire[ds]?\b", r"\bstruck\b",
    r"\bdeleted\b", r"\bcorrect(?:ed|ion|ions)\b", r"\bwas wrong\b", r"\bis wrong\b",
    r"\bmust not\b", r"\bdo not (?:restate|print|write|say|quote|reinstate)\b",
    r"\bsec(?:tion)?\.?\s*13\b", r"\bsec(?:tion)?\.?\s*2\b", r"\bbanned\b",
    r"\bforbid\w*", r"\bdead claim\b", r"\bhad been changed\b", r"\bchanged to\b",
    r"\bthe defect\b", r"\bcontradict\w*", r"\bdisagree\w*", r"\bnothing caught it\b",
]
_DISAVOWAL_RE = re.compile("|".join(_DISAVOWAL), re.IGNORECASE)

# PAST-TENSE ATTRIBUTION. What a correction note reaches for when it reports what the text
# used to say. The present-tense reporting verbs (`says`, `states`, `asserts`, `claims`)
# are DELIBERATELY ABSENT -- they are how a live claim is cited, and admitting them would
# let "the ruling states that the N=40 floor takes the question bootstrap" buy its own
# exculpation off a nearby word.
_ATTRIBUTED = re.compile(
    r"\b(?:said|read|carried|gave|stated|instructed|told|wrote|printed|reprinted"
    r"|named|claimed|asserted|proposed|concluded"
    r"|used to \w+|went on \w+ing|had \w+ed|was \w+ing|previously \w+)\b",
    re.IGNORECASE)

# A quoted stretch. `"` and the curly pair only: `'` is an apostrophe far more often than
# a quotation mark in this repo's prose, and backticks are already gone by the time the
# plain flattener is done with them.
_QUOTE_RE = re.compile(r"[\"“][^\"“”]{0,600}[\"”]")


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

# --------------------------------------------------------------------------------------
# THE WITHDRAWN N=40 FLOOR INTERVALS (2026-08-19).
#
# `results/n40_floor_estimator_ruling.md` withdrew BOTH candidate intervals for the
# measured N=40 achievable false-alarm floor. The reason is NON-IDENTIFICATION and it uses
# no population model: once the ceiling atom empties, whether the pool's top rung is the
# population's top rung is undecidable at n=200, and the two readings differ by more than
# two orders of magnitude.
#
# The coverage pair often quoted here is branch-conditional and was corrected on
# 2026-08-26 (ruling sec. 8.4, nominal 95%): under the calibrated Ewens fit Wilson covers
# 53.67% and the question bootstrap 0.00%; under the zero branch, 95.06% and 100%. This
# comment previously gave the first pair alone and said "the estimand is [broken], once
# the ceiling atom empties" -- sec. 13 retracts that, since it holds in one branch only.
# The paper now prints the point, 2.0%, with no interval, and carries the at-cap mass
# 0/200 = 0.0% [0.0, 1.9] as the quantity that does have one -- valid in BOTH branches.
#
# WHY HERE AND NOT ONLY IN `derived_paper_quantities.py`. That script pins the literals it
# knows about, site by site, and it is the right guard for "this exact string came back".
# It is the wrong guard for "this VALUE came back in some other markup" -- and the reason
# these four are armed at all is that the digit `5.03` survived a whole round of edits
# unguarded. `PCT` is a REQUIRED percent sign, so the fair-pool rule's `\b5\.0\\?%` cannot
# match `5.03`; it never could, and the concession turned on that digit at three sites.
#
# ARMED AS PAIRS WHERE THE ENDPOINTS ARE COMMON, on this file's standing precedent
# (`\b9\.0\s*,\s*12\.2`). `0.5`, `4.0`, `0.8` and `5.0` are all live numbers elsewhere in
# the paper; only their ADJACENCY is the retired interval. `5.03` and `0.78` are unique to
# this interval and are armed alone -- `0.78` with a lookahead, because `0.787` is the
# score-coupled replication AUROC and is a different number entirely.
# --------------------------------------------------------------------------------------
# THE REPLACEMENT POSITION, shared by every word rule below so that the six renderings of
# one claim cannot drift apart in what they say about it -- the same reason
# `_DISTINCT_COUNT_ADVICE` is shared by its two generative patterns.
_NOT_IDENTIFIED = (
    "tau_top is NOT IDENTIFIED at n=200, and that is the finding rather than a weaker "
    "version of it. 2.0% is the cheapest alarm 200 correct answers can EXHIBIT; whether "
    "it is also the population's floor turns on whether the population can ever produce "
    "39 mutually inequivalent answers out of 40, and 0/200 is the modal outcome under "
    "both branches, so the sample cannot choose. The two readings differ by more than two "
    "orders of magnitude. State the dichotomy or state neither branch -- and note that "
    "the retraction does NOT license the opposite claim either: the deep-tail misfit "
    "widens the estimand's range in both directions at once. "
    "See results/n40_floor_estimator_ruling.md sections 1 (M5), 2, 8.4 and 13"
)

# The coverage numbers are TRUE. What is retracted is quoting them bare. This string is
# written so that it PASSES the two rules it advises on -- it names the branch in the same
# sentence as each figure -- and a test pins that, because a ledger whose own advice would
# fail its own rule is a ledger nobody can quote from.
_COVERAGE_PAIR = (
    "coverage for the two withdrawn candidates is BRANCH-CONDITIONAL and must never "
    "travel without the population it was measured under (ruling sec. 8.4, nominal 95%): "
    "under the calibrated Ewens fit Wilson covers 53.67% and the question bootstrap "
    "0.00%, while under the zero branch the same two cover 95.06% and 100%. Name the "
    "branch in the same sentence, or give the model-free reason instead -- tau_top is not "
    "identified at n=200. See results/n40_floor_estimator_ruling.md sections 8.4 and 13"
)

# WHAT COUNTS AS STATING THE OTHER BRANCH. This list is the whole of the conditional
# awareness, so its two failure directions are worth naming rather than discovering.
#
# TOO NARROW and the guard reddens a correct passage, which is the failure mode that gets
# a guard switched off. TOO BROAD and it becomes a magic word: write "if" anywhere in the
# sentence and the retracted claim goes green. The compromise drawn here is that a bare
# `\bif\b` is NOT enough -- the conditional has to be about the thing in dispute, so the
# `if` entries name their subject. Checked rather than asserted: all FIVE passages in
# this repo that state the dichotomy correctly -- discussion.tex, n_scaling_grid.md,
# make_floor_budget_figure.py, n_scaling_grid.py and test_n_scaling_grid.py -- are
# exculpated, and every one of them by the FIRST entry. discussion.tex is additionally
# pinned green by name in tests/test_population_labels.py.
_BOTH_BRANCHES = [
    r"\bif (?:it|that|this|they|so|not|the population|the pool|the top|the sample"
    r"|the atom|the rung)\b",
    r"\bonly if\b",
    # `whether` and `unless` WERE BARE UNTIL 2026-08-27, and bare they are magic words in
    # the same way `calibrated` was: "reports a smaller floor, whether or not anyone
    # checks" and "...unless the run crashes" both exculpated on a conditional about
    # something else entirely. They now have to be conditional ON THE THING IN DISPUTE,
    # which is the rule the `if` entry above has always followed and the reason it names
    # its subjects. Checked afterwards against all five passages in this repo that state
    # the dichotomy correctly: none of them loses its exculpation, because every one is
    # already carried by the `if` entry.
    r"\bwhether (?:it|that|this|the population|the pool|the top|the sample|the atom"
    r"|the rung|the floor|a larger pool|\w+ can)\b",
    r"\bunless (?:it|that|this|the population|the pool|the top|the sample|the atom"
    r"|the rung|the floor)\b",
    r"\bnot identified\b", r"\bnon-?identif", r"\bunidentified\b",
    r"\bnot determinable\b", r"\bcannot be (?:decided|settled|determined)\b",
    r"\bcannot (?:decide|settle|tell|distinguish|choose)\b",
    r"\bzero branch\b", r"\bboth branches\b", r"\beither branch\b",
    r"\bboth readings\b", r"\btwo readings\b", r"\beither reading\b",
    r"\bordinary (?:population|binomial) proportion\b",
    r"\bno larger pool\b",
]

# NAMING THE POPULATION A COVERAGE FIGURE WAS MEASURED UNDER. The brief for this rule named
# four; `calibrated`/`branch-conditional` are added because the corrected sites all use one
# of them and a guard that reddened the corrected text would be worse than useless.
#
# WHAT IS DELIBERATELY NOT HERE: "population model", "validated out-of-sample", "the fitted
# model". Every one of the sixteen defective sites named a model in exactly those words --
# "against a population model validated out-of-sample on the N=20 and N=10 atoms" -- and
# none of them named WHICH BRANCH, which is the entire defect. Admitting those phrases
# would turn all sixteen green.
#
# KNOWN GAP, specific to the current .tex scope: `strip_latex` deletes `\tau` along
# with every other command, so `$\tau^*$` arrives here as a bare `^*` and
# `$\tau_{\mathrm{top}}$` as ` top `, and neither symbol entry below can match it.
# In a .tex file only the WORDS "Ewens" and "zero branch" can exculpate. The symbol
# entries earn their place the moment the scope widens to results/ and scripts/, where
# the corrected tables are plain text and do carry a literal `tau_top`. Verified rather
# than assumed -- test_strip_latex_is_not_safe_for_the_files_this_ledger_is_aimed_at.
#
# `calibrated` IS NO LONGER A MAGIC WORD, 2026-08-27. It was admitted bare, and bare it
# exculpates on a word that has nothing to do with this dichotomy: `\bcalibrated\b` occurs
# in 36 of the 228 tier-2 files, meaning embedding calibration, judge-threshold
# calibration or probability calibration, so
#     "The judge threshold was calibrated on the pilot; Wilson covers 53.7% at nominal 95%"
# passed with no branch named anywhere in it -- the exact defect, wearing a neighbouring
# subfield's vocabulary. The exculpation is now tied to the BRANCH BEING NAMED: `calibrated`
# has to be calibrating the Ewens fit / the model / the branch, which is what every
# corrected site in this repo actually writes ("calibrated Ewens (tau_top = 0.2726%)").
# Re-measured against the corrected sites afterwards: no loss.
_BRANCH_NAMED = [
    r"\bEwens\b", r"\bzero branch\b", r"\btau[_ ]?top\b", r"\btau\s*\*",
    r"\bcalibrated (?:\w+ ){0,2}(?:fit|model|branch|Ewens)\b",
    r"\bcalibrated Ewens\b", r"\bbranch[- ]conditional\b",
]

# Topical gates. `_FLOOR_CTX` keeps "reports a smaller one" pinned to this floor;
# `_COVERAGE_CTX` keeps `0.00%` pinned to a coverage claim; `_FLOOR_RESOLUTION_CTX`
# separates this floor's "property of the detector" from the class-separation one.
_FLOOR_CTX = [r"\bfloor\b", r"\brung\b", r"\bpool\b", r"\batom\b"]
# `_COVERAGE_CTX` was `[cover*, nominal, bootstrap, Wilson]` when first drafted and it
# was too loose, which a dry run over results/ found before this shipped: `0.00% of
# bootstrap replicates have a denominator at or through zero`
# (results/winners_curse_se_false_alarm.md) matched on the word `bootstrap` alone, and
# a `0.00%` column in results/likelihood_weight_sensitivity.md matched 13 times on a
# neighbouring `Wilson`. The discriminating sense is COVERAGE, not the estimator's name,
# so the estimator names are gone. Re-measured against the sixteen sites afterwards:
# no loss.
_COVERAGE_CTX = [r"\bcover(?:s|ed|age|ing)?\b", r"\bnominal\b"]
_FLOOR_RESOLUTION_CTX = [r"\bresolution\b", r"\b4/200\b", rf"\b2\.0{PCT}",
                         r"\bfloor\b", r"N\s*\{?=\}?\s*40\b"]

# --------------------------------------------------------------------------------------
# THE SHAPES, 2026-08-27. Widened from single spellings after 30 of 56 evasion probes got
# through -- and widened only as far as the THREAT MODEL justifies, which is the part worth
# reading. This guard does not defend against an adversary; nobody is trying to smuggle a
# retracted claim past it. It defends against a writer working from a stale brief. So the
# test for admitting a rendering is "would a careless writer produce this sentence", and
# the test for declining one is the same question answered no.
#
# ADMITTED, because they are the ordinary English for the retracted claim:
#   dissolves / breaks / stops existing / ceases to exist   (the six that were already here)
#   vanishes / evaporates / disappears / dissipates / goes away / melts away
#   is undefined / is no longer well defined / stops being well defined
#   has no referent / has nothing left to name / stops naming anything
#
# DECLINED, each with the writer who would have to produce it:
#   * "the estimand sublimates", "the estimand is annihilated". Nobody writing about a
#     false-alarm floor reaches for these. A rule for them buys nothing and enlarges the
#     surface on which a false positive can happen.
#   * Any rendering that drops the noun `estimand` entirely -- "there is nothing left to
#     estimate", "the target of estimation goes away". These are declined for a specific
#     reason rather than for taste: the ceiling-atom argument the paper makes CORRECTLY
#     uses that vocabulary ("what is left varying is which 200 questions were drawn"), and
#     an anchor-free rule would have to arbitrate a topic it cannot see. The noun is what
#     makes the claim about the estimand rather than about the estimator, and the estimator
#     half is exactly what six correct passages say ("both estimators fail").
#   * The passive with an agent -- "the estimand is dissolved by the empty atom". Grammatical
#     and vanishingly unlikely; and `dissolv\w*` catches it anyway, which is the argument for
#     stemming rather than enumerating.
_ESTIMAND_GONE = (
    r"(?:dissolv\w*|stops? existing|stopped existing|ceas\w+ to exist"
    r"|breaks?\b|broken\b|no longer exists?\b"
    r"|vanish\w*|evaporat\w*|disappear\w*|dissipat\w*|goes away\b|melts? away\b"
    r"|undefined\b|stops? being (?:well[- ])?defined"
    r"|has no (?:referent|target|meaning)\b|stops? naming\b)")

# THE SMALLER-FLOOR SHAPE. Same widening, same test. The rule matched one verb and two
# nouns -- `reports a smaller floor|one` -- and missed "reports a LOWER floor", "gives a
# smaller number for the floor" and "the floor shrinks as the pool grows", all three of
# which are how the claim gets restated by someone paraphrasing rather than copying.
#
# TWO PATTERNS, NOT ONE, because the claim has two grammars. The TRANSITIVE one has the
# pool as subject ("a larger pool reports a smaller floor"); the INTRANSITIVE one has the
# floor as subject ("the floor shrinks as the pool grows") and no reporting verb at all,
# so no widening of the first can reach it.
#
# DECLINED: "the floor is a decreasing function of pool size" (nobody in this repo writes
# in that register, and a rule for it would reach every monotonicity statement in the
# Methods); and the quantified form "537 of 1000 replicate pools reached a higher rung",
# which is a MEASUREMENT of the branch rather than an assertion of it -- the ruling's own
# section 8 prints numbers of that shape on purpose.
_SMALLER = r"(?:strictly |much |far |slightly |systematically )?(?:smaller|lower|tinier)"
_REPORTS_SMALLER = (
    r"(?:report|give|yield|produce|return|record|show|quote|print)\w*\s+"
    r"(?:a |an |the )?" + _SMALLER + r"\s+(?:floor|one|number|rate|value|estimate)\b"
    # ...but not the displaced-noun form, which the rule below owns. Without this the
    # single sentence "gives a smaller number for the floor" is reported twice, and a
    # register that reports one site twice is a register that gets skimmed.
    r"(?!\s+for (?:the |its )?floor\b)")
# ...and with the noun displaced: "gives a smaller number FOR THE FLOOR".
_REPORTS_SMALLER_FOR = (
    r"(?:report|give|yield|produce|return|record|show|quote|print)\w*\s+"
    r"(?:a |an |the )?" + _SMALLER + r"\s+\w+\s+for (?:the |its )?floor\b")
# The intransitive grammar. Gated on the pool GROWING, because a floor that falls for some
# other reason is not this claim -- the whole content of the retracted sentence is that the
# quantity moves WITH THE POOL.
_FLOOR_FALLS = (r"\bfloor\b[^.;:!?]{0,24}?"
                r"\b(?:shrinks?|falls?|drops?|declines?|goes down|gets smaller"
                r"|becomes smaller|is smaller|is lower)\b")
_POOL_GROWS = [r"larger pool", r"bigger pool", r"wider pool", r"pool grows",
               r"pool gets larger", r"as the pool", r"with the pool", r"pool size",
               r"more answers", r"grows\b"]

_FLOOR_WITHDRAWN = (
    "the N=40 floor is printed as a POINT with no interval; the interval that survives "
    "at that budget is the at-cap mass, 0/200 = 0.0% [0.0, 1.9] (threshold ln 40, fixed "
    "a priori). See results/n40_floor_estimator_ruling.md"
)

SUPERSEDED: list[dict] = [
    {"pattern": r"\b5\.03", "quantity": "Wilson UPPER end on 4/200 for the N=40 floor",
     "run": "pre-ruling", "replacement": _FLOOR_WITHDRAWN},
    {"pattern": r"\b0\.78(?!\d)",
     "quantity": "Wilson LOWER end on 4/200 for the N=40 floor",
     "run": "pre-ruling", "replacement": _FLOOR_WITHDRAWN},
    {"pattern": r"\b0\.5\s*,\s*4\.0(?!\d)",
     "quantity": "question-bootstrap interval for the N=40 floor (its lower endpoint is "
                 "pinned at 1/200 by construction and exceeds the true floor in 100% of "
                 "simulated pools)",
     "run": "pre-ruling", "replacement": _FLOOR_WITHDRAWN},
    {"pattern": r"\b0\.8\s*,\s*5\.0(?!\d)",
     "quantity": "Wilson interval on 4/200 for the N=40 floor, rounded to 1 dp",
     "run": "pre-ruling", "replacement": _FLOOR_WITHDRAWN},
    # THE FULL-PRECISION PAIR, armed 2026-08-19 after an audit found that NONE of the four
    # rules above matches it. Wilson on 4/200 is [0.78037%, 5.02866%], and the four rules
    # were written against the ROUNDED renderings the paper happened to carry:
    # `\b0\.78(?!\d)` is blocked by the very next digit of `0.7804`, and `\b5\.03` cannot
    # match `5.0287`, which reads `5.02`. The unrounded pair is not hypothetical -- it is
    # sitting in figures/fig_floor_budget_stats.json under
    # `withdrawn_wilson_on_the_floor_count`, correctly labelled there, one copy-paste from
    # the paper. That sidecar is the right place for it; paper/ is not, and paper/ is what
    # this checker reads.
    #
    # ARMED ALONE, not as a pair, on the same reasoning the note above gives for `5.03`
    # and `0.78`: at four and five significant figures these digit strings are unique to
    # this interval. `0\.780` cannot be the replication AUROC `0.787`, which is the one
    # collision the 2 dp rule had to dodge with a lookahead.
    {"pattern": r"\b0\.780\d*",
     "quantity": "Wilson LOWER end on 4/200 for the N=40 floor, at full precision "
                 "(0.78037; renders as 0.780 / 0.7804 / 0.78037)",
     "run": "pre-ruling", "replacement": _FLOOR_WITHDRAWN},
    {"pattern": r"\b5\.02[89]\d*",
     "quantity": "Wilson UPPER end on 4/200 for the N=40 floor, at full precision "
                 "(5.02866; renders as 5.028 / 5.0287 / 5.029)",
     "run": "pre-ruling", "replacement": _FLOOR_WITHDRAWN},
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
    #
    # ---- THE RETIRED POSITIONS THAT CONTAIN NO DIGIT, 2026-08-26 ------------------------
    # Armed after a defect survived FOUR rounds of adversarial review in
    # `paper/sections/discussion.tex`: one line said the measured N=40 floor "takes the
    # question bootstrap" -- a position withdrawn on 2026-08-19 -- while another line of the
    # same file said it "takes neither". It survived because IT CONTAINS NO DIGIT. Every
    # guard watching that quantity, including the six rules directly above, matches a
    # RENDERED NUMERAL, and every sweep grepped for numbers. A follow-up sweep then found
    # the same class at sixteen more sites across results/, scripts/, tests/ and figures/:
    # generator string literals, code comments, docstrings, a provenance banner, test
    # docstrings, an assertion message, and one refusal message (commit 852e0f7, whose
    # subject line is "sixteen more sites, none of them containing a digit").
    #
    # WHY THIS FILE AND NOT `derived_paper_quantities.py`. That script has eight
    # `PaperClaim(..., present=False)` entries pinning the retired N=40 intervals, and it
    # was the obvious home. It is the wrong one on three counts, all structural: a
    # PaperClaim is a PER-SITE pin (`name`, `value`, `literal`, one source file), it is
    # scoped to five named .tex constants, and every entry needs a LITERAL RENDERING to
    # match against. A defect with no rendering has nothing for it to pin. This file
    # already is the retired-position ledger -- SUPERSEDED is a list of `{pattern,
    # quantity, replacement}` with six entries already armed on this exact ruling -- and it
    # already matches against `strip_latex(raw)`, so markup cannot split a phrase the way
    # `\emph{}` split the phrases the manual sweeps were grepping for.
    #
    # THE SETTLED POSITION, so a future reader does not have to reconstruct it. At N=10 and
    # N=20 the ceiling atom is full, the floor threshold is the a-priori ln N, and Wilson is
    # correct. At N=40 the atom is empty (0/200) and the floor becomes an order statistic.
    # TWO BRANCHES EXIST AND n=200 CANNOT SEPARATE THEM: if the population can never yield
    # 39 mutually inequivalent answers out of 40 then 4/200 = 2.0% estimates a real
    # population quantity; if it can, 2.0% is the pool's resolution and may be arbitrarily
    # far above the truth. 0/200 is the modal outcome under BOTH. So the retraction is not
    # "the floor is smaller than we said" -- it is that tau_top is NOT IDENTIFIED, which is
    # model-free and stronger. Ruling sections 1 (M5), 2, 8.4 and 13.
    # `denial` IS ARMED ON EVERY WORD RULE BELOW and on neither coverage rule. A word rule
    # has to survive being quoted in the sentence that disowns it, because that is how every
    # corrected file in this repo records what it used to say. A coverage rule must not:
    # "not 53.7%" is still 53.7% quoted with no branch named, which is the defect.
    # `denial` is `_is_disowned` -- three named disowning constructions, NOT a
    # proximity-to-a-negative-word test; see the block above that function for what each one
    # is, what changed on 2026-08-27 and what the change costs.
    #
    # THE VERB SET IS A SHAPE, NOT A SPELLING (widened 2026-08-27). It carried six verbs and
    # a literal noun, and 30 of 56 evasion probes walked through the gaps: `the estimand
    # vanishes`, `evaporates`, `is no longer well defined`. Every one of those is a sentence
    # a writer working from a stale brief would actually produce -- they are the ordinary
    # English for "dissolves" -- so they are closed here, on the `\b\d+/97\b` precedent that
    # this file already applies to numerators. What is DECLINED, and why, is in the note
    # below `_ESTIMAND_GONE`.
    {"pattern": r"estimand\b(?:(?!" + _NEGATOR + r")[^.;:!?]){0,28}?\b" + _ESTIMAND_GONE,
     "denial": True, "wide": True, "run": "pre-sec-13",
     "quantity": "the N=40 floor's estimand described as DISSOLVING, breaking or ceasing "
                 "to exist once the ceiling atom empties",
     "replacement": _NOT_IDENTIFIED},
    # ...AND THE RENDERINGS WHOSE OWN WORDS CARRY THE NEGATION. "the estimand is no longer
    # well defined" and "the estimand is not well defined" ARE the retracted claim; the
    # negator belongs to the claim, not to a denial of it. They cannot ride on the rule
    # above, whose tempered gap refuses to span a negator -- that tempering is what keeps
    # "the estimand does not break" green and it must stay. So they are armed separately.
    # `_is_disowned` reads only OUTER constructions, so the constitutive negation inside
    # these patterns cannot exculpate them, while "It is not that the estimand is no longer
    # well defined" still goes green on D2.
    {"pattern": r"estimand\b[^.;:!?]{0,28}?\b(?:is|was|becomes?|became)\s+"
                r"(?:no longer|not)\s+(?:a\s+|an\s+)?"
                r"(?:well[- ]defined|defined|meaningful|coherent|identifiable"
                r"|a real quantity|anything at all)",
     "denial": True, "wide": True, "run": "pre-sec-13",
     "quantity": "the N=40 floor's estimand described as NO LONGER WELL DEFINED once the "
                 "ceiling atom empties -- the same retracted claim with the negation "
                 "inside it",
     "replacement": _NOT_IDENTIFIED},
    # THE SAME CLAIM WITH THE WORDS THE OTHER WAY ROUND, which the rule above cannot see
    # because it anchors on the noun and scans forward. `results/n_scaling_grid.md` and its
    # generator both carried "the empty atom -- also breaks the floor as an estimand", and
    # a ledger that only knew `estimand <verb>` would have called that file clean. This is
    # the `97`-numerator lesson in a sentence: enumerate the SHAPE, not one spelling of it.
    {"pattern": r"break\w*\b[^.;:!?]{0,32}?\bas an estimand\b",
     "denial": True, "wide": True, "run": "pre-sec-13",
     "quantity": "the N=40 floor's estimand described as BROKEN by the empty atom "
                 "(verb-first rendering)",
     "replacement": _NOT_IDENTIFIED},
    # ...AND WITH THE VERB ELIDED ALTOGETHER. "Neither estimator is broken -- the estimand
    # is" was live in `figures/README.md` and in the comment at the top of THIS FILE, and
    # neither of the two rules above matches it: the only verb in the clause belongs to the
    # estimator. Armed as the ADJACENCY of the two clauses rather than as either one alone,
    # because "both estimators fail" is a phrase SIX correct passages now use --
    # n40_floor_estimator_ruling.md, n_scaling_grid.md, replay_control.md,
    # n_scaling_grid.py (twice) and replay_control.py -- always under attribution
    # ("is a statement about the first row only"), and a flat match on the estimator
    # half would flag every one of them.
    {"pattern": r"neither estimator is broken\W{0,6}(?:the\W{0,6})?estimand\b",
     "denial": True, "wide": True, "run": "pre-sec-13",
     "quantity": "'neither estimator is broken -- the estimand is', the retracted framing "
                 "with its verb elided",
     "replacement": _NOT_IDENTIFIED},
    # THE CONDITIONAL-AWARE ONE, and it is the one that matters most. See the ABSENT_SPAN
    # note above for why the gate looks both ways and counts sentences rather than
    # characters. `near` is doing a second, smaller job here: it is what keeps the
    # "...reports a smaller one" rendering (which `docs/START_HERE_overnight.md` carried)
    # from matching a smaller anything in a passage that is not about this floor at all.
    #
    # IT NOW CARRIES `denial` TOO, AND THAT IS A FALSE-POSITIVE FIX (2026-08-27). It shipped
    # without one, on the argument recorded in
    # test_the_denial_gate_is_armed_on_the_flat_rules_and_on_no_coverage_rule: that a "not"
    # thirty characters back is not evidence the DICHOTOMY was stated. The argument was
    # sound about the OLD gate and it produced a plain false positive anyway --
    #     "It does not follow that a larger pool reports a smaller floor"
    # was RED, which is the guard reddening a sentence that says the right thing, on a rule
    # whose own comment says a guard that fires on correct usage teaches its user to silence
    # it. The premise has also changed: `_is_disowned` is not a lookback, it is a test for
    # three disowning CONSTRUCTIONS, and "it does not follow that X" is one of them by
    # construction rather than by proximity. `absent` still does the work it always did --
    # stating the dichotomy is still what green normally requires -- and `denial` only adds
    # the case where the sentence denies the claim outright instead of conditioning it.
    {"pattern": _REPORTS_SMALLER,
     "near": _FLOOR_CTX, "absent": _BOTH_BRANCHES, "span": 1, "denial": True,
     "wide": True, "run": "pre-sec-13",
     "quantity": "'a larger pool reaches a higher rung and reports a smaller floor' "
                 "stated UNCONDITIONALLY -- one branch of a dichotomy the sample cannot "
                 "settle, presented as the finding",
     "replacement": _NOT_IDENTIFIED},
    # ...the same claim with the noun displaced ("a smaller NUMBER for the floor"), which
    # the pattern above cannot see because it requires the floor noun in the object slot.
    {"pattern": _REPORTS_SMALLER_FOR,
     "near": _FLOOR_CTX, "absent": _BOTH_BRANCHES, "span": 1, "denial": True,
     "wide": True, "run": "pre-sec-13",
     "quantity": "'a larger pool gives a smaller number for the floor' stated "
                 "UNCONDITIONALLY -- the same single branch, with the floor noun moved "
                 "out of the object slot",
     "replacement": _NOT_IDENTIFIED},
    # ...and the INTRANSITIVE grammar, which has no reporting verb at all and so cannot be
    # reached by widening either pattern above: "the floor shrinks as the pool grows". Its
    # `near` gate is `_POOL_GROWS` rather than `_FLOOR_CTX`, because a floor that falls for
    # any other reason is a different sentence -- the retracted content is specifically that
    # the quantity moves WITH THE POOL.
    {"pattern": _FLOOR_FALLS,
     "near": _POOL_GROWS, "absent": _BOTH_BRANCHES, "span": 1, "denial": True,
     "wide": True, "run": "pre-sec-13",
     "quantity": "'the floor shrinks as the pool grows' stated UNCONDITIONALLY -- the "
                 "same single branch in the grammar where the floor is the subject",
     "replacement": _NOT_IDENTIFIED},
    # THE COVERAGE PAIR, ARMED AS AN ADJACENCY RULE RATHER THAN A PHRASE RULE, on this
    # file's standing paired-endpoint precedent (`\b9\.0\s*,\s*12\.2`, where 9.0 is live
    # elsewhere and only the adjacency is the retired interval). The retired thing here is
    # not the digits: 53.67% and 0.00% are the TRUE coverages under the calibrated Ewens
    # fit. What is retracted is quoting them with no branch named, because under the zero
    # branch the same two estimators cover 95.06% and 100%, and the data excludes neither
    # branch (p = 0.1175 for the fitted model against 0/200; the model-free bound
    # [0%, 1.88%] contains both zero and the model's 1.065%). So the gate is `absent`.
    #
    # SPAN 1, NOT 0, AND THE REASON IS MEASURED RATHER THAN CHOSEN. "The branch must
    # be named in the same sentence" is the right SPECIFICATION and span 0 is the
    # wrong IMPLEMENTATION of it, because `_TERM_RE` counts a colon as a sentence
    # boundary and every corrected site in this repo puts the branch label in front
    # of one:
    #     calibrated Ewens (tau_top = 0.2726%): Wilson 53.67%, question bootstrap 0.00%
    # -- scripts/make_floor_budget_figure.py:71, scripts/n_scaling_grid.py:799 and
    # scripts/derived_paper_quantities.py:306, all three of them the CORRECTED text.
    # At span 0 the label sits on the far side of that colon and all three go red,
    # which is the guard reddening the fix. Widening to 1 costs nothing measurable:
    # re-run against the sixteen prose sites of 852e0f7, span 1 catches exactly what
    # span 0 catches, because not one of the defective sites had a branch name
    # anywhere near it -- that was the defect.
    #
    # 53.7 IS UNIQUE IN THIS REPO AND IS ARMED ALONE; 53.4, 53.5, 53.8 and 53.9 are live
    # numbers in `achievable_fpr_grid.md`, `cluster_count_bound.md` and
    # `null_control_cost_options.md`, which is why the pattern pins the digit rather than
    # the two-decimal prefix.
    {"pattern": r"\b53\.(?:7(?!\d)|67\d*)",
     "absent": _BRANCH_NAMED, "span": 1,
     "wide": True, "run": "pre-sec-8.4",
     "quantity": "Wilson's coverage for the N=40 floor count, quoted WITHOUT the "
                 "population it was measured under",
     "replacement": _COVERAGE_PAIR},
    # 0.00% CANNOT BE ARMED ALONE and gets both gates. `\b0\.00` with no required percent
    # sign would reach the exact subset-saturation curve of ruling section 1 (M3), where
    # `U_39 = 0.000000%` is a MEASURED, model-free, exhaustively enumerated value and the
    # single most quotable number in that section -- flagging it would be flagging the
    # replacement. PCT blocks that (`0.000000%` continues with a digit, not a `%`) and
    # `near` blocks a zero rate that has nothing to do with coverage. The cost of the
    # required percent sign is stated rather than hidden: a rendering as bare `0.00` in a
    # bracketed pair goes unseen, which is the same blind spot the `5.03` note above
    # records for the fair-pool rule, accepted here for the same reason -- `0.00`
    # unadorned is not unique to this quantity.
    {"pattern": rf"\b0\.00{PCT}",
     "near": _COVERAGE_CTX, "absent": _BRANCH_NAMED, "span": 1,
     "wide": True, "run": "pre-sec-8.4",
     "quantity": "the question bootstrap's coverage for the N=40 floor, quoted WITHOUT "
                 "the population it was measured under",
     "replacement": _COVERAGE_PAIR},
    # ORDINARY NUMBER FORMS FOR THE SAME TWO COVERAGES, added 2026-08-27. The two rules
    # above pin exact renderings -- `53.7` / `53.67` and `0.00%` -- and a writer restating a
    # figure rounds it, drops a decimal or drops the percent sign. Measured: `0%`, `0.0%`
    # and `about 54%` all passed.
    #
    # ARMED AS AN ADJACENCY TO THE COVERAGE VERB, NOT AS A NUMBER WITH A 300-CHARACTER
    # `near` WINDOW, and the difference is a false positive this rule would otherwise
    # certainly produce. `0.0%` is ALSO the at-cap mass -- `0/200 = 0.0% [0.0%, 1.9%]` --
    # which is the quantity the ruling tells everyone to print INSTEAD, and in the corrected
    # banners it sits one sentence away from the word "covers". A `near` gate cannot tell
    # those apart; requiring the zero to be the grammatical object of the covering verb can,
    # because nobody writes "covers 0.0%" about the at-cap mass. So the number has to sit
    # within a clause of `cover*`, on either side of it, with no sentence boundary between.
    #
    # THE SET IS `0`, `0.0`, `54`, `54.0` AND NOTHING ELSE, and every exclusion was forced
    # by a dry run rather than chosen:
    #   * `53.x` is absent because the two exact rules already arm `53.7` and `53.67`, and
    #     leaving it in produced a SECOND finding on the same site in two files -- one
    #     figure reported twice is how a register learns to be skimmed. 53.67 rounds to 54
    #     anyway, so a writer who rounds writes 54 and a writer who writes 53 is writing a
    #     different number.
    #   * `(?<![\d.%])` is load-bearing. Without it `\b0` matches the trailing zero of
    #     `5.0%` -- `.` is a non-word character, so `\b` sits happily between the two -- and
    #     `results/n_scaling_plan.md` has a budget table whose every row ends
    #     `| 4.0% | ... | no -- interval covers 5% |`. Twenty rows of correct arithmetic,
    #     reported as withdrawn coverage figures.
    #   * the REVERSE arm requires the noun `coverage`, not any `cover*`, because a verb
    #     after the number is nearly always the containment sense ("interval covers 5%")
    #     and the noun is nearly always the probabilistic one ("0.00% coverage").
    # Counts out of a replicate pool -- "covers in 537 of 1000 pools" -- are also absent,
    # and that is a threat-model call rather than an oversight: a careless writer restating
    # a coverage quotes the percentage, and the ruling's own section 8 prints replicate
    # counts on purpose.
    {"pattern": r"cover(?:s|ed|age|ing)?\b[^.;:!?]{0,44}?"
                r"(?:about |roughly |around |approximately |nearly |just over "
                r"|just under |some )?(?<![\d.%])(?:0|0\.0|54|54\.0)\s*" + PCT + r"(?!\d)"
                r"|(?<![\d.%])(?:0|0\.0|54|54\.0)\s*" + PCT + r"(?!\d)"
                r"[^.;:!?]{0,26}?\bcoverage\b",
     "absent": _BRANCH_NAMED, "span": 1,
     "wide": True, "run": "pre-sec-8.4",
     "quantity": "one of the two withdrawn coverage figures in a rounded or "
                 "decimal-free rendering, quoted WITHOUT the population it was measured "
                 "under",
     "replacement": _COVERAGE_PAIR},
    # THE SENTENCE THE RULING FORBIDS BY NAME. Section 2: "The first version proposed the
    # Abstract say that the 2.0% 'is the resolution of the pool and not a property of the
    # detector'. Do not print that sentence." It reached the Abstract and was committed
    # there. NO `absent` GATE ON THESE TWO, deliberately: the ruling withdraws the sentence
    # outright rather than conditioning it, and the both-branches-safe wording it supplies
    # instead ("whether that is a property of the detector OR of the pool's size turns on
    # ...") contains neither pattern -- there is no "resolution ... of the pool" in it, and
    # no "not a property of the detector".
    {"pattern": r"resolution (?:limit )?of (?:the|a|an|this|our|its)\b"
                r"[^.;:!?]{0,26}?\bpool\b",
     "denial": True, "wide": True, "run": "pre-sec-2",
     "quantity": "the N=40 floor's 2.0% described as 'the resolution of the pool'",
     "replacement": _NOT_IDENTIFIED},
    # ...and its other half, which needs `near` because the phrase is LIVE AND CORRECT
    # about a different quantity. `results/dynamic_range_finding.md` and
    # `results/CORRECTIONS_2026-08-02.md` both call the +0.184-nat class separation "not a
    # fixed property of the detector", correctly, and neither passage mentions the floor,
    # 4/200, 2.0% or N=40. The gate is what tells the two apart, and both of those sites
    # are pinned green by name in tests/test_population_labels.py.
    {"pattern": r"not a (?:fixed |mere |simple )?property of the detector\b",
     "near": _FLOOR_RESOLUTION_CTX,
     "denial": True, "wide": True, "run": "pre-sec-2",
     "quantity": "the N=40 floor's 2.0% described as 'not a property of the detector'",
     "replacement": _NOT_IDENTIFIED},
]
SUPERSEDED_RUN = "wk9_def"
CURRENT_RUN = "wk9_defb"
NEAR_WINDOW = 300

# --------------------------------------------------------------------------------------
# ESTIMATOR OWNERSHIP: WHICH INTERVAL EACH ROW TAKES.  (2026-08-27)
#
# WHY THIS EXISTS, AND IT IS NOT A NEW CLASS. It is the INDEX CASE of the class the eight
# rules above were built for, and until today not one of them caught it. The defect that
# opened round five was `paper/sections/discussion.tex:306`:
#
#     "the measured $N{=}40$ floor is a count at no fixed threshold at all and takes the
#      question bootstrap for the reason given above."
#
# -- while line 166 of the same file said it "takes neither", 144 lines apart. Run through
# all 37 SUPERSEDED patterns in both tiers, that sentence PASSES, and so do three obvious
# rewordings ("takes a bootstrap over the 200 questions"; "We quote a question bootstrap
# interval for the measured N=40 floor"; and the same assertion with Wilson in it). The
# eight rules were fitted to the SWEEP -- the sixteen follow-on sites, every one of which
# happened to be about dissolution or about a bare coverage figure -- and not to the CLASS.
# A ledger that catches the follow-ons and not the original is a ledger built backwards,
# and the original design note said so: it proposed this rule and nobody built it.
#
# WHY A TABLE AND NOT A REGEX. The vocabulary here is CLOSED. There are three estimators
# (Wilson, the question bootstrap, neither) and a small fixed set of rows, and every row's
# answer is a RULING -- results/n40_floor_estimator_ruling.md sections 1, 2, 8.4 and 13 --
# not a fact about wording. So the answer is DATA. A future re-ruling changes one cell of
# `OWNERSHIP_ROWS` and nothing else; it does not send anyone into a regex to work out which
# alternation branch meant which row. That is the same reason FROZEN_COUNTS is a registry
# and the same reason GROWING_CELLS is keyed by cell.
#
# THE ROWS AND THEIR ANSWERS, with the ruling section that decides each:
#
#   the measured N=40 floor (2.0%, 4/200)        NEITHER   sec. 1 (M6, M7), 2 row 1, 13
#       Its threshold is not fixed a priori -- it is the top score THIS sample attained --
#       so Wilson's coverage is branch-dependent and the bootstrap's lower endpoint is
#       placed at 1/200 by the estimator's range rather than by the data. Both were
#       withdrawn. The row prints a POINT.
#   the at-cap mass at ln 40 (0/200 = 0.0%)      WILSON    sec. 1, 2 row 1
#       Threshold fixed before the data, so the interval is valid in BOTH branches. This
#       is the quantity the ruling tells everyone to print instead.
#   the direct N=10 floor (19/200 at ln 10)      WILSON    sec. 2; discussion.tex:310
#       A count of independent indicators at an a-priori threshold.
#   the achieved 5%-budget point (10/200)        WILSON    sec. 2 row 2 -- "Print Wilson,
#       5.0% [2.7, 9.0], and retire the bootstrap [2.5, 5.0]". Note this row runs the
#       OPPOSITE way to row 1, which is exactly why `docs/START_HERE_overnight.md` warns
#       against "making the two rows consistent" by giving them the same estimator.
#   the replayed / subset-averaged rows          BOOTSTRAP discussion.tex:162-166
#       Their point estimate is an average over subset draws and no count exists, so what
#       is left varying is which 200 questions were drawn: a bootstrap over questions is
#       the whole of it.
#
# NOT IN THE TABLE, AND THE OMISSION IS THE INTERESTING PART: "the N=20 floor" and "the
# N=10 floor" unqualified. Each names TWO different rows -- the direct count (Wilson) and
# the subset-averaged replay (bootstrap) -- and the paper quotes the replayed one at both
# budgets while measuring the direct one at N=10. A rule that guessed would be wrong half
# the time, and being wrong here means reddening correct prose. Silence is the right answer
# for an ambiguous row name; only `direct N=10` and `replayed` are unambiguous, and only
# those are listed.
#
# HOW IT DECIDES, and every step is chosen to fail SILENT rather than LOUD:
#   1. Find an OWNERSHIP PHRASE -- a predicate from the closed list immediately followed,
#      within 40 characters and no sentence boundary, by an estimator name. "takes the
#      question bootstrap", "belongs to Wilson", "is priced by Wilson", "carries a Wilson
#      interval", "we quote a question bootstrap interval". The adjacency is what keeps the
#      rule off "Wilson prices a count of independent indicators", where the predicate is
#      followed by a noun phrase and the ownership is asserted about a row named 60
#      characters later, and off "Neither prices the floor", where the estimator precedes
#      the predicate.
#   2. Find the NEAREST row name in the same clause, either side. Nearest, not any-in-
#      window, because "...the empty at-cap mass at ln 40---while the replayed rows take a
#      bootstrap over the 200 questions" names two rows before one ownership phrase and the
#      near one owns it. Clause-bounded, because discussion.tex:310 puts two rows and two
#      answers on either side of a semicolon and a window that crossed it would flag the
#      correct sentence.
#   3. No row in range -> SILENT. "the paper takes Wilson on the count for those rows"
#      (results/replay_control.md:18) names no row this table knows, and the guard has
#      nothing to say about it.
#   4. `_is_disowned` applies, so "the N=40 floor does not take the question bootstrap" and
#      the quoted-to-disown correction notes stay green.
# --------------------------------------------------------------------------------------
# The estimators. Three, and the set is closed by the ruling rather than by this file.
_EST_PATTERNS: dict[str, str] = {
    "wilson": r"Wilson",
    "bootstrap": r"(?:question |questions |q-)?bootstraps?",
    "neither": r"neither",
}
_EST_ALT = "|".join(f"(?P<{k}>{v})" for k, v in _EST_PATTERNS.items())

# The ownership predicates. Closed list, from the design note, plus the two spellings the
# repo actually uses (`prices`, `quote ... for`). `uses` and `gets` are in because they are
# what a paraphraser reaches for; each is harmless on its own and only counts when an
# estimator name follows it inside the clause.
_OWNS_PRED = (r"(?:takes?|taking|took|belongs? to|belonging to|is priced by|are priced by"
              r"|priced by|prices?|gets?|carries|carry|carrying|quotes?|quoting|quote"
              r"|uses?|using|is given|are given|is interval\w+ by|goes to)")
# `|` WAS EXCLUDED FROM THIS GAP FOR ONE AFTERNOON and the exclusion is gone, because it
# turned out to be redundant AND to cost recall -- which is the interesting half. The table
# it was added for is results/replay_control.md's own summary, where a predicate in the
# first cell and an estimator in the third bound to a row name in the NEXT table row; the
# `|` in `_CLAUSE_BREAK_RE` already refuses that binding on its own, measured. Excluding
# `|` here as well bought nothing and silenced a real defect: a three-column mapping table
# reading `| the measured N=40 floor | none | takes | Wilson |` states the ownership across
# cell walls, and that is exactly the shape the one table in this repo whose job is to state
# the mapping actually had when it went wrong. Two mechanisms doing one job is how a suite
# ends up with a mutation nothing catches.
_OWNERSHIP_RE = re.compile(
    r"\b" + _OWNS_PRED + r"\b(?:[^.;:!?]{0,40}?)\b(?:" + _EST_ALT + r")\b",
    re.IGNORECASE)

# How far from an ownership phrase a row name may sit and still be the row it is about.
# Clause-bounded first; this is the second, harder stop.
OWNERSHIP_CHAR_CAP = 220
# ...and how far a row name may sit AFTER one, where it has to be the predicate's object
# rather than the next clause's subject. See the asymmetry note in `_check_ownership`.
OWNERSHIP_OBJECT_GAP = 40

_N40 = r"N\s*\{?=\}?\s*40"
_N10 = r"N\s*\{?=\}?\s*10"
OWNERSHIP_ROWS: list[dict] = [
    {"row": "the measured N=40 floor (2.0%, 4/200)",
     "takes": "neither",
     "names": [rf"measured\s+{_N40}\s+(?:achievable\s+)?(?:false-alarm\s+)?floor",
               rf"{_N40}\s+(?:achievable\s+)?(?:false-alarm\s+)?floor",
               rf"floor\s+at\s+{_N40}",
               rf"{_N40}\s+floor'?s?",
               r"measured\s+floor"],
     "why": "its threshold is the top score THIS sample attained and not a value fixed "
            "in advance, so Wilson's coverage is branch-dependent and the question "
            "bootstrap's lower endpoint is placed at 1/200 by the estimator's range "
            "rather than by the data. BOTH candidates are withdrawn; the row prints the "
            "point 2.0% with no interval (ruling sec. 1 M6/M7, sec. 2 row 1, sec. 13)"},
    {"row": "the at-cap mass at ln 40 (0/200 = 0.0% [0.0, 1.9])",
     "takes": "wilson",
     "names": [r"at-cap mass", r"at-cap column", r"at-cap row",
               r"ceiling[- ]atom mass", r"empty at-cap\w*"],
     "why": "its threshold IS fixed before the data (ln 40), so the Wilson interval is "
            "valid in both branches -- this is the quantity the ruling tells the paper to "
            "print instead of an interval on the floor (sec. 1, sec. 2 row 1)"},
    {"row": "the direct N=10 floor (19/200 at ln 10)",
     "takes": "wilson",
     "names": [rf"direct(?:ly)?[- ]?(?:measured |cache |cached )?{_N10}\s+"
               r"(?:achievable\s+)?(?:floor|row)",
               r"direct[- ]cache floor", r"direct\s+cache\s+floor"],
     "why": "it is a count of independent indicators at the a-priori threshold ln 10 "
            "(ruling sec. 2; paper/sections/discussion.tex:310)"},
    {"row": "the achieved 5%-budget operating point (10/200 = 5.0% [2.7, 9.0])",
     "takes": "wilson",
     "names": [r"achieved\s+5(?:\.0)?\s*\\?%?[- ]budget",
               r"5(?:\.0)?\s*\\?%[- ]budget\s+(?:operating\s+)?point",
               r"achieved\s+5(?:\.0)?\s*\\?%\s+(?:operating\s+)?point"],
     "why": "ruling sec. 2 row 2: print Wilson, 5.0% [2.7, 9.0], and retire the "
            "bootstrap [2.5, 5.0]. This row runs the OPPOSITE way to the N=40 floor -- "
            "do not 'make the two rows consistent' by giving them one estimator"},
    {"row": "the replayed / subset-averaged rows (12.0% at N=10, 3.1% at N=20)",
     "takes": "bootstrap",
     "names": [r"replayed\s+rows?", r"replay(?:ed)?\s+floors?",
               r"subset-averaged\s+(?:replay(?:ed)?\s+)?floor",
               r"subset-averaged\s+rows?"],
     "why": "their point estimate is an average over subset draws and no count exists, "
            "so what is left varying is which 200 questions were drawn and a bootstrap "
            "over questions is the whole of it "
            "(paper/sections/discussion.tex:162-166)"},
]

OWNERSHIP_ADVICE = (
    "the vocabulary here is closed -- three estimators, five rows -- and the answer for "
    "each row is a RULING, not a matter of wording. Look the row up in OWNERSHIP_ROWS "
    "before writing which interval it takes, and if the ruling has changed, change the "
    "table there in the same commit. See results/n40_floor_estimator_ruling.md "
    "sections 1, 2, 8.4 and 13")

# THE TIER-2 LEDGER: the entries that run outside paper/. Derived from the `wide` flag
# rather than from a second hand-maintained list, so the two cannot drift -- the shape that
# failed for `labels` (defect 5), for `numbers` (defect 6) and for FROZEN_COUNTS (defect 7)
# was always two lists that had to be edited together and were not.
#
# THE MEMBERSHIP TEST IS A PROPERTY, NOT A TASTE: an entry is `wide` iff its `replacement`
# is a POSITION -- what to say instead -- rather than a recomputed `current` value. A value
# is stored, pinned and corrected all over this repo; a position is only ever asserted.
# test_the_wide_set_is_exactly_the_position_rules holds the two definitions together, so a
# future entry cannot get the wider scope by carrying the flag alone.
WIDE_SUPERSEDED: list[dict] = [item for item in SUPERSEDED if item.get("wide")]

# --------------------------------------------------------------------------------------
# THE RATCHET. Retired-position findings per TIER-2 file, as of 2026-08-26.
#
# A file that GAINS one fails. A file that DROPS below its baseline also fails, so the
# register cannot rot upward while the docs are cleaned. Files absent from this map must be
# clean (baseline 0), and an entry naming a file that is no longer in scope is itself
# reported -- an allow-list of facts about the world expires exactly the way `labels` and
# `numbers` did (defects 5, 6 and 7 above), and this one is a third copy of that shape.
#
# WHAT EACH ENTRY IS. Every one of the 26 was read and classified; the classes are stated
# rather than averaged into a number, because "7 open findings" tells the next reader
# nothing about whether anyone should care. 23 + 3 = 26.
#
#   A COVERAGE FIGURE WITH NO BRANCH NAMED (23). The large class and the intended one:
#   `| N=40 (atom empty) | 0.27% | 53.7% | 0.00% |` in three copies of one table, the prose
#   that reduces the 53.7% to an identity, a refusal message, a risk-register row, and the
#   post-mortem sentences that cite "withdrawn at 0.00% coverage" while discussing a
#   scheduling error. All 23 figures are TRUE under the calibrated Ewens fit; what is
#   retracted is quoting them bare, because under the zero branch the same two estimators
#   cover 95.06% and 100% and the data excludes neither branch. Most are one word from
#   green.
#
#   A LIVE, UNCONDITIONAL ASSERTION OF A RETRACTED POSITION (3), in two files, and these
#   are findings rather than debt. They are named per file below. Nobody may lower one of
#   them by editing this map.
#
#   AND A THIRD CLASS THAT IS NO LONGER HERE, which is the part of this revision worth
#   reading. The register shipped on 2026-08-26 with SIX findings classified as
#   QUOTED-TO-DISOWN -- correct sentences, in files that had already been fixed, recording
#   what they used to say -- pinned because the `denial` gate could not see a disavowal
#   that FOLLOWS its quotation. The module docstring meanwhile told readers that
#   quoting-to-disown was the one innocent restatement and that "the `denial` gate already
#   handles" it. Both cannot be true, and the register was the honest half. The gate now
#   handles it (D3 in the block above `_is_disowned`), and all six went green without a
#   line of those files changing: figures/README.md 1 -> 0,
#   scripts/derived_paper_quantities.py 1 -> 0, results/replay_control.md 7 -> 5,
#   scripts/replay_control.py 9 -> 7. Two files leave the register entirely.
#   Six false positives on correct writing, held for a day, is the honest description of
#   what that was -- and by this file's own threat model it outranked every miss it was
#   traded against.
#
# WHAT THIS REGISTER WAS STRUCK AGAINST, because a baseline with no provenance is the same
# object as an untagged operational figure. Struck 2026-08-27 against the working tree at
# commit e58915f, UNDER THE RULESET IN THIS FILE AS IT NOW STANDS -- and the second half of
# that sentence is the half the previous note left out. A finding count is a function of
# the RULES as much as of the files. The old note read "at HEAD the tier-2 backlog is 41
# findings in 10 files" with no commit named and no ruleset named, and both omissions
# matter, because that figure is now three different numbers depending on what you hold
# fixed. Re-derived, all four cells, rather than repeated:
#
#                                   ruleset at e58915f      ruleset shipping here
#     tree at 852e0f7                  41 in 10 files          36 in  9 files
#     tree at e58915f (= today)        32 in  7 files          26 in  5 files
#
# The COLUMNS differ by this revision's disowning gate: 5 and 6 quoted-to-disown findings
# respectively, cleared without a line of those files changing. The ROWS differ by the four
# corrections that landed after 852e0f7 -- figures/README.md,
# results/derived_paper_quantities.md, tests/test_derived_paper_quantities.py,
# tests/test_replay_control.py -- which account for 9 findings under the old rules
# (3->1, 2->0, 3->0, 2->0) and 10 under these (3->0, 2->0, 3->0, 2->0). Every cell
# reproduces:
#     git archive 852e0f7 | tar -x -C /tmp/at852
#     python -c "import pathlib, check_population_labels as C; \
#       print(sum(len(C.check_file(f)) for f in C.wide_files(pathlib.Path('/tmp/at852'))))"
# If those four edits are ever reverted the ratchet breaches on four files, and that is the
# correct behaviour, not a false alarm.
KNOWN_OPEN: dict[str, int] = {
    # 3, all `0.00%` with no branch named, all three in the post-mortem prose that
    # describes the scheduling defect ("...toward the estimator that had been retired at
    # 0.00% measured coverage"). The figure is true under the calibrated Ewens fit and the
    # sentences are about the handoff rather than about coverage -- but they are exactly
    # the shape the rule exists to catch, and the fix is one clause each. Note what is NOT
    # in this count: the file's corrected line at :190 ("The reason is not data selection,
    # and it is NOT that...") is GREEN, because the disowning gate reads it -- and the
    # PRE-fix wording of that same line, which puts a full stop where the comma is, is
    # still RED. That pair is a test.
    "docs/START_HERE_overnight.md": 3,
    # 5, and TWO OF THEM ARE LIVE. The coverage table's N=40 row reads
    # `| N=40 (atom empty) | 0.27% | 53.7% | 0.00% |` and is followed by "Neither estimator
    # is broken. The estimand dissolves at the moment the atom empties" -- an unconditional
    # assertion of the position section 13 retracts. It is not a quotation, it is not
    # attributed to a past state of the file, and nothing near it disowns it. This is the
    # single most valuable finding the widening produced and it must not be pinned away:
    # the entry stays at 5 until someone edits that paragraph.
    #
    # WHY THIS FILE IS IN SCOPE AT ALL, given that critique_log.md is not. It is dated
    # 2026-08-19, a week before the ruling that retracts the sentence, so the append-only
    # argument reaches for it. It is also the file the project's own memory index cites as
    # where the current decisions live -- so it is READ FORWARD, and forward is the whole
    # of the scope test. A document cannot be both the record of what was believed and the
    # place a reader is sent for what is true. In scope until it stops being the latter.
    "results/morning_review_2026_08_19.md": 5,
    # 5: 2 on the coverage table at :401-405 + 3 in the prose that reduces the 53.7% to an
    # identity. (It was 7; the two correction notes are half of the quoted-to-disown class
    # the new gate reads.) The table's branch is named nowhere near it: the paragraph above
    # says "a population model ... fitted at N=40, tuned on N=20, validated out of sample on
    # the N=10 atom", which is precisely the wording `_BRANCH_NAMED` deliberately refuses --
    # every one of the sixteen defective sites named a model in those words and not one
    # named WHICH BRANCH, which was the entire defect. So these are true findings of the
    # intended class; the table's fix is one word in a header.
    "results/replay_control.md": 5,
    # 6, and ONE IS LIVE: "Wilson covers in 53.7% ... the question bootstrap in 0.00% --
    # because the estimand dissolves once the ceiling atom empties" gives the retracted
    # position as the REASON for the withdrawal and quotes both coverages with no branch
    # named. The other five are the risk-register row `| Wilson 53.7% / bootstrap 0.00%
    # coverage, 40,000 pools | MEASURED |` and post-mortem sentences. A schedule is read
    # FORWARD by whoever works next, which makes this the entry to clear first even though
    # it is not the largest.
    "results/schedule_2026_08_26.md": 6,
    # 7: the largest, and it is results/replay_control.md with its generator's `log(...)`
    # calls wrapped round it -- 2 in the refusal message that fires when the floor row
    # grows an interval again, 2 on the coverage table, 3 on the identity paragraphs.
    # Fixing results/replay_control.md WITHOUT fixing this file would regenerate the
    # finding on the next run, which is the ratchet earning its keep: the pair must move
    # together, and a drop on one side alone is reported as ratchet-stale on the other.
    "scripts/replay_control.py": 7,
}

RATCHET_ADVICE = (
    "HOW TO LOWER A BASELINE HONESTLY: fix the site -- name the branch in the same "
    "sentence as the coverage figure, or state the dichotomy instead of one arm of it -- "
    "then lower this file's number in KNOWN_OPEN in the SAME commit, and say in the "
    "message which site you fixed.\n"
    "      HOW IT IS LOWERED DISHONESTLY, so that it is recognisable when the suite is red "
    "and the deadline is close: raising the pin to whatever the run just printed, "
    "deleting the file's entry, adding the file to OUT_OF_SCOPE, or widening a gate "
    "(`denial`, `absent`, `_BRANCH_NAMED`) until the finding disappears. The last is the "
    "hardest to spot and the worst, because it disarms the rule everywhere at once while "
    "looking like a fix -- results/n40_floor_estimator_ruling.md sec. 13 is the ruling a "
    "widened `_BRANCH_NAMED` would quietly repeal. Do none of them without saying so.")

# --------------------------------------------------------------------------------------
# CONDITIONAL AWARENESS, for the retired positions that are stated in WORDS.
#
# `near` is a gate that says "fire only if this cue is nearby", and it is how a bare
# decimal is kept from meaning something it does not. The word rules below need the
# OPPOSITE gate, for a reason specific to this class of defect: the retracted claims are
# not false sentences. They are TRUE BRANCHES of a dichotomy, asserted as though the
# dichotomy had been settled. `paper/sections/discussion.tex` says "a larger pool reaches
# a higher rung and reports a smaller floor" and is CORRECT, because the clauses on either
# side of it state the other branch. A flat phrase match would go red on the one site in
# the repo that gets this right, and a guard that fires on correct usage teaches its user
# to silence it -- "a check that cannot fail is not a check" wearing its other face.
#
# So `absent` lists patterns that EXCULPATE, and `span` says how far the search for them
# may run -- measured in SENTENCE BOUNDARIES, not characters.
#
# WHY NOT THE OBVIOUS SPELLING. The natural way to write this is a negative lookahead
# bounded by `[^.]*`, and it is wrong twice over. `[^.]*` stops dead at the decimal point
# of `2.0`, so a correct conditional sentence with a number in it fires anyway; and a
# lookahead cannot look BACKWARD, which is where the correct sites in this repo put their
# conditional ("If it is not, a larger pool reaches a higher rung and ..."). `_TERM_RE`
# already solves the decimal problem -- `[.:;!?](?=\s)` only ends a sentence when
# whitespace follows -- and it is already exercised by the label geometry above. Note that
# a semicolon IS a terminator here, which matters: the if/else at discussion.tex is joined
# by one, so `span` must be at least 1 for the forward half of that site to be visible.
# The backward half ("If it is not,") is visible at span 0, and both are checked below.
# `ABSENT_SPAN = 1` USED TO SIT HERE AS A DEFAULT AND IT WAS DEAD, removed 2026-08-27.
# Every rule with an `absent` gate states its own `span`, so `item.get("span",
# ABSENT_SPAN)` never once took the fallback -- which is why setting the constant to 9 left
# the entire suite green. A default nobody takes is a claim about the code that is not
# true, and this file's own standard for that is stated three times over: a check that
# cannot fail is not a check. `span` is now REQUIRED on any entry with `absent`, and
# test_every_absent_rule_states_its_own_span holds it there.
#
# ABSENT_CHAR_CAP survives, but it needed the same interrogation and it now has a mutation
# test of its own (test_mutation_raising_the_char_cap_licenses_a_distant_exculpation).
# Without it a passage with no terminators in it -- a generated table, a `log(...)` block,
# a Python comment run through `strip_plain`, all of which this repo is full of -- would
# let a branch name 5000 characters up the page exculpate a bare coverage figure.
ABSENT_CHAR_CAP = 600  # a hard stop, so unpunctuated prose is not a blanket licence


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


def strip_plain(text: str) -> str:
    r"""Flatten Markdown / Python / shell / JSON. The TIER-2 flattener.

    THIS EXISTS BECAUSE `strip_latex` IS A LATEX FLATTENER AND SAYS SO. Applied to a `.md`
    or `.py` file it deletes from an unescaped `%` to end of line -- correct for a LaTeX
    comment, catastrophic here, since `53.7% of the time and the` becomes `53.7` and
    `0.00%` becomes `0.00`, which `PCT` (a REQUIRED percent sign) then refuses. That single
    behaviour is the whole of the 16 -> 14 gap the previous phase measured and pinned in
    test_strip_latex_is_not_safe_for_the_files_this_ledger_is_aimed_at. The blocker was
    named before the scope moved; this is the fix, and the pin now asserts BOTH halves --
    that `strip_latex` still behaves that way (Table 1's saturation row depends on it) and
    that this function does not.

    WHAT IT DOES, and every line of it is one of the sixteen sites' markup:

      backticks     `results/n40_floor_estimator_ruling.md`, `4/200`, and the ``` fences
                    around every generated block. A backtick inside a phrase splits it the
                    way `\emph{}` split "fair pool" for the manual sweeps.
      `*` emphasis  docs/START_HERE_overnight.md carried "a resolution limit of the *pool*
                    and not a property of the detector" -- the retired sentence with one
                    asterisk pair in the middle of it, which is a phrase rule's blind spot
                    exactly.

    WHAT IT DELIBERATELY DOES NOT DO, each with its reason:

      `_` IS NOT AN EMPHASIS MARKER HERE. It is the word separator in every path,
      identifier and constant this repo cites -- `n40_floor_estimator_ruling.md`,
      `_BRANCH_NAMED`, `at_cap` -- and blanking it turns the ruling's filename into four
      words. `check_operational_provenance.py`'s `strip_markup` makes the same call for the
      same reason and states it in the same place. The cost is a real blind spot: a
      markdown `_estimand_` written with underscore emphasis breaks `\b` and is not seen.
      Accepted, and it is in the residual list below rather than hidden.

      `$`, `{`, `}` ARE LEFT ALONE. They are math delimiters in .tex and nothing of the
      kind here: `$HOME` in a shell script, an f-string's braces in Python, a JSON object.
      Blanking them buys no phrase repair and mangles source.

      NO `\command` STRIPPING. Python string literals carry `\"` and `\n`; there are no
      LaTeX commands to remove.

    Same-length-out is NOT preserved (nor is it in `strip_latex`), which is why `_line_hint`
    re-searches the RAW text for a source line rather than trusting an offset.
    """
    text = re.sub(r"`{1,3}", " ", text)                          # fences and code spans
    text = re.sub(r"(?<![*\w])\*{1,3}(?=\S)", " ", text)         # opening * emphasis
    text = re.sub(r"(?<=\S)\*{1,3}(?![*\w])", " ", text)         # closing * emphasis
    return re.sub(r"\s+", " ", text)


def flatten(text: str, suffix: str) -> str:
    """Per-suffix flattener. `.tex` keeps the LaTeX one; everything else gets `strip_plain`.

    Dispatching on SUFFIX rather than on directory is deliberate and load-bearing for the
    tests: every one of the hundred-odd probes in tests/test_population_labels.py writes a
    `probe.tex` into a tmp_path that is nowhere near `paper/`, and they must go on getting
    the LaTeX flattener and the full ruleset. It is also the honest rule -- the pool and
    growing families are written for LaTeX prose, not for the directory they happen to sit
    in -- so a `.tex` file that ever appears outside `paper/` is FLATTENED as one. Note the
    limit of that: WIDE_GLOBS names no `.tex` pattern, so such a file is not REACHED at all
    until someone adds one. Suffix decides the ruleset; the globs decide the reach.
    """
    return strip_latex(text) if suffix == ".tex" else strip_plain(text)


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


def _absent_window(flat: str, terms: list[int], start: int, end: int,
                   span: int) -> tuple[int, int]:
    """The stretch of text a provenance hit may look at for an EXCULPATING phrase.

    `span=0` is the hit's own sentence; each further unit adds one sentence on each side.
    Clipped to ABSENT_CHAR_CAP in both directions so that a passage with no terminators in
    it cannot license a hit from arbitrarily far away.
    """
    i = bisect_left(terms, start) - 1 - span
    lo = terms[i] + 1 if i >= 0 else 0
    j = bisect_left(terms, end) + span
    hi = terms[j] if j < len(terms) else len(flat)
    return max(lo, start - ABSENT_CHAR_CAP), min(hi, end + ABSENT_CHAR_CAP)


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




def _clause_scope(flat: str, start: int) -> int:
    """Index where the clause containing `start` begins. See `_CLAUSE_BREAK_RE`."""
    lo = 0
    for m in _CLAUSE_BREAK_RE.finditer(flat, 0, start):
        lo = max(lo, m.end())
    return lo


def _clause_bounds(flat: str, terms: list[int], pos: int) -> tuple[int, int]:
    """The SENTENCE-ish unit around `pos`, as (lo, hi).

    Deliberately NOT `_CLAUSE_BREAK_RE`. That function's job is to decide whether a
    negation reaches a claim, where a coordinating conjunction genuinely starts a new
    clause. Estimator ownership needs the wider unit: `discussion.tex:310` writes
    "the direct N=10 row is a count ... AND takes Wilson", where the row and its predicate
    sit either side of a bare `and`, and a boundary there would blind the rule to the one
    correct sentence it most needs to read. The SEMICOLON in that same line is what has to
    stop the search, and `_TERM_RE` already treats it as one.
    """
    i = bisect_left(terms, pos) - 1
    lo = terms[i] + 1 if i >= 0 else 0
    j = bisect_left(terms, pos)
    hi = terms[j] if j < len(terms) else len(flat)
    return lo, hi


def _is_disowned(flat: str, start: int, end: int, terms: list[int]) -> bool:
    """True if this occurrence of a retired position is being DISOWNED rather than made.

    D2 and D3 only. D1 -- "the claim's own verb is negated" -- is NOT implemented here,
    and the reason is worth stating because the obvious implementation is a trap. A
    span-internal negator test cannot tell a DENIAL from a CONSTITUTIVE negation, and half
    the patterns in this ledger contain one: `neither estimator is broken`, `not a property
    of the detector`, `estimand ... no longer exists`, `takes neither`. Every one of those
    would exculpate itself on the very word that makes it a defect -- measured, on the
    first build of this gate: "The at-cap mass takes neither" went green, and so did four
    probes that had been red since round five.
    So the claim's own verb is negated WHERE THE PATTERN CAN SEE IT: the estimand rule
    carries a TEMPERED gap that refuses to span a negator, which is the same job done in
    the one place that knows which words are the claim's own. That mechanism predates this
    gate and has its own mutation test.
    """
    if _DISOWN_RE.search(flat[_clause_scope(flat, start):start]):
        return True                                             # D2
    # D3, two keys. Key (i): quoted, or attributed in the past tense earlier in the same
    # sentence. Key (ii): a disavowal within a sentence either side.
    quoted = any(q.start() < end and start < q.end() for q in _QUOTE_RE.finditer(flat))
    sent_lo, _ = _clause_bounds(flat, terms, start)
    attributed = bool(_ATTRIBUTED.search(flat[sent_lo:start]))
    if quoted or attributed:
        lo, hi = _absent_window(flat, terms, start, end, 1)
        if _DISAVOWAL_RE.search(flat[lo:hi]):
            return True
    return False


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
    """Repo-relative, POSIX separators, on every platform.

    `str(Path)` gives `results\\replay_control.md` on Windows, and the ratchet's keys are
    written `results/replay_control.md` -- so a native-separator name silently misses every
    KNOWN_OPEN entry and reports a 32-finding backlog as 32 NEW findings. Found by the
    first dry run rather than by reasoning, which is the argument for running one.
    `check_operational_provenance.py` uses `.as_posix()` here for the same reason.
    """
    try:
        return path.relative_to(REPO).as_posix()
    except ValueError:
        return path.name


def _line_hint(raw: str, matched: str) -> str:
    """Best-effort source line for a token that markup may have split (`$22$ of the $39$`).

    TWO PASSES, and the second one was added 2026-08-27 for the estimator-ownership rule.
    The flatteners collapse newlines, so a matched phrase routinely straddles a line break
    in the source -- and the index case is exactly that shape:

        the measured $N{=}40$ floor is a count at no fixed threshold at all and takes the
        question bootstrap for the reason given above.

    A per-line search can never find `takes the question bootstrap` there, so the finding
    was printed with no line number at all -- on the one sentence this whole round exists
    to catch. The second pass joins each adjacent PAIR of lines and reports the first of
    the pair, which is where a reader should start looking. Pairs only: three-line spans
    are rare enough, and widening the search costs precision in a file that repeats its
    values on every table row.
    """
    parts = [re.escape(p) for p in matched.split() if p]
    if not parts:
        return ""
    pat = re.compile(r"[\s$\\{}~]*".join(parts), re.IGNORECASE)
    lines = raw.splitlines()
    for i, line in enumerate(lines, 1):
        if pat.search(line):
            return f":{i}"
    for i in range(len(lines) - 1):
        if pat.search(lines[i] + " " + lines[i + 1]):
            return f":{i + 1}"
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


def _check_provenance(raw: str, flat: str, terms: list[int], shown: str,
                      items: list[dict] | None = None) -> list[str]:
    """Catch a number -- or a POSITION -- that outlived the ruling it was computed under.

    Three gates. `near` requires a cue to be PRESENT before firing (a bare decimal that
    means nothing on its own). `absent` requires one to be ABSENT within `span` sentences
    (a phrase that is correct when it names the branch it belongs to, and retracted when
    it does not). `denial` asks `_is_disowned` -- named DISOWNING CONSTRUCTIONS, not
    a proximity-to-a-negative-word test -- so a retired position that is being disowned
    ("it is NOT that the estimand dissolves: ruling sec. 13 retracts that sentence",
    `docs/START_HERE_overnight.md`) or quoted in order to be withdrawn ("This banner said
    '...' until 2026-08-26") stays green, while "The reason is not obvious, but the
    estimand dissolves" does not. See the block above `_is_disowned` for what each
    construction is and what the gate costs.

    `items` selects the ledger. It defaults to all of SUPERSEDED (tier 1, `paper/*.tex`);
    tier 2 passes WIDE_SUPERSEDED, the eight retired POSITIONS. See the SCOPE section of
    the module docstring for the 1083-finding measurement behind that split.
    """
    problems: list[str] = []
    for item in (SUPERSEDED if items is None else items):
        for hit in re.finditer(item["pattern"], flat, re.IGNORECASE):
            if "near" in item:
                lo = max(0, hit.start() - NEAR_WINDOW)
                hi = min(len(flat), hit.end() + NEAR_WINDOW)
                ctx = flat[lo:hi]
                if not any(re.search(p, ctx, re.IGNORECASE) for p in item["near"]):
                    continue
            if "absent" in item:
                lo, hi = _absent_window(flat, terms, hit.start(), hit.end(),
                                        item["span"])
                if any(re.search(p, flat[lo:hi], re.IGNORECASE) for p in item["absent"]):
                    continue
            if item.get("denial") and _is_disowned(flat, hit.start(), hit.end(), terms):
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


def _check_ownership(raw: str, flat: str, terms: list[int], shown: str) -> list[str]:
    """Flag a row of the floor table assigned to the wrong estimator.

    A POSITION rule whose answers are a TABLE: see the block above `OWNERSHIP_ROWS` for
    why the vocabulary is closed, why the row's correct estimator is data rather than a
    regex, and why an ambiguous row name (a bare "N=20 floor") is deliberately absent.

    The arbitration is the same shape the pool rules use -- nearest binding name wins --
    with two differences that both push toward silence. There is no trailing penalty,
    because "we quote a question bootstrap interval FOR the measured N=40 floor" puts the
    row after the phrase and is as much an assertion as the other order; and a phrase with
    no row name in its clause is not reported at all, because the guard cannot know which
    row was meant and guessing here means reddening correct prose.
    """
    problems: list[str] = []
    names: list[tuple[int, int, dict]] = []
    for spec in OWNERSHIP_ROWS:
        for pat in spec["names"]:
            for m in re.finditer(pat, flat, re.IGNORECASE):
                names.append((m.start(), m.end(), spec))

    for hit in _OWNERSHIP_RE.finditer(flat):
        claimed = next(k for k in _EST_PATTERNS if hit.group(k))
        # `_is_disowned` reads only OUTER constructions, which is what this rule needs:
        # one of the three estimator names IS a negator, so a span-internal test would let
        # "the at-cap mass takes neither" exculpate itself on the word that makes it a
        # defect. "The N=40 floor does NOT take the question bootstrap" puts its negator
        # before the predicate, where D2 reads it.
        if _is_disowned(flat, hit.start(), hit.end(), terms):
            continue
        lo = max(_clause_bounds(flat, terms, hit.start())[0],
                 hit.start() - OWNERSHIP_CHAR_CAP)
        hi = min(_clause_bounds(flat, terms, hit.end())[1],
                 hit.end() + OWNERSHIP_CHAR_CAP)
        best = None
        for ns, ne, spec in names:
            if ns >= hit.start() and ne <= hit.end():
                continue                       # the phrase cannot name its own row
            if ne <= hit.start():
                dist = hit.start() - ne
                if ns < lo:
                    continue
            elif ns >= hit.end():
                # A row name AFTER the phrase has to be its OBJECT, and the test is
                # asymmetric on purpose. Before the phrase, a row name is the subject and
                # any amount of clause may sit between them: "the measured N=40 floor is a
                # count at no fixed threshold at all AND takes the question bootstrap" is
                # the index case, and a backward clause-break test would lose it on that
                # `and`. After the phrase, a coordinating conjunction means a NEW clause
                # with a new subject, which is live repo text --
                #     "takes Wilson, as everywhere else in the paper, and only the replayed
                #      rows ... take the bootstrap"   (scripts/replay_control.py:1131)
                # -- where "the replayed rows" is the subject of the next clause and has
                # nothing to do with the Wilson assertion. So a trailing row must be close
                # and unbroken: at most OWNERSHIP_OBJECT_GAP characters, with no clause
                # break between. "we quote a question bootstrap interval FOR the measured
                # N=40 floor" clears both.
                dist = ns - hit.end()
                gap = flat[hit.end():ns]
                if ne > hi or dist > OWNERSHIP_OBJECT_GAP:
                    continue
                if _CLAUSE_BREAK_RE.search(gap):
                    continue
            else:
                dist = 0
            if best is None or dist < best[0]:
                best = (dist, spec, flat[ns:ne])
        if best is None:
            continue                           # no row named -- nothing to check against
        _, spec, named = best
        if claimed == spec["takes"]:
            continue
        want = ("NEITHER estimator" if spec["takes"] == "neither"
                else f"the {spec['takes']}")
        where = f"{shown}{_line_hint(raw, hit.group(0))}"
        snippet = flat[max(0, hit.start() - 110):hit.end() + 110].strip()
        problems.append(
            f"{where}: [estimator ownership] WRONG ESTIMATOR FOR THIS ROW.\n"
            f"      '{hit.group(0).strip()}' assigns "
            f"{'no estimator' if claimed == 'neither' else 'the ' + claimed} to "
            f"'{named}' -> {spec['row']},\n"
            f"      which takes {want}: {spec['why']}.\n"
            f"      {OWNERSHIP_ADVICE}.\n"
            f"      context: ...{snippet}...")
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
    """Every problem in one file. The RULESET depends on the suffix -- see `flatten`.

    `.tex`        tier 1: pools + provenance (every entry) + growing denominators +
                  estimator ownership.
    anything else tier 2: the retired POSITIONS only -- the `wide` half of SUPERSEDED and
                  estimator ownership -- on the plain flattener.

    ESTIMATOR OWNERSHIP RUNS IN BOTH TIERS, and it belongs in tier 2 by the same property
    test as the `wide` flag: its finding is a POSITION ("this row takes neither"), never a
    recomputed value. A value is stored, pinned and corrected all over this repo; an
    assignment of the wrong estimator to a row is only ever asserted.

    The tier-2 findings are what the ratchet counts, so this returns them and does not
    apply the baseline; `main` does that, because a baseline is a property of a file's
    place in the register and not of the file.
    """
    raw = path.read_text(encoding="utf-8", errors="replace")
    flat = flatten(raw, path.suffix)
    terms = _terminators(flat)
    shown = _rel(path)
    if path.suffix == ".tex":
        return (_check_pools(raw, flat, terms, shown)
                + _check_provenance(raw, flat, terms, shown)
                + _check_ownership(raw, flat, terms, shown)
                + _check_growing(raw, flat, shown))
    return (_check_provenance(raw, flat, terms, shown, items=WIDE_SUPERSEDED)
            + _check_ownership(raw, flat, terms, shown))


def paper_files(repo: Path | None = None) -> list[Path]:
    root = (repo or REPO) / "paper"
    return sorted(root.glob("*.tex")) + sorted((root / "sections").glob("*.tex"))


def wide_files(repo: Path | None = None) -> list[Path]:
    """Tier-2 targets: WIDE_GLOBS minus OUT_OF_SCOPE, de-duplicated, in display order."""
    repo = repo or REPO
    seen: dict[str, Path] = {}
    for g in WIDE_GLOBS:
        for f in sorted(repo.glob(g)):
            if f.is_file():
                rel = f.relative_to(repo).as_posix()
                if rel not in OUT_OF_SCOPE:
                    seen.setdefault(rel, f)
    return [seen[k] for k in sorted(seen)]


def _ratchet(counts: dict[str, int]) -> list[str]:
    """Compare tier-2 findings against KNOWN_OPEN. BOTH directions are failures.

    A file that GAINS a finding fails, which is the point. A file that LOSES one also
    fails, so the register cannot be raised and then left -- that is defect 7's shape (a
    registry that expired while the guard went on trusting it), and this is the third list
    in this file to carry that failure mode.
    """
    problems: list[str] = []
    for shown in sorted(set(counts) | set(KNOWN_OPEN)):
        found = counts.get(shown)
        baseline = KNOWN_OPEN.get(shown, 0)
        if found is None:
            problems.append(
                f"{shown}: ratchet-orphan: KNOWN_OPEN pins {baseline} finding(s) in a file "
                f"that is no longer in tier-2 scope.\n"
                f"      Either the file moved and WIDE_GLOBS has to follow it, or it was "
                f"deleted and the entry goes with it. A register that outlives its subject "
                f"is how the hide arm stayed 'open' for six days after it closed.")
            continue
        if found > baseline:
            problems.append(
                f"{shown}: ratchet: {found} retired-position finding(s) against a baseline "
                f"of {baseline}. {found - baseline} NEW one(s).\n"
                f"      {RATCHET_ADVICE}")
        elif found < baseline:
            problems.append(
                f"{shown}: ratchet-stale: {found} finding(s) against a baseline of "
                f"{baseline}. Progress -- lower KNOWN_OPEN['{shown}'] to {found} in the "
                f"same commit, so the register cannot rot upward.")
    return problems


def scope_census(repo: Path | None = None) -> dict[str, tuple[int, int]]:
    """What each rule FAMILY would report over the tier-2 files. (findings, files) each.

    THE SCOPE ARGUMENT IS A MEASUREMENT, so it has to be re-runnable rather than quoted
    from a session nobody can reproduce. Every number in the module docstring's SCOPE
    section comes from here and is printed by `--dry-run`. If a family's count collapses,
    the argument for keeping it out of tier 2 has weakened and the line should be moved
    deliberately, in a commit that says the new number -- not by noticing a comment aged.
    """
    narrow = [s for s in SUPERSEDED if not s.get("wide")]
    tally = {k: [0, 0] for k in ("pools", "growing", "retired-value", "retired-position")}
    for f in wide_files(repo):
        raw = f.read_text(encoding="utf-8", errors="replace")
        flat = flatten(raw, f.suffix)
        terms = _terminators(flat)
        shown = _rel(f)
        for key, found in (
                ("pools", _check_pools(raw, flat, terms, shown)),
                ("growing", _check_growing(raw, flat, shown)),
                ("retired-value",
                 _check_provenance(raw, flat, terms, shown, items=narrow)),
                # ESTIMATOR OWNERSHIP IS COUNTED INSIDE `retired-position`, not beside it.
                # The census row has to equal what tier 2 actually runs, or the ratchet and
                # the argument the docstring makes from the census drift apart -- and two
                # lists that must be edited together and are not is the shape this file has
                # logged three times.
                ("retired-position",
                 _check_provenance(raw, flat, terms, shown, items=WIDE_SUPERSEDED)
                 + _check_ownership(raw, flat, terms, shown))):
            if found:
                tally[key][0] += len(found)
                tally[key][1] += 1
    return {k: (v[0], v[1]) for k, v in tally.items()}


def _dry_run(repo: Path | None = None) -> int:
    """Per-file tier-2 counts beside the pin, plus the family census. Always exits 0.

    This is how the register is re-struck honestly: it prints what IS next to what is
    PINNED, so the two can be compared without the pressure of a red suite.
    """
    files = wide_files(repo)
    for f in files:
        shown = _rel(f)
        n = len(check_file(f))
        pin = KNOWN_OPEN.get(shown, 0)
        if n or pin:
            mark = "  " if n == pin else ("<-" if n < pin else "->")
            print(f"{mark} {shown:46s} found {n:3d}   pinned {pin:3d}")
    print("   (-> a file has GAINED findings; <- it has lost some and the pin is now "
          "stale -- lower it)")
    print(f"\n{len(files)} tier-2 files, {len(OUT_OF_SCOPE)} excluded by name, "
          f"{len(WIDE_SUPERSEDED)} retired-position rules + {len(OWNERSHIP_ROWS)} "
          f"ownership rows, "
          f"{sum(KNOWN_OPEN.values())} finding(s) pinned in {len(KNOWN_OPEN)} file(s).")
    # WHAT THE EXCLUSIONS COST, PRINTED RATHER THAN QUOTED. Each of these reasons used to
    # carry a hand-written count and four of the eight had gone stale within a day. A
    # figure a reader can re-derive on demand cannot go stale; one written into a comment
    # always does.
    print("\nExcluded by name, with what each would report if it were not (see "
          "OUT_OF_SCOPE for why each is out):")
    root = repo or REPO
    for shown in sorted(OUT_OF_SCOPE):
        f = root / shown
        n = len(check_file(f)) if f.is_file() else -1
        print(f"  {shown:46s} {'MISSING' if n < 0 else f'{n:5d} finding(s)'}")
    print("\nWhat each family WOULD report over those files -- the measurement the tier-2 "
          "line rests on\n(module docstring, SCOPE). Only the last row runs:")
    for name, (found, in_files) in scope_census(repo).items():
        runs = "RUNS" if name == "retired-position" else "scoped to .tex"
        print(f"  {name:18s} {found:5d} finding(s) in {in_files:3d} file(s)   [{runs}]")
    return 0


def main(argv: list[str] | None = None) -> int:
    argv = sys.argv[1:] if argv is None else argv
    if "--dry-run" in argv:
        return _dry_run()

    targets = paper_files()
    if not targets:
        print("no .tex files found under paper/", file=sys.stderr)
        return 1
    problems: list[str] = []
    for t in targets:
        problems.extend(check_file(t))

    wide = wide_files()
    counts: dict[str, int] = {}
    wide_problems: list[str] = []
    for f in wide:
        found = check_file(f)
        counts[_rel(f)] = len(found)
        wide_problems.extend(found)
    ratchet = _ratchet(counts)
    # The findings themselves are printed only for files that BREACH the ratchet. Printing
    # all 32 pinned ones on every red run buries the new one among them, and this file's
    # own docstring says a guard whose user learns to skip its output has the same end
    # state as a guard that cannot fail. `--dry-run` prints the register on demand.
    breached = {p.split(":")[0] for p in ratchet}
    problems.extend(p for p in wide_problems if p.split(":")[0] in breached)
    problems.extend(ratchet)

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
              "clause that carries the number. The third is disjoint from both.\n"
              "\nOUTSIDE paper/ only the RETIRED POSITIONS are checked -- the claims that "
              "sec. 13 of results/n40_floor_estimator_ruling.md withdraws, which carry no "
              "digit and which four rounds of review missed for exactly that reason. "
              "tau_top is NOT IDENTIFIED at n=200: state the dichotomy, or name the branch "
              "a coverage figure was measured under, but never one arm of it alone.")
        return 1

    n_numbers = sum(len(r["numbers"]) for r in RULES)
    print(f"population-label check: OK ({len(targets)} paper files, {len(RULES)} rules, "
          f"{n_numbers} number patterns, {len(SUPERSEDED)} superseded-run patterns, "
          f"{len(GROWING_CELLS)} growing-cell patterns over {len(FROZEN_COUNTS)} frozen "
          f"counts; {len(wide)} wider files on {len(WIDE_SUPERSEDED)} retired-position "
          f"rules and {len(OWNERSHIP_ROWS)} estimator-ownership rows, "
          f"{sum(KNOWN_OPEN.values())} finding(s) pinned in {len(KNOWN_OPEN)})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
