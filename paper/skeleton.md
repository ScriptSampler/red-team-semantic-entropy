# Paper skeleton (draft, Phase 3 brought forward)

Working title (avoid collision with "Adversarial Paraphrasing" 2506.07001):
**"Crying Wolf: Meaning-Preserving Paraphrases Break Sampling-Based Hallucination
Detectors in Both Directions."**

Narrative spine, per docs/positioning.md: lead with **False-alarm** (induced
false positives), establish **transferability** across SE/SRE (and SEP if the
stretch lands), close with a **defense** probe. Target venue cs.CL; arXiv 15 Sep.

## 1. Abstract (<250 words, write last)
Sampling-based hallucination detectors (Semantic Entropy and variants) are
deployed on the claim that they are invariant to surface form because they
cluster on meaning. We show that claim is false: a meaning-preserving paraphrase
of the *question*, verified equivalent by bidirectional NLI, can move a detector's
uncertainty score in either direction while the model's answer is unchanged. The
under-explored False-alarm direction makes a *correct* answer look hallucinated;
the Hide direction conceals a real hallucination. One paraphrase transfers across
SE and SRE, indicating a paradigm-level weakness, and partially reaches a
hidden-state probe (SEP). A simple input-paraphrase-averaging defense recovers
part of the lost reliability. [Fill numbers from results/.]

## 2. Introduction (~600 words)
Hook: deployed safety mechanisms are trusted but not adversarially evaluated as
*detectors*. The surprising risk is not evasion (expected) but **induced false
positives** — making a reliable detector fire on correct answers erodes trust in
the whole tool. Contribution list: (i) bidirectional attack on sampling-based
hallucination detectors under a hard NLI-equivalence constraint; (ii) the
False-alarm direction, previously unaddressed; (iii) cross-detector
transferability (SE<->SRE, SE->SEP); (iv) a first defense. Explicitly position
vs SECA/REALISTA (attack the model, not the detector) and CORVUS (model-side,
suppression-only, no NLI).

## 3. Related Work (~700 words; spine in docs/positioning.md, refs in related_work.bib)
Four buckets: detectors we attack (SE, SRE, SEPs); hallucination-elicitation
attacks on models (SECA, REALISTA — shared tooling, different target);
paraphrase-evasion of text-origin classifiers (Adversarial Paraphrasing, CoPA —
different victim, one-directional); attacks on uncertainty/probes
(Uncertainty-is-Fragile, CORVUS — differentiate threat model).

## 4. Methods (~800 words)
Recap SE (Farquhar) and SRE (Tong et al., Semantic Reformulation Entropy).
Define the two attack objectives with the sign convention (Hide maximizes
-entropy, False-alarm maximizes +entropy). The bidirectional DeBERTa-NLI
equivalence gate. The SECA-derived zeroth-order beam-search optimizer (cite,
state the objective/constraint swap). SEP probe and the defense, briefly.

## 5. Experiments (~900 words)
Setup: Llama 3.1 8B 4-bit, TriviaQA + SQuAD, N=10 SE / N=3xK=8 SRE, NLI
deberta-large-mnli. Replication: SE TriviaQA AUROC 0.787 (vs literature 0.828;
NLI-size caveat). Main matrix: clean vs attacked AUROC for SE/SRE x both
benchmarks x both attacks, False-alarm reported first. Transferability table.
SEP-transfer + defense (if done). Headline figure: AUROC by detector x attack,
False-alarm group leading.

## 6. Discussion (~400 words)
Why does it work: SE's equivalence clustering is itself NLI-bounded, so a
paraphrase that shifts the *model's sampling distribution* without crossing the
NLI boundary moves entropy without changing meaning. False-alarm exploits SE's
own over-fragmentation (a correct answer phrased many ways). Implications for
deploying uncertainty detectors as trust signals.

## 7. Limitations (~250 words)
Single model family; English only; deberta-large NLI weaker than the
v2-xlarge used by the SE/SEP papers (replication 0.787 vs 0.828); reduced attack
budget on one 16GB GPU (state the exact iterations/pool sizes); SRE reproduced
with NLI-union-find clustering rather than the full energy-based HSC.

## 8. Conclusion (~200 words)
Sampling-based hallucination detection is not surface-form invariant; the
invariance claim is breakable in both directions and across the detector family;
a cheap reformulation defense helps but does not close the gap. Future work: SEP
hardening, multilingual, larger models.
