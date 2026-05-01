#!/usr/bin/env python3
"""Deterministic replay shadow runner — Phase 甲 baseline verification.

Runs the same pipeline input twice and asserts identical output.

Usage (synthetic smoke — no data dependency):
  PYTHONPATH=src python3 examples/run_replay_shadow.py --mode synthetic --frames 4 --objects 6

Usage (Replica — requires remote data):
  PYTHONPATH=src python3 examples/run_replay_shadow.py --mode replica --scene room0
"""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import replace
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from duograph3d.contracts import (
    FrameInput, Observation, ObservationSupport, ObjectObservationPayload,
    PipelineConfig, TemporalVariant,
)
from duograph3d.events import BRANCH_DUOGRAPH3D
from duograph3d.experiments import apply_observation_dropout
from duograph3d.pipeline import DuoGraph3DPipeline


def _build_synthetic_frames(num_frames: int, objects_per_frame: int) -> list[FrameInput]:
    """Build deterministic synthetic frames for smoke testing."""
    frames = []
    for fi in range(num_frames):
        obs = []
        for oi in range(objects_per_frame):
            obs.append(Observation(
                observation_id=f"o{fi}-{oi}",
                descriptor="chair" if oi % 2 == 0 else "desk",
                geometry_key=f"room0:gsa:item:{oi // 2}:0",
                confidence=0.95,
                repair_group_id=f"chair" if oi % 2 == 0 else "desk",
                support=ObservationSupport(
                    proposal_id=f"p{fi}-{oi}",
                    frame_token=f"f{fi}",
                    support_size=0.5 + oi * 0.05,
                    depth_scale=1.0,
                    appearance_key="chair" if oi % 2 == 0 else "desk",
                    continuity_key=f"scene:obj{oi}",
                    geometry_support=0.6,
                ),
                object_payload=ObjectObservationPayload(
                    label="chair" if oi % 2 == 0 else "desk",
                    points_sample=tuple((float(i), float(j), float(k)) for i in range(3) for j in range(2) for k in range(2)),
                    centroid=(0.5, 0.5, float(oi) * 0.3),
                    mask_area=500.0,
                    detection_count=1,
                ),
            ))
        frames.append(FrameInput(frame_id=f"f{fi}", observations=obs))
    return frames


def _compare_runs(run1, run2):
    """Return (identical: bool, diffs: list[str])."""
    diffs = []
    res1, _log1 = run1
    res2, _log2 = run2

    if res1.event_count != res2.event_count:
        diffs.append(f"event_count: {res1.event_count} vs {res2.event_count}")
    if len(res1.decisions) != len(res2.decisions):
        diffs.append(f"decisions: {len(res1.decisions)} vs {len(res2.decisions)}")
    if len(res1.memory_nodes) != len(res2.memory_nodes):
        diffs.append(f"memory_nodes: {len(res1.memory_nodes)} vs {len(res2.memory_nodes)}")

    for key in sorted(set(res1.memory_nodes) | set(res2.memory_nodes)):
        n1 = res1.memory_nodes.get(key)
        n2 = res2.memory_nodes.get(key)
        if n1 is None or n2 is None:
            diffs.append(f"node {key}: missing from one run")
            continue
        for attr in ("object_id", "status", "birth_step", "last_seen_step",
                     "detection_count", "descriptor_fused", "geometry_key",
                     "miss_count", "reentry_count", "point_count"):
            v1, v2 = getattr(n1, attr, None), getattr(n2, attr, None)
            if v1 != v2:
                diffs.append(f"node {key}.{attr}: {v1!r} vs {v2!r}")

    for i, (d1, d2) in enumerate(zip(res1.decisions, res2.decisions)):
        if d1.action != d2.action or d1.object_id != d2.object_id:
            diffs.append(f"decision[{i}]: {d1.action}/{d1.object_id} vs {d2.action}/{d2.object_id}")

    # Compare event stream ordering
    log1_types = [r.event_type for r in _log1.records]
    log2_types = [r.event_type for r in _log2.records]
    if log1_types != log2_types:
        for i in range(min(len(log1_types), len(log2_types))):
            if log1_types[i] != log2_types[i]:
                diffs.append(f"event[{i}]: {log1_types[i]} vs {log2_types[i]}")
                break
        diffs.append(f"event seq lengths: {len(log1_types)} vs {len(log2_types)}")

    return len(diffs) == 0, diffs


def _hashable_summary(result) -> str:
    """Stable hash for quick comparison."""
    parts = []
    for nid in sorted(result.memory_nodes):
        node = result.memory_nodes[nid]
        parts.append(
            f"{nid}:{node.status.value}:{node.birth_step}:{node.last_seen_step}:"
            f"{node.detection_count}:{node.geometry_key}:{node.descriptor_fused}"
        )
    for d in result.decisions:
        parts.append(f"D:{d.action}:{d.object_id}:{d.hypothesis_id}")
    return "|".join(parts)


def main():
    parser = argparse.ArgumentParser(description="DuoGraph3D deterministic replay shadow")
    parser.add_argument("--mode", default="synthetic", choices=("synthetic", "replica"))
    parser.add_argument("--scene", default="room0")
    parser.add_argument("--frames", type=int, default=4)
    parser.add_argument("--objects", type=int, default=6)
    parser.add_argument("--limit", type=int, default=6)
    parser.add_argument("--drop-every", type=int, default=2)
    parser.add_argument("--output", default=None)
    parser.add_argument("--replays", type=int, default=2)
    parser.add_argument("--temporal", default="deva_style",
                        choices=("none", "naive_framewise", "deva_style"))
    args = parser.parse_args()

    # --- Build input ---
    if args.mode == "synthetic":
        frames = _build_synthetic_frames(args.frames, args.objects)
    else:
        try:
            from duograph3d.data import build_replica_bounded_slice
        except ImportError:
            print("Replica mode requires remote data. Use --mode synthetic.", file=sys.stderr)
            sys.exit(1)
        bounded = build_replica_bounded_slice(f"/home/nebula/xxy/dataset/Replica/{args.scene}",
                                               limit=args.limit)
        frames = bounded.frames
        if args.drop_every > 0:
            frames = apply_observation_dropout(frames, drop_every=args.drop_every)

    if not frames:
        print("No frames loaded.", file=sys.stderr)
        sys.exit(1)

    temporal = {
        "none": TemporalVariant.NONE,
        "naive_framewise": TemporalVariant.NAIVE_FRAMEWISE,
        "deva_style": TemporalVariant.DEVA_STYLE,
    }[args.temporal]

    config = PipelineConfig()
    pipeline = DuoGraph3DPipeline(config)

    runs = []
    for trial in range(args.replays):
        frozen_frames = [replace(frame, observations=list(frame.observations)) for frame in frames]
        result, logger = pipeline.run_sequence(
            sequence_id=f"replay-{args.mode}-{args.scene}",
            frames=frozen_frames,
            temporal_variant=temporal,
            branch_id=BRANCH_DUOGRAPH3D,
        )
        runs.append((result, logger))

    identical, diffs = _compare_runs(runs[0], runs[1])

    report = {
        "mode": args.mode,
        "scene": args.scene,
        "frame_count": len(frames),
        "replay_count": args.replays,
        "temporal_variant": args.temporal,
        "deterministic": identical,
        "diffs": diffs,
        "memory_node_count": len(runs[0][0].memory_nodes),
        "event_count": runs[0][0].event_count,
        "decision_count": len(runs[0][0].decisions),
        "hash_0": _hashable_summary(runs[0][0]),
    }

    if identical:
        print(f"✓ DETERMINISTIC — {args.replays} replays identical")
    else:
        print(f"✗ NON-DETERMINISTIC — {len(diffs)} diffs:")
        for d in diffs[:15]:
            print(f"  - {d}")

    if args.output:
        p = Path(args.output)
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(json.dumps(report, indent=2, default=str))

    sys.exit(0 if identical else 1)


if __name__ == "__main__":
    main()
