"""The worktree-debt guard, and proof that it is neither vacuous nor a suppression list.

WHAT THIS FILE HAS TO ANSWER FOR.

This repo has written the lesson down twice, in commit messages, after paying for it twice:
*"a check that cannot fail is not a check"* and *"the guard built after the defect does not
catch the defect"*. `scripts/check_worktree_debt.py` was written on 2026-08-31, eighteen days
after the defect it is about, so it is exactly the kind of guard those two commits warn about.
Every probe below is therefore paired with a CONTROL -- the same situation in its benign form
-- because a rule that flags every worktree is not a rule.

The property that matters most here is the one in `test_an_OPEN_verdict_does_not_clear_the_
finding`. A register that any entry can silence is a suppression list wearing a ratchet's
clothes, and the whole value of this guard is that adding a name to it costs you reading a
diff. `OPEN` exists so that "I have seen this and not decided" is expressible WITHOUT the
register claiming the matter is settled -- and it must stay red, or the escape hatch is back.

WHY THERE IS NO test_the_repo_is_green. As of 2026-08-31 `main()` returns 1, on purpose:
`dreamy-williamson-8cace1` holds a one-line provenance citation for `paper/`, which is under a
do-not-edit rule for the session that adjudicated it, so its verdict is honestly OPEN. Pinning
that as green would be the suppression this file exists to refuse.
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "scripts"))

import check_worktree_debt as W  # noqa: E402

PORCELAIN = """worktree I:/repo
HEAD 1111111111111111111111111111111111111111
branch refs/heads/main

worktree I:/repo/.claude/worktrees/probe-one
HEAD 2222222222222222222222222222222222222222
branch refs/heads/claude/probe-one
"""


def _fake_git(status: str = "", ahead: str = ""):
    def g(args, cwd):
        if args[0] == "worktree":
            return PORCELAIN
        if args[0] == "status":
            return status
        if args[0] == "log":
            return ahead
        return ""
    return g


def _rules(problems: list[str]) -> set[str]:
    out = set()
    for p in problems:
        m = re.match(r"(?:\.claude/worktrees/\S+?: )?(unadjudicated|open verdict|note)", p)
        if m:
            out.add(m.group(1))
    return out


def _run(monkeypatch, *, status="", ahead="", register=None) -> list[str]:
    monkeypatch.setattr(W, "_git", _fake_git(status, ahead))
    monkeypatch.setattr(W, "ADJUDICATED", {} if register is None else register)
    problems, _ = W.check(repo=Path("I:/repo"))
    return problems


# ======================================================================================
# Rule 1 -- work with no ref pointing at it. The shape all six 2026-08-31 findings had.
# ======================================================================================
def test_an_unregistered_dirty_worktree_is_caught(monkeypatch):
    problems = _run(monkeypatch, status=" M results/plan.md\n")
    assert "unadjudicated" in _rules(problems), problems


def test_a_clean_worktree_is_not_caught(monkeypatch):
    """The CONTROL. An agent worktree that committed and merged is not debt, and a guard
    that cannot tell the difference would be turned off within a week."""
    assert _run(monkeypatch) == []


def test_unmerged_commits_are_caught_even_with_a_clean_tree(monkeypatch):
    problems = _run(monkeypatch, ahead="abc1234 some analysis\n")
    assert "unadjudicated" in _rules(problems), problems


def test_untracked_files_count_as_debt(monkeypatch):
    """`serene-hypatia-56260a` held FIVE untracked files and nothing else. A rule that only
    looked at tracked modifications would have missed the orphan that was actually rescued."""
    problems = _run(monkeypatch, status="?? scripts/length_confound_probe.py\n")
    assert "unadjudicated" in _rules(problems), problems


# ======================================================================================
# Rule 2 -- the register, and the reason it is not an off switch
# ======================================================================================
@pytest.mark.parametrize("verdict", W.TERMINAL)
def test_a_terminal_verdict_clears_the_finding(monkeypatch, verdict):
    problems = _run(monkeypatch, status=" M results/plan.md\n",
                    register={"probe-one": (verdict, "2026-08-31", "read it, ruled on it")})
    assert problems == [], problems


def test_an_OPEN_verdict_does_not_clear_the_finding(monkeypatch):
    """THE most important test here. `OPEN` records that a worktree has been SEEN without
    claiming it has been SETTLED. If it cleared the finding, the register would be a
    suppression list and this guard would buy nothing."""
    problems = _run(monkeypatch, status=" M results/plan.md\n",
                    register={"probe-one": ("OPEN", "2026-08-31", "owner decision pending")})
    assert "open verdict" in _rules(problems), problems


def test_a_bogus_verdict_string_cannot_silence_anything(monkeypatch):
    """Non-vacuity in the other direction: only the four terminal words clear a finding, so
    a typo or an invented verdict fails loudly rather than passing quietly."""
    problems = _run(monkeypatch, status=" M results/plan.md\n",
                    register={"probe-one": ("PROBABLY FINE", "2026-08-31", "shrug")})
    assert "open verdict" in _rules(problems), problems


def test_a_register_entry_for_a_vanished_worktree_is_a_note_and_not_a_failure(monkeypatch):
    """This ratchet deliberately does NOT fail upward, unlike KNOWN_OPEN in
    check_operational_provenance.py, and the asymmetry is on purpose: a retired operational
    figure that stops being quoted may have been laundered, but a worktree that is gone is
    genuinely gone. The verdict is still worth keeping as the record of what was in it."""
    monkeypatch.setattr(W, "_git", _fake_git())
    monkeypatch.setattr(W, "ADJUDICATED",
                        {"long-deleted": ("LANDED", "2026-08-01", "landed and pruned")})
    problems, _ = W.check(repo=Path("I:/repo"))
    assert _rules(problems) == {"note"}, problems
    assert W.main(["--list"]) == 0


# ======================================================================================
# Rule 3 -- the classifier names the dangerous shape
# ======================================================================================
def test_the_orphan_shape_is_named_distinctly():
    """Uncommitted AND no commits is the shape with NO ref pointing at it, and it is the one
    that survived two critic panels and an external reviewer. It must not read the same as an
    ordinary unmerged branch, which `git log` finds on its own."""
    orphan = W.classify({"dirty": [" M a"], "ahead": []})
    unmerged = W.classify({"dirty": [], "ahead": ["abc single commit"]})
    assert "ORPHAN" in orphan
    assert "ORPHAN" not in unmerged
    assert W.classify({"dirty": [], "ahead": []}) == "clean"


def test_the_finding_says_what_to_do_and_names_the_command(monkeypatch):
    """A guard that says 'wrong' without saying 'do this instead' gets worked around --
    the same rule check_operational_provenance.py holds its own messages to."""
    problems = _run(monkeypatch, status=" M results/plan.md\n")
    body = "\n".join(problems)
    assert "git -C" in body and "diff" in body
    assert all(v in body for v in W.TERMINAL)
    assert "check_worktree_debt.py" in body


# ======================================================================================
# The register as it actually stands
# ======================================================================================
def test_every_register_entry_is_well_formed():
    assert W.ADJUDICATED, "an empty register would make every test above vacuous"
    for name, entry in W.ADJUDICATED.items():
        verdict, date, why = entry
        assert verdict in W.TERMINAL or verdict == "OPEN", f"{name}: bad verdict {verdict!r}"
        assert re.fullmatch(r"\d{4}-\d{2}-\d{2}", date), f"{name}: bad date {date!r}"
        assert len(why) > 60, (
            f"{name}: the reason is too short to be evidence that anyone read the diff")


def test_every_dirty_worktree_in_this_repo_has_been_read():
    """The live assertion, and the one that fails when a new agent leaves work behind.

    It is deliberately weaker than `main() == 0`: it requires that somebody LOOKED at every
    worktree carrying work, not that every verdict is terminal. An honest OPEN keeps the
    script red and this test green, which is the correct split -- the script is the debt
    ledger, this is the tripwire.
    """
    problems, states = W.check()
    if not states:
        pytest.skip("no agent worktrees in this clone")
    unread = [p for p in problems if "unadjudicated" in p]
    assert not unread, (
        "a worktree is carrying work that nothing else in this repo can see:\n"
        + "\n".join(unread))
