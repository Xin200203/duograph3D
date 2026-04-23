from __future__ import annotations

import argparse
import json
from pathlib import Path

from duograph3d.deva_contract import export_replica_deva_contract


def main() -> None:
    parser = argparse.ArgumentParser(description="Export a Replica scene into a DEVA-style offline contract scaffold")
    parser.add_argument("scene_root")
    parser.add_argument("--output-dir", default="outputs_deva_contract")
    parser.add_argument("--limit", type=int, default=6)
    parser.add_argument("--allow-placeholder-canvas", action="store_true")
    args = parser.parse_args()

    summary = export_replica_deva_contract(
        args.scene_root,
        args.output_dir,
        limit=args.limit,
        allow_placeholder_canvas=args.allow_placeholder_canvas,
    )
    summary_path = Path(args.output_dir) / "deva_contract_summary.json"
    summary_path.write_text(json.dumps(summary, indent=2) + "\n")
    print(summary_path)


if __name__ == "__main__":
    main()
