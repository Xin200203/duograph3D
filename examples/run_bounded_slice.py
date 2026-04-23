from __future__ import annotations

import argparse
from pathlib import Path

from duograph3d import RemoteExperimentPaths
from duograph3d.data import build_replica_bounded_slice, build_scannet_bounded_slice
from duograph3d.experiments import apply_occlusion_regime, run_temporal_triplet
from duograph3d.g2 import build_g2_summary
from duograph3d.io_utils import write_json
from duograph3d.metrics import serialize_records, summarize_run
from duograph3d.rivals import run_all_branches


def main() -> None:
    parser = argparse.ArgumentParser(description="Run DuoGraph3D bounded-slice experiment")
    parser.add_argument("--dataset", choices=["replica", "scannet"], required=True)
    parser.add_argument("--scene", required=True)
    parser.add_argument("--limit", type=int, default=8)
    parser.add_argument("--output", default="outputs")
    parser.add_argument("--drop-mode", choices=["none", "alternate", "burst", "random"], default="alternate")
    parser.add_argument("--drop-every", type=int, default=0)
    parser.add_argument("--drop-offset", type=int, default=1)
    parser.add_argument("--burst-size", type=int, default=2)
    parser.add_argument("--burst-start-index", type=int, default=1)
    parser.add_argument("--drop-probability", type=float, default=0.35)
    parser.add_argument("--random-seed", type=int, default=0)
    args = parser.parse_args()

    paths = RemoteExperimentPaths()
    if args.dataset == "replica":
        bounded = build_replica_bounded_slice(paths.replica_root / args.scene, limit=args.limit)
    else:
        bounded = build_scannet_bounded_slice(
            paths.scannet_scans_root / args.scene,
            paths.scannet_pose_centered_root / args.scene,
            limit=args.limit,
        )

    experiment_frames = apply_occlusion_regime(
        bounded.frames,
        mode=args.drop_mode,
        drop_every=args.drop_every,
        drop_offset=args.drop_offset,
        burst_size=args.burst_size,
        burst_start_index=args.burst_start_index,
        drop_probability=args.drop_probability,
        random_seed=args.random_seed,
    )
    results = run_all_branches(f"{args.dataset}-{args.scene}", experiment_frames)
    temporal_triplet = run_temporal_triplet(f"{args.dataset}-{args.scene}-triplet", experiment_frames)
    branch_event_files = {}
    for branch_id, (_, logger) in results.items():
        event_path = Path(args.output) / f"events_{args.dataset}_{args.scene}_{branch_id}.json"
        write_json(serialize_records(logger), event_path)
        branch_event_files[branch_id] = str(event_path)
    report = {
        "dataset": bounded.dataset_name,
        "scene": bounded.scene_name,
        "frame_count": len(bounded.frames),
        "frames_with_observations": sum(1 for frame in experiment_frames if frame.observations),
        "drop_mode": args.drop_mode,
        "drop_every": args.drop_every,
        "drop_offset": args.drop_offset,
        "burst_size": args.burst_size,
        "burst_start_index": args.burst_start_index,
        "drop_probability": args.drop_probability,
        "random_seed": args.random_seed,
        "source_paths": bounded.source_paths,
        "issues": bounded.issues,
        "branches": {branch_id: summarize_run(result, logger) for branch_id, (result, logger) in results.items()},
        "branch_event_files": branch_event_files,
        "temporal_triplet": temporal_triplet,
    }
    output_path = Path(args.output) / f"bounded_slice_{args.dataset}_{args.scene}.json"
    g2_path = Path(args.output) / f"g2_summary_{args.dataset}_{args.scene}.json"
    write_json(report, output_path)
    write_json(build_g2_summary(report), g2_path)
    print(output_path)
    print(g2_path)


if __name__ == "__main__":
    main()
