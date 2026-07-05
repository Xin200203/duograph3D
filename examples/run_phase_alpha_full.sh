#!/bin/bash
# Phase 甲 full experiment runner — execute on remote server 10.177.69.184
#
# Workflow:
#   1. Local:  git push origin <branch>
#   2. Remote: cd /home/nebula/xxy/DuoGraph3D && git pull
#   3. Remote: bash examples/run_phase_alpha_full.sh
#
# Generates:
#   outputs/shadow_b0/
#     room0_b0_baseline_deva_style_events.jsonl
#     room1_b0_baseline_deva_style_events.jsonl
#     metrics/
#       room0_candidate_recall.json
#       room0_memory_purity.json
#       room0_promotion_pending.json
#       room0_carrier.json
#       room1_*.json
#     comparison_report.json

set -euo pipefail

BRANCH="${1:-conceptgraphs-engineering-optimizations-20260426}"
RUN_TAG="${2:-b0_baseline}"
OUTDIR="outputs/shadow_b0"
SCENES=("room0" "room1")
TEMPORAL="deva_style"
REPLICA_ROOT="/home/nebula/xxy/dataset/Replica"

echo "============================================"
echo " Phase 甲 Baseline Shadow — Full Run"
echo " branch:  $BRANCH"
echo " tag:     $RUN_TAG"
echo " scenes:  ${SCENES[*]}"
echo " temporal: $TEMPORAL"
echo " output:  $OUTDIR"
echo "============================================"

cd /home/nebula/xxy/DuoGraph3D

# Ensure on correct branch
git checkout "$BRANCH" 2>/dev/null || echo "(branch unchanged)"
git pull origin "$BRANCH" 2>/dev/null || echo "(pull skipped, may be up to date)"

echo ""
echo "--- Step 1: Verify imports ---"
python3 -c "from duograph3d.experiment_logger import ExperimentRunMetadata; print('OK')" || {
    echo "ERROR: experiment_logger module not found. Ensure code is synced."
    exit 1
}

echo ""
echo "--- Step 2: Run deterministic replay verification ---"
PYTHONPATH=src python3 examples/run_replay_shadow.py \
    --mode synthetic --frames 4 --objects 6 --replays 2

echo ""
echo "--- Step 3: Run baseline shadow for each scene ---"
for SCENE in "${SCENES[@]}"; do
    echo ""
    echo ">>> Scene: $SCENE"
    PYTHONPATH=src python3 examples/run_baseline_shadow.py \
        --scene "$SCENE" \
        --temporal "$TEMPORAL" \
        --replica-root "$REPLICA_ROOT" \
        --output "$OUTDIR" \
        --run-tag "$RUN_TAG" \
        --config-preset conceptgraphs_parity
done

echo ""
echo "--- Step 4: Collect unified summary ---"
PYTHONPATH=src python3 -c "
import json
from pathlib import Path

out = Path('$OUTDIR')
metrics = out / 'metrics'
scenes = ['room0', 'room1']
tag = '$RUN_TAG'

summary = {'branch': '$BRANCH', 'run_tag': tag, 'scenes': {}}
for scene in scenes:
    report_path = metrics / f'{scene}_shadow_report.json'
    if report_path.exists():
        data = json.loads(report_path.read_text())
        summary['scenes'][scene] = {
            'candidate_recall': {k: v for k, v in data.get('candidate_recall', {}).items() if not k.startswith('rows')},
            'memory_purity': {k: v for k, v in data.get('memory_purity', {}).items() if not k.startswith('rows')},
            'promotion_pending': {k: v for k, v in data.get('promotion_pending', {}).items() if k != 'step_counts'},
        }

summary_path = out / 'all_scenes_summary.json'
summary_path.write_text(json.dumps(summary, indent=2, default=str))
print(f'Unified summary: {summary_path}')
"

echo ""
echo "============================================"
echo " Phase 甲 complete!"
echo " Outputs in: $OUTDIR/"
echo "============================================"
echo ""
echo "Next steps:"
echo "  1. Review metric tables in $OUTDIR/metrics/"
echo "  2. Compare against CG baseline:"
echo "     PYTHONPATH=src python3 examples/compare_with_cg_baseline.py --shadow-dir $OUTDIR"
echo "  3. Check event stream: "
echo "     head -3 $OUTDIR/*_events.jsonl | python3 -m json.tool"
