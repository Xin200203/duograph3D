#!/usr/bin/env bash
# Stage ScanNet 25k-export scenes into CG's ScannetDataset layout and generate
# class-agnostic GSA detections (SAM + CLIP, gsa_variant=none) — the input
# stack for the ScanNet mechanism-transfer table.
#
# Layout produced per scene under $STAGE_ROOT/<scene>/:
#   color/ depth/ pose/    (symlinks into dataset/2D/<scene>/)
#   intrinsic/intrinsic_color.txt  (synthesized: scene color intrinsics scaled
#                                   from 1296x968 metadata to the 640x480 export)
# Usage: run_scannet_stage_and_gsa_20260706.sh <stamp> "<scene> <scene> ..."
set -euo pipefail
PY=${DUOGRAPH_PY:-/home/nebula/miniconda3/envs/duograph-baselines-cu118/bin/python}
CG_ROOT=${DUOGRAPH_CG_MAIN:-/home/nebula/xxy/concept-graphs-main}
TWOD=/home/nebula/xxy/dataset/2D
SCANS=/home/nebula/xxy/dataset/scannet_v2/scans
STAGE_ROOT=/home/nebula/xxy/dataset/scannet_cg
ART=${DUOGRAPH_ART:-/home/nebula/xxy/duograph3d_artifacts}
STAMP=${1:-20260706}
SCENES=${2:-"scene0568_00 scene0304_00 scene0488_00 scene0412_00 scene0217_00 scene0019_00 scene0414_00 scene0575_00"}
OUT="$ART/scannet_gsa_${STAMP}"
mkdir -p "$OUT/logs" "$STAGE_ROOT"

stage_scene() {
  local scene=$1
  local dst="$STAGE_ROOT/$scene"
  mkdir -p "$dst/intrinsic"
  for sub in color depth pose; do
    [ -e "$dst/$sub" ] || ln -s "$TWOD/$scene/$sub" "$dst/$sub"
  done
  $PY - "$SCANS/$scene/$scene.txt" "$TWOD/$scene/color" "$dst/intrinsic/intrinsic_color.txt" <<'PYEOF'
import sys
from pathlib import Path
from PIL import Image

meta_path, color_dir, out_path = sys.argv[1:4]
meta = {}
for line in Path(meta_path).read_text().splitlines():
    if "=" in line:
        key, value = line.split("=", 1)
        meta[key.strip()] = value.strip()
fx, fy = float(meta["fx_color"]), float(meta["fy_color"])
cx, cy = float(meta["mx_color"]), float(meta["my_color"])
w0, h0 = float(meta["colorWidth"]), float(meta["colorHeight"])
sample = next(Path(color_dir).glob("*.jpg"))
w1, h1 = Image.open(sample).size
sx, sy = w1 / w0, h1 / h0
rows = [
    [fx * sx, 0.0, cx * sx, 0.0],
    [0.0, fy * sy, cy * sy, 0.0],
    [0.0, 0.0, 1.0, 0.0],
    [0.0, 0.0, 0.0, 1.0],
]
Path(out_path).write_text("\n".join(" ".join(f"{v:.6f}" for v in row) for row in rows) + "\n")
print(f"intrinsics scaled {w0:.0f}x{h0:.0f} -> {w1}x{h1}: fx={fx*sx:.2f} cx={cx*sx:.2f}")
PYEOF
}

cd "$CG_ROOT/conceptgraph"
# The official Replica GSA environment (GSA_PATH, Grounded-Segment-Anything
# paths, import stubs, concept-graphs-main package resolution) is codified in
# the official run contract's env.sh — reuse it verbatim.
set +u
source /home/nebula/xxy/duograph3d_artifacts/conceptgraphs_replica_official_20260423/env.sh
set -u
: > "$OUT/gsa_status.tsv"
for scene in $SCENES; do
  echo "[$(date -Is)] SCANNET_GSA_START $scene" | tee -a "$OUT/logs/driver.log"
  stage_scene "$scene" 2>&1 | tee -a "$OUT/logs/driver.log"
  set +e
  $PY scripts/generate_gsa_results.py \
    --dataset_root "$STAGE_ROOT" \
    --dataset_config "$CG_ROOT/conceptgraph/dataset/dataconfigs/scannet/base.yaml" \
    --scene_id "$scene" \
    --class_set none \
    --stride 1 \
    --device cuda \
    > "$OUT/logs/gsa_${scene}.log" 2>&1
  status=$?
  set -e
  echo -e "$scene\t$status\t$(ls $STAGE_ROOT/$scene/gsa_detections_none 2>/dev/null | wc -l)" | tee -a "$OUT/gsa_status.tsv"
  echo "[$(date -Is)] SCANNET_GSA_END $scene status=$status" | tee -a "$OUT/logs/driver.log"
done
echo "SCANNET_GSA_ALL_DONE"
