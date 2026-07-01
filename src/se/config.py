"""Central configuration for the project.

Keeping model ids, quantisation settings, and paths in one place so the
SE pipeline (Week 3), the attacks (Phase 2), and the eval scripts all
agree on what "the model" and "the settings" mean.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

import torch

# Repo paths. config.py lives at src/se/config.py, so the root is two up.
REPO_ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = REPO_ROOT / "data"
RESULTS_DIR = REPO_ROOT / "results"

# Models
LLAMA_MODEL_ID = "meta-llama/Llama-3.1-8B-Instruct"
NLI_MODEL_ID = "microsoft/deberta-large-mnli"  # used from Week 3


@dataclass
class GenConfig:
    """Generation settings.

    The SE method (Farquhar et al.) samples N answers per question at a
    moderate temperature, then clusters them by semantic equivalence.
    Defaults here match that: N=10 at T=1.0. Greedy single-answer
    generation uses do_sample=False.
    """
    # PINNED across every condition (clean SE, SRE, attacks, defense). Cluster
    # granularity depends on generation length, so a single value must be used
    # everywhere or the effect could be a length artifact (external review §7).
    # All Phase-1/2 runs used 48; the old 96 default was a latent inconsistency.
    max_new_tokens: int = 48
    temperature: float = 1.0
    top_p: float = 1.0
    n_samples: int = 10            # N in the SE paper
    seed: int | None = None


@dataclass
class ModelConfig:
    """How to load Llama 3.1 8B.

    4-bit nf4 with double quantisation, bf16 compute. bf16 is preferred
    over fp16 on RDNA 4 for numerical stability, and the 9070 XT supports
    it natively.
    """
    model_id: str = LLAMA_MODEL_ID
    load_in_4bit: bool = True
    bnb_4bit_quant_type: str = "nf4"
    bnb_4bit_use_double_quant: bool = True
    compute_dtype: torch.dtype = field(default=torch.bfloat16)
    device: str = "cuda"
