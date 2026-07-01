"""Tests for the correctness oracle (B3). CPU-only, no model."""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from se.data import TriviaQAExample
from se.scoring import (
    normalize_answer,
    is_correct,
    is_acceptable,
    is_acceptable_substring,
)


def ex(answer, aliases=None):
    return TriviaQAExample("q", "?", answer, aliases or [])


# ---- normalize_answer ------------------------------------------------------

def test_normalize_deletes_punct_and_articles():
    assert normalize_answer("The U.S.A.!") == "usa"
    assert normalize_answer("a Paris,") == "paris"
    assert normalize_answer("  multiple   spaces ") == "multiple spaces"


# ---- span oracle: the word-boundary over-credit fix ------------------------

def test_span_rejects_substring_inside_word():
    # Old substring oracle credits "paris" inside "comparison"; span must not.
    e = ex("Paris")
    gen = "This is a comparison of several answer options."
    assert is_acceptable_substring(gen, e) is True     # documents the old flaw
    assert is_acceptable(gen, e) is False              # span fixes it


def test_span_accepts_answer_embedded_in_sentence():
    e = ex("Paris")
    assert is_acceptable("The capital of France is Paris.", e) is True


def test_span_accepts_phrase_answer():
    e = ex("In 1912, in Stockholm")
    gen = "The games were held in 1912 in Stockholm, Sweden."
    assert is_acceptable(gen, e) is True


def test_span_uses_aliases_for_undercredit():
    # Gold canonical is the full name; generation uses a shorter alias.
    e = ex("Denver Broncos", aliases=["Broncos"])
    assert is_acceptable("I think the Broncos won that year.", e) is True


def test_span_rejects_wrong_answer():
    e = ex("Denver Broncos", aliases=["Broncos"])
    assert is_acceptable("The Carolina Panthers.", e) is False


def test_span_rejects_reordered_phrase():
    # Contiguity matters: a reordered phrase is not a match (aliases would cover
    # legitimate reorderings in the real data).
    e = ex("New York City")
    assert is_acceptable("City of New York style.", e) is False
    assert is_acceptable("It is New York City.", e) is True


# ---- strict oracle (sensitivity bound) -------------------------------------

def test_strict_is_whole_string_match():
    e = ex("Paris")
    assert is_correct("Paris", e, mode="strict") is True
    assert is_correct("The answer is Paris", e, mode="strict") is False
    assert is_correct("paris.", e, mode="strict") is True  # normalisation


# ---- documented residual limitation ----------------------------------------

def test_article_in_title_is_stripped_but_alias_saves_it():
    # normalize_answer strips a/an/the (SQuAD standard), so "The Who" -> "who".
    # A generation naming the band still matches via the token "who"; and if the
    # alias set carries the article-free form, correctness holds. This documents
    # the residual: distinct entities differing ONLY by an article are unsafe.
    e = ex("The Who", aliases=["Who (band)"])
    assert normalize_answer("The Who") == "who"
    assert is_acceptable("The band was The Who.", e) is True
    # "A Beautiful Mind" -> "beautiful mind"; embedded still matches.
    film = ex("A Beautiful Mind")
    assert normalize_answer("A Beautiful Mind") == "beautiful mind"
    assert is_acceptable("The film is A Beautiful Mind.", film) is True


def test_span_entity_ambiguity_is_known_limitation():
    # A string oracle cannot tell the city Paris from Paris Hilton; span still
    # matches. This is documented; only a semantic judge resolves it.
    e = ex("Paris")
    assert is_acceptable("Paris Hilton attended the event.", e) is True
