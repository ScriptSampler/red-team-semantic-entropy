# Week 5: SECA fork operational + Hide objective

Forked github.com/Buyun-Liang/SECA into vendor/SECA. Ported the
zeroth-order beam search (src/seca.py) into se.attacks.optimizer with
the objective swapped from MC-confidence to semantic entropy.

loaded Llama 4-bit + DeBERTa NLI

## Proposer + feasibility + SE on 3 questions
### tc_2: Who was the man behind The Chipmunks?
original SE: 1.228 nats, 5 clusters
  paraphrase 0: feasible
    What is the identity of the person who created The Chipmunks?
    paraphrase SE: 2.164 nats (delta +0.936)
  paraphrase 1: feasible
    Who was the person behind the creation of The Chipmunks?
    paraphrase SE: 2.164 nats (delta +0.936)
  paraphrase 2: rejected (not bidirectionally entailed with original)
    Who created the characters of The Chipmunks?

### tc_33: Which Lloyd Webber musical premiered in the US on 10th December 1993?
original SE: 1.228 nats, 5 clusters
  paraphrase 0: feasible
    What Andrew Lloyd Webber musical made its US premiere on 10th December 1993?
    paraphrase SE: 1.748 nats (delta +0.521)
  paraphrase 1: feasible
    What musical composed by Andrew Lloyd Webber made its US premiere on December 10th, 1993?
    paraphrase SE: 0.639 nats (delta -0.588)
  paraphrase 2: feasible
    What Andrew Lloyd Webber musical opened in the US on December 10, 1993?
    paraphrase SE: 2.164 nats (delta +0.936)

### tc_40: Who was the next British Prime Minister after Arthur Balfour?
original SE: 1.834 nats, 7 clusters
  paraphrase 0: rejected (not bidirectionally entailed with original)
    What was the name of the British Prime Minister who succeeded Arthur Balfour?
  paraphrase 1: rejected (not bidirectionally entailed with original)
    What was the name of the British Prime Minister who succeeded Arthur Balfour?
  paraphrase 2: feasible
    Who succeeded Arthur Balfour as the Prime Minister of the United Kingdom?
    paraphrase SE: 1.973 nats (delta +0.139)

## Hide objective, short optimise() run on one example
objective direction: minimise_entropy
original entropy: 1.228
best entropy:     0.325
improved:         True
objective calls:  13
best query:       Who was the person behind The Chipmunks?

Fork is operational. Hide objective specified and runs end to end.
