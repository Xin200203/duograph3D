from __future__ import annotations

import argparse
import json
from pathlib import Path

from duograph3d.external_comparison import build_external_comparison, load_json, render_external_comparison_markdown


def main() -> None:
    parser = argparse.ArgumentParser(description="Render a side-by-side comparison seed table for DuoGraph3D vs an executed external baseline")
    parser.add_argument("duo_summary")
    parser.add_argument("external_summary")
    parser.add_argument("--output-dir", default="outputs_external_comparison")
    args = parser.parse_args()

    duo = load_json(args.duo_summary)
    external = load_json(args.external_summary)
    summary = build_external_comparison(duo, external)
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    json_path = output_dir / "external_comparison_summary.json"
    md_path = output_dir / "external_comparison_summary.md"
    json_path.write_text(json.dumps(summary, indent=2) + "\n")
    md_path.write_text(render_external_comparison_markdown(summary) + "\n")
    print(json_path)
    print(md_path)


if __name__ == "__main__":
    main()
