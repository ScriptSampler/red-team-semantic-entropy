# N=20 ceiling pilot (critique_log 23)

Targets that saturate at N=10 (cap 2.3026), re-scored at N=20 (cap 2.9957), same seed.

- n = 15
- **still saturated at the new cap: 3/15 = 20%**
- baselines already at the new cap: 1/15
- mean attack move: 0.595 nats at N=10 -> 0.558 at N=20
- mean headroom at the new cap: 0.899 nats

READING: a LOW residual saturation rate means raising N buys back both effect-size identifiability and the exceedance test's power, and the full re-run is justified. A HIGH residual rate means the attack simply drives the model to N distinct answers at any N, the ceiling is not an artifact of the sample budget, and false-alarm effect sizes in nats are not identifiable at feasible N — in which case report censoring-robust statistics only.
