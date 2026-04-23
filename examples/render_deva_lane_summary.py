from __future__ import annotations

import argparse
import json
from pathlib import Path

from duograph3d.deva_results import deva_scene_as_lane, summarize_deva_output
from duograph3d.baseline_adapter import render_baseline_lane_markdown


def main() -> None:
    parser = argparse.ArgumentParser(description="Render normalized DEVA lane results from executed DEVA output")
    parser.add_argument("output_root")
    parser.add_argument("--dataset", default="replica")
    parser.add_argument("--output-dir", default="outputs_deva_lane_summary")
    args = parser.parse_args()

    summary = summarize_deva_output(args.output_root)
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    aggregate_json = output_dir / "deva_lane_summary.json"
    aggregate_json.write_text(json.dumps(summary, indent=2) + "\n")
    md_dir = output_dir / "lanes"
    md_dir.mkdir(exist_ok=True)
    for row in summary["rows"]:
        lane = deva_scene_as_lane(row, dataset=args.dataset)
        lane_path = md_dir / f"{row['scene']}.json"
        lane_md = md_dir / f"{row['scene']}.md"
        lane_path.write_text(json.dumps(lane, indent=2) + "\n")
        lane_md.write_text(render_baseline_lane_markdown(lane) + "\n")
    print(aggregate_json)
    print(md_dir)


if __name__ == "__main__":
    main()
