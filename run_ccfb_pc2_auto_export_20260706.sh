#!/usr/bin/env bash
# PC2: export-source AUTO axis — the E70 forensics showed non-target scenes ran
# the coverage-gated geometry fallback (office4: 191 objects, geometry export,
# "memory_object_count_below_coverage_floor"), not forced memory-dense.  The
# unified config must therefore use `--export-source auto` (scene-independent
# coverage gates already in export_policy.py) instead of forcing memory-dense.
# Rows: five decisive scenes, beta + auto export + gate(floor)+mutual + sp.
# Usage: run_ccfb_pc2_auto_export_20260706.sh <stamp> "<scene> ..." [<floor>]
set -euo pipefail
CODE=${DUOGRAPH_CODE:-/home/nebula/xxy/DuoGraph3D}
cd "$CODE"
STAMP=${1:-20260706_pc2}
SCENES=${2:-"office4 room0 room2 office1 office2"}
FLOOR=${3:-2}

run_scene() {
  local scene=$1
  local stamp_row="${STAMP}_${scene}"
  echo "[$(date -Is)] PC2_ROW_START $scene floor=$FLOOR"
  # NOTE: run_ccfb_unified_full bakes --export-source memory-dense in CORE via
  # MEMDENSE; we override with a later --export-source auto (argparse last-wins).
  bash run_ccfb_unified_full_20260705.sh "$stamp_row" "$scene" apply \
    "--export-source auto --cg-merge-label-gate-min-obs $FLOOR"
  echo "[$(date -Is)] PC2_ROW_DONE $scene"
}

for scene in $SCENES; do
  run_scene "$scene"
done
echo "PC2_AUTO_EXPORT_DONE"
