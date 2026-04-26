from __future__ import annotations

import argparse
import json
from pathlib import Path

from duograph3d.io_utils import write_json
from duograph3d.observation_metrics import (
    render_observation_grounded_metrics_markdown,
    summarize_observation_grounded_metrics,
)
from duograph3d.presets import SuiteSpec
from duograph3d.suite_runner import run_suite


def main() -> None:
    parser = argparse.ArgumentParser(description="Run a paper-candidate real-observation suite and summarize observation-grounded metrics")
    parser.add_argument("--output-root", required=True)
    parser.add_argument("--scannet-scenes", nargs="*", required=True)
    parser.add_argument("--limit", type=int, default=6)
    parser.add_argument("--drop-mode", choices=["none", "alternate", "burst", "random"], default="alternate")
    parser.add_argument("--drop-every", type=int, default=2)
    parser.add_argument("--drop-offset", type=int, default=1)
    parser.add_argument("--burst-size", type=int, default=2)
    parser.add_argument("--burst-start-index", type=int, default=1)
    parser.add_argument("--drop-probability", type=float, default=0.35)
    parser.add_argument("--random-seed", type=int, default=0)
    args = parser.parse_args()

    output_root = Path(args.output_root)
    output_root.mkdir(parents=True, exist_ok=True)
    spec = SuiteSpec(
        name="phase4_real_candidate_suite",
        scannet_scenes=args.scannet_scenes,
        drop_mode=args.drop_mode,
        drop_every=args.drop_every,
        drop_offset=args.drop_offset,
        burst_size=args.burst_size,
        burst_start_index=args.burst_start_index,
        drop_probability=args.drop_probability,
        random_seed=args.random_seed,
        limit=args.limit,
        observation_source="real_external",
    )
    aggregate_path, _ = run_suite(spec, output_root)
    report_dir = aggregate_path.parent
    report_paths = [str(path) for path in sorted(report_dir.glob("bounded_slice_*.json"))]
    observation_summary = summarize_observation_grounded_metrics(report_paths)
    metrics_dir = output_root / "observation_metrics"
    metrics_dir.mkdir(exist_ok=True)
    write_json(observation_summary, metrics_dir / "observation_metrics_summary.json")
    (metrics_dir / "observation_metrics_summary.md").write_text(render_observation_grounded_metrics_markdown(observation_summary) + "\n")
    print(aggregate_path)
    print(metrics_dir / "observation_metrics_summary.json")
    print(metrics_dir / "observation_metrics_summary.md")


if __name__ == "__main__":
    main()
