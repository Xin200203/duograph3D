from __future__ import annotations

import argparse
import json
from pathlib import Path

from duograph3d.phase4_proxy_review import build_phase4_proxy_review, render_phase4_proxy_review_markdown


def main() -> None:
    parser = argparse.ArgumentParser(description="Render a Phase 4 legacy-proxy review from bounded-slice reports")
    parser.add_argument("report_paths", nargs="+")
    parser.add_argument("--output-dir", default="outputs_phase4_proxy_review")
    args = parser.parse_args()

    review = build_phase4_proxy_review(args.report_paths)
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "phase4_proxy_review.json").write_text(json.dumps(review, indent=2) + "\n")
    (output_dir / "phase4_proxy_review.md").write_text(render_phase4_proxy_review_markdown(review) + "\n")
    print(output_dir / "phase4_proxy_review.json")
    print(output_dir / "phase4_proxy_review.md")


if __name__ == "__main__":
    main()
