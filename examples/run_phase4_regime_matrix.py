from __future__ import annotations

import argparse
import json
from pathlib import Path

from duograph3d.io_utils import write_json
from duograph3d.observation_metrics import (
    render_observation_grounded_metrics_markdown,
    summarize_observation_grounded_metrics,
)
from duograph3d.summary_merge import merge_suite_summaries
from duograph3d.presets import SuiteSpec
from duograph3d.reporting import render_g2_table_markdown
from duograph3d.robustness import compare_suite_summaries, render_robustness_markdown
from duograph3d.suite_runner import run_suite


def _specs(
    *,
    replica_scenes: list[str],
    scannet_scenes: list[str],
    limit: int,
) -> list[SuiteSpec]:
    return [
        SuiteSpec(
            name="phase4_baseline",
            replica_scenes=replica_scenes,
            scannet_scenes=scannet_scenes,
            drop_mode="none",
            limit=limit,
            observation_source="real_external",
        ),
        SuiteSpec(
            name="phase4_stress",
            replica_scenes=replica_scenes,
            scannet_scenes=scannet_scenes,
            drop_mode="alternate",
            drop_every=2,
            limit=limit,
            observation_source="real_external",
        ),
        SuiteSpec(
            name="phase4_burst",
            replica_scenes=replica_scenes,
            scannet_scenes=scannet_scenes,
            drop_mode="burst",
            burst_size=2,
            limit=limit,
            observation_source="real_external",
        ),
        SuiteSpec(
            name="phase4_random",
            replica_scenes=replica_scenes,
            scannet_scenes=scannet_scenes,
            drop_mode="random",
            drop_probability=0.35,
            random_seed=7,
            limit=limit,
            observation_source="real_external",
        ),
    ]


def main() -> None:
    parser = argparse.ArgumentParser(description="Run a Phase 4 regime matrix over real-observation external inputs")
    parser.add_argument("--output-root", required=True)
    parser.add_argument("--replica-scenes", nargs="+", required=True)
    parser.add_argument("--scannet-scenes", nargs="+", required=True)
    parser.add_argument("--limit", type=int, default=6)
    args = parser.parse_args()

    output_root = Path(args.output_root)
    output_root.mkdir(parents=True, exist_ok=True)

    suite_summaries = []
    suite_paths = []
    report_paths: list[str] = []
    for spec in _specs(
        replica_scenes=args.replica_scenes,
        scannet_scenes=args.scannet_scenes,
        limit=args.limit,
    ):
        aggregate_path, _ = run_suite(spec, output_root)
        suite_paths.append(aggregate_path.parent)
        suite_summaries.append(json.loads(aggregate_path.read_text()))
        report_paths.extend(str(path) for path in aggregate_path.parent.glob("bounded_slice_*.json"))

    mega = merge_suite_summaries(suite_summaries)
    robustness = compare_suite_summaries([(path.name, summary) for path, summary in zip(suite_paths, suite_summaries)])
    observation_summary = summarize_observation_grounded_metrics(report_paths)

    package_root = output_root / "phase4_matrix_package"
    package_root.mkdir(exist_ok=True)
    write_json(mega, package_root / "mega_suite_summary.json")
    write_json(robustness, package_root / "robustness_summary.json")
    write_json(observation_summary, package_root / "observation_metrics_summary.json")
    (package_root / "mega_suite_summary.md").write_text(
        render_g2_table_markdown(mega, [str(path / "g2_suite_summary.json") for path in suite_paths]) + "\n"
    )
    (package_root / "robustness_summary.md").write_text(render_robustness_markdown(robustness) + "\n")
    (package_root / "observation_metrics_summary.md").write_text(
        render_observation_grounded_metrics_markdown(observation_summary) + "\n"
    )
    print(package_root / "mega_suite_summary.json")
    print(package_root / "robustness_summary.json")
    print(package_root / "observation_metrics_summary.json")


if __name__ == "__main__":
    main()
