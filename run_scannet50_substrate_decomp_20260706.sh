#!/usr/bin/env bash
# ScanNet-50 substrate decomposition — attribute the +14.4 headline gain.
# All mechanisms OFF (gate off, sp off); vary only the export substrate:
#   memdense : forced memory-dense (full two-layer consolidation)
#   geomonly : forced geometry-key coverage (no consolidation, export hygiene only)
# CG baseline (online-merged) = 12.02; full auto+mech = 26.42; wo_gate = 26.73.
# If memdense >> geomonly, the gain is the two-layer memory; if ~equal, it is
# export hygiene, not the memory.
set -euo pipefail
PY=/home/nebula/miniconda3/envs/duograph-baselines-cu118/bin/python
ART=/home/nebula/xxy/duograph3d_artifacts
cd /home/nebula/xxy/DuoGraph3D
SC="scene0568_00 scene0304_00 scene0488_00 scene0412_00 scene0217_00 scene0019_00 scene0414_00 scene0575_00 scene0019_01 scene0025_00 scene0025_01 scene0025_02 scene0050_00 scene0050_01 scene0050_02 scene0063_00 scene0169_00 scene0169_01 scene0221_00 scene0221_01 scene0257_00 scene0412_01 scene0426_00 scene0426_01 scene0426_02 scene0426_03 scene0488_01 scene0549_00 scene0549_01 scene0565_00 scene0568_01 scene0568_02 scene0575_01 scene0575_02 scene0578_00 scene0578_01 scene0578_02 scene0580_00 scene0580_01 scene0583_00 scene0583_01 scene0583_02 scene0655_00 scene0655_01 scene0655_02 scene0665_00 scene0665_01 scene0701_00 scene0701_01 scene0701_02"
EVALROOT="$ART/scannet50_eval_20260706sn50"

run_row() {
  local tag=$1; local src=$2
  echo "[$(date -Is)] SUBSTRATE_ROW_START $tag src=$src"
  PYTHONPATH=src $PY -u examples/run_conceptgraphs_engineered_parity.py \
    --dataset scannet --scenes $SC --phase beta \
    --root "$ART/scannet_substrate_${tag}" --pred-exp-name "sn_sub_${tag}" \
    --export-source "$src" --cg-merge-label-gate 0 --geometry-repair-scale-prior-mode off \
    --geometry-repair-keep-mode declared-auto \
    > "$ART/scannet_substrate_${tag}.log" 2>&1
  $PY -u examples/eval_scannet_semseg.py --scenes $SC \
    --pred-exp-name "sn_sub_${tag}" --output-root "$EVALROOT" \
    > "$ART/scannet50_eval_sub_${tag}.log" 2>&1
  echo "SUBSTRATE_ROW_DONE $tag $(grep 'SCANNET all' $ART/scannet50_eval_sub_${tag}.log | tail -1)" >> "$ART/scannet50_substrate_decomp.log"
}

: > "$ART/scannet50_substrate_decomp.log"
run_row memdense memory-dense
run_row geomonly geometry
echo "SUBSTRATE_DECOMP_DONE" >> "$ART/scannet50_substrate_decomp.log"
