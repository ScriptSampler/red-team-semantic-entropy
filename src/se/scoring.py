"""Correctness scoring.

Light SQuAD-style normalisation: lowercase, drop articles, strip
punctuation, collapse whitespace. A generation counts as acceptable
if any accepted form of the answer appears in it after normalisation.

This is the rough containment check we use to label samples and
compute correctness rates during sampling. Week 4 may swap in a more
careful scorer once we cross-check against Farquhar et al.'s exact
recipe, but for SE entropy itself the labels only need to be a
faithful proxy for "the model got it right".
"""
from __future__ import annotations

import re

from .data import TriviaQAExample


_ARTICLES = re.compile(r"\b(a|an|the)\b")
_PUNCT = re.compile(r"[^\w\s]")
_WS = re.compile(r"\s+")


def normalise(s: str) -> str:
    s = s.lower()
    s = _PUNCT.sub(" ", s)
    s = _ARTICLES.sub(" ", s)
    s = _WS.sub(" ", s).strip()
    return s


def is_acceptable(generation: str, ex: TriviaQAExample) -> bool:
    """True if any accepted form of ex's answer appears in generation."""
    g = normalise(generation)
    for form in ex.all_acceptable():
        f = normalise(form)
        if f and f in g:
            return True
    return False
