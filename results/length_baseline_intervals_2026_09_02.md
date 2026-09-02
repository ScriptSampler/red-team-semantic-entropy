# The five length-baseline confidence intervals in `experiments.tex`, and the convention that produces them

Written 2026-09-02. **Provenance artifact only.** It re-derives numbers already printed in
`paper/sections/experiments.tex` (the "What the clean detector beats" paragraph); it does not
change any claim and it introduces no new measurement.

## 0. Why this file exists

The length-baseline paragraph prints five confidence intervals that appeared in **no file under**
`results/`. Three endpoints differed from
`results/length_confound_verification_2026_08_31.md` by more than any rounding rule explains.

That was not a measurement error. The verification report computed the *fair-pool* column under
the **probe's** convention (`entropy.jsonl` scores, `n_boot=2000`) and the *full-pool* column
under its own; the paragraph's author re-derived every cell under **the paper's own** convention,
the one `scripts/fair_pool_check.py` already uses for the published `0.704 [0.653, 0.753]`, so
that one convention holds across the whole section. That was the right call. What was missing is
this file: the numbers have to be reproducible from the repository, and until now they were not.

## 1. The convention, stated exactly

Everything below is `scripts/fair_pool_check.py`'s `_clean_auroc` convention, extended to the
length score and to the paired differences.

| knob | value | where it comes from |
|---|---|---|
| labels and entropies | `relabeled.jsonl` (span-oracle B3 relabel), never `entropy.jsonl` | `se.attacks.select.RELABELED` |
| pool construction | `_stratum_ids(want, seed=0, labels)` then `[:200]` per stratum | `src/se/attacks/select.py` |
| **array order** | **wrong stratum first, then right** | `_clean_auroc(wrong_ids, right_ids, emap)` |
| positive class | label 1 = hallucination (`greedy_correct` is False) | `_clean_auroc` |
| **`n_boot`** | **3000** | `auroc_ci(..., n_boot=3000, seed=0)` |
| **seed** | **0**, one `np.random.default_rng(0)` stream per interval | `se.stats.auroc_ci` |
| resampling | i.i.d. over questions, `rng.integers(0, n, size=n)`; single-class replicates dropped | `se.stats.auroc_ci` |
| interval | percentile, `np.quantile` at 0.025 and 0.975 | `se.stats.auroc_ci` |
| AUROC implementation | `sklearn.metrics.roc_auc_score` | `se.stats` |
| paired differences | **one** index stream per replicate, both scores recomputed on it, then subtracted | `se.stats.auroc_diff_ci`'s rule |
| length score | mean words per sample, `mean(len(s.split()) for s in samples)`, over all 10 samples | `scripts/length_confound_probe.py` |
| rank-sum score | average ranks of SE plus average ranks of length, ties averaged | `scripts/length_confound_probe.py` |

`_stratum_ids` was **re-implemented from source rather than imported**, because `se.scoring` pulls
`se.data -> datasets -> pandas`, which does not import in this venv. The re-implementation is
verbatim: filter `relabeled.jsonl` on `bool(greedy_correct) == (want == "right")`, `sorted()` the
surviving ids, then `random.Random(f"{seed}:{want}").shuffle(ids)`. It reads no entropy and no
score, which is the property that makes the pool score-independent.

Sanity, established first: 2000 questions with both samples and labels, perfect id
intersection, exactly 10 samples each, 1424 correct / 576 hallucinating
under the span oracle. The fair pool is 200 + 200 of those.

## 2. The five intervals

Under the convention of section 1. The `paper` column is what `experiments.tex` prints.

| # | quantity | re-derived (4 dp) | rounded to 3 dp | paper | agrees? |
|---|---|---|---|---|---|
| A | Mean generation length alone, AUROC, fair pool (n=400) | 0.6344 [0.5795, 0.6868] | 0.634 [0.579, 0.687] | 0.634 [0.580, 0.687] | NO |
| B | Mean generation length alone, AUROC, full labelled pass (n=2000) | 0.6311 [0.6050, 0.6564] | 0.631 [0.605, 0.656] | 0.631 [0.605, 0.656] | **yes** |
| C | SE minus length, paired, fair pool (n=400) | +0.0699 [+0.0233, +0.1163] | +0.070 [+0.023, +0.116] | +0.070 [+0.023, +0.116] | **yes** |
| D | SE minus length, paired, full labelled pass (n=2000) | +0.0626 [+0.0397, +0.0843] | +0.063 [+0.040, +0.084] | +0.063 [+0.040, +0.084] | **yes** |
| E | rank-sum(SE, length) minus SE, paired, full pass (n=2000) | -0.0164 [-0.0276, -0.0047] | -0.016 [-0.028, -0.005] | -0.016 [-0.028, -0.005] | **yes** |

How this was checked: all nine (array order x `n_boot`) cells of section 3 were computed and the
printed values matched against every one of them. Exactly one cell reproduces four of the five to
three decimals, and it is the `_clean_auroc` cell above. **B** and **D**, the two full-pass cells,
were the two required to reproduce before the convention would be accepted, and both did; **C**
and **E** then fell out of the same cell. **A** did not, and that is the next paragraph.

**One endpoint of the five does not come from this cell, and it was deliberately left as it
stands.** Interval A's lower
endpoint is 0.57949 under this convention, which is 0.579 at three decimals.
`experiments.tex` prints **0.580**.
Five of the nine cells round that endpoint to 0.580 (`right_first/2000`, `right_first/3000`, `right_first/20000`, `sorted/20000`, `wrong_first/20000`), and **none of them reproduces the other**
**four intervals**. So A's printed lower endpoint came from a different realisation than B
through E, most plausibly `wrong_first`/`n_boot=20000`, the only one of the five that shares
A's array order (0.58036).

**Why it was left alone.** The disagreement is 0.0010, and it is inside the Monte-Carlo
error of the endpoint itself: across the nine cells this endpoint spans 0.0026
(section 3.2), about 3 times the disagreement. Neither digit is the
more correct estimate; what is true is only that the paragraph is not quite one convention at
its third decimal. Set against that, printing 0.579 turns a guard red and the guard is not
editable from here: `scripts/check_population_labels.py` quarantines the literal `0.579` as a
dead attacked-pool separation statistic (rule "QUARANTINED attacked-pool separation", a
`_def`-era value of a 97-target pool that no longer exists), so the string beside a fair-pool
label fails the population check. The rule is not wrong about what it protects; it cannot tell a
bootstrap endpoint from that corpse.

**This is the one open decision in this file, and it belongs to whoever owns `paper/`.** Either
print 0.579 and give the quarantine rule an exemption for this site, or keep 0.580 and treat
this file as the record of which cell it came from. Both are defensible. What is not defensible
is leaving the provenance unwritten, which was the state until today.

The published fair-pool SE figure reproduces in the same cell and is the anchor that identifies
the convention: 0.704 [0.653, 0.753] against the paper's 0.704 [0.653, 0.753].
Full-pass SE is 0.694 [0.669, 0.718], whose point estimate is the paper's operative 0.694.

## 3. The nine-cell sweep: point estimates are invariant, endpoints are not

Array order enters only through the bootstrap index stream, and `n_boot` only through Monte-Carlo
error. Neither touches the statistic. The sweep below is 3 array orders x 3 bootstrap counts, seed
0 throughout.

### 3.1 Point estimates, all nine cells

| quantity | distinct point estimates over 9 cells | value |
|---|---|---|
| A. Mean generation length alone | **1** | `0.634387500000` |
| B. Mean generation length alone | **1** | `0.631075169710` |
| C. SE minus length | **1** | `0.069875000000` |
| D. SE minus length | **1** | `0.062595705563` |
| E. rank-sum(SE | **1** | `-0.016426000702` |

**Byte-identical in every cell.** Nothing about the reported effect depends on the convention.

### 3.2 Interval endpoints, all nine cells

The paper's cell is marked `<--`.

**A. Mean generation length alone, AUROC, fair pool (n=400)** (paper prints `0.634 [0.580, 0.687]`)

| array order | n_boot=2000 | n_boot=3000 | n_boot=20000 |
|---|---|---|---|
| wrong_first | [0.5778, 0.6863] | [0.5795, 0.6868] `<--` | [0.5804, 0.6878] |
| right_first | [0.5795, 0.6879] | [0.5799, 0.6879] | [0.5798, 0.6886] |
| sorted | [0.5793, 0.6892] | [0.5793, 0.6888] | [0.5799, 0.6886] |

Spread across the nine cells: **0.0026** on the lower endpoint, **0.0029** on the upper.

**B. Mean generation length alone, AUROC, full labelled pass (n=2000)** (paper prints `0.631 [0.605, 0.656]`)

| array order | n_boot=2000 | n_boot=3000 | n_boot=20000 |
|---|---|---|---|
| wrong_first | [0.6056, 0.6565] | [0.6050, 0.6564] `<--` | [0.6060, 0.6562] |
| right_first | [0.6060, 0.6564] | [0.6063, 0.6562] | [0.6056, 0.6559] |
| sorted | [0.6050, 0.6563] | [0.6054, 0.6566] | [0.6056, 0.6563] |

Spread across the nine cells: **0.0012** on the lower endpoint, **0.0007** on the upper.

**C. SE minus length, paired, fair pool (n=400)** (paper prints `+0.070 [+0.023, +0.116]`)

| array order | n_boot=2000 | n_boot=3000 | n_boot=20000 |
|---|---|---|---|
| wrong_first | [+0.0233, +0.1176] | [+0.0233, +0.1163] `<--` | [+0.0231, +0.1168] |
| right_first | [+0.0249, +0.1172] | [+0.0241, +0.1176] | [+0.0237, +0.1172] |
| sorted | [+0.0238, +0.1159] | [+0.0239, +0.1160] | [+0.0234, +0.1170] |

Spread across the nine cells: **0.0018** on the lower endpoint, **0.0017** on the upper.

**D. SE minus length, paired, full labelled pass (n=2000)** (paper prints `+0.063 [+0.040, +0.084]`)

| array order | n_boot=2000 | n_boot=3000 | n_boot=20000 |
|---|---|---|---|
| wrong_first | [+0.0400, +0.0842] | [+0.0397, +0.0843] `<--` | [+0.0399, +0.0850] |
| right_first | [+0.0393, +0.0843] | [+0.0398, +0.0845] | [+0.0399, +0.0849] |
| sorted | [+0.0397, +0.0852] | [+0.0390, +0.0851] | [+0.0398, +0.0852] |

Spread across the nine cells: **0.0011** on the lower endpoint, **0.0010** on the upper.

**E. rank-sum(SE, length) minus SE, paired, full pass (n=2000)** (paper prints `-0.016 [-0.028, -0.005]`)

| array order | n_boot=2000 | n_boot=3000 | n_boot=20000 |
|---|---|---|---|
| wrong_first | [-0.0272, -0.0047] | [-0.0276, -0.0047] `<--` | [-0.0278, -0.0049] |
| right_first | [-0.0275, -0.0048] | [-0.0277, -0.0052] | [-0.0278, -0.0048] |
| sorted | [-0.0280, -0.0050] | [-0.0280, -0.0048] | [-0.0278, -0.0048] |

Spread across the nine cells: **0.0008** on the lower endpoint, **0.0004** on the upper.

### 3.3 What that means

Every point estimate is invariant to 12 decimal places. No endpoint moves by more than
**0.0029** across the nine cells, and most move by well under 0.002. So the disagreement
between this paragraph and `length_confound_verification_2026_08_31.md` is pure Monte-Carlo noise
from pool ordering and bootstrap count, and it is not a disagreement about any measured quantity.
It is nonetheless real at the third decimal, which is the precision the paper prints, and that is
why the section is held to one convention rather than to whichever cell each number came from.

## 4. Cross-check against `length_confound_verification_2026_08_31.md`

That report's section 2.1 table is reproduced here as the `right_first, n_boot=2000` cell for the
fair pool (the probe's convention) and is close to `wrong_first, n_boot=3000` for the full pool.
Its verdict, "CONFIRMED, every figure to 4 dp", stands: the point estimates it confirms are the
ones this file shows to be convention-invariant. Only its interval endpoints belong to a different
cell, and it says so itself where it notes that "the bootstrap index stream depends on array order".

## 5. Reproduction

```
# cache (WSL-side, read-only): ~/.cache/se-research/samples/wk4_full_2000q/
#   relabeled.jsonl, samples.jsonl
# interpreter: .venv/Scripts/python.exe
# CPU only. No GPU work, no model load, nothing launched.
```

| component | version |
|---|---|
| python | 3.11.9 |
| numpy | 2.1.3 |
| scikit-learn | 1.5.2 |

Everything in section 2 and section 3 is emitted by the generator, not transcribed by hand.

The whole of the computation is below, so this file does not depend on a script that lives
outside the repository. It prints the five intervals of section 2 and nothing else. Verified to
do so on 2026-09-02 against the table above.

```python
"""Reproduce the five length-baseline intervals of experiments.tex. CPU only.

Run:  .venv/Scripts/python.exe repro_length_baseline.py <path to wk4_full_2000q>
"""
import json, random, statistics, sys
from pathlib import Path
import numpy as np
from sklearn.metrics import roc_auc_score

CACHE = Path(sys.argv[1])
N_BOOT, SEED, N_STRATUM = 3000, 0, 200

def rj(p):
    return [json.loads(l) for l in p.read_text(encoding="utf-8").splitlines() if l.strip()]

rel = {r["question_id"]: r for r in rj(CACHE / "relabeled.jsonl")}
smp = {r["question_id"]: r for r in rj(CACHE / "samples.jsonl")}
qids = sorted(set(rel) & set(smp))
meanlen = {q: statistics.mean(len(s.split()) for s in smp[q]["samples"]) for q in qids}
ent = {q: rel[q]["entropy_nats"] for q in qids}
ok = {q: bool(rel[q]["greedy_correct"]) for q in qids}

def stratum_ids(want):                      # verbatim se.attacks.select._stratum_ids
    ids = sorted(q for q, lab in rel.items()
                 if bool(lab["greedy_correct"]) == (want == "right"))
    random.Random(f"{SEED}:{want}").shuffle(ids)
    return ids

def arrays(wrong_ids, right_ids):           # WRONG STRATUM FIRST, as _clean_auroc builds it
    ids = list(wrong_ids) + list(right_ids)
    return (np.array([0 if ok[q] else 1 for q in ids]),          # 1 = hallucination
            np.array([ent[q] for q in ids], float),
            np.array([meanlen[q] for q in ids], float))

def boot(y, fn):                            # se.stats.auroc_ci's index stream, seed 0
    rng = np.random.default_rng(SEED)
    v = []
    for _ in range(N_BOOT):
        i = rng.integers(0, len(y), size=len(y))
        if 0 < y[i].sum() < len(i):
            v.append(fn(i))
    return float(np.quantile(v, 0.025)), float(np.quantile(v, 0.975))

def ci(y, s):
    return (float(roc_auc_score(y, s)),
            *boot(y, lambda i: roc_auc_score(y[i], s[i])))

def diff(y, a, b):                          # ONE index stream, both scores, then subtract
    return (float(roc_auc_score(y, a)) - float(roc_auc_score(y, b)),
            *boot(y, lambda i: roc_auc_score(y[i], a[i]) - roc_auc_score(y[i], b[i])))

def ranks(a):
    o = np.argsort(a, kind="mergesort"); r = np.empty(len(a)); s = a[o]; i = 0
    while i < len(a):
        j = i
        while j + 1 < len(a) and s[j + 1] == s[i]:
            j += 1
        r[o[i:j + 1]] = (i + j) / 2.0 + 1.0
        i = j + 1
    return r

yF, seF, lnF = arrays(stratum_ids("wrong")[:N_STRATUM], stratum_ids("right")[:N_STRATUM])
yA, seA, lnA = arrays(sorted(q for q in qids if not ok[q]), sorted(q for q in qids if ok[q]))

for tag, t in (("A len fair ", ci(yF, lnF)),
               ("B len full ", ci(yA, lnA)),
               ("C SE-len fair", diff(yF, seF, lnF)),
               ("D SE-len full", diff(yA, seA, lnA)),
               ("E ranksum-SE full", diff(yA, ranks(seA) + ranks(lnA), seA))):
    print(f"{tag:20s} {t[0]:+.3f} [{t[1]:+.3f}, {t[2]:+.3f}]")
```

