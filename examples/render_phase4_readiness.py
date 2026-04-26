from __future__ import annotations

import argparse
import json
from pathlib import Path

from duograph3d.phase4_readiness import build_phase4_readiness, render_phase4_readiness_markdown


def main() -> None:
    parser = argparse.ArgumentParser(description="Render a Phase 4 readiness summary")
    parser.add_argument("mega_summary_json")
    parser.add_argument("robustness_summary_json")
    parser.add_argument("observation_metrics_summary_json")
    parser.add_argument("--proxy-review", default=None)
    parser.add_argument("--main-table", required=True)
    parser.add_argument("--ablation-table", required=True)
    parser.add_argument("--worst-best", required=True)
    parser.add_argument("--failure-casebook", required=True)
    parser.add_argument("--representative-casebook", required=True)
    parser.add_argument("--external-baseline-matrix", required=True)
    parser.add_argument("--output-dir", default="outputs_phase4_readiness")
    args = parser.parse_args()

    mega = json.loads(Path(args.mega_summary_json).read_text())
    robust = json.loads(Path(args.robustness_summary_json).read_text())
    obs = json.loads(Path(args.observation_metrics_summary_json).read_text())
    proxy_review = json.loads(Path(args.proxy_review).read_text()) if args.proxy_review else None
    readiness = build_phase4_readiness(
        mega_summary=mega,
        robustness_summary=robust,
        observation_summary=obs,
        proxy_review=proxy_review,
        has_main_table_candidate=Path(args.main_table).exists(),
        has_ablation_table_candidate=Path(args.ablation_table).exists(),
        has_worst_best_analysis=Path(args.worst_best).exists(),
        has_failure_casebook=Path(args.failure_casebook).exists(),
        has_representative_casebook=Path(args.representative_casebook).exists(),
        has_external_baseline_matrix=Path(args.external_baseline_matrix).exists(),
    )

    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "phase4_readiness.json").write_text(json.dumps(readiness, indent=2) + "\n")
    (output_dir / "phase4_readiness.md").write_text(render_phase4_readiness_markdown(readiness) + "\n")
    print(output_dir / "phase4_readiness.json")
    print(output_dir / "phase4_readiness.md")


if __name__ == "__main__":
    main()
