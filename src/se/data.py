"""Dataset loaders.

TriviaQA is the primary benchmark for SE replication (Farquhar et al.).
We use the rc.nocontext config: questions and answers only, no retrieval
documents. The validation split has public labels and is what we score
against for replication.

SQuAD is added in Phase 2 as a second benchmark for the attack matrix.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Iterator

from datasets import load_dataset


@dataclass
class TriviaQAExample:
    """One TriviaQA item.

    answer is the canonical string Farquhar et al. score against.
    aliases are the alternative forms the official scorer also accepts;
    we keep them so an SE pipeline can call any of them correct without
    relying on string equality alone.
    """
    question_id: str
    question: str
    answer: str
    aliases: list[str] = field(default_factory=list)

    def all_acceptable(self) -> list[str]:
        """The canonical answer plus all aliases, deduped, lowercased."""
        seen = set()
        out: list[str] = []
        for s in [self.answer, *self.aliases]:
            key = s.strip().lower()
            if key and key not in seen:
                seen.add(key)
                out.append(s.strip())
        return out


def load_triviaqa(
    split: str = "validation", limit: int | None = None
) -> list[TriviaQAExample]:
    """Load TriviaQA rc.nocontext.

    Splits available: train, validation, test. test has hidden answers,
    so for any scoring use validation.
    """
    ds = load_dataset("trivia_qa", "rc.nocontext", split=split)
    if limit is not None:
        ds = ds.select(range(min(limit, len(ds))))
    out: list[TriviaQAExample] = []
    for row in ds:
        ans = row["answer"]
        canonical = (ans.get("value") or "").strip()
        aliases = list(ans.get("aliases") or [])
        normalized = list(ans.get("normalized_aliases") or [])
        # Combine the two alias lists, dedup later in all_acceptable.
        all_aliases = aliases + normalized
        out.append(
            TriviaQAExample(
                question_id=row["question_id"],
                question=row["question"].strip(),
                answer=canonical,
                aliases=all_aliases,
            )
        )
    return out


def iter_triviaqa(
    split: str = "validation", limit: int | None = None
) -> Iterator[TriviaQAExample]:
    """Streaming iterator for when you do not want the full split in memory."""
    ds = load_dataset("trivia_qa", "rc.nocontext", split=split, streaming=True)
    if limit is not None:
        ds = ds.take(limit)
    for row in ds:
        ans = row["answer"]
        yield TriviaQAExample(
            question_id=row["question_id"],
            question=row["question"].strip(),
            answer=(ans.get("value") or "").strip(),
            aliases=list(ans.get("aliases") or []) + list(ans.get("normalized_aliases") or []),
        )
