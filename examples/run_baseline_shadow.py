#!/usr/bin/env python3
"""Phase 甲 baseline shadow runner — generates full monitoring report.

Runs the DuoGraph3D pipeline on Replica scenes with GSA observation JSONs,
exports the unified event stream, and generates the four core metric tables.

Intended for execution on the remote server (10.177.69.184).

Usage (remote server):
  cd /home/nebula/xxy/DuoGraph3D
  PYTHONPATH=src python3 examples/run_baseline_shadow.py \
      --scene room0 --limit 0 --temporal deva_style \
      --output outputs/shadow_b0 --run-tag b0_baseline

  PYTHONPATH=src python3 examples/run_baseline_shadow.py \
      --scene room1 --limit 0 --temporal deva_style \
      --output outputs/shadow_b0 --run-tag b0_baseline
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from dataclasses import asdict, replace
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from duograph3d.contracts import PipelineConfig, TemporalVariant
from duograph3d.data import build_replica_bounded_slice
from duograph3d.events import BRANCH_DUOGRAPH3D
from duograph3d.pipeline import DuoGraph3DPipeline
from duograph3d.experiment_logger import (
    ExperimentRunMetadata,
    config_to_snapshot,
    export_event_stream_jsonl,
)
from duograph3d.shadow_metrics import generate_shadow_report


def _get_git_commit() -> str:
    import subprocess
    try:
        return subprocess.check_output(
            ["git", "rev-parse", "--short", "HEAD"],
            text=True, stderr=subprocess.DEVNULL,
        ).strip()
    except Exception:
        return ""


def main():
    parser = argparse.ArgumentParser(description="Phase 甲 baseline shadow runner")
    parser.add_argument("--scene", default="room0", help="Replica scene name")
    parser.add_argument("--limit", type=int, default=0,
                        help="Frame limit (0 = all frames)")
    parser.add_argument("--temporal", default="deva_style",
                        choices=("none", "naive_framewise", "deva_style"))
    parser.add_argument("--branch", default=BRANCH_DUOGRAPH3D)
    parser.add_argument("--output", default="outputs/shadow_b0",
                        help="Output directory for reports")
    parser.add_argument("--run-tag", default="b0_baseline",
                        help="Run identifier tag")
    parser.add_argument("--replica-root",
                        default="/home/nebula/xxy/dataset/Replica",
                        help="Replica dataset root")
    parser.add_argument("--observation-json", default=None,
                        help="Path to GSA observation JSON (optional; synthetic if omitted)")
    parser.add_argument("--config-preset", default="default",
                        choices=("default", "conceptgraphs_parity"),
                        help="PipelineConfig preset")
    args = parser.parse_args()

    scene_root = Path(args.replica_root) / args.scene
    if not scene_root.exists():
        print(f"Scene root not found: {scene_root}", file=sys.stderr)
        print("Run on remote server (10.177.69.184) or use --replica-root.", file=sys.stderr)
        sys.exit(1)

    run_id = f"{args.run_tag}_{args.scene}_{args.temporal}"
    timestamp = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())

    # --- Build config ---
    if args.config_preset == "conceptgraphs_parity":
        config = PipelineConfig(
            emit_association_diagnostics=True,
            association_diagnostics_top_k=3,
            candidate_budget=5,
            candidate_retrieval_budget=12,
            candidate_retrieval_channel_budget=5,
            association_threshold=1.7,
            enable_object_consolidation=True,
            object_merge_interval=20,
        )
    else:
        config = PipelineConfig(
            emit_association_diagnostics=True,
            association_diagnostics_top_k=3,
        )

    print(f"=== Phase 甲 Baseline Shadow: {run_id} ===")
    print(f"  scene: {args.scene}  temporal: {args.temporal}  branch: {args.branch}")
    print(f"  config: association_threshold={config.association_threshold} "
          f"emit_diagnostics={config.emit_association_diagnostics}")

    # --- Build input slice ---
    bounded = build_replica_bounded_slice(
        scene_root,
        limit=args.limit if args.limit > 0 else 99999,
        observation_json=args.observation_json,
        observation_format="deva_output" if args.observation_json and "deva" in str(args.observation_json).lower() else "frame_observation_json",
        allow_synthetic_fallback=args.observation_json is None,
    )
    frames = bounded.frames
    if not frames:
        print("No frames loaded.", file=sys.stderr)
        sys.exit(1)
    print(f"  frames: {len(frames)}  metadata: {json.dumps(bounded.metadata, default=str)[:200]}")

    temporal = {
        "none": TemporalVariant.NONE,
        "naive_framewise": TemporalVariant.NAIVE_FRAMEWISE,
        "deva_style": TemporalVariant.DEVA_STYLE,
    }[args.temporal]

    # --- Run pipeline ---
    pipeline = DuoGraph3DPipeline(config)
    frozen_frames = [
        replace(frame, observations=list(frame.observations))
        for frame in frames
    ]
    t_start = time.time()
    result, logger = pipeline.run_sequence(
        sequence_id=run_id,
        frames=frozen_frames,
        temporal_variant=temporal,
        branch_id=args.branch,
    )
    elapsed = time.time() - t_start
    print(f"  pipeline: {elapsed:.1f}s  memory_nodes={len(result.memory_nodes)}  "
          f"events={len(logger.records)}  decisions={len(result.decisions)}")

    # --- Export event stream ---
    output_dir = Path(args.output)
    output_dir.mkdir(parents=True, exist_ok=True)
    events_path = output_dir / f"{run_id}_events.jsonl"

    metadata = ExperimentRunMetadata(
        run_id=run_id,
        branch_id=args.branch,
        scene_id=args.scene,
        temporal_variant=args.temporal,
        config_snapshot=config_to_snapshot(config),
        seed=0,
        timestamp=timestamp,
        git_commit=_get_git_commit(),
    )
    export_event_stream_jsonl(logger, events_path, metadata=metadata)
    print(f"  event stream: {events_path} ({events_path.stat().st_size} bytes)")

    # --- Generate shadow monitoring report ---
    metrics_dir = output_dir / "metrics"
    report = generate_shadow_report(
        events_path,
        run_id=run_id,
        scene_id=args.scene,
        output_dir=metrics_dir,
    )

    # --- Print summary ---
    cr = report.get("candidate_recall", {})
    mp = report.get("memory_purity", {})
    pp = report.get("promotion_pending", {})
    ca = report.get("carrier", {})

    print(f"\n--- Candidate Recall ---")
    print(f"  hypotheses={cr.get('total_hypotheses', '?')}  "
          f"birth_rate={cr.get('birth_rate', '?')}  "
          f"avg_best_score={cr.get('avg_best_score', '?')}")
    miss = {k: v for k, v in cr.items() if k.endswith("_count") and v}
    print(f"  miss distribution: {json.dumps(miss)}")

    print(f"\n--- Memory Purity ---")
    print(f"  nodes_created={mp.get('total_nodes_created', '?')}  "
          f"active={mp.get('nodes_active_final', '?')}  "
          f"retired={mp.get('nodes_retired_final', '?')}  "
          f"merges={mp.get('total_merges', '?')}")

    print(f"\n--- Promotion / Pending ---")
    print(f"  births={pp.get('total_births', '?')}  "
          f"associations={pp.get('total_associations', '?')}  "
          f"absorptions={pp.get('total_absorptions', '?')}  "
          f"reentries={pp.get('total_reentries', '?')}")

    print(f"\n--- Carrier / Export ---")
    print(f"  source={ca.get('export_source_selected', '?')}  "
          f"strategy={ca.get('export_source_strategy', '?')}  "
          f"verdict={ca.get('coverage_verdict', '?')}")

    # --- Write summary JSON ---
    summary_path = output_dir / f"{run_id}_summary.json"
    summary_path.write_text(json.dumps(report["meta"], indent=2, default=str))

    print(f"\n✓ Shadow report complete: {output_dir}")
    print(f"  metrics: {metrics_dir}/")
    return report


if __name__ == "__main__":
    main()
