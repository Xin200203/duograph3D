#!/usr/bin/env bash
set -euo pipefail
cd /home/nebula/xxy/OnlineAnySeg
export PYTHONPATH=/home/nebula/xxy/OnlineAnySeg:/home/nebula/xxy/OnlineAnySeg/third_party/FCGF
export OMP_NUM_THREADS=8
/home/nebula/miniconda3/bin/conda run -n duograph-oas-cu116 python main.py \
  -c /home/nebula/xxy/duograph3d_artifacts/onlineanyseg_official_scene0568_sparse83_20260423/scannet_scene0568_sparse83_clip512.yaml \
  -d /home/nebula/xxy/duograph3d_artifacts/onlineanyseg_official_scene0568_sparse83_20260423/input/scene0568_00 \
  -i /home/nebula/xxy/duograph3d_artifacts/onlineanyseg_official_scene0568_sparse83_20260423/instance/scene0568_00 \
  --seq_name scene0568_00 \
  --device cuda:0 \
  -o /home/nebula/xxy/duograph3d_artifacts/onlineanyseg_official_scene0568_sparse83_20260423/output
