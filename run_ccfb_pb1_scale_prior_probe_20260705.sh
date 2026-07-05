#!/usr/bin/env bash
# P-B1: scale-prior semantic-authority probe, log-only, four decisive scenes.
#
# ONE scene-independent config (label-gate merge + declared-auto keep-set +
# scale-prior log-only, NO hand-written label-pair rules).  Reading is the
# scale_prior_probe diagnostics, not the gap:
#   office1 -> tissue-paper carrier must violate, select cloth
#   office2 -> bin carrier must violate, select table
#   office4 -> vent carriers must abstain (no compatible target / weak share)
#   room0  -> cushion carriers must abstain (source_well_supported guard)
# Usage: run_ccfb_pb1_scale_prior_probe_20260705.sh <stamp> "<scene> <scene> ..."
set -euo pipefail
PY=${DUOGRAPH_PY:-/home/nebula/miniconda3/envs/duograph-baselines-cu118/bin/python}
ART=${DUOGRAPH_ART:-/home/nebula/xxy/duograph3d_artifacts}
CODE=${DUOGRAPH_CODE:-/home/nebula/xxy/DuoGraph3D}
cd "$CODE"
STAMP=${1:-$(date +%Y%m%d_%H%M%S)}
ONLY=${2:-}
QUEUE_ROOT="$ART/ccfb_pb1_scale_prior_probe_${STAMP}"
mkdir -p "$QUEUE_ROOT/logs"
SUMMARY="$QUEUE_ROOT/variant_summary.tsv"
if [ ! -f "$SUMMARY" ]; then
  printf "variant\tscene\tstatus\tgap_miou\tgap_mf1\tgap_fmiou\tsp_violations\tsp_relabels\tsp_abstains\tauto_keep_count\texport_objects\tstarted\tended\n" > "$SUMMARY"
fi
COMMON="PYTHONPATH=src"
MEMDENSE="--export-source memory-dense --memory-dense-split-by-label 1 --memory-dense-split-min-observations 1 --memory-dense-split-min-root-label-entropy 0.5 --memory-dense-split-max-root-top-share 0.9"
CORE="--phase beta --voxel-size 0.20 --min-object-detections 2 --max-points-per-obs 160 --max-points-per-object 4096 --drop-post-subtract-tiny 0 --text-feature-mode item --clip-feature-mode image --export-split-by-label 0 --multires-export 0 $MEMDENSE"
UNIFIED="--cg-merge-overlap-thresh 0.7 --cg-merge-label-gate 1 --geometry-repair-keep-mode declared-auto --geometry-repair-scale-prior-mode log-only"

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
extract_sp() {
  local summary_json=$1
  python3 - "$summary_json" <<'PY'
import json, sys
d = json.load(open(sys.argv[1]))
dbg = (d.get('scene_debug') or [{}])[0]
mon = dbg.get('export_monitor') or {}
geom = mon.get('geometry_repair_probe') or {}
sp = geom.get('scale_prior_probe') or {}
keep = geom.get('keep_mode_diagnostics') or {}
compact = dict(sort_keys=True, separators=(",", ":"))
print("\t".join([
    json.dumps(sp.get('violations_by_label') or {}, **compact),
    json.dumps(sp.get('relabel_counts') or {}, **compact),
    json.dumps(sp.get('abstain_reasons') or {}, **compact),
    str(keep.get('auto_label_count', 'NA')),
    str(dbg.get('export_object_count', 'NA')),
]))
PY
}
run_scene() {
  local scene=$1
  local variant="sp_logonly_${scene}"
  if [ -n "$ONLY" ] && ! grep -qw "$scene" <<< "$ONLY"; then
    return 0
  fi
  local started ended status gaps_tab sp_tab
  started=$(date -Is)
  local base="$QUEUE_ROOT/$variant"
  local pred="ccfb_${variant}_${STAMP}"
  mkdir -p "$base/logs" "$base/$scene"
  echo "[$started] VARIANT_START $variant scene=$scene" | tee -a "$QUEUE_ROOT/logs/queue.log" "$base/logs/driver.log"
  set +e
  eval "$COMMON $PY examples/run_conceptgraphs_engineered_parity.py --scenes $scene --skip-eval --root $base/$scene --pred-exp-name $pred $CORE $UNIFIED" > "$base/logs/${scene}.log" 2>&1
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
  sp_tab=$'{}\t{}\t{}\tNA\tNA'
  if [ "$status" -eq 0 ]; then
    gaps_tab=$(extract_row "$base/final_eval/duograph_monitored_gap_vs_conceptgraphs.csv" "$scene")
    sp_tab=$(extract_sp "$base/$scene/merge_monitor_summary.json")
  fi
  printf "%s\t%s\t%s\t%s\t%s\t%s\t%s\n" "$variant" "$scene" "$status" "$gaps_tab" "$sp_tab" "$started" "$ended" >> "$SUMMARY" || true
  echo "[$ended] VARIANT_DONE $variant status=$status $(echo "$gaps_tab" | tr '\t' ' ') sp=$(echo "$sp_tab" | tr '\t' ' ')" | tee -a "$QUEUE_ROOT/logs/queue.log" "$base/logs/driver.log"
}

run_scene office1
run_scene office2
run_scene office4
run_scene room0

echo "PB1_QUEUE_DONE $QUEUE_ROOT"
