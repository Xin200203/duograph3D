#!/usr/bin/env bash
# Table-1 candidate rows: CG's own maps + carrier-authority postprocess.
# One global config per row, zero scene names, official evaluator.
# Usage: run_ccfb_cg_authority_20260706.sh <stamp> "<row> <row> ..."
set -euo pipefail
PY=${DUOGRAPH_PY:-/home/nebula/miniconda3/envs/duograph-baselines-cu118/bin/python}
ART=${DUOGRAPH_ART:-/home/nebula/xxy/duograph3d_artifacts}
CODE=${DUOGRAPH_CODE:-/home/nebula/xxy/DuoGraph3D}
cd "$CODE"
STAMP=${1:-20260706}
ROWS=${2:-"cg_legacy cg_gate cg_sp cg_gate_sp"}
OUT="$ART/ccfb_cg_authority_${STAMP}"
mkdir -p "$OUT"
for row in $ROWS; do
  echo "[$(date -Is)] CG_AUTHORITY_ROW_START $row"
  $PY -u examples/run_cg_authority_postprocess.py \
    --row "$row" \
    --output-root "$OUT" \
    > "$OUT/${row}.log" 2>&1
  echo "[$(date -Is)] CG_AUTHORITY_ROW_END $row status=$?"
done
echo "CG_AUTHORITY_ALL_DONE $OUT"
