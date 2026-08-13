"""Fail the build when an OPERATIONAL number that schedules work has no provenance.

WHY THIS EXISTS, AND WHY IT IS NOT check_population_labels.py.

`check_population_labels.py` guards the paper's FACTUAL numbers -- which pool a rate belongs
to, which run produced it. It has caught real errors. It has nothing to say about the other
class of number in this repo: GPU-hours, seconds per evaluation, targets per night, per-cell
costs, batch sizes, capacities and deadlines. Those numbers never enter the paper (with one
exception, below) and they are not claims about the world. They are worse: they decide what
runs, what gets cut, and in what order, and they do it silently.

THE FAILURE, in full, because the shape of it is the whole design of this file.

On 2026-08-13 at 22:56 the definitive null control was moved to the back of the overnight
queue on the stated grounds that it had "~60 GPU-h left against a ~10 h night". That figure
was a MODEL: 55 clusterings/target at ~55 s each. The 55 s came from a K=8 probe recorded in
`docs/critique_log.md` entry 22 on 2026-08-02 and was carried forward, untouched, for eleven
days -- through entry 26a's pre-registration ("~67 GPU-hours"), through
`docs/definitive_run_plan.md`, through `docs/START_HERE_overnight.md`, and into the queue
header -- to cost a K=50 run at a different judge batch size.

Re-derived from three filesystem anchors on the run's own output, the true figure is 24.0 s
per clustering, 1191 s per target, 23-26 GPU-h. The correction was written into
`results/null_control_cost_options.md` at 23:27 the previous evening -- TWELVE AND A HALF
HOURS before the queue header that contradicted it was committed. Nothing was missing. The
measurement existed, on disk, in this repo, and the decision was taken against the model
anyway.

`results/operational_number_audit.md` then found the same failure at fifteen more sites,
including one in the paper (`experiments.tex:173`, "$228$ GPU-hours", 2.3x the measured
figure) and two that reverse a live decision.

WHAT A SCRIPT CAN AND CANNOT DO ABOUT THAT. Four parts, and only three are mechanisable:

  (a) IS IT TAGGED -- does an operational figure say whether it was measured or modelled?
      Mechanisable, but see THE RATCHET below: it cannot start green.

  (b) HAS A KNOWN-DEAD ANCHOR REAPPEARED -- mechanisable, zero baseline, and it is the
      highest-value rule here, because "55 s -> 67 GPU-h -> 60 GPU-h -> a scheduling
      decision" is a chain of literal restatements. DEAD_ANCHORS, below.

  (c) HAS THE UNDERLYING JOB SINCE RUN -- "a modelled figure must be re-derived once any of
      that work has run". A script cannot infer that `null_control_ckpt_defb.jsonl`
      supersedes "~67 GPU-h". It CAN require a MODELLED figure to declare its own trigger
      (`supersede-when: <path>`) and fail the moment that path appears on disk. Existence is
      binary, cheap, and needs no judgement.

  (d) IS THIS ANCHOR THE RIGHT ANCHOR FOR THIS JOB -- NOT MECHANISABLE. Nothing in the
      string "55 s" says it was measured at K=8. Nothing in "2.8 s" says it is a pro-rata
      token split of a call that also generates 480 tokens. Nothing in "73.9 s/eval" says
      generation was assumed linear in N when it is in fact flat. EVERY error the audit
      found is a type-(d) error. The only defence is that the anchor be NAMED IN PROSE next
      to the number, where a human reads it in the same glance -- which is what the
      `anchorless-model` rule forces. This script's job is not to catch the error. It is to
      make the error legible.

SCOPE, and why the critique log is deliberately outside it.

Guarded: live planning and decision documents -- the ones a person reads to decide what to
run tonight. `docs/START_HERE_overnight.md`, `docs/definitive_run_plan.md`,
`results/*_plan.md`, `results/*_options.md`, `results/derived_paper_quantities.md`,
`results/operational_number_audit.md`, `paper/sections/*.tex`, `scripts/overnight_*.sh`.

NOT guarded: `docs/critique_log.md` and `results/OVERNIGHT_*.md`. They are append-only
history. Rewriting history to satisfy a linter is worse than the disease, and the danger
from the log was never that it CONTAINS a dead number -- entry 22's 55 s was correct for
K=8 -- but that the number is QUOTED FORWARD. Forward is where the scope is.

THE RATCHET, and why this file does not simply demand tags everywhere.

Most operational numbers in this repo live in SCRIPT-GENERATED markdown:
`n_scaling_plan.md` from `n_scaling_grid.py`, `null_control_cost_options.md` from
`null_control_cost_options.py`, `judge_owed_conditions.md` from `judge_owed_conditions.py`,
and so on. Hand-tagging those files is wrong -- the next run overwrites the tags -- and the
fix belongs in the generators, one of which is off-limits while the GPU queue is on it.

A blanket "every GPU-h figure must be tagged" gate would therefore be RED ON ARRIVAL across
files nobody can currently fix. This repo already knows both halves of what happens next:
"A green test suite next to a known-broken statistic reads as validation of it" -- and a
permanently red one reads as nothing at all, which is worse, because it takes the other four
rules down with it.

So `untagged` is a RATCHET. KNOWN_OPEN records the exact number of untagged figures in each
scoped file today. The check fails when a file gains one, not because it has some. That is
the same device `check_population_labels.py` uses for SUPERSEDED, and it worked there.
When a generator is fixed, lower its entry; a file that drops BELOW its baseline also fails,
so the register cannot silently rot upward.

WHAT THIS STILL CANNOT CATCH -- read before trusting a green run:

  - Type (d), above. The central failure. A tag can be MEASURED and the measurement can be
    of the wrong thing (entry 22's 55 s WAS measured; it was measured at K=8).
  - Numbers written as words ("nine and a half GPU-days" -- which is exactly how the 228
    figure reads in `experiments.tex`, so that site is caught by the digits beside it and
    not by the words).
  - A figure with no unit attached to it at all ("the gate adds ~6%", "9.5 DAYS").
  - Wall-clock versus GPU-time confusion. The audit measured this ratio at between 1.00x
    and 2.28x on one chain. Every "GPU-h" figure in this repo is compute time and every
    decision that spends one is wall-clock. No regex sees that.
  - Whether a MEASURED figure is stale. Measurements age too; the ratchet only guards tags.
"""
from __future__ import annotations

import datetime as _dt
import re
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]

# --------------------------------------------------------------------------------------
# Scope. Globs relative to the repo root. Order is display order.
# --------------------------------------------------------------------------------------
SCOPE_GLOBS = (
    "docs/START_HERE_overnight.md",
    "docs/definitive_run_plan.md",
    "docs/framing_decision.md",
    "docs/revised_plan_wk9_17.md",
    "results/*_plan.md",
    "results/*_options.md",
    "results/derived_paper_quantities.md",
    "results/judge_owed_conditions.md",
    "results/power_under_ceiling.md",
    "paper/sections/*.tex",
    "scripts/overnight_*.sh",
)

# Explicitly OUT of scope, and each for a stated reason, not by oversight.
#
#   critique_log.md, OVERNIGHT_*.md   append-only history. Rewriting history to satisfy a
#                                     linter is worse than the disease, and the danger was
#                                     never that the log CONTAINS a dead number -- entry
#                                     22's 55 s was correct for K=8 -- but that it gets
#                                     quoted forward. Forward is where the scope is.
#
#   operational_number_audit.md       the register of dead anchors and their replacements.
#                                     Its inventory tables restate every superseded figure
#                                     by design; scoping it in would mean the guard's own
#                                     evidence file may not cite its own evidence. Same
#                                     class as the log: backward-looking record, not a
#                                     document that spends a number.
OUT_OF_SCOPE = (
    "docs/critique_log.md",
    "results/OVERNIGHT_2026-07-02.md",
    "results/OVERNIGHT_2026-07-05.md",
    "results/operational_number_audit.md",
)

# --------------------------------------------------------------------------------------
# Rule 1: dead anchors. A literal that a measurement has since refuted, and which must not
# be restated in a live planning document without saying that it is dead.
#
# Each entry: (pattern, context or None, human name, what replaced it and where).
#
# `context` is searched in a +-90 character window around the match, on BOTH sides. A bare
# "2.8 s" or "67 s" is not a dead anchor -- the anchor is that number attached to a
# particular unit -- and the disambiguating word is as likely to precede the number ("a
# judge clustering costs 67 s") as to follow it ("67 s per clustering"). A lookahead-only
# rule catches one phrasing and blesses the other.
#
# SEP allows the LaTeX non-breaking space: `$228$~GPU-hours` is the same figure as
# "228 GPU-hours" and markup must not be able to hide it.
SEP = r"[\s~]*"

DEAD_ANCHORS: list[tuple[str, str | None, str, str]] = [
    (r"55" + SEP + r"s(?:econds)?\b", r"clustering|judge|evaluation|per\s+target|each",
     "55 s / clustering",
     "MEASURED at K=8 / judge_batch_size 12 (critique_log 22) and spent on K=50 at batch 6. "
     "Superseded by 24.0 s/clustering -- results/null_control_cost_options.md section 1."),
    (r"228" + SEP + r"GPU-?" + SEP + r"h(?:ours?)?", None,
     "228 GPU-h",
     "MODELLED from the 55 s anchor. Re-priced at the measured 24.0 s/clustering: "
     "~99 GPU-h (~4.1 GPU-days) -- results/operational_number_audit.md section 2.4."),
    (r"67" + SEP + r"GPU-?" + SEP + r"h(?:ours?)?", None,
     "~67 GPU-h null control",
     "MODELLED from the 55 s anchor. Measured remainder is 23-26 GPU-h at 1191 s/target -- "
     "results/null_control_cost_options.md section 1."),
    (r"60" + SEP + r"GPU-?" + SEP + r"h(?:ours?)?", None,
     "~60 GPU-h null control",
     "The same model, restated in the overnight queue header. 23-26 GPU-h measured."),
    (r"73\.9" + SEP + r"s" + SEP + r"/?" + SEP + r"(?:eval|per\s+eval)", None,
     "73.9 s/eval at N=40",
     "MODELLED assuming generation is linear in N. Measured 43.4-45.2 s/eval -- generation "
     "is flat in N; results/operational_number_audit.md section 2.2."),
    (r"2\.8" + SEP + r"s\b", r"SE\s*eval|per\s+SE|s.SE|/\s*eval",
     "2.8 s per SE eval",
     "MODELLED by pro-rata token split. Measured 12.87 s/SE-eval -- "
     "results/operational_number_audit.md section 2.1."),
    (r"6\.1" + SEP + r"s\b", r"cheap\s+arm|arms\s+alone|per\s+eval|/\s*eval",
     "6.1 s cheap-arm eval",
     "Back-solved from critique_log 22's '25 GPU-h for 80 x 185'. Measured 12.87 s."),
    (r"67" + SEP + r"s\b", r"clustering|judge",
     "67 s per judge clustering",
     "MODELLED as a geometric-mean bracket over two anchors both taken at batch 12. "
     "Measured judge increment at batch 6 is 11.13 s."),
]

# A dead anchor may appear when the surrounding PARAGRAPH says it is dead. The window is
# the paragraph and not the sentence, deliberately: a correction reads "X came from a K=8
# probe. The deployed run refutes it." -- two sentences, one thought, and a sentence-scoped
# rule flags the document that is doing the correcting.
#
# This is the "presence in a window" pattern `check_population_labels.py` warns against, and
# the difference is worth stating. There, a nearby pool name was NOT evidence that the
# number was bound to that pool. Here, a nearby "superseded" IS evidence that the author
# knows the anchor is dead -- there is no competing hypothesis under which someone writes
# "refuted" next to a figure they are relying on. Note what is deliberately NOT a retirement
# marker: "this is a model, not a measurement" (honest disclosure, but it does not say the
# anchor is DEAD) and any MEASURED/MODELLED tag on its own.
RETIREMENT = re.compile(
    r"\b(?:superseded|supersedes|superseding|retired|refuted|refutes|withdrawn|withdraws|"
    # NOT "corrected"/"correction": experiments.tex:173 sits in a paragraph containing "the
    # budget correction then moved ...", which would launder the single most important dead
    # anchor in the repo. A word that is common in adjacent prose cannot be a retirement
    # marker; the marker has to be about THIS number.
    r"obsolete|stale|wrong\s+by|was\s+wrong|no\s+longer|assumed|"
    r"re-?derived|re-?priced|reconcil\w+|dead[- ]anchor|DEAD_ANCHORS|revers\w+|"
    r"the\s+budget'?s?\s+own\s+figure|for\s+comparison|SUPERSEDED)\b",
    re.IGNORECASE)


def _paragraph(flat: str, pos: int) -> tuple[int, int]:
    """Blank-line-delimited paragraph containing `pos`, capped so one long section cannot
    launder a dead anchor from the other end of the file."""
    a = flat.rfind("\n\n", 0, pos)
    a = 0 if a < 0 else a + 2
    b = flat.find("\n\n", pos)
    b = len(flat) if b < 0 else b
    return (max(a, pos - 900), min(b, pos + 900))

# --------------------------------------------------------------------------------------
# Rule 2/3: operational figures and their tags.
# --------------------------------------------------------------------------------------
NUMBER = r"(?:~|≈|about\s+|under\s+|over\s+)?\$?\d[\d,]*(?:\.\d+)?\$?"

OPERATIONAL = re.compile(
    NUMBER + r"[\s~]*(?:"
    r"GPU-?\s*h(?:ours?|rs?)?\b"
    r"|GPU-?\s*days?\b"
    r"|s\s*/\s*(?:eval|target|clustering|question|Q|call)\b"
    r"|s\s+per\s+(?:eval|target|clustering|question|call)\b"
    r"|min\s*/\s*target\b"
    r"|min(?:utes)?\s+per\s+target\b"
    r"|nights?\b"
    r")",
    re.IGNORECASE)

TAG = re.compile(r"\b(MEASURED|MODELLED|MODELED|UNMEASURED)\b")

# A MODELLED figure has to say what it was modelled FROM. This does not check that the
# anchor is appropriate -- nothing can (type (d)) -- only that it is written down.
ANCHOR_NAMED = re.compile(
    r"\b(?:from|via|per|using|based\s+on)\b"
    r"|critique_log\s*\d+"
    r"|[\w/]+\.(?:md|py|jsonl|log|sh|tex)\b"
    r"|`[^`]+`",
    re.IGNORECASE)

SUPERSEDE_WHEN = re.compile(r"supersede-when\s*:\s*([^\s,;)\]]+)", re.IGNORECASE)

# Rule 5: a countdown is monotone in time. This repo already learned to distrust statistics
# that move while you type them ("Ask 'monotone in n?' before any count enters a sentence").
COUNTDOWN = re.compile(r"(\d{1,4})\s*days?\b[^.\n]{0,70}?(\d{4}-\d{2}-\d{2})")

# --------------------------------------------------------------------------------------
# THE RATCHET. Untagged operational figures per scoped file, as of 2026-08-14.
#
# A file that GAINS one fails. A file that DROPS below its baseline also fails, so that the
# register cannot rot upward while the docs are cleaned. When a generator learns to emit
# tags, lower its entry in the same commit.
#
# Files absent from this map must be clean (baseline 0).
# --------------------------------------------------------------------------------------
KNOWN_OPEN: dict[str, int] = {
    "docs/START_HERE_overnight.md": 2,
    "docs/definitive_run_plan.md": 2,
    "docs/framing_decision.md": 2,
    # 1 -> 2 on 2026-08-14: correcting the dead 228 anchor introduced the measured ~99
    # beside it, and a paper's prose cannot carry a literal MEASURED token without
    # addressing the reader in the wrong register. Its provenance is in words instead
    # ("re-derived from the wall clock of runs that have since executed"), which this
    # checker cannot read. Paper numbers are guarded by check_population_labels.py and
    # by the standing rule that each trace to a committed artifact.
    "paper/sections/experiments.tex": 2,
    "results/derived_paper_quantities.md": 3,
    "results/judge_owed_conditions.md": 12,
    "results/n_scaling_plan.md": 40,
    "results/null_control_cost_options.md": 24,
    "results/null_objective_ablation_plan.md": 11,
    "results/power_under_ceiling.md": 1,
    "scripts/overnight_2026_08_13.sh": 2,
    "scripts/overnight_queue.sh": 5,
}


# --------------------------------------------------------------------------------------
def strip_markup(text: str) -> str:
    """Flatten LaTeX and markdown so a figure cannot hide inside markup.

    The lesson is `check_population_labels.py`'s: a manual grep for "fair pool" missed
    conclusion.tex because the source read `\\emph{fair} pool`. Same length out as in, so
    every offset stays valid.
    """
    out = text
    out = re.sub(r"\\(?:emph|textbf|textit|texttt|mathrm|text)\{", lambda m: " " * len(m.group(0)), out)
    out = re.sub(r"\\[a-zA-Z]+", lambda m: " " * len(m.group(0)), out)
    # NOT `_`: it is the word separator in every path and identifier this repo cites, and
    # blanking it turns `supersede-when: results/null_control_ckpt_defb.jsonl` into a path
    # that does not exist -- silently disarming the one rule that fires on real evidence.
    out = re.sub(r"[{}$*`]", " ", out)
    # Normalise the punctuation that markdown and LaTeX disagree about. Same length out as
    # in, so every offset stays valid -- "approximately" is one char in both renderings.
    for src, dst in (("\u2013", "-"), ("\u2014", "-"), ("\u2019", "'"),
                     ("\u2248", "~"), ("\u00d7", "x"), ("\u2264", "<"), ("\u2265", ">"),
                     ("\u2011", "-"), ("\u00a0", " ")):
        out = out.replace(src, dst)
    return out


def _sentences(flat: str) -> list[tuple[int, int]]:
    """Spans of the attachment windows: a sentence, a list item, or one table row.

    A newline ends a window because markdown tables put one claim per row and the tag for
    `| 8.22 GPU-h | MODELLED from ... |` belongs in that row, not three rows down.
    """
    bounds = [0]
    for m in re.finditer(r"(?:\.\s)|(?:\.$)|\n", flat, re.MULTILINE):
        bounds.append(m.end())
    bounds.append(len(flat))
    spans = []
    for a, b in zip(bounds, bounds[1:]):
        if b > a:
            spans.append((a, b))
    return spans


def _window(spans: list[tuple[int, int]], pos: int) -> tuple[int, int]:
    for a, b in spans:
        if a <= pos < b:
            return (a, b)
    return (pos, pos)


def _rel(path: Path) -> str:
    try:
        return path.relative_to(REPO).as_posix()
    except ValueError:
        return path.as_posix()


def _line_no(raw: str, pos: int) -> int:
    return raw.count("\n", 0, pos) + 1


def _quote(flat: str, a: int, b: int, limit: int = 110) -> str:
    s = " ".join(flat[a:b].split())
    return s if len(s) <= limit else s[: limit - 3] + "..."


# --------------------------------------------------------------------------------------
def check_file(path: Path, *, today: _dt.date | None = None,
               repo: Path | None = None) -> list[str]:
    """Return one string per problem. Empty list == clean."""
    today = today or _dt.date.today()
    repo = repo or REPO
    raw = path.read_text(encoding="utf-8", errors="replace")
    flat = strip_markup(raw)
    spans = _sentences(flat)
    shown = _rel(path)
    problems: list[str] = []

    # -- Rule 1: dead anchors -----------------------------------------------------------
    for pattern, context, name, replacement in DEAD_ANCHORS:
        for m in re.finditer(pattern, flat, re.IGNORECASE):
            if context is not None:
                near = flat[max(0, m.start() - 90):m.end() + 90]
                if not re.search(context, near, re.IGNORECASE):
                    continue
            a, b = _window(spans, m.start())
            pa, pb = _paragraph(flat, m.start())
            if RETIREMENT.search(flat[pa:pb]):
                continue
            problems.append(
                f"{shown}:{_line_no(raw, m.start())}: dead-anchor: '{name}' restated without "
                f"saying it is dead -- \"{_quote(flat, a, b)}\"\n"
                f"      {replacement}")

    # -- Rules 2-4: tags, anchors, supersede triggers ------------------------------------
    untagged = 0
    for m in OPERATIONAL.finditer(flat):
        a, b = _window(spans, m.start())
        sentence = flat[a:b]
        tag = TAG.search(sentence)
        if tag is None:
            untagged += 1
            continue
        if tag.group(1) in ("MODELLED", "MODELED"):
            after = sentence[tag.end():tag.end() + 200]
            if not ANCHOR_NAMED.search(after):
                problems.append(
                    f"{shown}:{_line_no(raw, m.start())}: anchorless-model: "
                    f"'{m.group(0).strip()}' is tagged MODELLED but does not say what it was "
                    f"modelled FROM -- \"{_quote(flat, a, b)}\"\n"
                    f"      Name the anchor and its operating point (K, N, batch size, which "
                    f"models were resident). A script cannot tell whether an anchor fits the "
                    f"job it is being spent on; a reader can, but only if it is written down.")
            trig = SUPERSEDE_WHEN.search(sentence)
            if trig:
                target = (repo / trig.group(1)).resolve()
                if target.exists():
                    problems.append(
                        f"{shown}:{_line_no(raw, m.start())}: supersede-trigger: "
                        f"'{m.group(0).strip()}' is MODELLED and declared "
                        f"supersede-when: {trig.group(1)} -- that artifact now EXISTS. "
                        f"The figure is owed a re-derivation from it.\n"
                        f"      A modelled cost stops being defensible the moment real timing "
                        f"data exists.")

    baseline = KNOWN_OPEN.get(shown, 0)
    if untagged > baseline:
        problems.append(
            f"{shown}: untagged: {untagged} operational figure(s) carry no "
            f"MEASURED/MODELLED/UNMEASURED tag, against a baseline of {baseline}. "
            f"{untagged - baseline} new one(s).\n"
            f"      Tag the new figures, or -- if this file is script-generated -- fix the "
            f"generator. Do not raise the baseline to make this pass.")
    elif untagged < baseline:
        problems.append(
            f"{shown}: ratchet-stale: {untagged} untagged figure(s) against a baseline of "
            f"{baseline}. Progress -- lower KNOWN_OPEN['{shown}'] to {untagged} in the same "
            f"commit, so the register cannot rot upward.")

    # -- Rule 5: countdowns are monotone in time ------------------------------------------
    for m in COUNTDOWN.finditer(flat):
        stated = int(m.group(1))
        try:
            target = _dt.date.fromisoformat(m.group(2))
        except ValueError:
            continue
        actual = (target - today).days
        if stated != actual:
            problems.append(
                f"{shown}:{_line_no(raw, m.start())}: stale-countdown: says {stated} days to "
                f"{m.group(2)}; it is {actual} today -- \"{_quote(flat, *_window(spans, m.start()))}\"\n"
                f"      A countdown is monotone in time, which is the same shape as the "
                f"sample statistics this project already learned to distrust.")

    return problems


def scoped_files(repo: Path | None = None) -> list[Path]:
    repo = repo or REPO
    seen: dict[str, Path] = {}
    for g in SCOPE_GLOBS:
        for p in sorted(repo.glob(g)):
            if p.is_file():
                seen.setdefault(_rel(p), p)
    return [seen[k] for k in sorted(seen)]


def main(repo: Path | None = None, today: _dt.date | None = None) -> int:
    repo = repo or REPO
    # The quoted source lines carry en-dashes and multiplication signs; a cp1252 console
    # must not be able to turn a finding into a traceback.
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(errors="replace")       # type: ignore[union-attr]
        except (AttributeError, ValueError):           # pragma: no cover - non-tty streams
            pass
    targets = scoped_files(repo)
    if not targets:
        print("no scoped files found", file=sys.stderr)
        return 1
    problems: list[str] = []
    for t in targets:
        problems.extend(check_file(t, today=today, repo=repo))
    if problems:
        print(f"OPERATIONAL-PROVENANCE CHECK FAILED - {len(problems)} problem(s):\n")
        for p in problems:
            print("  " + p)
        print(
            "\nEvery operational number that drives a decision -- GPU-hours, seconds per\n"
            "evaluation, targets per night, capacities, deadlines -- carries a MEASURED or\n"
            "MODELLED tag, and a MODELLED one names the anchor it came from AND that\n"
            "anchor's operating point (K, N, batch size, what was resident). A modelled\n"
            "cost stops being defensible the moment real timing data exists: declare\n"
            "`supersede-when: <path>` and re-derive when that path appears.\n"
            "\nWhat no checker can do for you (results/operational_number_audit.md 5.1(d)):\n"
            "decide whether the anchor FITS. A K=8 probe spent on a K=50 run, an N=10 rate\n"
            "spent at N=40, a single-question warmup spent on 17,944 questions -- all three\n"
            "happened here, all three were correctly measured, and all three were the wrong\n"
            "number. Before spending a modelled cost: has an hour of this job already run?\n"
            "If yes, divide. Three filesystem anchors and a division beat any model here.")
        return 1
    print(f"operational-provenance check: OK ({len(targets)} files, "
          f"{len(DEAD_ANCHORS)} dead anchors, {len(KNOWN_OPEN)} ratcheted files)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
