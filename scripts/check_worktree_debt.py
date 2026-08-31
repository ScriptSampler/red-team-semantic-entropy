"""Fail the build when work is sitting in a gitignored agent worktree with nothing naming it.

WHY THIS EXISTS.

`.gitignore` excludes `.claude/worktrees/`. That is correct -- 31 MB across seven full copies
of `results/`, one of them carrying the un-blinding key -- and it is also a hiding place with
no floor. An agent running under worktree isolation edits files in there. If its branch is
never merged, and its working tree is never committed, the work is invisible to EVERY surface
this project reviews by:

  * `git status` in the main tree says clean, because the path is ignored;
  * `git log main..<branch>` says nothing, because there are no commits;
  * `git diff` says nothing, because the changes are in another working tree;
  * every checker in `scripts/` reads tracked files, so none of them look;
  * a reviewer, a critic panel, and an external model all read the same three surfaces.

MEASURED 2026-08-31, which is why this file exists rather than a note in a log. Seven
worktrees, zero unmerged commits between them, and SIX carrying uncommitted working-tree
changes -- 700-odd lines. Two of the six were real and unlanded. One of those two was the
correction of an SE-evaluation cost constant that was wrong by 4.6x IN THE CHEAP DIRECTION,
written on 2026-08-13 and still unlanded on 2026-08-31. For eighteen days the schedule went on
pricing a job at about a quarter of what it costs, `results/operational_number_audit.md`
independently re-derived the same correction from scratch, and two critic panels plus an
external reviewer read the stale number without anything anywhere saying a correction existed.
A separate orphan (`serene-hypatia-56260a`) had already been found by hand and rescued in
`6fbec9a`; finding it by hand is not a mechanism, and it is the reason to write one.

THE SHAPE OF THE LOSS, stated exactly, because it decides what the rule has to be.

The dangerous worktree is not the one with unmerged commits. Unmerged commits are visible:
they have a branch, `git log` finds them, and a person can ask what the branch is for. The
dangerous one has **zero commits and a dirty working tree** -- an agent that did its analysis,
wrote it to disk, and stopped before committing. There is no ref pointing at that work. Only
the directory knows, and the directory is ignored. All six of the 2026-08-31 findings had
exactly this shape.

WHAT THIS SCRIPT CAN AND CANNOT DO.

It CANNOT tell you whether the work is any good. Of the six dirty worktrees found on
2026-08-31, one was already landed, two were superseded by better work on `main`, one was
affirmatively WRONG (it reimplemented a variance decomposition that
`results/post_overnight_claim_review.md` section 3.3 had retracted by name), and two were
worth landing. Nothing mechanisable separates those. Adjudication is a person's job.

What it CAN do is make sure the adjudication HAPPENS, and that its outcome is written down
where the next run reads it. That is the register below. A dirty worktree that nobody has
ruled on is a finding. A dirty worktree with a recorded verdict is not, because somebody
looked -- and the verdict is in a tracked file, so it survives the worktree it describes.

This is deliberately the same trade `check_operational_provenance.py` makes: the guard buys
LEGIBILITY, not correctness. It cannot know that a diff is right. It can refuse to let one sit
unread for eighteen days.

THE REGISTER, and why it is not a suppression list.

`ADJUDICATED` maps a worktree name to a terminal verdict and the date it was reached. Only
four verdicts are terminal -- LANDED, SUPERSEDED, WRONG, RESCUED. `OPEN` is accepted as a
value and deliberately does NOT clear the finding: it is how you record that you have seen a
worktree and not yet ruled on it, without the register lying about it having been settled.

Registering a worktree is therefore not the cheap way out of a red. It is a claim, in a
tracked file, that a person read the diff and reached a conclusion -- which is the entire
thing that did not happen for eighteen days.

    .venv/Scripts/python.exe scripts/check_worktree_debt.py
    .venv/Scripts/python.exe scripts/check_worktree_debt.py --list   # no verdicts, just state
"""
from __future__ import annotations

import argparse
import datetime as _dt
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]

TERMINAL = ("LANDED", "SUPERSEDED", "WRONG", "RESCUED")

# --------------------------------------------------------------------------------------
# THE REGISTER. worktree directory name -> (verdict, date, one line of why).
#
# A worktree carrying uncommitted changes or unmerged commits must appear here with a
# TERMINAL verdict, or this check fails. `OPEN` is a legal value and does not clear the
# finding -- see the docstring. Do not add an entry to silence a red; add it because you read
# the diff.
#
# Struck 2026-08-31, adjudicating all seven worktrees then in existence.
# --------------------------------------------------------------------------------------
ADJUDICATED: dict[str, tuple[str, str, str]] = {
    "ecstatic-mahavira-1d0279": (
        "LANDED", "2026-08-31",
        "Corrected the ablation's SE-eval unit from a pro-rata token split (2.8 s) to the "
        "measured 13.0 s, 4.6x in the cheap direction. Arithmetic re-verified against "
        "run_all.log, pipeline_check.md, run_all_status.txt and wk3_fri_entropy.md; C=53.91 "
        "and r=59/80 re-derived against the COMPLETED 80-target hide cell. Landed into "
        "results/null_objective_ablation_plan.md section 6, adapted: the stale queue "
        "paragraph and countdown were rewritten rather than carried over."),
    "serene-hypatia-56260a": (
        "RESCUED", "2026-08-13",
        "Length-confound probe, five untracked files. Rescued by hand in 6fbec9a. Left in "
        "place; the worktree still holds the untracked originals."),
    "brave-ishizaka-9861b8": (
        "SUPERSEDED", "2026-08-31",
        "Proposed a `PaperClaim` guard in derived_paper_quantities.py. main built a far "
        "stronger one (+1054 lines: present=False absence claims, standalone anchoring, "
        "lookbehind for denominators) and already holds the 1440-vs-1424 fix this diff was "
        "for. Landing it blind would BREAK the script: its must_contain literal reads 'over "
        "$1424$ clean correct answers' and main.tex says 'on'. Its one live fragment, the "
        "likelihood_weight_sensitivity.py docstring, was landed separately."),
    "brave-lederberg-0266d4": (
        "WRONG", "2026-08-31",
        "Its floor/ceiling-atom split is superseded by floor_cells() on main. Its "
        "distinctive part, replayed_floor_spread(), is affirmatively wrong: it resamples the "
        "subset draw ON TOP OF a Wilson interval, and results/post_overnight_claim_review.md "
        "section 3.3 -- the section this diff cites as its justification -- was RETRACTED on "
        "2026-08-19 as 'the origin of the error', because one replicate's binomial variance "
        "already contains both components. It would double-count, and would print an "
        "interval at N=40 where n40_floor_estimator_ruling.md says none is admissible."),
    "dreamy-williamson-8cace1": (
        "OPEN", "2026-08-31",
        "Reviewed 2026-08-31 by the owner. The substance is ONE provenance citation "
        "(scripts/power_sim_deployed.py + results/power_deployed_vs_oracle.md), which main "
        "genuinely lacks and which is worth having. Two reasons it is not landed yet, both "
        "concrete rather than a shrug. (1) DO NOT APPLY THIS HUNK AS A PATCH: it predates "
        "the em-dash removal, so its reflow would reintroduce '---' into a file that is "
        "now pure ASCII. Only the parenthetical clause should ever be taken. (2) The cited "
        "script is being rewritten right now because it encoded a refuted claim (that the "
        "realized design is stronger at a fixed cut; it is not, the cut compares levels "
        "0.0793 against 0.0437), and the cited report covers only the planned n=80 uniform "
        "design with no realized column. UNBLOCKS WHEN: the power rewrite lands and "
        "power_deployed_vs_oracle.md is regenerated from it. Then land the citation and "
        "close this LANDED. The report itself is sound and was right early: it flagged the "
        "deployed level as 0.041 against the paper's then-claimed 0.053."),
    "elated-clarke-3085b8": (
        "SUPERSEDED", "2026-08-31",
        "Both changes are dead. The K=5 provenance pointer it moves to "
        "null_control_3arm_judge_n6.md is already on main; the paper-file byte/sha table it "
        "updates is script-generated and main's regenerated copy is four commits newer."),
    "hopeful-davinci-9feece": (
        "SUPERSEDED", "2026-08-31",
        "Adds `!results/equivalence_audit*.csv` to .gitignore. That rule was already present "
        "in the worktree's OWN base commit 6d65384, further down the file and with better "
        "commentary, so the diff is a duplicate insertion. main has since also versioned the "
        ".claude/worktrees/ exclusion itself (32713f1)."),
}


# --------------------------------------------------------------------------------------
def _git(args: list[str], cwd: Path) -> str:
    out = subprocess.run(["git", *args], cwd=str(cwd), capture_output=True, text=True,
                         encoding="utf-8", errors="replace")
    return out.stdout if out.returncode == 0 else ""


def worktrees(repo: Path) -> list[dict]:
    """Every worktree except the main one, with its branch and HEAD."""
    porcelain = _git(["worktree", "list", "--porcelain"], repo)
    blocks, cur = [], {}
    for line in porcelain.splitlines():
        if not line.strip():
            if cur:
                blocks.append(cur)
            cur = {}
            continue
        key, _, val = line.partition(" ")
        cur[key] = val
    if cur:
        blocks.append(cur)
    main_path = None
    out = []
    for b in blocks:
        path = Path(b.get("worktree", ""))
        if main_path is None:
            main_path = path          # first block is always the main working tree
            continue
        out.append({
            "path": path,
            "name": path.name,
            "branch": b.get("branch", "").replace("refs/heads/", "") or "(detached)",
            "head": b.get("HEAD", "")[:7],
        })
    return out


def inspect(wt: dict, repo: Path, base: str = "main") -> dict:
    """State of one worktree: dirty files, unmerged commits, and how stale it is."""
    status = [l for l in _git(["status", "--porcelain"], wt["path"]).splitlines() if l.strip()]
    ahead = [l for l in _git(["log", "--oneline", f"{base}..{wt['branch']}"], repo).splitlines()
             if l.strip()]
    newest = None
    for line in status:
        rel = line[3:].strip().strip('"')
        f = wt["path"] / rel
        try:
            ts = f.stat().st_mtime
        except OSError:
            continue
        newest = ts if newest is None else max(newest, ts)
    age_days = None
    if newest is not None:
        age_days = (_dt.datetime.now() - _dt.datetime.fromtimestamp(newest)).days
    return {**wt, "dirty": status, "ahead": ahead, "age_days": age_days}


def classify(st: dict) -> str:
    """The orphan shape is the one worth naming, because it has no ref pointing at it."""
    if st["dirty"] and not st["ahead"]:
        return "ORPHAN (uncommitted, and NO commits either -- nothing anywhere refers to it)"
    if st["dirty"] and st["ahead"]:
        return "DIRTY + UNMERGED"
    if st["ahead"]:
        return "UNMERGED COMMITS"
    return "clean"


def check(repo: Path | None = None, base: str = "main") -> tuple[list[str], list[dict]]:
    """Return (problems, states). Empty problems == every debt is adjudicated."""
    repo = repo or REPO
    states = [inspect(w, repo, base) for w in worktrees(repo)]
    problems: list[str] = []
    for st in states:
        if not st["dirty"] and not st["ahead"]:
            continue
        entry = ADJUDICATED.get(st["name"])
        age = "" if st["age_days"] is None else f", newest change {st['age_days']} day(s) old"
        what = (f"{len(st['dirty'])} uncommitted file(s), {len(st['ahead'])} unmerged "
                f"commit(s){age}")
        if entry is None:
            problems.append(
                f".claude/worktrees/{st['name']}: unadjudicated: {what}.\n"
                f"      {classify(st)}\n"
                f"      This work is invisible to `git status`, to `git log {base}..`, and to "
                f"every checker in scripts/. Read the diff -- `git -C \"{st['path']}\" diff` "
                f"-- decide LANDED / SUPERSEDED / WRONG / RESCUED, and record it in "
                f"ADJUDICATED in scripts/check_worktree_debt.py. Do not register it without "
                f"reading it; the register is a claim that somebody did.")
        elif entry[0] not in TERMINAL:
            problems.append(
                f".claude/worktrees/{st['name']}: open verdict '{entry[0]}' ({entry[1]}): "
                f"{what}.\n"
                f"      {classify(st)}\n"
                f"      {entry[2]}\n"
                f"      Recorded but not settled. This stays red until the verdict is one of "
                f"{', '.join(TERMINAL)}.")
    stale = [n for n in ADJUDICATED if n not in {s["name"] for s in states}]
    if stale:
        problems.append(
            "note: ADJUDICATED names worktrees that no longer exist: "
            + ", ".join(sorted(stale))
            + "\n      Not a failure. A worktree that is gone is genuinely resolved, and the "
              "verdict is worth keeping as the record of what was in it.")
    return problems, states


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--list", action="store_true",
                    help="print worktree state and exit 0 without adjudicating")
    ap.add_argument("--base", default="main")
    args = ap.parse_args(argv)

    problems, states = check(base=args.base)

    if not states:
        print("worktree-debt check: OK (no agent worktrees)")
        return 0

    print(f"worktree-debt check: {len(states)} worktree(s) under .claude/worktrees/\n")
    for st in states:
        verdict = ADJUDICATED.get(st["name"], ("UNADJUDICATED", "", ""))[0]
        age = "" if st["age_days"] is None else f"  {st['age_days']}d"
        print(f"  {st['name']:<26} {classify(st):<62} "
              f"{len(st['dirty'])} file(s){age}  [{verdict}]")
    print()

    if args.list:
        return 0

    for p in problems:
        print("  " + p)

    hard = [p for p in problems if not p.startswith("note:")]
    if hard:
        print(f"\n{len(hard)} worktree(s) carry work nothing else in this repo can see.")
        return 1
    print("Every worktree carrying work has an adjudicated verdict. Nothing is hiding.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
