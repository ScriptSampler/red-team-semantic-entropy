"""Correctness scoring for TriviaQA / SQuAD-style short-answer QA.

The correctness oracle drives target selection, the attack success metric, and
the AUROC labels, so it must be strong and, critically, not itself surface-form
sensitive in a way that correlates with the paraphrase manipulation under study
(external review, B3). We provide three oracles and let experiments report
sensitivity across them:

  is_correct(gen, ex, mode="span")     PRIMARY. Word-boundary-aware: a generation
                                        is correct iff the normalised token
                                        sequence of some accepted answer form
                                        appears as a CONTIGUOUS subsequence of the
                                        normalised generation tokens. This is the
                                        SQuAD-style "gold answer span is present"
                                        notion with the TriviaQA alias set.
  is_correct(gen, ex, mode="strict")   Whole-generation exact match (very low
                                        recall on free-form sentences; used only
                                        as a strict sensitivity bound).
  is_correct(gen, ex, mode="substring") The old raw substring oracle, kept so the
                                        headline can be reported under all three
                                        and shown to survive the stricter one.

Normalisation is the canonical SQuAD `normalize_answer` (lowercase, remove
punctuation, remove articles a/an/the, collapse whitespace).

Known residual limitation of any STRING oracle: entity ambiguity. Gold "Paris"
matches "Paris Hilton" because "paris" is genuinely a token; only a semantic /
model-graded judge resolves this. Such a judge (with a reported human-agreement
number) is the recommended stronger oracle and is left as the next upgrade; the
span oracle already removes the more common word-boundary over-crediting (e.g.
"Paris" inside "comparison") and, with the alias set, most under-crediting.

`is_acceptable` is retained as the project-wide entry point and now points at the
primary span oracle. `is_acceptable_substring` exposes the old behaviour.
"""
from __future__ import annotations

import re
import string
from typing import Literal

from .data import TriviaQAExample


_ARTICLES = re.compile(r"\b(a|an|the)\b")
_PUNCT_TABLE = {ord(c): None for c in string.punctuation}


def normalize_answer(s: str) -> str:
    """Canonical SQuAD normalisation: lower, drop punctuation, drop articles,
    collapse whitespace. Punctuation is DELETED (SQuAD `remove_punc`), so
    'u.s.a.' -> 'usa' and 'state-of-the-art' -> 'stateoftheart'."""
    s = s.lower()
    s = s.translate(_PUNCT_TABLE)          # delete punctuation
    s = _ARTICLES.sub(" ", s)              # drop articles as whole words
    s = " ".join(s.split())               # collapse whitespace
    return s


# Backwards-compatible name used across the codebase for cluster normalisation.
# NOTE: this now deletes punctuation (canonical SQuAD) rather than replacing it
# with a space; behaviour is identical after whitespace-collapse for the token
# uses in the clustering code (tokens are compared, not raw strings).
def normalise(s: str) -> str:
    return normalize_answer(s)


def _tokens(s: str) -> list[str]:
    n = normalize_answer(s)
    return n.split() if n else []


def _is_contiguous_subsequence(needle: list[str], haystack: list[str]) -> bool:
    """True if `needle` appears as a contiguous run inside `haystack`."""
    if not needle:
        return False
    if len(needle) > len(haystack):
        return False
    first = needle[0]
    for i in range(len(haystack) - len(needle) + 1):
        if haystack[i] == first and haystack[i:i + len(needle)] == needle:
            return True
    return False


Mode = Literal["span", "strict", "substring"]


def is_correct(generation: str, ex: TriviaQAExample, mode: Mode = "span") -> bool:
    """Whether `generation` answers `ex` correctly under the chosen oracle."""
    forms = ex.all_acceptable()
    if mode == "substring":
        g = normalize_answer(generation)
        return any(normalize_answer(f) in g for f in forms if normalize_answer(f))
    if mode == "strict":
        g = normalize_answer(generation)
        return any(g == normalize_answer(f) for f in forms if normalize_answer(f))
    # span (primary): gold token sequence is a contiguous subsequence of the gen.
    gen_toks = _tokens(generation)
    for f in forms:
        ftoks = _tokens(f)
        if ftoks and _is_contiguous_subsequence(ftoks, gen_toks):
            return True
    return False


def is_acceptable(generation: str, ex: TriviaQAExample) -> bool:
    """Project-wide correctness entry point. Now the word-boundary-aware span
    oracle (was raw substring; see module docstring / external review B3)."""
    return is_correct(generation, ex, mode="span")


def is_acceptable_substring(generation: str, ex: TriviaQAExample) -> bool:
    """The old raw-substring oracle, retained for oracle-sensitivity reporting."""
    return is_correct(generation, ex, mode="substring")
