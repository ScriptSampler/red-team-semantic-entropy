"""Sentence-embedding encoder for the independent (finding-14) clusterer.

Loads a NON-NLI sentence encoder as the reframe-(b) adjudicator. Default
`intfloat/e5-base-unsupervised`: the E5 checkpoint trained only by weakly-supervised
contrastive learning on CCPairs (CommunityQA, CommonCrawl, Wikipedia, scientific,
news; arXiv:2212.03533), BEFORE the supervised fine-tuning stage that adds SNLI/MNLI
(arXiv:2402.05672) — so it provably never observes NLI labels and is independent of
the DeBERTa-large-MNLI the detector uses to cluster. (all-mpnet / e5-v2 / gte train on
AllNLI and would re-import the confound — do NOT use them here.) Fallback: gtr-t5-base
(QA + MS-MARCO, no NLI, no prefix).

Provides embed_fn(list[str]) -> normalized (n, d) numpy array for
`entropy.cluster_samples_embedding`. Independence scope is honest: it holds for the
MNLI *supervision* signal, not the generic web-text pretraining both models inherit.
"""
from __future__ import annotations

import numpy as np
import torch
import torch.nn.functional as F
from transformers import AutoModel, AutoTokenizer

E5_UNSUP = "intfloat/e5-base-unsupervised"     # primary: provably NLI-free
GTR_BASE = "sentence-transformers/gtr-t5-base"  # fallback: NLI-free, no prefix


def _avg_pool(last_hidden, mask):
    """Mask-aware mean pooling (the e5 model card's native pooling)."""
    h = last_hidden.masked_fill(~mask[..., None].bool(), 0.0)
    return h.sum(1) / mask.sum(1)[..., None].clamp(min=1e-9)


def load_embedder(model_id: str = E5_UNSUP, device: str = "cuda",
                  prefix: str = "query: ", max_length: int = 512):
    """Return embed_fn(texts) -> L2-normalized (n, d) numpy array.

    The SAME prefix is applied to both sides of every pair so retrieval asymmetry is
    neutralised and cosine is symmetric (use prefix='' for gtr-t5-base)."""
    tok = AutoTokenizer.from_pretrained(model_id)
    mdl = AutoModel.from_pretrained(model_id).eval().to(device)

    @torch.no_grad()
    def embed_fn(texts):
        texts = [prefix + t for t in texts]
        b = tok(texts, padding=True, truncation=True, max_length=max_length,
                return_tensors="pt").to(device)
        emb = _avg_pool(mdl(**b).last_hidden_state, b["attention_mask"])
        return F.normalize(emb, p=2, dim=1).cpu().numpy().astype(np.float64)

    return embed_fn
