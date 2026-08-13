"""Fail the build when a population-sensitive number is unlabelled, MISLABELLED, or STALE.

WHY THIS EXISTS. Binding a statistic to the wrong population is this project's most-repeated
error: it has now been found and fixed at SIX separate sites (critique_log 28, 31), each time
by a manual sweep, and each sweep found a site the previous one missed. A manual process that
has failed six times should not be the guard on the seventh.

TWO POPULATIONS, and they are not interchangeable:

  fair pool      200 correct + 200 hallucinating, drawn score-independently.
                 AUROC 0.704 [0.653, 0.753]; separation 0.463 nats, d ~ 0.76.
                 Clean means 1.380 (correct) / 1.843 (wrong), headroom 0.923.
                 The ONLY population on which claims about "the detector" may be made.

  attacked pool  97 targets = 80 correct + 17 wrong, the attack campaign's own targets,
                 with the hide arm truncated mid-campaign.
                 AUROC 0.579; separation 0.184 nats, d = 0.28. QUARANTINED for any
                 class-separation claim. The ceiling and granularity statistics (8/80 at
                 the cap, 21/80 in the top tenth, 22 of 39 values realised, 42/80 = 52.5%
                 at the cap after attack) live HERE.

THEY ARE NESTED, NOT DISJOINT. The attacked targets are literally the first 80 of the fair
pool's 200 correct (src/se/attacks/select.py, _stratum_ids + [:n]). So a sentence may
legitimately mention the fair pool *as the provenance* of an attacked-pool number
("the 80 targets are drawn from the fair pool's correct stratum"). Nothing here may assume
disjointness; see NON_BINDING_CUES.

THE MARKUP LESSON. The critic's own grep for "fair pool" missed conclusion.tex because the
source reads `\\emph{fair} pool`. Phrase matching does not survive LaTeX. So we strip markup
before matching, and we anchor on NUMBERS, which markup cannot split.

--------------------------------------------------------------------------------------
WHAT THIS CHECKS (and why the first version of it was near-vacuous)

An audit constructed eight genuine population errors and the original rule missed seven.
Every miss had the same shape: the rule asked whether an allowed label was PRESENT within
420 characters, which in a paper that discusses both pools contrastively in one paragraph is
almost always true -- exactly where the error is likeliest. Four defects, all now closed:

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
     FIX: labels are POOL PHRASES ("attack campaign", "attacked subset", "97 targets"), and
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
  * The oracle-calibrated vs shipped power figures (0.84/0.71 vs 0.77/0.51) are a
    test-variant provenance problem, not a population one, and are not guarded here.
  * Numbers rendered as words ("a tenth", "a quarter", "past half", "nearly two fifths")
    are invisible to a number-anchored check -- for staleness as much as for population.
    They are the reason prose claims still need a human read.
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
        "what": "attacked pool (the optimiser's own targets; 80 correct + a truncated "
                "wrong stratum)",
        "labels": [
            r"attacked pool", r"attacked subset", r"attacked targets", r"attacked sample",
            r"attack pool", r"attack campaign", r"attack arm", r"attacked stratum",
            r"false-alarm attack pool", r"false-alarm targets", r"false-alarm arm",
            r"97 targets", r"97-target",
            NOT_A_DENOMINATOR + r"\b80 correct",
            NOT_A_DENOMINATOR + r"\b80 false-alarm",
            NOT_A_DENOMINATOR + r"\b17 wrong",
            NOT_A_DENOMINATOR + r"\b17 hide",
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
        "what": "our own SE replication run on TriviaQA",
        "labels": [r"replicat"],
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
    {
        "name": "97-target pool identity",
        "owner": "attacked",
        "foreign": ["fair"],
        "numbers": [r"97 targets", r"across 97", r"97-target"],
        # NOT the full attacked label list: "97 targets" must not license itself.
        "requires": [r"attack campaign", r"attacked (?:pool|subset|targets)",
                     r"attack (?:pool|arm)", NOT_A_DENOMINATOR + r"\b80 correct",
                     NOT_A_DENOMINATOR + r"\b17 wrong",
                     r"targets the optimiser was run on"],
        "window": 300,
    },
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
        "name": "our SE replication AUROC",
        "owner": "replication",
        "foreign": ["fair", "attacked"],
        "numbers": [r"0\.787"],
        "window": 300,
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
]
SUPERSEDED_RUN = "wk9_def"
CURRENT_RUN = "wk9_defb"
NEAR_WINDOW = 300


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
                if foreign_best is not None:
                    fc, fs, ftext, fpool = foreign_best
                    beaten = (own_prox is None
                              or fc < own_prox[0]
                              or (fc == own_prox[0] and fs + MARGIN < own_prox[1]))
                    if beaten:
                        near = ("no owning-pool label within "
                                f"{prox} chars" if own_prox is None
                                else f"its own label '{own_prox[2]}' binds less tightly")
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
                        f"{where}: [{rule['name']}] UNLABELLED.\n"
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


def check_file(path: Path) -> list[str]:
    raw = path.read_text(encoding="utf-8", errors="replace")
    flat = strip_latex(raw)
    terms = _terminators(flat)
    shown = _rel(path)
    return _check_pools(raw, flat, terms, shown) + _check_provenance(raw, flat, shown)


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
              "near a mention of one. The two are NOT interchangeable: 0.704 is the fair "
              "pool (200+200); the ceiling, granularity and saturation counts are the "
              "97-target attacked pool. They are nested, not disjoint, so say which one "
              "you mean in the clause that carries the number.")
        return 1
    n_numbers = sum(len(r["numbers"]) for r in RULES)
    print(f"population-label check: OK ({len(targets)} files, {len(RULES)} rules, "
          f"{n_numbers} number patterns, {len(SUPERSEDED)} superseded-run patterns)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
