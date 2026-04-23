from __future__ import annotations

import argparse
import json
from pathlib import Path

from duograph3d.package_docs import render_g3_package_markdown


def main() -> None:
    parser = argparse.ArgumentParser(description="Render a single G3 evidence package markdown from mega/robustness/casebook/statistics JSON")
    parser.add_argument("mega_summary")
    parser.add_argument("robustness_summary")
    parser.add_argument("casebook_json")
    parser.add_argument("statistics_json")
    parser.add_argument("--output", default="g3_evidence_package.md")
    args = parser.parse_args()

    mega = json.loads(Path(args.mega_summary).read_text())
    robustness = json.loads(Path(args.robustness_summary).read_text())
    casebook = json.loads(Path(args.casebook_json).read_text())
    stats = json.loads(Path(args.statistics_json).read_text())
    metadata = json.loads(Path(args.metadata_json).read_text()) if args.metadata_json else None

    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        render_g3_package_markdown(
            mega_summary=mega,
            robustness_summary=robustness,
            casebook=casebook,
            statistics_summary=stats,
            metadata_summary=metadata,
        )
        + "\n"
    )
    print(output)


if __name__ == "__main__":
    main()
