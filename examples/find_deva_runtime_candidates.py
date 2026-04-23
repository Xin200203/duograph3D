from __future__ import annotations

import argparse
import json
from pathlib import Path

from duograph3d.deva_runtime import find_deva_runtime_candidates, render_deva_runtime_candidates_markdown


def main() -> None:
    parser = argparse.ArgumentParser(description="Scan for Python executables that satisfy DEVA runtime imports")
    parser.add_argument("search_roots", nargs="+")
    parser.add_argument("--output-dir", default="outputs_deva_runtime_candidates")
    parser.add_argument("--max-depth", type=int, default=3)
    args = parser.parse_args()

    summary = find_deva_runtime_candidates(args.search_roots, max_depth=args.max_depth)
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    json_path = output_dir / "deva_runtime_candidates.json"
    md_path = output_dir / "deva_runtime_candidates.md"
    json_path.write_text(json.dumps(summary, indent=2) + "\n")
    md_path.write_text(render_deva_runtime_candidates_markdown(summary) + "\n")
    print(json_path)
    print(md_path)


if __name__ == "__main__":
    main()
