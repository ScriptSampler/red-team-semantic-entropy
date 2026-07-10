"""LLM-judge equivalence oracle — the finding-14/15 adjudicator of last resort.

A pairwise answer-equivalence judge using an instruct model that is INDEPENDENT of both
the victim (NOT Llama-3.1-8B -> no circularity) and the DeBERTa-MNLI (NOT NLI-trained ->
does not re-import the shared-clusterer confound). Recommended: Qwen2.5-7B-Instruct
(Alibaba; Apache-2.0; a different model family from Llama, strong on the short-answer
equivalence case where sentence embedders were near-chance). 14B is the higher-capability
option and still fits 16 GB at 4-bit.

The judge must be SELF-VALIDATED on labeled pairs before it may adjudicate
(scripts/validate_judge.py): report its accuracy on the HARD-negative short-answer stratum
that killed e5. Only if it clears that stratum is it a trustworthy oracle; otherwise the
finding-14 attribution stays the NLI/exact-match bracket.

`judge_fn(a, b) -> bool` plugs straight into entropy.cluster_samples_judge. The judge is
symmetric-by-construction here (we do not assume the model is order-invariant; see
make_judge_fn's `symmetric` option).
"""
from __future__ import annotations

_PROMPT = (
    "Two short answers to the same trivia question are given. Decide whether they refer "
    "to the SAME answer. Count an alias, nickname, abbreviation, partial name, or surface "
    "variant as the SAME (they name the same entity). Count different entities or "
    "different values as DIFFERENT. Reply with ONLY 'yes' (same) or 'no' (different).\n"
    "Examples:\n"
    "Answer 1: Broncos | Answer 2: Denver Broncos -> yes\n"
    "Answer 1: JFK | Answer 2: John F. Kennedy -> yes\n"
    "Answer 1: the Nile | Answer 2: Nile River -> yes\n"
    "Answer 1: Denver Broncos | Answer 2: Denver Nuggets -> no\n"
    "Answer 1: 1912 | Answer 2: 1921 -> no\n"
    "Answer 1: Paris | Answer 2: Paris, Texas -> no\n"
    "Now decide.\n"
    "Answer 1: {a} | Answer 2: {b} -> "
)


def _parse_yes_no(text: str) -> bool:
    """Robustly parse a yes/no judgement; defaults to False (not-equivalent) if unclear,
    so an unparseable judge conservatively over-splits (higher entropy) rather than
    silently merging different answers."""
    t = (text or "").strip().lower()
    if t.startswith("yes"):
        return True
    if t.startswith("no"):
        return False
    iy, ino = t.find("yes"), t.find("no")
    if iy == -1:
        return False
    if ino == -1:
        return True
    return iy < ino


def make_judge_fn(generate_fn, *, symmetric: bool = True):
    """Wrap a text `generate_fn(prompt) -> str` into judge_fn(a, b) -> bool. When
    symmetric, requires BOTH orderings to agree on 'yes' (an equivalence relation should
    be order-invariant; disagreement -> treat as not-equivalent, the conservative call)."""
    def judge(a: str, b: str) -> bool:
        ab = _parse_yes_no(generate_fn(_PROMPT.format(a=a, b=b)))
        if not symmetric:
            return ab
        ba = _parse_yes_no(generate_fn(_PROMPT.format(a=b, b=a)))
        return ab and ba
    return judge


def make_batched_judge_fn(generate_batch_fn, *, symmetric: bool = True):
    """Wrap a batched `generate_batch_fn(prompts) -> list[str]` into
    judge_pairs(pairs) -> list[bool], one bool per (a, b). Both orderings (if symmetric)
    for ALL pairs go into ONE generate call, so clustering a set of N samples costs one
    GPU batch instead of O(N^2) sequential forwards.

    Semantics are identical to applying make_judge_fn per pair, PROVIDED batched greedy
    generation returns the same per-prompt output as single-prompt generation (verified by
    scripts/probe_batched_judge.py before this path is trusted). The judge is deterministic
    (do_sample=False), so batching cannot change a verdict except through that numerics
    equivalence, which the probe checks."""
    def judge_pairs(pairs):
        if not pairs:
            return []
        prompts = [_PROMPT.format(a=a, b=b) for a, b in pairs]
        if symmetric:
            prompts += [_PROMPT.format(a=b, b=a) for a, b in pairs]
        outs = generate_batch_fn(prompts)
        m = len(pairs)
        ab = [_parse_yes_no(outs[k]) for k in range(m)]
        if not symmetric:
            return ab
        ba = [_parse_yes_no(outs[m + k]) for k in range(m)]
        return [ab[k] and ba[k] for k in range(m)]
    return judge_pairs


def load_judge(model_id: str = "Qwen/Qwen2.5-7B-Instruct", device: str = "cuda",
               max_new_tokens: int = 3, load_in_4bit: bool = True, symmetric: bool = True,
               batched: bool = False, judge_batch_size: int = 12):
    """Load an instruct model and return the judge callable. 4-bit keeps a 7B/14B judge
    within 16 GB alongside nothing else (run the judge AFTER the attack matrix frees the
    GPU). With batched=False (default) returns judge_fn(a, b) -> bool (the validated path,
    used by validate_judge.py). With batched=True returns judge_pairs(pairs) -> list[bool]
    (the fast path for the scale run; plug into entropy.cluster_samples_judge_batched).

    judge_batch_size caps how many prompts go into ONE generate() forward pass. The full
    O(n^2) set (up to ~90 for N=10 symmetric) OOMs a 16 GB GPU that is ALSO holding the
    victim + DeBERTa, so we sub-batch. Per-prompt greedy output is invariant to which other
    prompts share its chunk (pad tokens are attention-masked), so chunking stays
    verdict-identical to both the single-call batch and the unbatched judge."""
    import torch
    from transformers import AutoModelForCausalLM, AutoTokenizer, BitsAndBytesConfig

    tok = AutoTokenizer.from_pretrained(model_id)
    if tok.pad_token_id is None:
        tok.pad_token = tok.eos_token
    qcfg = BitsAndBytesConfig(load_in_4bit=True, bnb_4bit_compute_dtype=torch.float16,
                              bnb_4bit_quant_type="nf4") if load_in_4bit else None
    mdl = AutoModelForCausalLM.from_pretrained(
        model_id, quantization_config=qcfg,
        torch_dtype=torch.float16, device_map=device).eval()

    @torch.no_grad()
    def generate_fn(prompt: str) -> str:
        msgs = [{"role": "user", "content": prompt}]
        ids = tok.apply_chat_template(msgs, add_generation_prompt=True, return_tensors="pt").to(mdl.device)
        out = mdl.generate(ids, max_new_tokens=max_new_tokens, do_sample=False,
                           pad_token_id=tok.eos_token_id)
        return tok.decode(out[0, ids.shape[1]:], skip_special_tokens=True)

    if not batched:
        return make_judge_fn(generate_fn, symmetric=symmetric)

    @torch.no_grad()
    def generate_batch_fn(prompts: list[str]) -> list[str]:
        # Decoder-only batched generation needs LEFT padding so the generated tokens of
        # every row start at the same position; attention_mask masks the pad tokens out.
        # Sub-batch to judge_batch_size so the activation for one chunk fits alongside the
        # victim + DeBERTa; per-prompt output does not depend on chunk composition.
        texts = [tok.apply_chat_template([{"role": "user", "content": p}],
                                         add_generation_prompt=True, tokenize=False)
                 for p in prompts]
        outs: list[str] = []
        old_side = tok.padding_side
        tok.padding_side = "left"
        try:
            for i in range(0, len(texts), judge_batch_size):
                chunk = texts[i:i + judge_batch_size]
                enc = tok(chunk, return_tensors="pt", padding=True,
                          add_special_tokens=False).to(mdl.device)
                out = mdl.generate(**enc, max_new_tokens=max_new_tokens, do_sample=False,
                                   pad_token_id=tok.eos_token_id)
                gen = out[:, enc["input_ids"].shape[1]:]
                outs.extend(tok.decode(g, skip_special_tokens=True) for g in gen)
        finally:
            tok.padding_side = old_side
        return outs

    return make_batched_judge_fn(generate_batch_fn, symmetric=symmetric)
