from __future__ import annotations

import argparse
import json
from pathlib import Path

from duograph3d.phase4_analysis import (
    build_failure_casebook,
    build_phase4_ablation_table,
    build_phase4_main_table,
    build_worst_best_analysis,
    render_failure_casebook_markdown,
    render_phase4_ablation_table_markdown,
    render_phase4_main_table_markdown,
    render_worst_best_markdown,
)


def main() -> None:
    parser = argparse.ArgumentParser(description="Render Phase 4 main-table and analysis artifacts from observation metrics summary")
    parser.add_argument("observation_metrics_summary_json")
    parser.add_argument("--output-dir", default="outputs_phase4_analysis")
    args = parser.parse_args()

    summary = json.loads(Path(args.observation_metrics_summary_json).read_text())
    table = build_phase4_main_table(summary)
    ablation = build_phase4_ablation_table(summary)
    worst_best = build_worst_best_analysis(summary)
    casebook = build_failure_casebook(summary)

    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "phase4_main_table_candidate.json").write_text(json.dumps(table, indent=2) + "\n")
    (output_dir / "phase4_main_table_candidate.md").write_text(render_phase4_main_table_markdown(table) + "\n")
    (output_dir / "phase4_ablation_table_candidate.json").write_text(json.dumps(ablation, indent=2) + "\n")
    (output_dir / "phase4_ablation_table_candidate.md").write_text(render_phase4_ablation_table_markdown(ablation) + "\n")
    (output_dir / "phase4_worst_best_analysis.json").write_text(json.dumps(worst_best, indent=2) + "\n")
    (output_dir / "phase4_worst_best_analysis.md").write_text(render_worst_best_markdown(worst_best) + "\n")
    (output_dir / "phase4_failure_casebook.json").write_text(json.dumps(casebook, indent=2) + "\n")
    (output_dir / "phase4_failure_casebook.md").write_text(render_failure_casebook_markdown(casebook) + "\n")
    print(output_dir / "phase4_main_table_candidate.json")
    print(output_dir / "phase4_ablation_table_candidate.json")
    print(output_dir / "phase4_worst_best_analysis.json")
    print(output_dir / "phase4_failure_casebook.json")


if __name__ == "__main__":
    main()
