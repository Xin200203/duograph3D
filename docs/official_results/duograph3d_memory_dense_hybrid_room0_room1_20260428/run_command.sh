#!/usr/bin/env bash
cd /home/nebula/xxy/DuoGraph3D
/home/nebula/miniconda3/envs/duograph-baselines-cu118/bin/python examples/run_conceptgraphs_engineered_parity.py \
  --root /home/nebula/xxy/duograph3d_artifacts/duograph3d_memory_dense_hybrid_room0_room1_20260428 \
  --pred-exp-name duograph3d_memory_dense_hybrid_room0_room1_20260428 \
  --min-object-detections 2 \
  --export-source memory-dense \
  --scenes room0 room1
