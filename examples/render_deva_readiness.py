from __future__ import annotations

import argparse
import json
from pathlib import Path

from duograph3d.deva_readiness import render_deva_readiness_markdown, summarize_deva_contract


def main() -> None:
    parser = argparse.ArgumentParser(description="Render a readiness summary for a DEVA contract export")
    parser.add_argument("contract_root")
    parser.add_argument("--output-dir", default="outputs_deva_readiness")
    args = parser.parse_args()

    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    summary = summarize_deva_contract(args.contract_root)
    if summary["scene_count"] == 0:
        raise RuntimeError(f"No DEVA contract scenes found under {args.contract_root}")
    json_path = output_dir / "deva_readiness_summary.json"
    md_path = output_dir / "deva_readiness_summary.md"
    json_path.write_text(json.dumps(summary, indent=2) + "\n")
    md_path.write_text(render_deva_readiness_markdown(summary) + "\n")
    print(json_path)
    print(md_path)


if __name__ == "__main__":
    main()
