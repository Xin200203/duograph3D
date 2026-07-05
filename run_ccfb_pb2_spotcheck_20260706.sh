#!/usr/bin/env bash
# PB2 spot-check: unified-v2 mechanisms (mutual-containment guard + evidence
# floor + hard-ratio override + CLIP-compatible fallback) on the four decisive
# scenes.  Floor 24 is preliminary pending the PA2 sweep.
#   office1 : hard-ratio must fire tissue->cloth via clip-fallback -> ~+8.17
#   room0   : floor+mutual must kill the noise vetoes -> recover positive
#   room2   : mutual must kill coincident-pair vetoes -> recover ~CG level
#   office2 : + carve isolates the cushion:sofa carve contribution -> ~+8.1
set -euo pipefail
CODE=${DUOGRAPH_CODE:-/home/nebula/xxy/DuoGraph3D}
cd "$CODE"
STAMP=${1:-20260706_pb2}
FLOOR=${2:-24}
bash run_ccfb_unified_full_20260705.sh "${STAMP}_o1"    "office1" apply "--cg-merge-label-gate-min-obs $FLOOR"
bash run_ccfb_unified_full_20260705.sh "${STAMP}_room0" "room0"   apply "--cg-merge-label-gate-min-obs $FLOOR"
bash run_ccfb_unified_full_20260705.sh "${STAMP}_room2" "room2"   apply "--cg-merge-label-gate-min-obs $FLOOR"
bash run_ccfb_unified_full_20260705.sh "${STAMP}_o4"    "office4" apply "--cg-merge-label-gate-min-obs $FLOOR"
bash run_ccfb_unified_full_20260705.sh "${STAMP}_o2carve" "office2" apply "--cg-merge-label-gate-min-obs $FLOOR --geometry-repair-carve-rules cushion:sofa:0.04"
echo "PB2_SPOTCHECK_DONE"
