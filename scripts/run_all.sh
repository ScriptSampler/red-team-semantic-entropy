#!/bin/bash
# Autonomous overnight driver: Phase 1 replication -> Phase 2 attacks, end to end.
#
# Every stage is resumable, so this script can be killed and re-invoked and it
# continues where it left off. It writes a one-line status to
# results/run_all_status.txt after each stage and a full log to
# results/run_all.log.
#
# Phase 2 runs at a REDUCED scale (documented below), because the full plan
# scale (200 questions x 20 iterations x M=3,top_N=3) is ~50 GPU-days on one
# card. This is a logged compute-scoping decision, not a silent cap.
#
#   Phase 2 reduced config:
#     wk6/wk7 Hide/False-alarm: 10 questions, max_iter=6, M=2, top_N=2
#     wk8 SRE:                  60 questions
#     wk9 scale-up:             15 questions/campaign, max_iter=6, M=2, top_N=2,
#                               all 8 cells (triviaqa+squad x se+sre x hide+false_alarm)
#
# Run:
#   wsl -d Ubuntu-24.04 bash "/mnt/i/GITHUBPROJECTS/SE Research/scripts/run_all.sh"
set -uo pipefail

# Single-instance guard: if another run_all.sh holds the lock, exit quietly so
# a relaunch (from a watchdog) cannot start a second sampler writing the same
# file. The lock auto-releases when this process exits.
exec 9>"/tmp/se_run_all.lock"
if ! flock -n 9; then
    echo "run_all.sh already running; exiting this instance."
    exit 0
fi

cd "/mnt/i/GITHUBPROJECTS/SE Research"
source .venv-wsl/bin/activate

RESULTS="results"
STATUS="$RESULTS/run_all_status.txt"
SAMPLES="$HOME/.cache/se-research/samples/wk4_full_2000q/samples.jsonl"
ENTROPY="$HOME/.cache/se-research/samples/wk4_full_2000q/entropy.jsonl"
N_TARGET=2000
SANITY_FLOOR=0.65

mkdir -p "$RESULTS"

stamp() { date '+%Y-%m-%d %H:%M:%S'; }
status() { echo "[$(stamp)] $1" | tee -a "$STATUS"; echo "[$(stamp)] $1"; }

count() { [ -f "$1" ] && wc -l < "$1" | tr -d ' ' || echo 0; }

status "DRIVER START"

# ---- Stage 1: sampling (resumable, retry until 2000 records) ---------------
status "STAGE sample: begin (have $(count "$SAMPLES")/$N_TARGET)"
tries=0
while [ "$(count "$SAMPLES")" -lt "$N_TARGET" ] && [ "$tries" -lt 12 ]; do
    tries=$((tries+1))
    status "STAGE sample: pass $tries (have $(count "$SAMPLES"))"
    python scripts/wk4_sample.py >> "$RESULTS/run_all.log" 2>&1 || \
        status "STAGE sample: wk4_sample exited non-zero, will retry"
done
have=$(count "$SAMPLES")
if [ "$have" -lt "$N_TARGET" ]; then
    status "STAGE sample: INCOMPLETE ($have/$N_TARGET) after $tries passes; proceeding with what we have"
else
    status "STAGE sample: done ($have/$N_TARGET)"
fi

# ---- Stage 2: clustering (resumable) ---------------------------------------
status "STAGE cluster: begin (have $(count "$ENTROPY"))"
tries=0
while [ "$(count "$ENTROPY")" -lt "$have" ] && [ "$tries" -lt 6 ]; do
    tries=$((tries+1))
    status "STAGE cluster: pass $tries (have $(count "$ENTROPY")/$have)"
    python scripts/wk4_cluster.py >> "$RESULTS/run_all.log" 2>&1 || \
        status "STAGE cluster: wk4_cluster exited non-zero, will retry"
done
status "STAGE cluster: done ($(count "$ENTROPY")/$have)"

# ---- Stage 3: AUROC --------------------------------------------------------
status "STAGE auroc: begin"
python scripts/wk4_auroc.py >> "$RESULTS/run_all.log" 2>&1 || status "STAGE auroc: non-zero exit"
BEST_AUC=$(python -c "import json;print(json.load(open('$RESULTS/replication_auroc.json'))['best_auroc'])" 2>/dev/null || echo 0)
IN_TARGET=$(python -c "import json;print(json.load(open('$RESULTS/replication_auroc.json'))['in_target'])" 2>/dev/null || echo False)
status "STAGE auroc: best_auroc=$BEST_AUC in_target=$IN_TARGET"

# ---- Phase 1 -> Phase 2 sanity gate ----------------------------------------
PROCEED=$(python -c "print(1 if float('$BEST_AUC') >= $SANITY_FLOOR else 0)" 2>/dev/null || echo 0)
if [ "$PROCEED" != "1" ]; then
    status "GATE: best AUROC $BEST_AUC below sanity floor $SANITY_FLOOR. HALTING before Phase 2."
    status "DRIVER DONE (phase 1 only; detector below sanity floor)"
    exit 0
fi
status "GATE: best AUROC $BEST_AUC >= $SANITY_FLOOR. Proceeding to Phase 2 (reduced scale)."

# ---- Phase 2 reduced config ------------------------------------------------
export ATTACK_N=10
export ATTACK_MAX_ITER=6
export ATTACK_M=2
export ATTACK_TOPN=2
export SRE_N=60
WK9_ARGS="--n 15 --max_iteration 6 --candidate_size_M 2 --top_N 2"

run_py() {  # run_py <stage-name> <python args...>
    local name="$1"; shift
    status "STAGE $name: begin"
    if python "$@" >> "$RESULTS/run_all.log" 2>&1; then
        status "STAGE $name: done"
    else
        status "STAGE $name: NON-ZERO EXIT (continuing)"
    fi
}

# ---- Stage 4: Week 5 smoke -------------------------------------------------
run_py wk5_smoke scripts/wk5_seca_explore.py

# ---- Stage 5-6: Week 6 Hide, Week 7 False-alarm ----------------------------
run_py wk6_hide scripts/wk6_hide_attack.py
run_py wk7_false_alarm scripts/wk7_false_alarm.py

# ---- Stage 7: Week 8 SRE ---------------------------------------------------
run_py wk8_sre scripts/wk8_sre.py

# ---- Stage 8: Week 9 scale-up campaigns (8 cells, each resumable) ----------
for dataset in triviaqa squad; do
  for detector in se sre; do
    for attack in hide false_alarm; do
      run_py "wk9_${dataset}_${detector}_${attack}" \
        scripts/wk9_scaleup.py --attack "$attack" --detector "$detector" \
        --dataset "$dataset" $WK9_ARGS
    done
  done
done

# ---- Stage 9: Week 10 matrix + Week 11 analysis ----------------------------
run_py wk10_matrix scripts/wk10_matrix.py
run_py wk11_analysis scripts/wk11_analysis.py

# ---- Stage 10: feedback-driven extensions ----------------------------------
# Cross-detector transfer (SE<->SRE), the input-paraphrase-averaging defense,
# and the headline figure. These consume the wk9 caches. The SEP-transfer
# stretch (wk_seps_transfer.py) is intentionally NOT auto-run here: it extracts
# hidden states for all 2000 questions plus the attacks and is the heaviest,
# most optional experiment; run it manually when ready.
run_py wk_transfer scripts/wk_transfer.py
run_py wk_defense scripts/wk_defense.py
run_py make_figures scripts/make_figures.py

status "DRIVER DONE (full pipeline + extensions)"
