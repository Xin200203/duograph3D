#!/usr/bin/env bash
set -uo pipefail
ROOT=/home/nebula/xxy/duograph3d_artifacts/onlineanyseg_official_subset5_sparse_20260423
cd /home/nebula/xxy/OnlineAnySeg
export PYTHONPATH=/home/nebula/xxy/OnlineAnySeg:/home/nebula/xxy/OnlineAnySeg/third_party/FCGF
export OMP_NUM_THREADS=8
SCENES=(scene0568_00 scene0568_01 scene0568_02 scene0304_00 scene0488_00)
mkdir -p "$ROOT/logs" "$ROOT/output"
: > "$ROOT/run_status.tsv"
for scene in "${SCENES[@]}"; do
  echo "===== $scene $(date -Is) =====" | tee "$ROOT/logs/${scene}.log"
  rm -rf "$ROOT/output/$scene"
  /home/nebula/miniconda3/bin/conda run -n duograph-oas-cu116 python main.py \
    -c "$ROOT/scannet_subset5_sparse_clip512.yaml" \
    -d "$ROOT/input/$scene" \
    -i "$ROOT/instance/$scene" \
    --seq_name "$scene" \
    --device cuda:0 \
    -o "$ROOT/output" 2>&1 | tee -a "$ROOT/logs/${scene}.log"
  code=${PIPESTATUS[0]}
  if [ "$code" -eq 0 ]; then
    echo -e "$scene\tOK" | tee -a "$ROOT/run_status.tsv"
  else
    echo -e "$scene\tFAIL:$code" | tee -a "$ROOT/run_status.tsv"
  fi
done
