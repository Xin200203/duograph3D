#!/usr/bin/env bash
# PC1: phase x guards matrix — the beta-everywhere generalization failed on
# office4 (beta+guards = -36 while the gate was nearly inert), so the phase is
# re-examined as the pivotal knob.  Questions, one row each:
#   o4_gamma_plain : office4 gamma, no gate, no sp  -> E70-region control (~+1.7?)
#   o4_beta_plain  : office4 beta, no gate, no sp   -> isolates beta's raw damage
#   o4_gamma_v2    : office4 gamma + guards + sp    -> guarded-gamma candidate
#   o2_gamma_v2    : office2 gamma + guards + sp    -> does guarded-gamma recover
#                    office2 to the binonly level (+6.3) that raw gamma+gate lost?
#   o1_gamma_v2    : office1 gamma + guards + sp    -> guarded-gamma on office1
#   room2_gamma_v2 : room2 gamma + guards + sp      -> guarded-gamma on room2
#   room0_gamma_v2 : room0 gamma + guards + sp      -> guarded-gamma on room0
# Usage: run_ccfb_pc1_phase_matrix_20260706.sh <stamp> "<row> <row> ..." [<floor>]
set -euo pipefail
CODE=${DUOGRAPH_CODE:-/home/nebula/xxy/DuoGraph3D}
cd "$CODE"
STAMP=${1:-20260706_pc1}
ROWS=${2:-"o4_gamma_plain o4_beta_plain o4_gamma_v2 o2_gamma_v2 o1_gamma_v2 room2_gamma_v2 room0_gamma_v2"}
FLOOR=${3:-24}
GUARDS="--cg-merge-label-gate-min-obs $FLOOR"

run_row() {
  local row=$1
  local scene phase sp extra
  case "$row" in
    o4_gamma_plain)  scene=office4; phase=gamma; sp=off;   extra="--cg-merge-label-gate 0" ;;
    o4_beta_plain)   scene=office4; phase=beta;  sp=off;   extra="--cg-merge-label-gate 0" ;;
    o4_gamma_v2)     scene=office4; phase=gamma; sp=apply; extra="$GUARDS" ;;
    o2_gamma_v2)     scene=office2; phase=gamma; sp=apply; extra="$GUARDS" ;;
    o1_gamma_v2)     scene=office1; phase=gamma; sp=apply; extra="$GUARDS" ;;
    room2_gamma_v2)  scene=room2;   phase=gamma; sp=apply; extra="$GUARDS" ;;
    room0_gamma_v2)  scene=room0;   phase=gamma; sp=apply; extra="$GUARDS" ;;
    *) echo "unknown row: $row" >&2; return 1 ;;
  esac
  echo "[$(date -Is)] PC1_ROW_START $row scene=$scene phase=$phase sp=$sp extra='$extra'"
  bash run_ccfb_unified_full_20260705.sh "${STAMP}_${row}" "$scene" "$sp" "--phase $phase $extra"
  echo "[$(date -Is)] PC1_ROW_DONE $row"
}

for row in $ROWS; do
  run_row "$row"
done
echo "PC1_MATRIX_DONE"
