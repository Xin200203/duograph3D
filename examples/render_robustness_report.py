from __future__ import annotations

import argparse
import json
from pathlib import Path

from duograph3d.io_utils import write_json
from duograph3d.robustness import compare_suite_summaries, render_robustness_markdown


def main() -> None:
    parser = argparse.ArgumentParser(description="Render a robustness report from multiple suite summaries")
    parser.add_argument("--suite", nargs=2, action="append", metavar=("REGIME", "SUMMARY_JSON"), required=True)
    parser.add_argument("--output-dir", default="outputs_robustness")
    args = parser.parse_args()

    named_summaries = []
    for regime, summary_path in args.suite:
        named_summaries.append((regime, json.loads(Path(summary_path).read_text())))

    report = compare_suite_summaries(named_summaries)
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    json_path = output_dir / "robustness_summary.json"
    md_path = output_dir / "robustness_summary.md"
    write_json(report, json_path)
    md_path.write_text(render_robustness_markdown(report) + "\n")
    print(json_path)
    print(md_path)


if __name__ == "__main__":
    main()
