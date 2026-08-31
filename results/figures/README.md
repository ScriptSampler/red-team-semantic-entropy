> **SUPERSEDED (2026-07-02): pre-B1 extreme-entropy selection.** Both files in this directory
> use the discredited selection rule where clean AUROC = 1.000 by construction (external review
> B1). Do NOT cite. B1-corrected fair-pool results: scripts/recompute_fair.py ->
> results/fair_recompute_report.md.

# results/figures/ - retired, and kept only as a record

| file | what it is | status |
| --- | --- | --- |
| `headline_auroc.json` | machine-readable AUROC table from the pre-B1 wk9 campaigns | **retired** |
| `headline_auroc.png` | the bar chart drawn from that same table | **retired** |
| `headline_auroc.json.SUPERSEDED.json` | the machine-readable retirement notice for both | current |

Neither file is included by the paper, and nothing in the repository reads either one:
`scripts/make_figures.py` only writes them. The paper's figures live in the top-level
`figures/`, and `figures/README.md` maps each of those to the population it is measured on.

**What is wrong with them.** Their targets were selected on the detector's own entropy score.
Selecting that way inflates the clean AUROC to 1.000 by construction, on the 30-question
per-cell wk9 pools. That inflation is the artifact the paper's protocol contribution exists to
refute, so a reader who lifts the 1.000 out of this directory reaches the opposite of the
paper's conclusion. On the score-independent fair pool the clean AUROC is
0.704 [0.653, 0.753] (`results/fair_pool_report.md`), which also reports the extreme-entropy
ablation as 1.000 [1.000, 1.000] and labels it as selection, not detection.

The prose form of this banner is on `results/attack_matrix.md` and the four
`results/wk9_*.md` reports, all of which come from the same campaigns.
