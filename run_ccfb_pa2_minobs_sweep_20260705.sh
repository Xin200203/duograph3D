#!/usr/bin/env bash
# P-A2: evidence-floor calibration for the label-cluster merge veto.
#
# The PA1b/c probes showed the veto separates the two failure regimes by
# multi-view evidence volume: office2's same-table fragments (min-side 12-17
# declared obs, must merge) vs office1's distinct carriers (cloth|picture
# 164/567, must stay separate).  This sweep calibrates
# --cg-merge-label-gate-min-obs on the two development scenes; the chosen
# floor is then validated untouched on the remaining six scenes.
# Usage: run_ccfb_pa2_minobs_sweep_20260705.sh <stamp> "<scene> ..." "<minobs> ..."
set -euo pipefail
PY=${DUOGRAPH_PY:-/home/nebula/miniconda3/envs/duograph-baselines-cu118/bin/python}
ART=${DUOGRAPH_ART:-/home/nebula/xxy/duograph3d_artifacts}
CODE=${DUOGRAPH_CODE:-/home/nebula/xxy/DuoGraph3D}
cd "$CODE"
STAMP=${1:-$(date +%Y%m%d_%H%M%S)}
SCENES=${2:-"office1 office2"}
MINOBS_LIST=${3:-"8 16 24 48 96"}
QUEUE_ROOT="$ART/ccfb_pa2_minobs_sweep_${STAMP}"
mkdir -p "$QUEUE_ROOT/logs"
SUMMARY="$QUEUE_ROOT/variant_summary.tsv"
if [ ! -f "$SUMMARY" ]; then
  printf "variant\tscene\tmin_obs\tstatus\tgap_miou\tgap_mf1\tgap_fmiou\trelabel_counts\texport_objects\tgate_candidates\tgate_merged\tgate_vetoed\tstarted\tended\n" > "$SUMMARY"
fi
COMMON="PYTHONPATH=src"
MEMDENSE="--export-source memory-dense --memory-dense-split-by-label 1 --memory-dense-split-min-observations 1 --memory-dense-split-min-root-label-entropy 0.5 --memory-dense-split-max-root-top-share 0.9"
CORE="--voxel-size 0.20 --min-object-detections 2 --max-points-per-obs 160 --max-points-per-object 4096 --drop-post-subtract-tiny 0 --text-feature-mode item --clip-feature-mode image --export-split-by-label 0 --multires-export 0 $MEMDENSE"
O1_RULES="--geometry-repair-large-label-rules tissue-paper:cloth:0.8 --geometry-repair-large-label-evidence-mode off"
O2_RULES="--geometry-repair-keep-labels bin,bottle,camera,chair,clock,cushion,lamp,panel,sofa,stool,table,tablet,tissue-paper,tv-screen,vent,wall-plug --geometry-repair-carve-rules cushion:sofa:0.04 --geometry-repair-large-label-rules bin:table:1.0 --geometry-repair-large-label-evidence-mode off"

extract_row() {
  local csv=$1; local scene=$2
  python3 - "$csv" "$scene" <<'PY'
import csv, sys
path, scene = sys.argv[1:3]
row = None
with open(path) as f:
    for r in csv.DictReader(f):
        if r.get('scene_id') == scene:
            row = r; break
print('NA\tNA\tNA' if row is None else f"{row['gap_miou']}\t{row['gap_mf1score']}\t{row['gap_fmiou']}")
PY
}
extract_probe() {
  local summary_json=$1
  python3 - "$summary_json" <<'PY'
import json, sys
d = json.load(open(sys.argv[1]))
dbg = (d.get('scene_debug') or [{}])[0]
mon = dbg.get('export_monitor') or {}
geom = mon.get('geometry_repair_probe') or {}
gate = mon.get('cg_merge_label_gate_probe') or {}
compact = dict(sort_keys=True, separators=(",", ":"))
print("\t".join([
    json.dumps(geom.get('relabel_counts') or {}, **compact),
    str(dbg.get('export_object_count', 'NA')),
    str(gate.get('legacy_merge_candidate_pairs', 'NA')),
    str(gate.get('merged_pairs', 'NA')),
    str(gate.get('vetoed_pairs', 'NA')),
]))
PY
}
run_variant() {
  local scene=$1; local minobs=$2
  local variant="minobs${minobs}_${scene}"
  local phase_args rules
  if [ "$scene" = "office1" ]; then
    phase_args="--phase beta"; rules="$O1_RULES"
  else
    phase_args="--phase gamma"; rules="$O2_RULES"
  fi
  local gate="--cg-merge-overlap-thresh 0.7 --cg-merge-label-gate 1 --cg-merge-label-gate-min-obs $minobs"
  local started ended status gaps_tab probe_tab
  started=$(date -Is)
  local base="$QUEUE_ROOT/$variant"
  local pred="ccfb_${variant}_${STAMP}"
  mkdir -p "$base/logs" "$base/$scene"
  echo "[$started] VARIANT_START $variant" | tee -a "$QUEUE_ROOT/logs/queue.log"
  set +e
  eval "$COMMON $PY examples/run_conceptgraphs_engineered_parity.py --scenes $scene --skip-eval --root $base/$scene --pred-exp-name $pred $phase_args $CORE $gate $rules" > "$base/logs/${scene}.log" 2>&1
  status=$?
  set -e
  if [ "$status" -eq 0 ]; then
    set +e
    eval "$COMMON $PY examples/evaluate_composite_policy.py --root $base --pred-exp-name $pred --output-root $base/final_eval --scenes $scene" > "$base/logs/evaluate_${scene}.log" 2>&1
    status=$?
    set -e
  fi
  ended=$(date -Is)
  gaps_tab=$'NA\tNA\tNA'
  probe_tab=$'{}\tNA\tNA\tNA\tNA'
  if [ "$status" -eq 0 ]; then
    gaps_tab=$(extract_row "$base/final_eval/duograph_monitored_gap_vs_conceptgraphs.csv" "$scene")
    probe_tab=$(extract_probe "$base/$scene/merge_monitor_summary.json")
  fi
  printf "%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\n" "$variant" "$scene" "$minobs" "$status" "$gaps_tab" "$probe_tab" "$started" "$ended" >> "$SUMMARY" || true
  echo "[$ended] VARIANT_DONE $variant status=$status $(echo "$gaps_tab" | tr '\t' ' ') probe=$(echo "$probe_tab" | tr '\t' ' ')" | tee -a "$QUEUE_ROOT/logs/queue.log"
}

for scene in $SCENES; do
  for minobs in $MINOBS_LIST; do
    run_variant "$scene" "$minobs"
  done
done
echo "PA2_QUEUE_DONE $QUEUE_ROOT"
