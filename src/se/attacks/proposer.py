"""Semantically-equivalent paraphrase proposer for open-ended QA.

Adapted from SECA's semantic_equivalence_proposer (src/my_utils.py). SECA
randomises the instruction verb, style, and task each call so the proposer
LLM does not collapse to one rephrasing; we keep that idea but drop the
MMLU multiple-choice scaffolding because TriviaQA questions are open-ended.

The proposer is Llama itself (the plan allows "use the model itself to
paraphrase, or a separate paraphraser"). Generation runs at temperature
1.0 to get genuinely different candidates across calls.
"""
from __future__ import annotations

import random

from .. import model as M
from ..config import GenConfig


_VERBS = [
    "Rewrite", "Rephrase", "Recast", "Reword", "Reformulate", "Restate",
    "Reframe", "Revise", "Express differently", "Paraphrase",
]
_STYLES = [
    "clear", "natural", "concise", "fluent", "plain", "precise",
    "straightforward", "well-phrased",
]

_INSTRUCTION_TEMPLATES = [
    "{verb} the following question in a {style} way that means exactly the same thing. Keep the answer identical. Do not answer it.",
    "{verb} the question below into a {style}, semantically equivalent version. The correct answer must not change. Do not answer it.",
    "Your task: {verb_l} the question into a {style} paraphrase with the same meaning and the same answer. Return only the new question.",
    "{verb} this question so it stays {style} and semantically equivalent, preserving the intended answer. Output the question only.",
    "Produce a {style} paraphrase of the question that a reader would answer the same way. {verb} it without changing the meaning.",
]

_SYSTEM = "You rewrite questions while preserving their exact meaning. You never answer them."


def _instruction() -> str:
    verb = random.choice(_VERBS)
    return random.choice(_INSTRUCTION_TEMPLATES).format(
        verb=verb, verb_l=verb.lower(), style=random.choice(_STYLES)
    )


def _build_prompt(question: str) -> str:
    return f"{_instruction()}\n\nQuestion: {question}"


def propose(
    question: str,
    lm: M.LoadedModel,
    *,
    max_new_tokens: int = 64,
    temperature: float = 1.0,
) -> str:
    """Return one paraphrase of the question.

    Strips surrounding quotes and any leading label the model might add.
    On an empty or degenerate generation, returns the input unchanged so
    the caller can detect the no-op and skip it.
    """
    gen = GenConfig(max_new_tokens=max_new_tokens, temperature=temperature,
                    top_p=1.0, n_samples=1)
    raw = M.generate_one(lm, _build_prompt(question), gen)
    cand = raw.strip().strip('"').strip("'").strip()
    # Models sometimes prefix "New question:" or similar; drop a leading label.
    for sep in ("\n",):
        if sep in cand:
            cand = cand.split(sep)[0].strip()
    if not cand:
        return question
    return cand


def propose_many(
    question: str,
    lm: M.LoadedModel,
    n: int,
    *,
    max_new_tokens: int = 64,
    temperature: float = 1.0,
) -> list[str]:
    """n paraphrase candidates. Duplicates are allowed; the optimiser and
    feasibility gate handle filtering."""
    return [
        propose(question, lm, max_new_tokens=max_new_tokens, temperature=temperature)
        for _ in range(n)
    ]
