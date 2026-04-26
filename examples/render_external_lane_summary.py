from __future__ import annotations

import argparse
from pathlib import Path

from duograph3d.external_lane_summary import build_external_lane_summary, render_external_lane_summary_markdown
from duograph3d.io_utils import write_json


def main() -> None:
    parser = argparse.ArgumentParser(description="Render a story-aligned external baseline lane summary.")
    parser.add_argument("--lane-id", required=True)
    parser.add_argument("--role", required=True)
    parser.add_argument("--status", required=True)
    parser.add_argument("--health-log", required=True)
    parser.add_argument("--evaluator-log", default=None)
    parser.add_argument("--artifact", action="append", default=[], help="Artifact mapping as name=path; may be repeated.")
    parser.add_argument("--boundary", default="")
    parser.add_argument("--next-step", action="append", default=[])
    parser.add_argument("--output-json", required=True)
    parser.add_argument("--output-md", required=True)
    args = parser.parse_args()

    artifacts = {}
    for item in args.artifact:
        if "=" not in item:
            raise ValueError(f"artifact must be name=path: {item}")
        name, path = item.split("=", 1)
        artifacts[name] = path

    summary = build_external_lane_summary(
        lane_id=args.lane_id,
        role=args.role,
        status=args.status,
        health_log_path=args.health_log,
        evaluator_log_path=args.evaluator_log,
        artifacts=artifacts,
        boundary=args.boundary,
        next_steps=args.next_step,
    )
    write_json(summary, args.output_json)
    Path(args.output_md).parent.mkdir(parents=True, exist_ok=True)
    Path(args.output_md).write_text(render_external_lane_summary_markdown(summary) + "\n")
    print(args.output_json)
    print(args.output_md)


if __name__ == "__main__":
    main()
