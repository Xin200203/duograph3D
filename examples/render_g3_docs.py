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


def main() -> None:
    parser = argparse.ArgumentParser(description="Render G3 markdown docs from a G2 suite summary JSON")
    parser.add_argument("summary_json")
    parser.add_argument("--output-dir", default="outputs_g3")
    args = parser.parse_args()

    summary = json.loads(Path(args.summary_json).read_text())
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    files = {
        "results-matrix.md": render_results_matrix_markdown(summary),
        "nearest-neighbor-defense.md": render_nearest_neighbor_defense_markdown(summary),
        "reviewer-attack-matrix.md": render_reviewer_attack_matrix_markdown(summary),
        "failure-taxonomy.md": render_failure_taxonomy_markdown(summary),
        "g3-defense-table.md": render_g3_defense_table_markdown(summary),
    }
    for name, content in files.items():
        (output_dir / name).write_text(content + "\n")
    for name in files:
        print(output_dir / name)


if __name__ == "__main__":
    main()
