from __future__ import annotations

import argparse
import json
from pathlib import Path

from duograph3d.io_utils import write_json
from duograph3d.statistics import compute_row_statistics, render_statistics_markdown


def main() -> None:
    parser = argparse.ArgumentParser(description="Render statistical summary from mega suite summary")
    parser.add_argument("mega_summary")
    parser.add_argument("--output-dir", default="outputs_stats")
    args = parser.parse_args()

    mega = json.loads(Path(args.mega_summary).read_text())
    stats = compute_row_statistics(mega)
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    json_path = output_dir / "statistics_summary.json"
    md_path = output_dir / "statistics_summary.md"
    write_json(stats, json_path)
    md_path.write_text(render_statistics_markdown(mega, stats) + "\n")
    print(json_path)
    print(md_path)


if __name__ == "__main__":
    main()
