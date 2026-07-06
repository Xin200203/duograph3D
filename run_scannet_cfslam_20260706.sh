#!/usr/bin/env bash
# ScanNet CG-baseline mapping: official cfslam parameters, scannet dataconfig,
# staged 25k-export scenes.  Produces full_pcd_none_*.pkl.gz per scene — the
# CG baseline maps for the transfer table and the substrate for in-loop rows.
# Usage: run_scannet_cfslam_20260706.sh <stamp> "<scene> ..."
set -euo pipefail
CG_ROOT=${DUOGRAPH_CG_MAIN:-/home/nebula/xxy/concept-graphs-main}
STAGE_ROOT=/home/nebula/xxy/dataset/scannet_cg
ART=${DUOGRAPH_ART:-/home/nebula/xxy/duograph3d_artifacts}
STAMP=${1:-20260706}
SCENES=${2:-"scene0568_00 scene0304_00 scene0488_00 scene0412_00 scene0217_00 scene0019_00 scene0414_00 scene0575_00"}
OUT="$ART/scannet_cfslam_${STAMP}"
mkdir -p "$OUT/logs"
source /home/nebula/miniconda3/etc/profile.d/conda.sh
set +u
conda activate duograph-baselines-cu118
source /home/nebula/xxy/duograph3d_artifacts/conceptgraphs_replica_official_20260423/env.sh
set -u
cd "$CG_ROOT/conceptgraph"
: > "$OUT/cfslam_status.tsv"
for scene in $SCENES; do
  echo "[$(date -Is)] SCANNET_CFSLAM_START $scene" | tee -a "$OUT/logs/driver.log"
  set +e
  python slam/cfslam_pipeline_batch.py \
    dataset_root="$STAGE_ROOT" \
    dataset_config="$CG_ROOT/conceptgraph/dataset/dataconfigs/scannet/base.yaml" \
    stride=1 \
    scene_id="$scene" \
    spatial_sim_type=overlap \
    mask_conf_threshold=0.95 \
    match_method=sim_sum \
    sim_threshold=1.2 \
    dbscan_eps=0.1 \
    gsa_variant=none \
    class_agnostic=True \
    skip_bg=True \
    max_bbox_area_ratio=0.5 \
    save_suffix=overlap_maskconf0.95_simsum1.2_dbscan.1_merge20_masksub \
    merge_interval=20 \
    merge_visual_sim_thresh=0.8 \
    merge_text_sim_thresh=0.8 \
    > "$OUT/logs/cfslam_${scene}.log" 2>&1
  status=$?
  set -e
  echo -e "$scene\t$status" | tee -a "$OUT/cfslam_status.tsv"
  echo "[$(date -Is)] SCANNET_CFSLAM_END $scene status=$status" | tee -a "$OUT/logs/driver.log"
done
echo "SCANNET_CFSLAM_ALL_DONE"
