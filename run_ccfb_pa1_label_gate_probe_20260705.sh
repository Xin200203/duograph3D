#!/usr/bin/env bash
# P-A1: per-pair label-cluster merge gate — office1/office2 unification probe.
#
# Question: does ONE merge config (overlap 0.7 + label gate) preserve the office1
# tissue-paper carrier (which previously needed merge=1.0/off) while keeping the
# office2 table-fragment merging (which previously needed merge=0.7)?  Plus phase
# unification probes (office1@gamma, office2@beta).
#
# Env-parametrized so the same script runs on 184 (defaults) and 76:
#   DUOGRAPH_PY, DUOGRAPH_ART, DUOGRAPH_CODE  (+ DUOGRAPH_* path vars on 76)
# Usage: run_ccfb_pa1_label_gate_probe_20260705.sh <stamp> "<variant> <variant> ..."
set -euo pipefail
PY=${DUOGRAPH_PY:-/home/nebula/miniconda3/envs/duograph-baselines-cu118/bin/python}
ART=${DUOGRAPH_ART:-/home/nebula/xxy/duograph3d_artifacts}
CODE=${DUOGRAPH_CODE:-/home/nebula/xxy/DuoGraph3D}
cd "$CODE"
STAMP=${1:-$(date +%Y%m%d_%H%M%S)}
ONLY=${2:-}
QUEUE_ROOT="$ART/ccfb_pa1_label_gate_probe_${STAMP}"
mkdir -p "$QUEUE_ROOT/logs"
SUMMARY="$QUEUE_ROOT/variant_summary.tsv"
if [ ! -f "$SUMMARY" ]; then
  printf "variant\tscene\tstatus\tgap_miou\tgap_mf1\tgap_fmiou\trelabel_counts\tblocked_relabel_counts\texport_objects\tgate_candidate_pairs\tgate_merged\tgate_vetoed\tstarted\tended\n" > "$SUMMARY"
fi
COMMON="PYTHONPATH=src"
MEMDENSE="--export-source memory-dense --memory-dense-split-by-label 1 --memory-dense-split-min-observations 1 --memory-dense-split-min-root-label-entropy 0.5 --memory-dense-split-max-root-top-share 0.9"
CORE="--voxel-size 0.20 --min-object-detections 2 --max-points-per-obs 160 --max-points-per-object 4096 --drop-post-subtract-tiny 0 --text-feature-mode item --clip-feature-mode image --export-split-by-label 0 --multires-export 0 $MEMDENSE"
O1_RULES="--geometry-repair-large-label-rules tissue-paper:cloth:0.8 --geometry-repair-large-label-evidence-mode off"
O2_KEEP="--geometry-repair-keep-labels bin,bottle,camera,chair,clock,cushion,lamp,panel,sofa,stool,table,tablet,tissue-paper,tv-screen,vent,wall-plug"
O2_RULES="$O2_KEEP --geometry-repair-carve-rules cushion:sofa:0.04 --geometry-repair-large-label-rules bin:table:1.0 --geometry-repair-large-label-evidence-mode off"
GATE="--cg-merge-overlap-thresh 0.7 --cg-merge-label-gate 1"
NOGATE="--cg-merge-overlap-thresh 0.7 --cg-merge-label-gate 0"

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
print('NA NA NA' if row is None else f"{row['gap_miou']} {row['gap_mf1score']} {row['gap_fmiou']}")
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
fields = [
    json.dumps(geom.get('relabel_counts') or geom.get('large_label_relabel_counts') or {}, **compact),
    json.dumps(geom.get('blocked_relabel_counts') or {}, **compact),
    str(dbg.get('export_object_count', 'NA')),
    str(gate.get('legacy_merge_candidate_pairs', 'NA')),
    str(gate.get('merged_pairs', 'NA')),
    str(gate.get('vetoed_pairs', 'NA')),
]
print("\t".join(fields))
PY
}
run_variant() {
  local variant=$1; shift
  local scene=$1; shift
  local args="$*"
  if [ -n "$ONLY" ] && ! grep -qw "$variant" <<< "$ONLY"; then
    return 0
  fi
  local started ended status gaps probe
  started=$(date -Is)
  local base="$QUEUE_ROOT/$variant"
  local pred="ccfb_${variant}_${STAMP}"
  mkdir -p "$base/logs" "$base/$scene"
  echo "[$started] VARIANT_START $variant scene=$scene args='$args'" | tee -a "$QUEUE_ROOT/logs/queue.log" "$base/logs/driver.log"
  set +e
  eval "$COMMON $PY examples/run_conceptgraphs_engineered_parity.py --scenes $scene --skip-eval --root $base/$scene --pred-exp-name $pred $args" > "$base/logs/${scene}.log" 2>&1
  status=$?
  set -e
  if [ "$status" -eq 0 ]; then
    set +e
    eval "$COMMON $PY examples/evaluate_composite_policy.py --root $base --pred-exp-name $pred --output-root $base/final_eval --scenes $scene" > "$base/logs/evaluate_${scene}.log" 2>&1
    status=$?
    set -e
  fi
  ended=$(date -Is)
  local gaps_tab=$'NA\tNA\tNA'
  local probe_tab=$'{}\t{}\tNA\tNA\tNA\tNA'
  if [ "$status" -eq 0 ]; then
    gaps_tab=$(extract_row "$base/final_eval/duograph_monitored_gap_vs_conceptgraphs.csv" "$scene" | tr ' ' '\t')
    probe_tab=$(extract_probe "$base/$scene/merge_monitor_summary.json")
  fi
  printf "%s\t%s\t%s\t%s\t%s\t%s\t%s\n" "$variant" "$scene" "$status" "$gaps_tab" "$probe_tab" "$started" "$ended" >> "$SUMMARY" || true
  echo "[$ended] VARIANT_DONE $variant status=$status gaps=$(echo "$gaps_tab" | tr '\t' ' ') probe=$(echo "$probe_tab" | tr '\t' ' ')" | tee -a "$QUEUE_ROOT/logs/queue.log" "$base/logs/driver.log"
}

# office1 rows (tissue carrier preservation under one merge config)
run_variant o1_gate_m07        office1 "--phase beta $CORE $GATE $O1_RULES"
run_variant o1_nogate_m07      office1 "--phase beta $CORE $NOGATE $O1_RULES"
run_variant o1_gate_m07_gamma  office1 "--phase gamma $CORE $GATE $O1_RULES"
# office2 rows (table-fragment merging must survive the gate)
run_variant o2_gate_m07        office2 "--phase gamma $CORE $GATE $O2_RULES"
run_variant o2_nogate_m07      office2 "--phase gamma $CORE $NOGATE $O2_RULES"
run_variant o2_gate_m07_beta   office2 "--phase beta $CORE $GATE $O2_RULES"

echo "PA1_QUEUE_DONE $QUEUE_ROOT"
