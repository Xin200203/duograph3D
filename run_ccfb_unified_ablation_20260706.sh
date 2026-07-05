#!/usr/bin/env bash
# Unified-config ablation matrix — full Replica, one row per mechanism removal.
#
# Rows (each a full 8-scene official run via run_ccfb_unified_full_20260705.sh):
#   wo_gate       : legacy CG merge (label gate off), auto-keep + scale-prior on
#   wo_auto_keep  : configured/broad keep-set, gate + scale-prior on
#   pure_beta     : gate off + scale-prior off (system floor without our mechanisms)
#   gamma_phase   : unified mechanisms but phase gamma (phase ablation)
# The w/o-scale-prior row is the log-only control run; the oracle upper bound is
# the archived E70 composite — neither needs a rerun here.
# Usage: run_ccfb_unified_ablation_20260706.sh <stamp> "<row> <row> ..."
set -euo pipefail
CODE=${DUOGRAPH_CODE:-/home/nebula/xxy/DuoGraph3D}
cd "$CODE"
STAMP=${1:-$(date +%Y%m%d)}
ROWS=${2:-"wo_gate wo_auto_keep pure_beta gamma_phase"}
ALL_SCENES="room0 room1 room2 office0 office1 office2 office3 office4"

run_row() {
  local row=$1
  local sp_mode=apply
  local extra=""
  case "$row" in
    wo_gate)      extra="--cg-merge-label-gate 0" ;;
    wo_auto_keep) extra="--geometry-repair-keep-mode configured" ;;
    pure_beta)    sp_mode=off; extra="--cg-merge-label-gate 0" ;;
    gamma_phase)  extra="--phase gamma" ;;
    *) echo "unknown row: $row" >&2; return 1 ;;
  esac
  echo "[$(date -Is)] ABLATION_ROW_START $row sp=$sp_mode extra='$extra'"
  bash run_ccfb_unified_full_20260705.sh "${STAMP}_${row}" "$ALL_SCENES" "$sp_mode" "$extra"
  echo "[$(date -Is)] ABLATION_ROW_DONE $row"
}

for row in $ROWS; do
  run_row "$row"
done
echo "ABLATION_MATRIX_DONE"
