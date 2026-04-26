from __future__ import annotations

import argparse
from pathlib import Path

from duograph3d.io_utils import write_json
from duograph3d.official_results import OfficialRun, compare_official_runs, render_official_comparison_markdown


def main() -> None:
    parser = argparse.ArgumentParser(description="Render a formal evaluator comparison from metrics JSON files.")
    parser.add_argument("--baseline-metrics", required=True)
    parser.add_argument("--candidate-metrics", required=True)
    parser.add_argument("--baseline-monitor", default=None)
    parser.add_argument("--candidate-monitor", default=None)
    parser.add_argument("--baseline-name", default="baseline")
    parser.add_argument("--candidate-name", default="duograph3d")
    parser.add_argument("--output-json", required=True)
    parser.add_argument("--output-md", required=True)
    args = parser.parse_args()

    comparison = compare_official_runs(
        baseline=OfficialRun(
            method=args.baseline_name,
            metrics_path=Path(args.baseline_metrics),
            monitor_path=Path(args.baseline_monitor) if args.baseline_monitor else None,
        ),
        candidate=OfficialRun(
            method=args.candidate_name,
            metrics_path=Path(args.candidate_metrics),
            monitor_path=Path(args.candidate_monitor) if args.candidate_monitor else None,
        ),
    )
    write_json(comparison, args.output_json)
    Path(args.output_md).parent.mkdir(parents=True, exist_ok=True)
    Path(args.output_md).write_text(render_official_comparison_markdown(comparison) + "\n")
    print(args.output_json)
    print(args.output_md)


if __name__ == "__main__":
    main()
