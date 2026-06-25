"""Semantic Entropy Probes (SEPs) and the SE -> SEP transfer experiment.

Reference: Kossen et al., COLM 2024, arXiv 2406.15927. A SEP is a linear probe
on a single LLM hidden state that approximates the (binarized) semantic entropy
of the model on that input, without paying SE's N-sample sampling cost.

Why this is in the project: the positioning work (docs/positioning.md) argues the
strongest version of our result is "attack the paradigm", i.e. show that an input
paraphrase tuned against sampling-based SE also moves a *hidden-state* probe that
never samples. If it does, the vulnerability is in the representation, not just
the decoding. The closest prior art, CORVUS (arXiv 2601.14310), also degrades SEP
but model-side (LoRA), suppression-only, no NLI constraint; our angle is input-side,
bidirectional, NLI-constrained, so it must be differentiated explicitly.

Token position: we use TBG ("token before generating") = the hidden state at the
last input-prompt token, before any generation. Kossen et al. find TBG informative,
and it is the natural transfer target here because the attack perturbs the *input*:
a paraphrase changes the TBG hidden state directly, with no generation needed.

This module separates the GPU part (extract_tbg_features) from the pure-ML part
(SEPProbe), so the probe logic is unit-testable on synthetic features without a GPU.
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from .config import GenConfig  # noqa: F401  (kept for API symmetry / future use)


# ---- pure-ML probe (no GPU, unit-testable) ---------------------------------

@dataclass
class SEPProbe:
    """Standardize -> logistic regression probe predicting P(high entropy).

    Thin wrapper so callers do not depend on sklearn internals and so the
    transfer experiment can serialize/reuse a trained probe.
    """
    scaler_mean: np.ndarray
    scaler_std: np.ndarray
    coef: np.ndarray
    intercept: float

    @staticmethod
    def train(features: np.ndarray, labels: np.ndarray, C: float = 1.0) -> "SEPProbe":
        from sklearn.preprocessing import StandardScaler
        from sklearn.linear_model import LogisticRegression

        scaler = StandardScaler().fit(features)
        Xs = scaler.transform(features)
        clf = LogisticRegression(C=C, max_iter=2000).fit(Xs, labels)
        return SEPProbe(
            scaler_mean=scaler.mean_.astype(np.float64),
            scaler_std=np.where(scaler.scale_ == 0, 1.0, scaler.scale_).astype(np.float64),
            coef=clf.coef_.reshape(-1).astype(np.float64),
            intercept=float(clf.intercept_[0]),
        )

    def score(self, features: np.ndarray) -> np.ndarray:
        """Return P(high entropy) for each row. This is the SEP detector score."""
        X = np.asarray(features, dtype=np.float64)
        Xs = (X - self.scaler_mean) / self.scaler_std
        logits = Xs @ self.coef + self.intercept
        return 1.0 / (1.0 + np.exp(-logits))


def binarize_entropy(entropies: np.ndarray, threshold: float | None = None) -> np.ndarray:
    """Label high entropy (>= threshold) as 1. Default threshold = median.

    Matches Kossen et al.'s framing of SEPs as predicting a binarized SE
    (high vs low semantic uncertainty).
    """
    e = np.asarray(entropies, dtype=np.float64)
    if threshold is None:
        threshold = float(np.median(e))
    return (e >= threshold).astype(int)


# ---- GPU feature extraction (run on the model) ------------------------------

def build_chat_input(lm, question: str):
    """Tokenize the chat-templated prompt the same way se.model does."""
    messages = [{"role": "user", "content": question}]
    text = lm.tokenizer.apply_chat_template(
        messages, tokenize=False, add_generation_prompt=True
    )
    return lm.tokenizer(text, return_tensors="pt").to(lm.model.device)


def extract_tbg_features(lm, questions: list[str], layer: int = -1,
                         progress_every: int = 200) -> np.ndarray:
    """Hidden state at the last input token (TBG), one vector per question.

    Returns an (n_questions, hidden_dim) float32 array. Requires the model;
    runs one forward pass per question with output_hidden_states=True. No
    generation, so this is cheap relative to SE sampling.
    """
    import torch

    feats: list[np.ndarray] = []
    with torch.no_grad():
        for i, q in enumerate(questions):
            inputs = build_chat_input(lm, q)
            out = lm.model(**inputs, output_hidden_states=True)
            # hidden_states: tuple(num_layers+1) of (1, seq, hidden); take chosen
            # layer, last token position (TBG).
            hs = out.hidden_states[layer][0, -1, :]
            feats.append(hs.float().cpu().numpy())
            if (i + 1) % progress_every == 0:
                print(f"  TBG features {i+1}/{len(questions)}", flush=True)
    return np.stack(feats, axis=0)
