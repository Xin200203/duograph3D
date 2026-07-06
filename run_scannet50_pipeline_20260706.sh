#!/usr/bin/env bash
# ScanNet val_50 scale-up: stage+GSA -> CG cfslam -> in-loop mechanisms ->
# both evaluations, for the 42 scenes not yet processed; final evals cover all
# 50 (the 8 pilot scenes reuse their existing artifacts).  Headline-table run.
set -euo pipefail
CODE=${DUOGRAPH_CODE:-/home/nebula/xxy/DuoGraph3D}
ART=${DUOGRAPH_ART:-/home/nebula/xxy/duograph3d_artifacts}
PY=${DUOGRAPH_PY:-/home/nebula/miniconda3/envs/duograph-baselines-cu118/bin/python}
cd "$CODE"
STAMP=${1:-20260706sn50}
NEW_SCENES="scene0019_01 scene0025_00 scene0025_01 scene0025_02 scene0050_00 scene0050_01 scene0050_02 scene0063_00 scene0169_00 scene0169_01 scene0221_00 scene0221_01 scene0257_00 scene0412_01 scene0426_00 scene0426_01 scene0426_02 scene0426_03 scene0488_01 scene0549_00 scene0549_01 scene0565_00 scene0568_01 scene0568_02 scene0575_01 scene0575_02 scene0578_00 scene0578_01 scene0578_02 scene0580_00 scene0580_01 scene0583_00 scene0583_01 scene0583_02 scene0655_00 scene0655_01 scene0655_02 scene0665_00 scene0665_01 scene0701_00 scene0701_01 scene0701_02"
PILOT_SCENES="scene0568_00 scene0304_00 scene0488_00 scene0412_00 scene0217_00 scene0019_00 scene0414_00 scene0575_00"
ALL_SCENES="$PILOT_SCENES $NEW_SCENES"

echo "[$(date -Is)] SN50_STAGE1_GSA_START (42 new scenes)"
bash run_scannet_stage_and_gsa_20260706.sh "$STAMP" "$NEW_SCENES"
echo "[$(date -Is)] SN50_STAGE2_CFSLAM_START"
bash run_scannet_cfslam_20260706.sh "$STAMP" "$NEW_SCENES"
echo "[$(date -Is)] SN50_STAGE3_INLOOP_START"
PYTHONPATH=src $PY -u examples/run_conceptgraphs_engineered_parity.py \
  --dataset scannet --scenes $NEW_SCENES --phase beta \
  --root "$ART/scannet_inloop_${STAMP}" --pred-exp-name sn_inloop_v1 \
  --export-source consolidation-auto --mechanisms-scope consolidated-only \
  --cg-merge-label-gate 1 --geometry-repair-keep-mode declared-auto \
  --geometry-repair-scale-prior-mode apply \
  > "$ART/scannet_inloop_${STAMP}.log" 2>&1
echo "[$(date -Is)] SN50_STAGE4_EVALS_START (all 50 scenes)"
$PY -u examples/eval_scannet_semseg.py \
  --scenes $ALL_SCENES \
  --pred-exp-name none_overlap_maskconf0.95_simsum1.2_dbscan.1_merge20_masksub \
  --output-root "$ART/scannet50_eval_${STAMP}" \
  > "$ART/scannet50_eval_cg.log" 2>&1
$PY -u examples/eval_scannet_semseg.py \
  --scenes $ALL_SCENES \
  --pred-exp-name sn_inloop_v1 \
  --output-root "$ART/scannet50_eval_${STAMP}" \
  > "$ART/scannet50_eval_inloop.log" 2>&1
echo "SN50_PIPELINE_DONE $ART/scannet50_eval_${STAMP}"
