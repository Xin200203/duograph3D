#!/usr/bin/env bash
# Unified scene-independent full-Replica run.
#
# ONE config for all 8 scenes — no scene names, no hand keep lists, no
# label-pair rules: label-gate merge (方案 A) + declared-auto keep-set (B1) +
# scale-prior repair (B2, mode from $3: log-only or apply).
# Official all-scene evaluation happens inside the runner (no --skip-eval).
# Usage: run_ccfb_unified_full_20260705.sh <stamp> [<scenes...>] [<sp-mode>] [<extra-args>]
#   <extra-args> appended verbatim — used by the ablation matrix, e.g.
#   "--cg-merge-label-gate 0" for the w/o-gate row.
set -euo pipefail
PY=${DUOGRAPH_PY:-/home/nebula/miniconda3/envs/duograph-baselines-cu118/bin/python}
ART=${DUOGRAPH_ART:-/home/nebula/xxy/duograph3d_artifacts}
CODE=${DUOGRAPH_CODE:-/home/nebula/xxy/DuoGraph3D}
cd "$CODE"
STAMP=${1:-$(date +%Y%m%d_%H%M%S)}
SCENES=${2:-"room0 room1 room2 office0 office1 office2 office3 office4"}
SP_MODE=${3:-apply}
EXTRA=${4:-}
ROOT="$ART/ccfb_unified_full_${STAMP}"
PRED="ccfb_unified_full_${STAMP}"
mkdir -p "$ROOT/logs"
MEMDENSE="--export-source memory-dense --memory-dense-split-by-label 1 --memory-dense-split-min-observations 1 --memory-dense-split-min-root-label-entropy 0.5 --memory-dense-split-max-root-top-share 0.9"
CORE="--phase beta --voxel-size 0.20 --min-object-detections 2 --max-points-per-obs 160 --max-points-per-object 4096 --drop-post-subtract-tiny 0 --text-feature-mode item --clip-feature-mode image --export-split-by-label 0 --multires-export 0 $MEMDENSE"
UNIFIED="--cg-merge-overlap-thresh 0.7 --cg-merge-label-gate 1 --geometry-repair-keep-mode declared-auto --geometry-repair-scale-prior-mode $SP_MODE"
echo "[$(date -Is)] UNIFIED_FULL_START scenes='$SCENES' sp_mode=$SP_MODE extra='$EXTRA'" | tee -a "$ROOT/logs/driver.log"
set +e
PYTHONPATH=src $PY examples/run_conceptgraphs_engineered_parity.py \
  --scenes $SCENES \
  --root "$ROOT" \
  --pred-exp-name "$PRED" \
  $CORE $UNIFIED $EXTRA > "$ROOT/logs/run.log" 2>&1
STATUS=$?
set -e
echo "[$(date -Is)] UNIFIED_FULL_DONE status=$STATUS" | tee -a "$ROOT/logs/driver.log"
if [ "$STATUS" -eq 0 ]; then
  tail -5 "$ROOT/duograph_monitored_gap_vs_conceptgraphs.csv" 2>/dev/null | tee -a "$ROOT/logs/driver.log"
fi
echo "UNIFIED_FULL_EXIT $STATUS $ROOT"
