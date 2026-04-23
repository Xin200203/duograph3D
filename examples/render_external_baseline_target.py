from __future__ import annotations

import argparse
import json
from pathlib import Path

from duograph3d.external_baselines import deva_official_target, render_external_baseline_target_markdown


def main() -> None:
    parser = argparse.ArgumentParser(description="Render an external baseline target manifest")
    parser.add_argument("--repo-commit", required=True)
    parser.add_argument("--output-dir", default="outputs_external_baseline_target")
    args = parser.parse_args()

    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    target = deva_official_target(args.repo_commit)
    json_path = output_dir / "external_baseline_target.json"
    md_path = output_dir / "external_baseline_target.md"
    json_path.write_text(json.dumps(target, indent=2) + "\n")
    md_path.write_text(render_external_baseline_target_markdown(target) + "\n")
    print(json_path)
    print(md_path)


if __name__ == "__main__":
    main()
