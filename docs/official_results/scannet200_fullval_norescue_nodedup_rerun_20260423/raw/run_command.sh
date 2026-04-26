#!/usr/bin/env bash
set -euo pipefail
cd /home/nebula/xxy/3D_Reconstruction
export PYTHONPATH=/home/nebula/xxy/3D_Reconstruction
/home/nebula/miniconda3/bin/conda run -n ESAM python tools/test.py \
  /home/nebula/xxy/3D_Reconstruction/work_dirs/ESAM_online_scannet200_CA_mv_fast_ab/fullval_baseline_dino/ESAM_online_scannet200_CA_dino.py \
  /home/nebula/xxy/3D_Reconstruction/work_dirs/tmp/ESAM_CA_online_epoch_128.pth \
  --work-dir /home/nebula/xxy/duograph3d_artifacts/formal_fullval_norescue_nodedup_rerun_20260423/norescue_nodedup_strict_independent \
  --cat-agnostic \
  --cfg-options test_evaluator.online_monitor.out_dir=online_monitor
