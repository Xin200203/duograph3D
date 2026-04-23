from __future__ import annotations

import argparse
import json
from pathlib import Path

from duograph3d.deva_contract import export_replica_deva_contract_batch
from duograph3d.presets import REPLICA_SCENES
from duograph3d.remote_config import RemoteExperimentPaths


def main() -> None:
    parser = argparse.ArgumentParser(description="Export the Replica pilot split into a DEVA-style offline contract scaffold")
    parser.add_argument("--output-dir", default="outputs_deva_pilot")
    parser.add_argument("--limit", type=int, default=6)
    parser.add_argument("--allow-placeholder-canvas", action="store_true")
    parser.add_argument("--scenes", nargs="*", default=REPLICA_SCENES)
    args = parser.parse_args()

    paths = RemoteExperimentPaths()
    scene_roots = [paths.replica_root / scene for scene in args.scenes]
    summary = export_replica_deva_contract_batch(
        scene_roots,
        args.output_dir,
        limit=args.limit,
        allow_placeholder_canvas=args.allow_placeholder_canvas,
    )
    summary_path = Path(args.output_dir) / "deva_pilot_summary.json"
    summary_path.write_text(json.dumps(summary, indent=2) + "\n")
    print(summary_path)


if __name__ == "__main__":
    main()
