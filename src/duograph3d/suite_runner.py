from __future__ import annotations

import json
from pathlib import Path

from .data import build_replica_bounded_slice, build_scannet_bounded_slice
from .experiments import apply_occlusion_regime, run_temporal_triplet
from .g2 import build_g2_summary
from .io_utils import write_json
from .metrics import serialize_records, summarize_run
from .presets import REPLICA_SCENES, SuiteSpec
from .remote_config import RemoteExperimentPaths
from .rivals import run_all_branches


def run_one(dataset: str, scene: str, spec: SuiteSpec, output_dir: Path) -> tuple[Path, Path]:
    paths = RemoteExperimentPaths()
    use_real_observations = spec.observation_source == "real_external"
    if dataset == "replica":
        observation_json = paths.replica_deva_output_json_root / f"{scene}.json" if use_real_observations else None
        bounded = build_replica_bounded_slice(
            paths.replica_root / scene,
            limit=spec.limit,
            observation_json=observation_json,
            observation_format="deva_output",
            allow_synthetic_fallback=not use_real_observations,
        )
    else:
        bounded = build_scannet_bounded_slice(
            paths.scannet_scans_root / scene,
            paths.scannet_pose_centered_root / scene,
            limit=spec.limit,
            observation_json=paths.scannet_esam_online_monitor_json if use_real_observations else None,
            observation_format="scannet_online_monitor" if use_real_observations else "frame_observation_json",
            allow_synthetic_fallback=not use_real_observations,
        )
    experiment_frames = apply_occlusion_regime(
        bounded.frames,
        mode=spec.drop_mode,
        drop_every=spec.drop_every,
        drop_offset=spec.drop_offset,
        burst_size=spec.burst_size,
        burst_start_index=spec.burst_start_index,
        drop_probability=spec.drop_probability,
        random_seed=spec.random_seed,
    )
    results = run_all_branches(f"{dataset}-{scene}", experiment_frames)
    temporal_triplet = run_temporal_triplet(f"{dataset}-{scene}-triplet", experiment_frames)
    branch_event_files = {}
    for branch_id, (_, logger) in results.items():
        event_path = output_dir / f"events_{dataset}_{scene}_{branch_id}.json"
        write_json(serialize_records(logger), event_path)
        branch_event_files[branch_id] = str(event_path)
    report = {
        "dataset": bounded.dataset_name,
        "scene": bounded.scene_name,
        "frame_count": len(bounded.frames),
        "frames_with_observations": sum(1 for frame in experiment_frames if frame.observations),
        "drop_mode": spec.drop_mode,
        "drop_every": spec.drop_every,
        "drop_offset": spec.drop_offset,
        "burst_size": spec.burst_size,
        "burst_start_index": spec.burst_start_index,
        "drop_probability": spec.drop_probability,
        "random_seed": spec.random_seed,
        "source_paths": bounded.source_paths,
        "issues": bounded.issues,
        "scene_metadata": bounded.metadata,
        "branches": {branch_id: summarize_run(result, logger) for branch_id, (result, logger) in results.items()},
        "branch_event_files": branch_event_files,
        "temporal_triplet": temporal_triplet,
    }
    report_path = output_dir / f"bounded_slice_{dataset}_{scene}.json"
    g2_path = output_dir / f"g2_summary_{dataset}_{scene}.json"
    write_json(report, report_path)
    write_json(build_g2_summary(report), g2_path)
    return report_path, g2_path


def run_suite(spec: SuiteSpec, output_root: Path | None = None) -> tuple[Path, Path]:
    output_dir = (output_root or Path('.')) / spec.name
    output_dir.mkdir(parents=True, exist_ok=True)
    source_g2_paths = []
    g2_summaries = []
    replica_scenes = spec.replica_scenes or REPLICA_SCENES
    for scene in replica_scenes:
        _, g2_path = run_one("replica", scene, spec, output_dir)
        source_g2_paths.append(str(g2_path))
        g2_summaries.append(json.loads(g2_path.read_text()))
    for scene in spec.scannet_scenes:
        _, g2_path = run_one("scannet", scene, spec, output_dir)
        source_g2_paths.append(str(g2_path))
        g2_summaries.append(json.loads(g2_path.read_text()))
    from .reporting import aggregate_g2_summaries, render_g2_table_markdown
    aggregate = aggregate_g2_summaries(g2_summaries)
    aggregate_path = output_dir / "g2_suite_summary.json"
    markdown_path = output_dir / "g2_suite_summary.md"
    write_json(aggregate, aggregate_path)
    markdown_path.write_text(render_g2_table_markdown(aggregate, source_g2_paths) + "\n")
    return aggregate_path, markdown_path
