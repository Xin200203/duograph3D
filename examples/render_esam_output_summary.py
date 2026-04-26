from __future__ import annotations

import argparse
import json
from pathlib import Path

from duograph3d.esam_results import esam_summary_as_lane, render_esam_output_markdown, summarize_esam_scannet_output


def main() -> None:
    parser = argparse.ArgumentParser(description="Render an ESAM ScanNet output summary")
    parser.add_argument("metric_json")
    parser.add_argument("online_monitor_summary_json")
    parser.add_argument("executed_repo_root")
    parser.add_argument("--output-dir", default="outputs_esam_summary")
    args = parser.parse_args()

    summary = summarize_esam_scannet_output(
        metric_json=args.metric_json,
        online_monitor_summary_json=args.online_monitor_summary_json,
        executed_repo_root=args.executed_repo_root,
    )
    lane = esam_summary_as_lane(summary)

    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    json_path = output_dir / "esam_output_summary.json"
    lane_path = output_dir / "esam_lane.json"
    md_path = output_dir / "esam_output_summary.md"
    json_path.write_text(json.dumps(summary, indent=2) + "\n")
    lane_path.write_text(json.dumps(lane, indent=2) + "\n")
    md_path.write_text(render_esam_output_markdown(summary) + "\n")
    print(json_path)
    print(lane_path)
    print(md_path)


if __name__ == "__main__":
    main()
