from __future__ import annotations

import json
from pathlib import Path

from duograph3d import DuoGraph3DPipeline, RemoteExperimentPaths, TemporalVariant
from duograph3d.data import ReplicaSequence, ScanNetPoseCenteredScene, ScanNetRawScene
from duograph3d.events import BRANCH_DUOGRAPH3D


def summarize_replica(paths: RemoteExperimentPaths) -> dict[str, object]:
    replica = ReplicaSequence.from_root(paths.replica_root / "office0")
    issues = replica.validate()
    pipeline = DuoGraph3DPipeline()
    run_result, logger = pipeline.run_sequence(
        sequence_id="replica-office0-smoke",
        frames=replica.to_frame_inputs(limit=3),
        temporal_variant=TemporalVariant.DEVA_STYLE,
        branch_id=BRANCH_DUOGRAPH3D,
    )
    return {
        "root": str(replica.root),
        "issues": issues,
        "rgb_count": len(replica.rgb_frames),
        "depth_count": len(replica.depth_frames),
        "memory_nodes": sorted(run_result.memory_nodes.keys()),
        "event_count": len(logger.records),
        "births": logger.count("birth_commit"),
    }


def summarize_scannet(paths: RemoteExperimentPaths) -> dict[str, object]:
    raw_scene = ScanNetRawScene.from_root(paths.scannet_scans_root / "scene0008_00")
    pose_scene = ScanNetPoseCenteredScene.from_root(paths.scannet_pose_centered_root / "scene0008_00")
    issues = raw_scene.validate() + pose_scene.validate()
    pipeline = DuoGraph3DPipeline()
    run_result, logger = pipeline.run_sequence(
        sequence_id="scannet-scene0008-smoke",
        frames=pose_scene.to_frame_inputs(limit=3),
        temporal_variant=TemporalVariant.NAIVE_FRAMEWISE,
        branch_id=BRANCH_DUOGRAPH3D,
    )
    return {
        "raw_root": str(raw_scene.root),
        "pose_root": str(pose_scene.root),
        "issues": issues,
        "pose_count": len(pose_scene.pose_files),
        "memory_nodes": sorted(run_result.memory_nodes.keys()),
        "event_count": len(logger.records),
        "births": logger.count("birth_commit"),
    }


def main() -> None:
    paths = RemoteExperimentPaths()
    report = {
        "replica": summarize_replica(paths),
        "scannet": summarize_scannet(paths),
    }
    print(json.dumps(report, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
