"""Select attackable questions from a Week 4 entropy.jsonl run.

Hide attacks target questions the model gets WRONG (we then try to make
the detector miss them). False-alarm attacks target questions the model
gets RIGHT. We read the cached greedy-correctness labels so we do not
re-run the model just to pick targets.

If no entropy.jsonl exists yet (Week 4 not finished), the caller can fall
back to labelling fresh with se.se_pipeline.
"""
from __future__ import annotations

import json
from pathlib import Path

from ..data import TriviaQAExample, load_triviaqa
from ..sampling import DEFAULT_SAMPLES_DIR


WK4_DIR = DEFAULT_SAMPLES_DIR / "wk4_full_2000q"


def _labels_from_entropy(entropy_path: Path) -> dict[str, dict]:
    out: dict[str, dict] = {}
    if not entropy_path.exists():
        return out
    for line in entropy_path.read_text().splitlines():
        if line.strip():
            obj = json.loads(line)
            out[obj["question_id"]] = obj
    return out


def select_examples(
    want: str,                       # "wrong" (Hide) or "right" (False-alarm)
    n: int,
    *,
    split: str = "validation",
    entropy_dir: Path = WK4_DIR,
    prefer_extreme_entropy: bool = True,
) -> list[TriviaQAExample]:
    """Return n examples matching the desired greedy correctness.

    prefer_extreme_entropy orders Hide targets by HIGHEST entropy (most to
    gain by hiding) and False-alarm targets by LOWEST entropy (most to gain
    by raising), which is where each attack has the most headroom.
    """
    labels = _labels_from_entropy(entropy_dir / "entropy.jsonl")
    if not labels:
        raise FileNotFoundError(
            f"No entropy.jsonl in {entropy_dir}. Run Week 4 first, or label fresh."
        )

    by_id = {ex.question_id: ex for ex in load_triviaqa(split=split)}
    want_correct = (want == "right")

    rows = []
    for qid, lab in labels.items():
        if qid not in by_id:
            continue
        if bool(lab["greedy_correct"]) == want_correct:
            rows.append((qid, lab["entropy_nats"]))

    if prefer_extreme_entropy:
        # Hide wants high-entropy wrong cases; False-alarm wants low-entropy right cases.
        reverse = (want == "wrong")
        rows.sort(key=lambda r: r[1], reverse=reverse)

    return [by_id[qid] for qid, _ in rows[:n]]
