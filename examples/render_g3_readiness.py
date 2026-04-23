from __future__ import annotations

import argparse
import json
from pathlib import Path

from duograph3d.io_utils import write_json
from duograph3d.readiness import build_g3_readiness, render_g3_readiness_markdown


def main() -> None:
    parser = argparse.ArgumentParser(description="Render a G3 readiness summary from mega/robustness/casebook JSON")
    parser.add_argument("mega_summary")
    parser.add_argument("robustness_summary")
    parser.add_argument("casebook_json")
    parser.add_argument("--output-dir", default="outputs_readiness")
    args = parser.parse_args()

    mega = json.loads(Path(args.mega_summary).read_text())
    robustness = json.loads(Path(args.robustness_summary).read_text())
    casebook = json.loads(Path(args.casebook_json).read_text())
    readiness = build_g3_readiness(mega, robustness, casebook)

    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    json_path = output_dir / "g3_readiness.json"
    md_path = output_dir / "g3_readiness.md"
    write_json(readiness, json_path)
    md_path.write_text(render_g3_readiness_markdown(readiness) + "\n")
    print(json_path)
    print(md_path)


if __name__ == "__main__":
    main()
