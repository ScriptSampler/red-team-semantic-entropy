"""Fail the build when a population-sensitive number appears without its population named.

WHY THIS EXISTS. Binding a statistic to the wrong population is this project's most-repeated
error: it has now been found and fixed at FIVE separate sites (critique_log 28, 31), each
time by a manual sweep, and each sweep found a site the previous one missed. The critic gate
predicts a sixth at Table 1 fill-in, when the definitive numbers land. A manual process that
has failed five times should not be the guard on the sixth.

TWO POPULATIONS, and they are not interchangeable:

  fair pool      200 correct + 200 hallucinating, drawn score-independently.
                 AUROC 0.704 [0.653, 0.753]; separation 0.463 nats, d ~ 0.76.
                 The ONLY population on which claims about "the detector" may be made.

  attacked pool  97 targets = 80 correct + 17 wrong, the attack campaign's own targets,
                 with the hide arm truncated mid-campaign.
                 AUROC 0.579; separation 0.184 nats, d = 0.28. QUARANTINED for any
                 class-separation claim. The ceiling and granularity statistics (a tenth at
                 the cap, a quarter in the top tenth, 22 distinct values) live HERE.

THE MARKUP LESSON. The critic's own grep for "fair pool" missed conclusion.tex because the
source reads `\\emph{fair} pool`. Phrase matching does not survive LaTeX. So we strip markup
before matching, and we anchor on NUMBERS, which markup cannot split.

Run: python scripts/check_population_labels.py    (exit 1 on any unlabelled site)
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
PAPER = REPO / "paper"

# Numbers that are meaningless without a population, and the labels that satisfy them.
# `window` is how many characters either side count as "nearby" (roughly a sentence or two).
RULES = [
    {
        "name": "fair-pool AUROC",
        "numbers": [r"0\.704", r"0\.653", r"0\.753", r"0\.463"],
        "requires": [r"fair pool", r"score-independent pool", r"200 correct"],
        "window": 420,
    },
    {
        "name": "quarantined attacked-subset separation",
        "numbers": [r"0\.579", r"0\.184"],
        "requires": [r"attacked", r"attack campaign", r"quarantin", r"partial hide"],
        "window": 420,
    },
    {
        "name": "ceiling / granularity counts (attacked pool)",
        "numbers": [r"22 distinct", r"22 attainable"],
        "requires": [r"97", r"attack campaign", r"attacked"],
        "window": 420,
    },
    {
        "name": "97-target pool identity",
        "numbers": [r"97 targets", r"across 97"],
        "requires": [r"attack campaign", r"attacked", r"80 correct"],
        "window": 300,
    },
]


def strip_latex(text: str) -> str:
    """Flatten markup so phrase matching works. `\\emph{fair} pool` -> `fair pool`.

    This is the whole point: the manual sweeps failed because \\emph{} split the phrases
    they were grepping for.
    """
    text = re.sub(r"%.*?$", "", text, flags=re.MULTILINE)          # comments
    text = re.sub(r"\\(?:emph|textbf|textit|mathrm|text)\{([^{}]*)\}", r"\1", text)
    text = re.sub(r"\\citep?\{[^{}]*\}", " ", text)                # citations
    text = re.sub(r"\\ref\{[^{}]*\}", " ", text)
    text = re.sub(r"\\[a-zA-Z]+", " ", text)                       # remaining commands
    text = text.replace("{", " ").replace("}", " ").replace("~", " ")
    text = text.replace("$", "")            # math delimiters: $97$ and 97 must match alike
    return re.sub(r"\s+", " ", text)


def check_file(path: Path) -> list[str]:
    raw = path.read_text(encoding="utf-8", errors="replace")
    flat = strip_latex(raw)
    problems: list[str] = []
    for rule in RULES:
        for num in rule["numbers"]:
            for hit in re.finditer(num, flat):
                lo = max(0, hit.start() - rule["window"])
                hi = min(len(flat), hit.end() + rule["window"])
                ctx = flat[lo:hi]
                if not any(re.search(req, ctx, re.IGNORECASE) for req in rule["requires"]):
                    # Report an approximate source line by counting matches so far.
                    snippet = flat[max(0, hit.start() - 60):hit.end() + 60].strip()
                    try:
                        shown = path.relative_to(REPO)
                    except ValueError:
                        shown = path.name
                    problems.append(
                        f"{shown}: [{rule['name']}] "
                        f"'{hit.group(0)}' has no population label within "
                        f"{rule['window']} chars.\n"
                        f"      needs one of: {rule['requires']}\n"
                        f"      context: ...{snippet}...")
    return problems


def main() -> int:
    targets = sorted(PAPER.glob("*.tex")) + sorted((PAPER / "sections").glob("*.tex"))
    if not targets:
        print("no .tex files found under paper/", file=sys.stderr)
        return 1
    problems: list[str] = []
    for t in targets:
        problems.extend(check_file(t))
    if problems:
        print(f"POPULATION-LABEL CHECK FAILED — {len(problems)} unlabelled site(s):\n")
        for p in problems:
            print("  " + p)
        print("\nEvery population-sensitive number must name its pool nearby. The two are "
              "NOT interchangeable: 0.704 is the fair pool (200+200); the ceiling and "
              "granularity counts are the 97-target attacked pool.")
        return 1
    print(f"population-label check: OK ({len(targets)} files, "
          f"{sum(len(r['numbers']) for r in RULES)} number patterns)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
