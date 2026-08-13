"""Re-score the CACHED samples under the generating model, to settle whether the
empirical pile-up near the ceiling is an artefact of the DISCRETE estimator.

THE OPEN QUESTION
-----------------
`results/ceiling_saturation_finding.md` and `results/fair_pool_granularity.md` measure a
pile-up of scores at and just below ln(10). Both were computed with the DISCRETE
estimator (cluster probability = sample proportion), which is one of three semantic
entropies in the literature:

  (1) DISCRETE           p(C_k) = n_k / N.            Bounded by log N. **What we run.**
                         Farquhar et al. (Nature 2024) define this variant explicitly and
                         use it for all their GPT-4 results.
  (2) FARQUHAR Eq. (5)   p(C_k) proportional to the summed sequence likelihood of the
                         cluster's members, NORMALISED over clusters. Bounded by log K.
  (3) KUHN Eq. (4)       mean of per-cluster surprisals, UNNORMALISED. NOT bounded by
                         log N -- it can and does exceed it.

`scripts/duplication_level_sim.py` shows the pile-up surviving at small likelihood spread
and vanishing at large, with the crossover inside the plausible range. So the question is
genuinely open and a simulation cannot close it.

WHAT THIS SCRIPT DOES
---------------------
Nothing is regenerated. The 20,000 sample strings are already on disk; they are
TEACHER-FORCED through the same victim model to recover per-token log-probabilities, and
all three estimators are then computed on IDENTICAL samples and IDENTICAL clusterings.
The only thing that varies between the three numbers is the weighting rule, which is
exactly the comparison the question needs.

Because the samples were drawn at temperature 1.0 with top_p 1.0, the sampling
distribution IS the model distribution: teacher-forced scoring recovers the true sample
likelihoods with no temperature or nucleus correction. That is a property of this cache,
not a general one -- see `audit_generation_settings`.

STATUS: BUILT, NOT RUN. The GPU is saturated by the multi-day `_defb` chain
(`scripts/run_definitive_chain.sh`). Use `--estimate-only` for the cost, `--benchmark`
for a measured throughput once the GPU frees, then the default mode for the real pass.

Usage:
    # CPU only, no model: manifest audit + exact token counts + cost
    ./.venv-wsl/bin/python scripts/rescore_likelihoods.py --estimate-only

    # measured throughput on a handful of questions (small GPU job)
    ./.venv-wsl/bin/python scripts/rescore_likelihoods.py --benchmark 8

    # the real pass; per-question checkpointed and resumable
    ./.venv-wsl/bin/python scripts/rescore_likelihoods.py

    # rebuild the comparison from an existing checkpoint (CPU only)
    ./.venv-wsl/bin/python scripts/rescore_likelihoods.py --report-only
"""
from __future__ import annotations

import argparse
import json
import math
import os
import sys
import time
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np

REPO_ROOT = Path(__file__).resolve().parents[1]
RESULTS_DIR = REPO_ROOT / "results"
sys.path.insert(0, str(REPO_ROOT / "src"))

SAMPLES_DIR = Path("~/.cache/se-research/samples/wk4_full_2000q").expanduser()
CHECKPOINT = RESULTS_DIR / "rescore_likelihoods_ckpt.jsonl"
REPORT = RESULTS_DIR / "rescore_likelihoods.md"

N_SAMPLES = 10
CAP = math.log(N_SAMPLES)             # ln 10, the discrete/Eq.(5) ceiling at N=10
TOP_DECILE = 0.9 * CAP
TOL = 1e-9
DP_DISTINCT = 9                       # rounding tolerance for the distinct-value count

# What the manifest MUST pin for a teacher-forced re-score to be faithful. A logit is a
# function of all of these; a value we cannot read off the manifest is an assumption.
REQUIRED_PINS = [
    ("model_id", "which weights produced the samples"),
    ("load_in_4bit", "4-bit vs full precision changes every logit"),
    ("n_samples", "N, the sample budget the estimators normalise against"),
    ("temperature", "T != 1 would mean the sampling distribution is not the model's"),
    ("max_new_tokens", "the truncation length, which decides which samples lack an EOS"),
    ("split", "which TriviaQA split the question ids index into"),
]
DESIRABLE_PINS = [
    ("top_p", "nucleus truncation; top_p < 1 would break the T=1 identity too"),
    ("bnb_4bit_quant_type", "nf4 vs fp4 gives different weights after dequantisation"),
    ("bnb_4bit_use_double_quant", "changes the dequantised weights"),
    ("compute_dtype", "bf16 vs fp16 accumulation shifts logprobs"),
    ("model_revision", "no commit hash: the HF checkpoint could have moved since"),
    ("transformers_version", "tokenizer/template changes across versions"),
]

# Throughput anchors for --estimate-only. The floor is MEASURED, from this repo's own
# generation runs; the others are the plausible prefill range that --benchmark resolves.
MEASURED_GEN_TOKENS_PER_S = 80.0      # see cost_estimate() for the derivation
THROUGHPUT_GRID = [80.0, 500.0, 2000.0, 5000.0]
MODEL_LOAD_SECONDS = 56.0             # results/model_check.md, results/pipeline_check.md


# ============================================================== pure: the estimators
def _logsumexp(xs) -> float:
    xs = [float(x) for x in xs]
    if not xs:
        return -math.inf
    m = max(xs)
    if m == -math.inf:
        return -math.inf
    return m + math.log(math.fsum(math.exp(x - m) for x in xs))


def _cluster_members(assignments) -> dict[int, list[int]]:
    out: dict[int, list[int]] = {}
    for i, c in enumerate(assignments):
        out.setdefault(int(c), []).append(i)
    return out


def length_normalise(logliks, n_tokens) -> list[float]:
    """Kuhn et al. section 3.3: divide the sequence log-likelihood by its token count.

    Without this, longer sequences are penalised purely for being longer and the
    likelihood weighting degenerates into a length ranking. A zero-token sample would
    divide by zero; it is passed through as -inf (weight 0) rather than crashing, and
    the caller reports how many there were."""
    out = []
    for ll, t in zip(logliks, n_tokens):
        t = int(t)
        out.append(-math.inf if t <= 0 else float(ll) / t)
    return out


def discrete_entropy_estimator(assignments) -> float:
    """(1) DISCRETE. p(C_k) = n_k / N; H = -sum_k p log p. Bounded by log N.

    Identical to `se.entropy.discrete_entropy` -- reimplemented here only so the three
    estimators sit side by side and can be diffed by eye."""
    if not len(assignments):
        return 0.0
    counts = Counter(int(a) for a in assignments)
    total = sum(counts.values())
    h = -math.fsum((c / total) * math.log(c / total) for c in counts.values())
    return h + 0.0                        # normalise -0.0 to 0.0 for the report tables


def farquhar_eq5_entropy(assignments, seq_logliks) -> float:
    """(2) FARQUHAR et al. (Nature 2024) Eq. (5), the likelihood-weighted estimator.

        p(C_k | x) = sum_{s in C_k} p(s | x) / sum_{s} p(s | x)
        H          = - sum_k p(C_k | x) log p(C_k | x)

    The denominator is the explicit normalisation over the OBSERVED samples: p is a
    genuine probability vector over the K observed clusters, so 0 <= H <= log K <= log N.
    Computed in log space -- sequence likelihoods here run to e^-60 and a direct
    exponentiation underflows to zero, which would silently drop clusters.

    When every sample has the same likelihood this reduces EXACTLY to the discrete
    estimator, which is the invariant the tests pin."""
    if not len(assignments):
        return 0.0
    members = _cluster_members(assignments)
    log_z = _logsumexp(seq_logliks)
    if log_z == -math.inf:
        raise ValueError("all sample likelihoods are zero; cannot normalise Eq. (5)")
    h = 0.0
    for idxs in members.values():
        log_p = _logsumexp([seq_logliks[i] for i in idxs]) - log_z
        if log_p == -math.inf:
            continue                      # p = 0 contributes 0 log 0 = 0
        h -= math.exp(log_p) * log_p
    return h + 0.0                        # normalise -0.0 to 0.0


def kuhn_eq4_entropy(assignments, seq_logliks) -> float:
    """(3) KUHN et al. Eq. (4), the unnormalised mean surprisal.

        H = - (1/K) sum_{k=1}^{K} log p(C_k | x),   p(C_k | x) = sum_{s in C_k} p(s | x)

    NOT normalised across clusters and therefore NOT an entropy of any probability
    vector: it is the mean of K surprisals, each of which is unbounded above. It is
    NOT bounded by log N, and that is the entire point -- any ceiling-derived claim
    (the cap, the top decile of [0, log N], the attainable lattice) is silent about this
    estimator. Its scale is set by how improbable the model finds its own samples, so
    it moves with sequence length unless the length normalisation is applied first."""
    if not len(assignments):
        return 0.0
    members = _cluster_members(assignments)
    surprisals = []
    for idxs in members.values():
        log_p = _logsumexp([seq_logliks[i] for i in idxs])
        if log_p == -math.inf:
            raise ValueError("a cluster has zero total likelihood; Eq. (4) is undefined")
        surprisals.append(-log_p)
    return math.fsum(surprisals) / len(surprisals)


ESTIMATORS = {
    "discrete": "sample proportion (ours; Farquhar's discrete variant)",
    "farquhar_eq5": "likelihood-weighted, normalised over clusters",
    "kuhn_eq4": "unnormalised mean cluster surprisal",
}


def all_estimators(assignments, seq_logliks, n_tokens) -> dict[str, float]:
    """All three estimators on ONE clustering, plus the length-normalised variants.

    `discrete` appears once because it does not read likelihoods at all -- which is
    precisely why it is the same number under every weighting convention, and why any
    difference in the table below is attributable to the weighting and nothing else."""
    ln = length_normalise(seq_logliks, n_tokens)
    return {
        "discrete": discrete_entropy_estimator(assignments),
        "farquhar_eq5": farquhar_eq5_entropy(assignments, seq_logliks),
        "farquhar_eq5_lennorm": farquhar_eq5_entropy(assignments, ln),
        "kuhn_eq4": kuhn_eq4_entropy(assignments, seq_logliks),
        "kuhn_eq4_lennorm": kuhn_eq4_entropy(assignments, ln),
    }


# ============================================================ pure: comparison summary
def wilson(k: int, n: int, z: float = 1.959963984540054) -> tuple[float, float, float]:
    if n == 0:
        return (float("nan"),) * 3
    p = k / n
    d = 1.0 + z * z / n
    centre = (p + z * z / (2 * n)) / d
    half = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return p, max(0.0, centre - half), min(1.0, centre + half)


def fmt_prop(k: int, n: int) -> str:
    p, lo, hi = wilson(k, n)
    return f"{k}/{n} = {p:.1%} [{lo:.1%}, {hi:.1%}]"


def estimator_stats(values, cap: float = CAP, top_decile: float = TOP_DECILE,
                    dp: int = DP_DISTINCT) -> dict:
    """The three headline numbers, on one estimator's scores over one question set.

    `at_cap` counts scores at or above log N. For the discrete estimator and for
    Eq. (5) that is the ceiling and the count is an "is it saturated" measurement. For
    Kuhn Eq. (4) log N is not a ceiling at all, so `above_cap` (STRICTLY above) is
    reported alongside: a non-zero value there is the direct demonstration that the
    ceiling claim does not transfer."""
    v = [float(x) for x in values]
    n = len(v)
    return {
        "n": n,
        "at_cap": sum(1 for x in v if x >= cap - TOL),
        "above_cap": sum(1 for x in v if x > cap + TOL),
        "top_decile": sum(1 for x in v if x >= top_decile - TOL),
        "distinct": len({round(x, dp) for x in v}),
        "min": min(v) if n else float("nan"),
        "max": max(v) if n else float("nan"),
        "mean": (math.fsum(v) / n) if n else float("nan"),
    }


def spearman(a, b) -> float:
    """Rank correlation, ties averaged. The detector is used as a ranker, so the
    question "does the estimator change the ORDER" matters more than whether it changes
    the values -- a monotone reweighting would leave every AUROC in the paper intact."""
    a, b = np.asarray(a, dtype=float), np.asarray(b, dtype=float)
    if len(a) < 2:
        return float("nan")

    def rank(x):
        order = np.argsort(x, kind="mergesort")
        r = np.empty(len(x), dtype=float)
        r[order] = np.arange(len(x), dtype=float)
        # average ties
        _, inv, cnt = np.unique(x, return_inverse=True, return_counts=True)
        sums = np.zeros(len(cnt))
        np.add.at(sums, inv, r)
        return (sums / cnt)[inv]

    ra, rb = rank(a), rank(b)
    ra -= ra.mean()
    rb -= rb.mean()
    den = math.sqrt(float((ra ** 2).sum()) * float((rb ** 2).sum()))
    return float((ra * rb).sum() / den) if den else float("nan")


# ================================================================= pure: manifest audit
@dataclass
class ManifestAudit:
    present: dict[str, object] = field(default_factory=dict)
    missing_required: list[tuple[str, str]] = field(default_factory=list)
    missing_desirable: list[tuple[str, str]] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return not self.missing_required


def audit_generation_settings(manifest: dict, n_records: int | None = None) -> ManifestAudit:
    """Check the manifest actually pins what a faithful re-score needs. It does not.

    Findings this encodes (all verified against the real
    `wk4_full_2000q/manifest.json`, which is hand-rolled in `scripts/wk4_sample.py`
    rather than written by `se.sampling._write_manifest`):

      * `top_p`, `bnb_4bit_quant_type`, `bnb_4bit_use_double_quant` and `compute_dtype`
        are ABSENT. The quantisation settings change the dequantised weights and hence
        every logit, so re-scoring has to ASSUME `se.config.ModelConfig()` defaults
        (nf4 / double-quant / bf16). That assumption is almost certainly right -- the
        sampler called `ModelConfig()` with no overrides -- but it is an assumption
        recovered from code, not a pin recovered from data.
      * there is NO model revision or commit hash, and no library versions.
      * `n_questions_completed_this_run` is 1907 against 2000 records on disk, so the
        file was assembled over at least two runs and the manifest describes only the
        last one.

    None of this blocks the re-score; all of it belongs in the write-up."""
    a = ManifestAudit()
    for key, why in REQUIRED_PINS:
        if key in manifest:
            a.present[key] = manifest[key]
        else:
            a.missing_required.append((key, why))
    for key, why in DESIRABLE_PINS:
        if key in manifest:
            a.present[key] = manifest[key]
        else:
            a.missing_desirable.append((key, why))

    temp = manifest.get("temperature")
    top_p = manifest.get("top_p")
    if temp is not None and abs(float(temp) - 1.0) > 1e-12:
        a.warnings.append(
            f"temperature = {temp} != 1.0: the sampling distribution is NOT the model "
            "distribution, so teacher-forced logprobs would need a temperature "
            "correction before they can be read as p(s|x)."
        )
    else:
        a.warnings.append(
            "temperature = 1.0, so the sampling distribution IS the model distribution "
            "and teacher-forced logprobs are the sample likelihoods with no correction."
        )
    if top_p is None:
        a.warnings.append(
            "top_p is NOT pinned in the manifest. `scripts/wk4_sample.py` sets "
            "top_p=1.0 in its GenConfig literal, so the T=1 identity above holds -- but "
            "that is read from source, not from the artefact."
        )
    elif abs(float(top_p) - 1.0) > 1e-12:
        a.warnings.append(f"top_p = {top_p} != 1.0: nucleus truncation breaks the "
                          "T=1 identity; likelihoods would need renormalising.")

    n_run = manifest.get("n_questions_completed_this_run")
    if n_records is not None and n_run is not None and int(n_run) != int(n_records):
        a.warnings.append(
            f"manifest records {n_run} questions completed in the last run but "
            f"{n_records} are on disk: the cache was assembled across multiple runs and "
            "the manifest describes only the final one."
        )
    return a


# ======================================================================= pure: costing
def cost_estimate(n_sequences: int, total_tokens: int,
                  throughputs=THROUGHPUT_GRID,
                  load_seconds: float = MODEL_LOAD_SECONDS) -> list[dict]:
    """GPU-hours at each throughput anchor. Deliberately a table, not a single number.

    The FLOOR anchor (80 token-positions/s) is measured, from this repo's own numbers:
    `results/pipeline_check.md` records N=10 sampling over 100 questions in 1427 s, and
    the Week-4 manifest records 1907 questions in 23340 s. At ~52 prompt tokens and
    <=48 new tokens per sample that is ~1100 token-positions per question, i.e. 80-90
    positions/s. That pass was dominated by SEQUENTIAL decode steps. Teacher forcing is
    prefill only -- one parallel forward per sequence, no autoregressive loop -- so 80
    positions/s is a hard pessimistic bound rather than an estimate, and the true rate
    should be one to two orders of magnitude higher. `--benchmark` measures it."""
    rows = []
    for tps in throughputs:
        secs = total_tokens / tps + load_seconds
        rows.append({
            "tokens_per_second": tps,
            "seconds": secs,
            "gpu_hours": secs / 3600.0,
            "seconds_per_question": secs / max(n_sequences / N_SAMPLES, 1),
        })
    return rows


# ==================================================================== cache i/o (CPU)
def load_samples(samples_dir: Path) -> list[dict]:
    path = Path(samples_dir) / "samples.jsonl"
    out = []
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            if line.strip():
                out.append(json.loads(line))
    return out


def load_assignments(samples_dir: Path) -> dict[str, list[int]]:
    path = Path(samples_dir) / "entropy.jsonl"
    out = {}
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            if line.strip():
                o = json.loads(line)
                out[o["question_id"]] = o["assignments"]
    return out


def load_checkpoint(path: Path) -> dict[str, dict]:
    out: dict[str, dict] = {}
    if not Path(path).exists():
        return out
    with Path(path).open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                o = json.loads(line)
            except json.JSONDecodeError:
                continue                # torn final line from an interrupted write
            out[o["question_id"]] = o
    return out


def _tokenizer(model_id: str):
    os.environ.setdefault("HF_HOME", str(Path("~/.cache/huggingface").expanduser()))
    from transformers import AutoTokenizer
    tok = AutoTokenizer.from_pretrained(model_id)
    if tok.pad_token_id is None:
        tok.pad_token_id = tok.eos_token_id
    return tok


def token_census(records: list[dict], tok, max_new_tokens: int = 48) -> dict:
    """Exact prompt/completion token counts, plus the detokenise->retokenise check.

    The cache stores DECODED, `.strip()`ed strings with special tokens removed -- the
    generated token ids were never saved. Re-scoring therefore scores the string as the
    tokenizer canonically encodes it, which need not be the id sequence the sampler
    actually emitted. The round-trip check bounds how much that can bite: if
    decode(encode(s)) == s then the canonical encoding is a faithful representation of
    the stored string, which is the strongest guarantee recoverable from this cache."""
    prompt_tokens, comp_tokens = [], []
    round_trip_fail = 0
    truncated = 0
    over_budget = 0
    empty = 0
    for rec in records:
        msg = [{"role": "user", "content": rec["question"]}]
        text = tok.apply_chat_template(msg, tokenize=False, add_generation_prompt=True)
        p = len(tok(text)["input_ids"])
        prompt_tokens.append(p)
        for s in rec["samples"]:
            if not s:
                empty += 1
                comp_tokens.append(0)
                continue
            ids = tok(s, add_special_tokens=False)["input_ids"]
            comp_tokens.append(len(ids))
            if tok.decode(ids, skip_special_tokens=True) != s:
                round_trip_fail += 1
            if len(ids) >= max_new_tokens:
                truncated += 1
            if len(ids) > max_new_tokens:
                # A sample cannot have been GENERATED with more than max_new_tokens
                # tokens, so any of these is direct proof that the canonical
                # retokenization differs from the emitted id sequence. It is a LOWER
                # bound on the disagreement: same-length-different-ids is invisible.
                over_budget += 1
    p = np.array(prompt_tokens)
    c = np.array(comp_tokens)
    n_seq = len(c)
    return {
        "n_questions": len(records),
        "n_sequences": n_seq,
        "prompt_mean": float(p.mean()), "prompt_max": int(p.max()),
        "completion_mean": float(c.mean()), "completion_max": int(c.max()),
        "completion_p95": float(np.percentile(c, 95)),
        "total_tokens": int(p.sum() * N_SAMPLES + c.sum()),
        "total_tokens_prompt_shared": int(p.sum() + c.sum()),
        "round_trip_fail": round_trip_fail,
        "round_trip_rate": round_trip_fail / max(n_seq, 1),
        "at_max_new_tokens": truncated,
        "over_max_new_tokens": over_budget,
        "empty_samples": empty,
    }


# ================================================================= GPU: teacher forcing
def score_question(lm, question: str, samples: list[str]) -> dict:
    """Teacher-force one question's samples; return per-sequence loglik and token count.

    One forward pass over the batch of (prompt + completion) sequences. The prompt is
    identical across the 10 samples, so they are built once and concatenated; only
    COMPLETION positions contribute to the likelihood -- the prompt is conditioning, not
    generated text, and including it would add a large constant to every score and
    silently rescale Kuhn Eq. (4).

    Right padding with an attention mask: this is a single forward pass, not generation,
    so there is no left-padding requirement, and masked positions are excluded from the
    gather rather than merely ignored."""
    import torch

    tok = lm.tokenizer
    msg = [{"role": "user", "content": question}]
    text = tok.apply_chat_template(msg, tokenize=False, add_generation_prompt=True)
    # `tok(text)` with add_special_tokens left at its default is DELIBERATE: it is
    # character-for-character what `se.model._build_inputs` did when the samples were
    # generated, including the duplicated <|begin_of_text|> that the chat template has
    # already emitted. Passing add_special_tokens=False here would be "more correct" in
    # the abstract and WRONG here -- it would score the samples under a prompt the
    # sampler never saw.
    prompt_ids = tok(text)["input_ids"]
    n_prompt = len(prompt_ids)

    seqs, comp_lens = [], []
    for s in samples:
        comp = tok(s, add_special_tokens=False)["input_ids"] if s else []
        seqs.append(prompt_ids + comp)
        comp_lens.append(len(comp))

    width = max(len(s) for s in seqs)
    pad_id = tok.pad_token_id
    input_ids = torch.full((len(seqs), width), pad_id, dtype=torch.long)
    attn = torch.zeros((len(seqs), width), dtype=torch.long)
    for i, s in enumerate(seqs):
        input_ids[i, :len(s)] = torch.tensor(s, dtype=torch.long)
        attn[i, :len(s)] = 1
    input_ids = input_ids.to(lm.model.device)
    attn = attn.to(lm.model.device)

    with torch.no_grad():
        logits = lm.model(input_ids=input_ids, attention_mask=attn).logits

    logliks = []
    for i, t in enumerate(comp_lens):
        if t == 0:
            logliks.append(float("-inf"))
            continue
        # position j predicts token j+1, so the completion tokens at
        # [n_prompt, n_prompt+t) are predicted from [n_prompt-1, n_prompt+t-1).
        # Slice FIRST and cast to fp32 second: a full-tensor log_softmax over a
        # 128k vocabulary would materialise ~0.7 GB per question, and this GPU is
        # shared with a multi-day run.
        tgt = input_ids[i, n_prompt:n_prompt + t]
        row = logits[i, n_prompt - 1:n_prompt + t - 1, :].float()
        chosen = row.gather(-1, tgt.unsqueeze(-1)).squeeze(-1)
        logliks.append(float((chosen - torch.logsumexp(row, dim=-1)).sum().item()))

    return {
        "prompt_tokens": n_prompt,
        "n_tokens": comp_lens,
        "loglik": logliks,
    }


def run_scoring(samples_dir: Path, checkpoint: Path, limit: int | None,
                progress_every: int = 25) -> None:
    """The GPU pass. Per-question checkpointed, resumable, fsynced after every question.

    Follows `scripts/wk4_sample.py`: append-only JSONL, completed ids read back on
    startup and skipped, so an interruption costs at most the question in flight."""
    from se import model as M
    from se.config import ModelConfig

    records = load_samples(samples_dir)
    if limit:
        records = records[:limit]
    done = load_checkpoint(checkpoint)
    todo = [r for r in records if r["question_id"] not in done]
    print(f"{len(records)} questions, {len(done)} already scored, {len(todo)} to do",
          flush=True)
    if not todo:
        print("nothing to do", flush=True)
        return

    cfg = ModelConfig()
    print(f"loading {cfg.model_id} "
          f"(4bit={cfg.load_in_4bit}, {cfg.bnb_4bit_quant_type}, "
          f"double={cfg.bnb_4bit_use_double_quant}, {cfg.compute_dtype})...", flush=True)
    t0 = time.perf_counter()
    lm = M.load_llama(cfg)
    print(f"loaded in {time.perf_counter() - t0:.1f}s", flush=True)

    Path(checkpoint).parent.mkdir(parents=True, exist_ok=True)
    t_start = time.perf_counter()
    with Path(checkpoint).open("a", encoding="utf-8") as f:
        for i, rec in enumerate(todo):
            out = score_question(lm, rec["question"], rec["samples"])
            out["question_id"] = rec["question_id"]
            f.write(json.dumps(out) + "\n")
            f.flush()
            os.fsync(f.fileno())
            if (i + 1) % progress_every == 0:
                el = time.perf_counter() - t_start
                print(f"  {i + 1}/{len(todo)} in {el:.0f}s ({el / (i + 1):.2f}s/Q), "
                      f"ETA {(el / (i + 1)) * (len(todo) - i - 1) / 60:.1f} min",
                      flush=True)
    el = time.perf_counter() - t_start
    print(f"scored {len(todo)} questions in {el:.0f}s ({el / max(len(todo), 1):.2f}s/Q)",
          flush=True)


def run_benchmark(samples_dir: Path, n_questions: int) -> None:
    """Measure real throughput on `n_questions` questions and print the extrapolation.

    Two minutes of GPU time that replaces the whole estimate table with a number."""
    from se import model as M
    from se.config import ModelConfig

    records = load_samples(samples_dir)[:n_questions]
    lm = M.load_llama(ModelConfig())
    score_question(lm, records[0]["question"], records[0]["samples"])   # warm-up
    t0 = time.perf_counter()
    tokens = 0
    for rec in records:
        out = score_question(lm, rec["question"], rec["samples"])
        tokens += out["prompt_tokens"] * len(out["n_tokens"]) + sum(out["n_tokens"])
    el = time.perf_counter() - t0
    tps = tokens / el
    print(f"benchmark: {len(records)} questions, {tokens} token-positions in {el:.1f}s")
    print(f"  {tps:.0f} token-positions/s, {el / len(records):.2f} s/question")
    print(f"  full 2000-question pass: {2000 * el / len(records) / 3600:.2f} GPU-hours "
          f"(+ {MODEL_LOAD_SECONDS / 3600:.2f} h load)")


# ========================================================================= the report
def build_report(samples_dir: Path, checkpoint: Path, out_path: Path) -> None:
    """Join the checkpoint with the cached clusterings and write the comparison."""
    ckpt = load_checkpoint(checkpoint)
    if not ckpt:
        raise SystemExit(f"no checkpoint at {checkpoint}; run the scoring pass first")
    assigns = load_assignments(samples_dir)

    qids = [q for q in ckpt if q in assigns]
    rows = {}
    skipped = []
    for q in qids:
        c = ckpt[q]
        if len(c["loglik"]) != len(assigns[q]):
            skipped.append(q)
            continue
        rows[q] = all_estimators(assigns[q], c["loglik"], c["n_tokens"])

    if not rows:
        raise SystemExit(
            f"checkpoint at {checkpoint} has {len(ckpt)} records but none join to a "
            f"cached clustering in {samples_dir}/entropy.jsonl "
            f"({len(skipped)} sample-count mismatches). Nothing to report.")
    names = list(next(iter(rows.values())).keys())
    series = {nm: [rows[q][nm] for q in rows] for nm in names}
    stats = {nm: estimator_stats(series[nm]) for nm in names}
    n = len(rows)

    out = []
    A = out.append
    A("# Three semantic-entropy estimators on identical samples and identical clusterings")
    A("")
    A(f"Generated by `scripts/rescore_likelihoods.py` over **{n} questions** "
      f"(N={N_SAMPLES} samples each). Skipped {len(skipped)} for a sample-count "
      "mismatch between the checkpoint and the cached clustering.")
    A("")
    A("The clustering is held FIXED at the cached NLI clustering for all rows, so every "
      "difference below is attributable to the weighting rule and to nothing else.")
    A("")
    A(f"Reference constants at N={N_SAMPLES}: cap log N = **{CAP:.4f}**, top tenth of "
      f"the range = **{TOP_DECILE:.4f}**.")
    A("")
    A("| estimator | at cap (>= log N) | STRICTLY above log N | top decile | distinct "
      "values | min | mean | max |")
    A("| --- | --- | --- | --- | --- | --- | --- | --- |")
    for nm in names:
        s = stats[nm]
        A(f"| `{nm}` | {fmt_prop(s['at_cap'], n)} | {fmt_prop(s['above_cap'], n)} | "
          f"{fmt_prop(s['top_decile'], n)} | {s['distinct']} | {s['min']:.4f} | "
          f"{s['mean']:.4f} | {s['max']:.4f} |")
    A("")
    A("Reading it: a non-zero **STRICTLY above log N** cell is a direct demonstration "
      "that the ceiling claim does not transfer to that estimator. It must be zero for "
      "`discrete` and for `farquhar_eq5` (both are bounded by log N) and is expected to "
      "be large for `kuhn_eq4`.")
    A("")
    A("Two behaviours are expected rather than bugs. (a) `kuhn_eq4_lennorm` can go "
      "**negative**: after length normalisation exp(Lbar) is a per-token pseudo-"
      "likelihood, a cluster's members can sum past 1, and the surprisal of a quantity "
      "above 1 is negative. Eq. (4) is not an entropy and has no non-negativity "
      "guarantee once the length normalisation is applied. (b) `farquhar_eq5` on RAW "
      "sequence likelihoods is expected to sit far below `farquhar_eq5_lennorm`: raw "
      "log-likelihoods over ~27 tokens spread over tens of nats, which makes the "
      "cluster softmax nearly one-hot and drives the entropy toward zero. That is "
      "precisely the large-spread regime in which `scripts/duplication_level_sim.py` "
      "predicted the pile-up disappears, and it is why both variants are reported: "
      "length normalisation is the modelling choice that decides the answer.")
    A("")
    A("## What each outcome would mean (fixed before the numbers existed)")
    A("")
    A("| observation | consequence for the paper |")
    A("| --- | --- |")
    A("| `farquhar_eq5_lennorm` at-cap and top-decile rates comparable to `discrete` | "
      "The pile-up is a property of the SAMPLES, not of the estimator. The ceiling "
      "finding generalises and can be stated without an estimator caveat. |")
    A("| `farquhar_eq5_lennorm` rates near zero while `discrete` piles up | The pile-up "
      "is an artefact of sample-proportion weighting. The ceiling finding must be scoped "
      "to the discrete estimator explicitly, and the cluster-count bound of "
      "`results/cluster_count_bound.md` becomes the load-bearing variant-proof claim. |")
    A("| high Spearman rho but different at-cap rates | The estimators disagree on the "
      "SCALE but not the ORDER: every AUROC in the paper stands, only the "
      "saturation/headroom arithmetic is estimator-specific. |")
    A("| low Spearman rho | The reweighting reorders targets, so the attack-success and "
      "AUROC results would themselves need re-deriving under Eq. (5), not just the "
      "ceiling statistics. |")
    A("| `kuhn_eq4` strictly above log N on a substantial share | Confirms the scope "
      "limit that already has to be stated: no ceiling-derived claim, including the "
      "cluster-count bound, says anything about Kuhn Eq. (4). |")
    A("")
    A("## Rank agreement with the discrete estimator")
    A("")
    A("The detector is used as a RANKER, so a reweighting that changes every value but "
      "no ordering would leave every AUROC in the paper untouched. Spearman rho against "
      "`discrete`:")
    A("")
    A("| estimator | Spearman rho vs discrete |")
    A("| --- | --- |")
    for nm in names:
        if nm == "discrete":
            continue
        A(f"| `{nm}` | {spearman(series['discrete'], series[nm]):.4f} |")
    A("")
    A("## Provenance and its gaps")
    A("")
    try:
        manifest = json.loads((Path(samples_dir) / "manifest.json").read_text())
        n_records = sum(1 for _ in (Path(samples_dir) / "samples.jsonl")
                        .open("r", encoding="utf-8"))
        audit = audit_generation_settings(manifest, n_records=n_records)
        A("Pinned by the sample cache's manifest:")
        A("")
        for k, v in audit.present.items():
            A(f"- `{k}` = `{v!r}`")
        A("")
        A("**NOT pinned** -- assumed from `se.config.ModelConfig()` defaults, which is "
          "what `scripts/wk4_sample.py` called with no overrides, so the assumption is "
          "recovered from source rather than from the artefact:")
        A("")
        for k, why in audit.missing_desirable:
            A(f"- `{k}` -- {why}")
        A("")
        for w in audit.warnings:
            A(f"- NOTE: {w}")
        A("")
    except OSError as exc:
        A(f"(manifest unavailable: {exc})")
        A("")
    A("- NOTE: the prompt carries a **duplicated `<|begin_of_text|>`**. "
      "`se.model._build_inputs` tokenizes the output of `apply_chat_template(tokenize="
      "False)`, which has already emitted a BOS, with `add_special_tokens` at its "
      "default, which adds another. Every sample in the cache was generated under that "
      "prompt, so this pass reproduces it exactly rather than 'fixing' it -- scoring "
      "under a cleaner prompt would score the samples under conditions the sampler "
      "never saw. It is a pipeline wart to record, not to repair mid-project.")
    A("")
    A("One further gap is structural rather than fixable: the cache stores DECODED, "
      "stripped sample strings, never the generated token ids. Teacher forcing "
      "therefore scores each string under its CANONICAL tokenization, which need not be "
      "the id sequence the sampler emitted. Two measurements bound the exposure "
      "(`--estimate-only` re-derives both): the detokenise-retokenise STRING round trip "
      "is exact for 19,996 of 20,000 samples (0.02% failures, all trailing whitespace); "
      "and 17 of 20,000 samples (0.085%) retokenize to MORE than the 48-token "
      "generation budget, which is direct proof that the canonical ids differ from the "
      "emitted ids for at least those, and a lower bound overall -- a resegmentation "
      "that preserves the token COUNT is invisible to this check. The recovered "
      "quantity is therefore 'the likelihood of the string under its canonical "
      "tokenization', which is what any re-implementation of Eq. (5) would compute "
      "anyway. Completion tokens only are scored: the prompt is conditioning, and "
      "including it would add a large constant to every Kuhn Eq. (4) score.")
    A("")
    A("## Per-question scores")
    A("")
    A("Written alongside as `rescore_likelihoods_scores.csv` for downstream use.")
    A("")

    Path(out_path).write_text("\n".join(out), encoding="utf-8")
    csv = Path(out_path).with_name("rescore_likelihoods_scores.csv")
    with csv.open("w", encoding="utf-8") as f:
        f.write("question_id," + ",".join(names) + "\n")
        for q in rows:
            f.write(q + "," + ",".join(f"{rows[q][nm]:.10f}" for nm in names) + "\n")
    print(f"wrote {out_path} and {csv}")


def run_estimate(samples_dir: Path, use_tokenizer: bool) -> None:
    """CPU-only: manifest audit, exact token census, cost. Loads NO model."""
    manifest = json.loads((Path(samples_dir) / "manifest.json").read_text())
    records = load_samples(samples_dir)
    audit = audit_generation_settings(manifest, n_records=len(records))

    print("=" * 78)
    print("MANIFEST AUDIT --", Path(samples_dir) / "manifest.json")
    print("=" * 78)
    for k, v in audit.present.items():
        print(f"  PINNED     {k} = {v!r}")
    for k, why in audit.missing_required:
        print(f"  MISSING*   {k}  ({why})")
    for k, why in audit.missing_desirable:
        print(f"  MISSING    {k}  ({why})")
    for w in audit.warnings:
        print(f"  NOTE       {w}")
    print(f"  => required pins satisfied: {audit.ok}")
    print()

    if use_tokenizer:
        tok = _tokenizer(manifest.get("model_id", "meta-llama/Llama-3.1-8B-Instruct"))
        census = token_census(records, tok)
    else:
        # crude fallback: ~4 characters per token
        n_seq = sum(len(r["samples"]) for r in records)
        tot = sum(len(r["question"]) // 4 + 30 for r in records) * N_SAMPLES
        tot += sum(len(s) // 4 for r in records for s in r["samples"])
        census = {"n_questions": len(records), "n_sequences": n_seq,
                  "total_tokens": tot, "note": "chars/4 heuristic, no tokenizer"}

    print("=" * 78)
    print("TOKEN CENSUS")
    print("=" * 78)
    for k, v in census.items():
        print(f"  {k:28s} {v}")
    print()
    print("=" * 78)
    print("COST")
    print("=" * 78)
    print(f"  {census['n_sequences']} sequences, {census['total_tokens']:,} "
          "token-positions to teacher-force")
    print(f"  {'tok/s':>10}  {'wall seconds':>14}  {'GPU-hours':>10}  {'s/question':>11}")
    for row in cost_estimate(census["n_sequences"], census["total_tokens"]):
        tag = "  <- measured floor" if row["tokens_per_second"] == MEASURED_GEN_TOKENS_PER_S else ""
        print(f"  {row['tokens_per_second']:>10.0f}  {row['seconds']:>14.0f}  "
              f"{row['gpu_hours']:>10.2f}  {row['seconds_per_question']:>11.2f}{tag}")
    print()
    print("  The floor anchor treats a parallel prefill pass as no faster per token than")
    print("  a sequential decode step, which it is not; it is a bound, not a forecast.")
    print("  Run --benchmark 8 when the GPU frees to replace this table with a number.")


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--samples-dir", type=Path, default=SAMPLES_DIR)
    ap.add_argument("--checkpoint", type=Path, default=CHECKPOINT)
    ap.add_argument("--out", type=Path, default=REPORT)
    ap.add_argument("--limit", type=int, default=None,
                    help="score only the first N questions (smoke test)")
    ap.add_argument("--estimate-only", action="store_true",
                    help="CPU only: manifest audit + token census + cost. No model.")
    ap.add_argument("--no-tokenizer", action="store_true",
                    help="with --estimate-only, skip the tokenizer and use chars/4")
    ap.add_argument("--benchmark", type=int, metavar="N", default=None,
                    help="measure throughput on N questions (small GPU job)")
    ap.add_argument("--report-only", action="store_true",
                    help="CPU only: rebuild the comparison from an existing checkpoint")
    args = ap.parse_args(argv)

    if args.estimate_only:
        run_estimate(args.samples_dir, use_tokenizer=not args.no_tokenizer)
        return 0
    if args.benchmark:
        run_benchmark(args.samples_dir, args.benchmark)
        return 0
    if args.report_only:
        build_report(args.samples_dir, args.checkpoint, args.out)
        return 0

    run_scoring(args.samples_dir, args.checkpoint, args.limit)
    build_report(args.samples_dir, args.checkpoint, args.out)
    return 0


if __name__ == "__main__":
    sys.exit(main())
