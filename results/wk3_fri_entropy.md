# Week 3 Fri: semantic clustering + entropy on the 50 Monday samples
GPU: AMD Radeon RX 9070 XT

## Load NLI
NLI loaded in 28.4s

## Cluster and score each question
records: 50
clustered 50 questions in 92.2s (1.84s/Q)

per-question entropy written to /home/abhi/.cache/se-research/samples/wk3_mon_50q/entropy.jsonl

## Distribution stats
entropy (nats): mean=1.631, median=1.748, min=0.000, max=2.303
cluster count:  mean=6.60, median=7, max=10

## Greedy-correct vs greedy-wrong, entropy
greedy correct (35): mean entropy 1.505 nats
greedy wrong   (15): mean entropy 1.926 nats
gap:            0.422 nats

## AUROC, entropy ranking vs greedy correctness
Positive class is greedy wrong (the hallucination we want to flag).
AUROC on 50 questions: 0.705

Caveat: 50 questions is small and the label is greedy correctness,
which Farquhar et al. handle differently. The Phase 1 stop-condition
number comes from the 2000 question Week 4 run with their convention.

## Top 10 highest entropy
Expectation: mostly greedy-wrong.

| entropy | clusters | greedy ok | samples ok | question_id | question |
| ------- | -------- | --------- | ---------- | ----------- | -------- |
| 2.303 | 10 | yes | 10/10 | tc_56 | What claimed the life of singer Kathleen Ferrier? |
| 2.303 | 10 |  no | 4/10 | tc_79 | What was the last US state to reintroduce alcohol after proh... |
| 2.303 | 10 | yes | 0/10 | tc_564 | What was Walter Matthau's first movie? |
| 2.164 | 9 |  no | 8/10 | tc_69 | Rita Coolidge sang the title song for which Bond film? |
| 2.164 | 9 |  no | 1/10 | tc_276 | Who had an 80s No 1 hit with Hold On To The Nights? |
| 2.164 | 9 | yes | 10/10 | tc_453 | In the Bible, who did the sun and moon stand still before? |
| 2.164 | 9 | yes | 5/10 | tc_517 | Who was the last inmate of Spandau jail in Berlin? |
| 2.164 | 9 | yes | 10/10 | tc_538 | In the 80s who wrote the novel Empire of The Sun? |
| 2.164 | 9 |  no | 0/10 | tc_559 | Kim Carnes' nine weeks at No 1 with Bette Davis Eyes was int... |
| 2.164 | 9 |  no | 3/10 | tc_585 | Otis Barton was a pioneer in exploring where? |

## Bottom 10 lowest entropy
Expectation: mostly greedy-correct.

| entropy | clusters | greedy ok | samples ok | question_id | question |
| ------- | -------- | --------- | ---------- | ----------- | -------- |
| 0.000 | 1 | yes | 10/10 | tc_280 | Who directed the classic 30s western Stagecoach? |
| 0.325 | 2 | yes | 10/10 | tc_219 | The flag of Libya is a plain rectangle of which color? |
| 0.325 | 2 | yes | 10/10 | tc_653 | How old was Jimi Hendrix when he died? |
| 0.611 | 2 | yes | 10/10 | tc_241 | Of which African country is Niamey the capital? |
| 0.639 | 3 | yes | 8/10 | tc_316 | If I Were A Rich Man Was a big hit from which stage show? |
| 0.802 | 3 |  no | 0/10 | tc_106 | Which actress was voted Miss Greenwich Village in 1942? |
| 0.940 | 4 | yes | 9/10 | tc_137 | What was the name of Michael Jackson's autobiography written... |
| 0.940 | 4 | yes | 10/10 | tc_543 | In which sport could the Pacers take on the Pistons? |
| 0.940 | 4 | yes | 10/10 | tc_665 | How was the European Recovery Program in the 1940s more comm... |
| 0.943 | 3 | yes | 9/10 | tc_49 | Who had a 70s No 1 hit with Kiss You All Over? |

