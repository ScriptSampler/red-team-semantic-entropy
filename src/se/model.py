"""Load Llama 3.1 8B Instruct at 4-bit and generate from it.

This is the foundation the SE sampler (Week 3) and the attacks (Phase 2)
build on. Two generation entry points:

    generate_one   single answer, greedy by default
    generate_samples   N answers at a temperature, for SE clustering
"""
from __future__ import annotations

import time
from dataclasses import dataclass

import torch
from transformers import (
    AutoModelForCausalLM,
    AutoTokenizer,
    BitsAndBytesConfig,
)

from .config import ModelConfig, GenConfig


@dataclass
class LoadedModel:
    model: AutoModelForCausalLM
    tokenizer: AutoTokenizer
    load_seconds: float
    load_vram_mb: float


def load_llama(cfg: ModelConfig | None = None) -> LoadedModel:
    """Load the model + tokenizer. Downloads and caches on first call."""
    cfg = cfg or ModelConfig()

    quant = None
    if cfg.load_in_4bit:
        quant = BitsAndBytesConfig(
            load_in_4bit=True,
            bnb_4bit_quant_type=cfg.bnb_4bit_quant_type,
            bnb_4bit_use_double_quant=cfg.bnb_4bit_use_double_quant,
            bnb_4bit_compute_dtype=cfg.compute_dtype,
        )

    if torch.cuda.is_available():
        torch.cuda.reset_peak_memory_stats()
    t0 = time.perf_counter()

    tokenizer = AutoTokenizer.from_pretrained(cfg.model_id)
    if tokenizer.pad_token_id is None:
        tokenizer.pad_token_id = tokenizer.eos_token_id

    model = AutoModelForCausalLM.from_pretrained(
        cfg.model_id,
        quantization_config=quant,
        torch_dtype=cfg.compute_dtype,
        device_map=cfg.device,
    )
    model.eval()

    load_seconds = time.perf_counter() - t0
    load_vram_mb = (
        torch.cuda.memory_allocated() / 1024**2 if torch.cuda.is_available() else 0.0
    )
    return LoadedModel(model, tokenizer, load_seconds, load_vram_mb)


def _build_inputs(lm: LoadedModel, question: str) -> dict:
    """Apply the Llama 3.1 chat template to a single question."""
    messages = [{"role": "user", "content": question}]
    text = lm.tokenizer.apply_chat_template(
        messages, tokenize=False, add_generation_prompt=True
    )
    return lm.tokenizer(text, return_tensors="pt").to(lm.model.device)


@torch.no_grad()
def generate_one(lm: LoadedModel, question: str, gen: GenConfig | None = None) -> str:
    """Single greedy answer. Returns the decoded continuation only."""
    gen = gen or GenConfig()
    inputs = _build_inputs(lm, question)
    out = lm.model.generate(
        **inputs,
        max_new_tokens=gen.max_new_tokens,
        do_sample=False,
        pad_token_id=lm.tokenizer.pad_token_id,
    )
    new_tokens = out[0, inputs["input_ids"].shape[1]:]
    return lm.tokenizer.decode(new_tokens, skip_special_tokens=True).strip()


@torch.no_grad()
def generate_samples(
    lm: LoadedModel, question: str, gen: GenConfig | None = None
) -> list[str]:
    """N sampled answers at a temperature. This is the SE sampling step.

    Uses num_return_sequences so the N samples share one forward pass over
    the prompt, which is far cheaper than N separate calls.
    """
    gen = gen or GenConfig()
    if gen.seed is not None:
        torch.manual_seed(gen.seed)
    inputs = _build_inputs(lm, question)
    out = lm.model.generate(
        **inputs,
        max_new_tokens=gen.max_new_tokens,
        do_sample=True,
        temperature=gen.temperature,
        top_p=gen.top_p,
        num_return_sequences=gen.n_samples,
        pad_token_id=lm.tokenizer.pad_token_id,
    )
    prompt_len = inputs["input_ids"].shape[1]
    return [
        lm.tokenizer.decode(seq[prompt_len:], skip_special_tokens=True).strip()
        for seq in out
    ]


def peak_vram_mb() -> float:
    return torch.cuda.max_memory_allocated() / 1024**2 if torch.cuda.is_available() else 0.0
