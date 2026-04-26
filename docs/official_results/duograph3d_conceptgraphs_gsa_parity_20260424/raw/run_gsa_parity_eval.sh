#!/usr/bin/env bash
set -eo pipefail
ROOT=/home/nebula/xxy/duograph3d_artifacts/duograph3d_conceptgraphs_gsa_parity_20260424
LOG=$ROOT/run_gsa_parity_eval.log
{
  echo "===== start $(date -Is) ====="
  source /home/nebula/miniconda3/etc/profile.d/conda.sh
  conda activate duograph-baselines-cu118
  export PYTHONUNBUFFERED=1
  export PYTHONPATH=/home/nebula/xxy/DuoGraph3D/src:/home/nebula/xxy/concept-graphs-main
  python "$ROOT/run_gsa_parity_eval.py" "$@"
  echo "===== done $(date -Is) ====="
} >> "$LOG" 2>&1
