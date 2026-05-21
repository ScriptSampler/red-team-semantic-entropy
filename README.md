# Red-Teaming Semantic Entropy

Adversarial paraphrasing attacks against Semantic Entropy (SE) and Self-Reflective Entropy (SRE) hallucination detection in LLMs.

The target output is an arXiv preprint by 15 September 2026. Week-by-week deliverables, stop conditions, and mitigations live in [SE_Project_Execution_Plan.md](SE_Project_Execution_Plan.md).

## What this project does

We attack the detector, not the model. Given a question Q and an LLM that may hallucinate, SE and SRE estimate the model's uncertainty over its own answer. We construct semantically equivalent paraphrases Q' that move that uncertainty score in the wrong direction.

The Hide attack pushes SE or SRE low on questions the model answers incorrectly, so the detector misses a hallucination. The False-alarm attack pushes SE or SRE high on questions the model answers correctly, so the detector cries wolf. Semantic equivalence between Q and Q' is checked by bidirectional NLI with DeBERTa-large-MNLI. The optimisation loop is forked from [Buyun-Liang/SECA](https://github.com/Buyun-Liang/SECA).

## Stack

The target model is Llama 3.1 8B Instruct, loaded in 4-bit via bitsandbytes. The NLI verifier is DeBERTa-large-MNLI. Benchmarks are TriviaQA (rc.nocontext split) and SQuAD. The GPU is an AMD Radeon RX 9070 XT (16 GB VRAM, RDNA 4, gfx1201). Everything runs under WSL2 with Ubuntu 24.04, ROCm 6.4, and PyTorch 2.9.1+rocm6.4. Native Windows ROCm for RDNA 4 is not yet workable, so we don't try. The full bootstrap is in [docs/setup_wsl_rocm.md](docs/setup_wsl_rocm.md).

## Setup

One-time bootstrap, from elevated Windows PowerShell:

```powershell
wsl --install
wsl --install -d Ubuntu-24.04
wsl -d Ubuntu-24.04 -u root bash "/mnt/i/GITHUBPROJECTS/SE Research/scripts/bootstrap_ubuntu_2404.sh"
wsl --shutdown
wsl -d Ubuntu-24.04 -u root bash "/mnt/i/GITHUBPROJECTS/SE Research/scripts/install_rocm_64_wsl.sh"
wsl -d Ubuntu-24.04 bash "/mnt/i/GITHUBPROJECTS/SE Research/scripts/setup_venv_wsl.sh"
```

Daily workflow:

```powershell
wsl -d Ubuntu-24.04 --cd "/mnt/i/GITHUBPROJECTS/SE Research"
# inside Ubuntu 24.04:
source .venv-wsl/bin/activate
python -c "import torch; print(torch.cuda.is_available(), torch.cuda.get_device_name(0))"
# Expect: True AMD Radeon RX 9070 XT
```

The Windows-side `.venv` (Python 3.11, CPU torch) exists only for IDE and editor tooling. Nothing computational runs there.

## Repo layout

```
.
├── README.md
├── SE_Project_Execution_Plan.md   # week-by-week plan
├── requirements.txt               # Windows venv (editor only)
├── requirements-wsl.txt           # WSL Ubuntu-24.04 venv (research runtime)
├── docs/                          # setup notes, methodology
├── scripts/                       # bootstrap + install scripts
├── src/                           # SE, SRE, attacks, eval
├── data/                          # raw + processed datasets (gitignored)
├── results/                       # AUROC numbers, figures, sample sets
├── configs/                       # YAML experiment configs
└── notebooks/                     # exploration
```

## Status

Week 1 (15 to 21 May): environment bootstrap, complete. Sessions run Mon/Wed/Fri 8 to 10 am, with a Sunday review 10 to 11 am. The Phase 1 stop condition is to replicate Farquhar SE AUROC within plus or minus three percentage points by 15 June.

## License

MIT, to be added before public release in Week 17.
