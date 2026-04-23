from __future__ import annotations

import argparse
import json
from pathlib import Path

from duograph3d.deva_results import render_deva_output_markdown, summarize_deva_output


def main() -> None:
    parser = argparse.ArgumentParser(description="Render a summary from executed DEVA output JSONFiles")
    parser.add_argument("output_root")
    parser.add_argument("--output-dir", default="outputs_deva_result_summary")
    args = parser.parse_args()

    summary = summarize_deva_output(args.output_root)
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    json_path = output_dir / "deva_output_summary.json"
    md_path = output_dir / "deva_output_summary.md"
    json_path.write_text(json.dumps(summary, indent=2) + "\n")
    md_path.write_text(render_deva_output_markdown(summary) + "\n")
    print(json_path)
    print(md_path)


if __name__ == "__main__":
    main()
