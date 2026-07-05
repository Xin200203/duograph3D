#!/usr/bin/env bash
# v4 ablation matrix — full Replica, one row per mechanism removal from the
# unified v4 config (consolidation-auto substrate + beta + label-gate floor2
# +mutual + declared-auto keep + declared-only scale-prior).
#   v4_main        : the unified v4 config itself (main-table candidate)
#   wo_gate        : legacy CG merge (gate off)
#   wo_sp          : scale-prior off
#   forced_dense   : substrate ablation — memory-dense everywhere (= v1 config)
#   forced_geo     : substrate ablation — geometry everywhere
#   gamma_phase    : phase ablation under v4 routing
# Usage: run_ccfb_v4_ablation_20260706.sh <stamp> "<row> <row> ..."
set -euo pipefail
CODE=${DUOGRAPH_CODE:-/home/nebula/xxy/DuoGraph3D}
cd "$CODE"
STAMP=${1:-20260706_v4}
ROWS=${2:-"v4_main wo_gate wo_sp forced_dense forced_geo gamma_phase"}
ALL="room0 room1 room2 office0 office1 office2 office3 office4"
V4="--export-source consolidation-auto --cg-merge-label-gate-min-obs 2 --mechanisms-scope consolidated-only"

run_row() {
  local row=$1 sp=apply extra=""
  case "$row" in
    v4_main)      extra="$V4" ;;
    wo_gate)      extra="$V4 --cg-merge-label-gate 0" ;;
    wo_sp)        sp=off; extra="$V4" ;;
    forced_dense) extra="--cg-merge-label-gate-min-obs 2" ;;  # memory-dense from CORE default
    forced_geo)   extra="--export-source geometry --cg-merge-label-gate-min-obs 2" ;;
    gamma_phase)  extra="$V4 --phase gamma" ;;
    *) echo "unknown row: $row" >&2; return 1 ;;
  esac
  echo "[$(date -Is)] V4_ROW_START $row sp=$sp extra='$extra'"
  bash run_ccfb_unified_full_20260705.sh "${STAMP}_${row}" "$ALL" "$sp" "$extra"
  echo "[$(date -Is)] V4_ROW_DONE $row"
}

for row in $ROWS; do
  run_row "$row"
done
echo "V4_ABLATION_DONE"
