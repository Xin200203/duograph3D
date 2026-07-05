#!/usr/bin/env python3
"""Phase experiment wrapper — runs the CG parity runner with custom PipelineConfig.

Usage:
  DUOGRAPH_PHASE=i1 PYTHONPATH=src python examples/run_phase_experiment.py \
    --scenes room0 room1 --output /path/to/artifacts/i1

The DUOGRAPH_PHASE env var controls the experiment config:
  b0 - current default
  b1 - no lifecycle (retire/occluded/dormant = 999)
  b2 - no lifecycle + unlimited candidate (candidate_budget=999)
  i1 - identity gate soft (no hard identity, threshold=1.0)
  i2 - margin override (simplified scoring, threshold=1.3)
"""

from __future__ import annotations

import argparse
import os
import sys
import time
from pathlib import Path

# --- Path setup (must match the 76 server paths) ---
_REPLICA_ROOT = Path(os.environ.get("REPLICA_ROOT", "/datadisk3/xxy/duograph3d/dataset/Replica"))
_DUOGRAPH3D_SRC = Path(os.environ.get("DUOGRAPH3D_SRC", "/datadisk3/xxy/duograph3d/DuoGraph3D/src"))
_CG_MAIN = Path(os.environ.get("CG_MAIN", "/datadisk3/xxy/duograph3d/concept-graphs-main"))
sys.path.insert(0, str(_DUOGRAPH3D_SRC))
sys.path.insert(0, str(_CG_MAIN))

from duograph3d.contracts import PipelineConfig, TemporalVariant
from duograph3d.pipeline import DuoGraph3DPipeline
from duograph3d.events import BRANCH_DUOGRAPH3D
from duograph3d.metrics import summarize_run


def build_phase_config(phase: str) -> PipelineConfig:
    """Build PipelineConfig for the given experiment phase."""
    kw = dict(
        emit_association_diagnostics=True,
        association_diagnostics_top_k=2,
    )

    if phase == "b0":
        pass  # all defaults

    elif phase == "b1":
        kw.update(retire_after_misses=999, occluded_after_misses=999, dormant_after_misses=999)

    elif phase == "b2":
        kw.update(retire_after_misses=999, occluded_after_misses=999, dormant_after_misses=999,
                   candidate_budget=999, candidate_retrieval_budget=999)

    elif phase == "i1":
        # Soft identity: no hard gate, lower threshold
        kw.update(layer2_require_strong_identity=False, association_threshold=1.0)

    elif phase == "i2":
        # Margin override: simplified scoring, moderate threshold
        kw.update(layer2_simplified_scoring=True, association_threshold=1.3)

    return PipelineConfig(**kw)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--scenes", nargs="+", default=["room0", "room1"])
    parser.add_argument("--output", required=True, help="Output directory")
    parser.add_argument("--export-source", default="memory-dense")
    parser.add_argument("--skip-eval", action="store_true")
    args = parser.parse_args()

    phase = os.environ.get("DUOGRAPH_PHASE", "b0")
    config = build_phase_config(phase)

    print(f"=== Phase experiment: {phase} ===")
    print(f"  retire={config.retire_after_misses} require_strong_id={config.layer2_require_strong_identity}")
    print(f"  simplified_scoring={config.layer2_simplified_scoring} threshold={config.association_threshold}")
    print(f"  candidate_budget={config.candidate_budget} retrieval_budget={config.candidate_retrieval_budget}")

    output_dir = Path(args.output)
    output_dir.mkdir(parents=True, exist_ok=True)

    from examples.run_conceptgraphs_engineered_parity import (
        prepare_scene, write_report, summarize_association_diagnostics,
        write_conceptgraphs_payload, compute_shadow_undermerge,
        REPLICA_CLASSES, class_feats_np, label_to_index,
    )
    import numpy as np
    import open_clip
    import torch

    # Load CLIP once
    print("Loading CLIP...")
    clip_model, _, _ = open_clip.create_model_and_transforms("ViT-H-14", "laion2b_s32b_b79k")
    tokenizer = open_clip.get_tokenizer("ViT-H-14")
    class_names = REPLICA_CLASSES
    class_feats = class_feats_np

    for scene in args.scenes:
        t0 = time.time()
        print(f"\n=== {scene}: prepare ===")

        # Use the run_conceptgraphs_engineered_parity prepare function
        frames, key_data, prep, frame_debug = prepare_scene(scene, class_names, class_feats)

        print(f"=== {scene}: DuoGraph3D ({phase}) ===")
        pipeline = DuoGraph3DPipeline(config)
        result, logger = pipeline.run_sequence(
            sequence_id=f"replica-{scene}-phase-{phase}",
            frames=frames,
            temporal_variant=TemporalVariant.NAIVE_FRAMEWISE,
            branch_id=BRANCH_DUOGRAPH3D,
        )
        summary = summarize_run(result, logger)
        summary["seconds"] = round(time.time() - t0, 3)
        summary["association_diagnostics"] = summarize_association_diagnostics(logger)

        print(f"  nodes={summary['memory_node_count']} births={summary['births']}")
        if summary.get('association_diagnostics'):
            births = summary['association_diagnostics'].get('birth_reasons', {})
            print(f"  birth_reasons: {births}")

        if not args.skip_eval:
            # Export and eval (simplified — full eval needs the CG runner)
            print(f"  (export/eval skipped in wrapper mode)")

        print(f"  done in {summary['seconds']:.1f}s")

    print(f"\n=== Experiment {phase} complete ===")


if __name__ == "__main__":
    main()
