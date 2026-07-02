# Null / noise-floor control (attack move vs benign floor)

K=8 benign feasible paraphrases per target; original noise band over 3 seeds. Success net of floor = attack move exceeds the best benign move. All on the fair pool (wk9_fair).

## SE / false_alarm  (n=6)

- mean attack move:      +0.534 nats
- mean null-best move:   +0.339 nats  (benign paraphrase floor)
- mean net (attack-floor): +0.195 [+0.000, +0.399] nats
- success NET of floor:  33% [0%, 67%] (attack beats the best of 8 benign paraphrases)
- original entropy noise (std over 3 seeds): mean 0.191 nats

Interpretation: if 'success NET of floor' and the net-move CI stay well above 0, the attack is real signal, not selection-on-noise. If they collapse toward 0, the apparent effect is largely the N=10 floor.

> CAVEAT (critic, critique_log entry 13): this compares max-over-~180 attack candidates
> vs max-over-8 benign — max grows with sample count, so the net is biased TOWARD the
> attack, and it STILL cleared only 33%. The definitive run must report the FULL benign
> distribution with the attack as a per-target percentile (not max-vs-max), add a same-
> question seed-noise floor as a second band, and run the shared-vs-independent clusterer
> 2x2 (finding 14) at n>=80/stratum. See docs/critique_log.md entry 13.

## se_hide: no outcomes yet

