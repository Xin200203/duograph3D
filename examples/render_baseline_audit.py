from __future__ import annotations

import argparse
import json
from pathlib import Path

from duograph3d.baseline_audit import normalize_baseline_audit, render_baseline_audit_markdown


def main() -> None:
    parser = argparse.ArgumentParser(description="Render a baseline audit from a bounded-slice report")
    parser.add_argument("report", help="Path to bounded_slice_*.json")
    parser.add_argument("--output-dir", default="outputs_baseline_audit")
    args = parser.parse_args()

    report_path = Path(args.report)
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    report = json.loads(report_path.read_text())
    audit = normalize_baseline_audit(report)
    json_path = output_dir / "baseline_audit.json"
    md_path = output_dir / "baseline_audit.md"
    json_path.write_text(json.dumps(audit, indent=2) + "\n")
    md_path.write_text(render_baseline_audit_markdown(audit) + "\n")
    print(json_path)
    print(md_path)


if __name__ == "__main__":
    main()
