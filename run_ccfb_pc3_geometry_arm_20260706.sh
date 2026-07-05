#!/usr/bin/env bash
# PC3: complete the substrate matrix — forced-GEOMETRY arm (gate floor2+mutual,
# declared-only sp) for the scenes missing a geometry+gate row under current
# code.  Together with the v1 forced-dense full run this gives the 8x2
# dense-vs-geometry table for the binary substrate-selector analysis.
# Usage: run_ccfb_pc3_geometry_arm_20260706.sh <stamp> "<scene> ..."
set -euo pipefail
CODE=${DUOGRAPH_CODE:-/home/nebula/xxy/DuoGraph3D}
cd "$CODE"
STAMP=${1:-20260706_pc3}
SCENES=${2:-"room1 office0 office3 office2"}
for scene in $SCENES; do
  echo "[$(date -Is)] PC3_ROW_START $scene"
  bash run_ccfb_unified_full_20260705.sh "${STAMP}_${scene}" "$scene" apply \
    "--export-source geometry --cg-merge-label-gate-min-obs 2"
  echo "[$(date -Is)] PC3_ROW_DONE $scene"
done
echo "PC3_GEOMETRY_ARM_DONE"
