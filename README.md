# Red-Teaming Semantic Entropy

Adversarial paraphrasing attacks against Semantic Entropy (SE) and Self-Reflective Entropy (SRE) hallucination detection in LLMs.

**Target output:** arXiv preprint, 2026-09-15.
**Plan of record:** [`SE_Project_Execution_Plan.md`](SE_Project_Execution_Plan.md) — week-by-week deliverables, stop-conditions, mitigations.

## What this project does

We attack hallucination detectors, not models. Given a question Q and an LLM that may hallucinate, SE/SRE estimate the model's uncertainty over its own answer. We construct semantically-equivalent paraphrases Q' that:

- **Hide attack:** drive SE/SRE *low* on questions the model gets *wrong* (detector misses the hallucination).
- **False-alarm attack:** drive SE/SRE *high* on questions the model gets *right* (detector cries wolf).

Equivalence is verified by bidirectional NLI (DeBERTa-large-MNLI). Optimisation is forked from [Buyun-Liang/SECA](https://github.com/Buyun-Liang/SECA).

## Stack

- **LLM:** Llama 3.1 8B Instruct, 4-bit (bitsandbytes-rocm or AWQ/GPTQ).
- **NLI verifier:** DeBERTa-large-MNLI.
- **Benchmarks:** TriviaQA (`rc.nocontext`) + SQuAD.
- **GPU:** AMD Radeon RX 9070 XT, 16GB VRAM, RDNA 4 (gfx1201).
- **Runtime:** WSL2 + Ubuntu-24.04 + ROCm 6.4 + PyTorch 2.9.1+rocm6.4. See [docs/setup_wsl_rocm.md](docs/setup_wsl_rocm.md) for the full bootstrap. Native-Windows ROCm for RDNA 4 isn't viable yet.

## Setup

Full bootstrap (one-time) — run these from elevated Windows PowerShell:

```powershell
wsl --install                       # WSL2 if not already
wsl --install -d Ubuntu-24.04       # the research runtime distro
wsl -d Ubuntu-24.04 -u root bash "/mnt/i/GITHUBPROJECTS/SE Research/scripts/bootstrap_ubuntu_2404.sh"
wsl --shutdown
wsl -d Ubuntu-24.04 -u root bash "/mnt/i/GITHUBPROJECTS/SE Research/scripts/install_rocm_64_wsl.sh"
wsl -d Ubuntu-24.04 bash "/mnt/i/GITHUBPROJECTS/SE Research/scripts/setup_venv_wsl.sh"
```

Daily workflow:

```powershell
wsl -d Ubuntu-24.04 --cd "/mnt/i/GITHUBPROJECTS/SE Research"
# now inside Ubuntu-24.04:
source .venv-wsl/bin/activate
python -c "import torch; print(torch.cuda.is_available(), torch.cuda.get_device_name(0))"
# Expected: True AMD Radeon RX 9070 XT (or similar)
```

> The Windows-side `.venv` (Python 3.11 + CPU torch) exists for editor/IDE support; nothing computational runs there.

## Repo layout

```
.
├── README.md
├── SE_Project_Execution_Plan.md   # source of truth, week-by-week
├── requirements.txt                # Windows venv (editor only)
├── requirements-wsl.txt            # WSL Ubuntu-24.04 venv (research runtime)
├── .gitignore
├── docs/                           # setup notes, methodology
├── scripts/                        # bootstrap + install scripts
├── src/                            # SE, SRE, attacks, eval
├── data/                           # raw + processed datasets (gitignored)
├── results/                        # AUROC numbers, figures, sample sets (gitignored except .md)
├── configs/                        # YAML experiment configs
└── notebooks/                      # exploration
```

## Status

- **Week 1 (15-21 May):** env bootstrap — in progress (this commit).
- Sessions: Mon/Wed/Fri 8-10am + Sun 10-11am review.
- Phase 1 stop-condition: replicate Farquhar SE AUROC ±3pp by 15 Jun.

## License

MIT (to be added before public release in Week 17).
