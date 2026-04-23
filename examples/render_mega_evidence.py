from __future__ import annotations

import argparse
import json
from pathlib import Path

from duograph3d.g3_docs import (
    render_failure_taxonomy_markdown,
    render_g3_defense_table_markdown,
    render_nearest_neighbor_defense_markdown,
    render_results_matrix_markdown,
    render_reviewer_attack_matrix_markdown,
)
from duograph3d.io_utils import write_json
from duograph3d.reporting import render_g2_table_markdown
from duograph3d.summary_merge import merge_suite_summaries


def main() -> None:
    parser = argparse.ArgumentParser(description="Merge multiple suite summaries into a mega evidence package")
    parser.add_argument("summaries", nargs="+")
    parser.add_argument("--output-dir", default="outputs_mega")
    args = parser.parse_args()

    suite_summaries = [json.loads(Path(path).read_text()) for path in args.summaries]
    merged = merge_suite_summaries(suite_summaries)
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    merged_json = output_dir / "mega_suite_summary.json"
    merged_md = output_dir / "mega_g2_evidence.md"
    results_md = output_dir / "results-matrix.md"
    defense_md = output_dir / "nearest-neighbor-defense.md"
    attack_md = output_dir / "reviewer-attack-matrix.md"
    failure_md = output_dir / "failure-taxonomy.md"
    g3_md = output_dir / "g3-defense-table.md"

    write_json(merged, merged_json)
    merged_md.write_text(render_g2_table_markdown(merged, args.summaries) + "\n")
    results_md.write_text(render_results_matrix_markdown(merged) + "\n")
    defense_md.write_text(render_nearest_neighbor_defense_markdown(merged) + "\n")
    attack_md.write_text(render_reviewer_attack_matrix_markdown(merged) + "\n")
    failure_md.write_text(render_failure_taxonomy_markdown(merged) + "\n")
    g3_md.write_text(render_g3_defense_table_markdown(merged) + "\n")

    for path in [merged_json, merged_md, results_md, defense_md, attack_md, failure_md, g3_md]:
        print(path)


if __name__ == "__main__":
    main()
