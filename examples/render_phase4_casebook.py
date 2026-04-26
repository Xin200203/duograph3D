from __future__ import annotations

import argparse
import json
from pathlib import Path

from duograph3d.phase4_casebook import build_phase4_representative_casebook, render_phase4_casebook_markdown


def main() -> None:
    parser = argparse.ArgumentParser(description="Render a Phase 4 representative casebook from bounded-slice reports")
    parser.add_argument("report_paths", nargs="+")
    parser.add_argument("--output-dir", default="outputs_phase4_casebook")
    args = parser.parse_args()

    casebook = build_phase4_representative_casebook(args.report_paths)
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "phase4_casebook.json").write_text(json.dumps(casebook, indent=2) + "\n")
    (output_dir / "phase4_casebook.md").write_text(render_phase4_casebook_markdown(casebook) + "\n")
    print(output_dir / "phase4_casebook.json")
    print(output_dir / "phase4_casebook.md")


if __name__ == "__main__":
    main()
