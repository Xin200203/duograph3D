from __future__ import annotations

import argparse
import json
from pathlib import Path

from duograph3d.observation_metrics import (
    render_observation_grounded_metrics_markdown,
    summarize_observation_grounded_metrics,
)


def main() -> None:
    parser = argparse.ArgumentParser(description="Render observation-grounded metric summaries from bounded-slice reports")
    parser.add_argument("report_paths", nargs="+")
    parser.add_argument("--output-dir", default="outputs_observation_metrics")
    args = parser.parse_args()

    summary = summarize_observation_grounded_metrics(args.report_paths)
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    json_path = output_dir / "observation_metrics_summary.json"
    md_path = output_dir / "observation_metrics_summary.md"
    json_path.write_text(json.dumps(summary, indent=2) + "\n")
    md_path.write_text(render_observation_grounded_metrics_markdown(summary) + "\n")
    print(json_path)
    print(md_path)


if __name__ == "__main__":
    main()
