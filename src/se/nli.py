"""Bidirectional NLI semantic equivalence via DeBERTa-large-MNLI.

Two strings are treated as semantically equivalent if MNLI labels both
directions of the pair as entailment. This is the same convention
Farquhar et al. used for semantic-entropy clustering, and SECA uses
the same constraint for its semantic-equivalence guarantee on attacks.

Strict argmax entailment in both directions is the default. score()
returns the full softmax over the three classes for callers that want
to threshold on entailment probability instead.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

import torch
from transformers import AutoModelForSequenceClassification, AutoTokenizer

from .config import NLI_MODEL_ID


# microsoft/deberta-large-mnli label order: contradiction, neutral, entailment
NLILabel = Literal["contradiction", "neutral", "entailment"]
_LABELS: tuple[NLILabel, NLILabel, NLILabel] = ("contradiction", "neutral", "entailment")


@dataclass
class NLIResult:
    label: NLILabel
    contradict_prob: float
    neutral_prob: float
    entail_prob: float


class NLI:
    def __init__(self, model_id: str = NLI_MODEL_ID, device: str | None = None):
        if device is None:
            device = "cuda" if torch.cuda.is_available() else "cpu"
        self.device = device
        self.tokenizer = AutoTokenizer.from_pretrained(model_id)
        self.model = AutoModelForSequenceClassification.from_pretrained(
            model_id, torch_dtype=torch.float32
        ).to(device)
        self.model.eval()

    @torch.no_grad()
    def score_batch(self, pairs: list[tuple[str, str]], batch_size: int = 32) -> list[NLIResult]:
        """Score a list of (premise, hypothesis) pairs."""
        results: list[NLIResult] = []
        for start in range(0, len(pairs), batch_size):
            chunk = pairs[start : start + batch_size]
            premises = [p for p, _ in chunk]
            hypotheses = [h for _, h in chunk]
            inputs = self.tokenizer(
                premises, hypotheses,
                return_tensors="pt", padding=True, truncation=True, max_length=512,
            ).to(self.device)
            logits = self.model(**inputs).logits  # (B, 3)
            probs = torch.softmax(logits, dim=-1).cpu().tolist()
            for p in probs:
                idx = max(range(3), key=lambda i: p[i])
                results.append(NLIResult(
                    label=_LABELS[idx],
                    contradict_prob=p[0],
                    neutral_prob=p[1],
                    entail_prob=p[2],
                ))
        return results

    def score(self, premise: str, hypothesis: str) -> NLIResult:
        return self.score_batch([(premise, hypothesis)])[0]

    def entails(self, premise: str, hypothesis: str) -> bool:
        return self.score(premise, hypothesis).label == "entailment"

    def bidirectional_equivalent(self, a: str, b: str) -> bool:
        """True iff both directions argmax to entailment."""
        results = self.score_batch([(a, b), (b, a)])
        return results[0].label == "entailment" and results[1].label == "entailment"

    @torch.no_grad()
    def bidirectional_equivalent_batch(self, pairs: list[tuple[str, str]],
                                       batch_size: int = 32) -> list[bool]:
        """Vectorised bidirectional check over many candidate pairs."""
        # Build a flat batch: forward pair, then reverse pair, for every input pair.
        flat: list[tuple[str, str]] = []
        for a, b in pairs:
            flat.append((a, b))
            flat.append((b, a))
        results = self.score_batch(flat, batch_size=batch_size)
        out: list[bool] = []
        for i in range(0, len(results), 2):
            fwd = results[i].label == "entailment"
            rev = results[i + 1].label == "entailment"
            out.append(fwd and rev)
        return out
