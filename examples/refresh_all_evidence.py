from __future__ import annotations

import argparse
from pathlib import Path
import shutil

from duograph3d.casebook import load_json
from duograph3d.baseline_candidates import summarize_candidate_lanes, render_candidate_lane_summary_markdown
from duograph3d.baseline_audit import summarize_baseline_audits, render_baseline_audit_summary_markdown
from duograph3d.presets import build_all_suite_specs, expected_scene_count
from duograph3d.suite_runner import run_suite
from duograph3d.io_utils import write_json
from duograph3d.package_docs import render_g3_package_markdown
from duograph3d.readiness import build_g3_readiness, render_g3_readiness_markdown
from duograph3d.reporting import render_g2_table_markdown
from duograph3d.robustness import compare_suite_summaries, render_robustness_markdown
from duograph3d.summary_merge import merge_suite_summaries
from duograph3d.g3_docs import render_results_matrix_markdown, render_nearest_neighbor_defense_markdown, render_reviewer_attack_matrix_markdown, render_failure_taxonomy_markdown, render_g3_defense_table_markdown
from duograph3d.g4_docs import render_paper_outline, render_intro_claim_stack, render_camera_ready_risk_list, render_extension_backlog, render_submission_readiness
from duograph3d.casebook import build_casebook, render_casebook_markdown
from duograph3d.statistics import compute_row_statistics, render_statistics_markdown
from duograph3d.metadata_grounding import summarize_metadata_grounding, render_metadata_grounding_markdown
from duograph3d.paper_metrics import summarize_paper_metrics, render_paper_metrics_markdown
from duograph3d.paper_table import build_paper_main_table, render_paper_main_table_markdown


def main() -> None:
    parser = argparse.ArgumentParser(description='Refresh the full DuoGraph3D evidence package')
    parser.add_argument('--output-root', default='refresh_outputs')
    args = parser.parse_args()

    output_root = Path(args.output_root)
    if output_root.exists():
        shutil.rmtree(output_root)
    output_root.mkdir(parents=True, exist_ok=True)

    suite_paths = []
    suite_summaries = []
    for spec in build_all_suite_specs():
        aggregate_path, _md_path = run_suite(spec, output_root)
        suite_paths.append(str(aggregate_path.parent))
        suite_summaries.append(load_json(aggregate_path))

    mega = merge_suite_summaries(suite_summaries)
    mega_dir = output_root / 'mega'
    mega_dir.mkdir(exist_ok=True)
    write_json(mega, mega_dir / 'mega_suite_summary.json')
    (mega_dir / 'mega_g2_evidence.md').write_text(render_g2_table_markdown(mega, [str(Path(path) / 'g2_suite_summary.json') for path in suite_paths]) + '\n')
    (mega_dir / 'results-matrix.md').write_text(render_results_matrix_markdown(mega) + '\n')
    (mega_dir / 'nearest-neighbor-defense.md').write_text(render_nearest_neighbor_defense_markdown(mega) + '\n')
    (mega_dir / 'reviewer-attack-matrix.md').write_text(render_reviewer_attack_matrix_markdown(mega) + '\n')
    (mega_dir / 'failure-taxonomy.md').write_text(render_failure_taxonomy_markdown(mega) + '\n')
    (mega_dir / 'g3-defense-table.md').write_text(render_g3_defense_table_markdown(mega) + '\n')

    robustness = compare_suite_summaries([(Path(path).name, summary) for path, summary in zip(suite_paths, suite_summaries)])
    robustness_dir = output_root / 'robustness'
    robustness_dir.mkdir(exist_ok=True)
    write_json(robustness, robustness_dir / 'robustness_summary.json')
    (robustness_dir / 'robustness_summary.md').write_text(render_robustness_markdown(robustness) + '\n')

    casebook = build_casebook(mega, suite_paths)
    metadata_summary = summarize_metadata_grounding(suite_paths)
    casebook_dir = output_root / 'casebook'
    casebook_dir.mkdir(exist_ok=True)
    write_json(casebook, casebook_dir / 'casebook.json')
    (casebook_dir / 'casebook.md').write_text(render_casebook_markdown(casebook) + '\n')

    stats = compute_row_statistics(mega)
    metadata_dir = output_root / 'metadata'
    metadata_dir.mkdir(exist_ok=True)
    write_json(metadata_summary, metadata_dir / 'metadata_grounding.json')
    (metadata_dir / 'metadata_grounding.md').write_text(render_metadata_grounding_markdown(metadata_summary) + '\n')
    stats_dir = output_root / 'stats'
    stats_dir.mkdir(exist_ok=True)
    write_json(stats, stats_dir / 'statistics_summary.json')
    (stats_dir / 'statistics_summary.md').write_text(render_statistics_markdown(mega, stats) + '\n')

    baseline_audit_paths = []
    for suite_path in suite_paths:
        baseline_audit_paths.extend(str(path) for path in Path(suite_path).glob('bounded_slice_*.json'))
    baseline_audit_summary = summarize_baseline_audits(baseline_audit_paths)
    baseline_audit_dir = output_root / 'baseline_audit'
    baseline_audit_dir.mkdir(exist_ok=True)
    write_json(baseline_audit_summary, baseline_audit_dir / 'baseline_audit_summary.json')
    (baseline_audit_dir / 'baseline_audit_summary.md').write_text(render_baseline_audit_summary_markdown(baseline_audit_summary) + '\n')

    baseline_candidate_summary = summarize_candidate_lanes(baseline_audit_paths)
    baseline_candidates_dir = output_root / 'baseline_candidates'
    baseline_candidates_dir.mkdir(exist_ok=True)
    write_json(baseline_candidate_summary, baseline_candidates_dir / 'baseline_candidate_summary.json')
    (baseline_candidates_dir / 'baseline_candidate_summary.md').write_text(render_candidate_lane_summary_markdown(baseline_candidate_summary) + '\n')

    paper_metrics_summary = summarize_paper_metrics(baseline_audit_paths)
    paper_metrics_dir = output_root / 'paper_metrics'
    paper_metrics_dir.mkdir(exist_ok=True)
    write_json(paper_metrics_summary, paper_metrics_dir / 'paper_metrics_summary.json')
    (paper_metrics_dir / 'paper_metrics_summary.md').write_text(render_paper_metrics_markdown(paper_metrics_summary) + '\n')
    paper_main_table = build_paper_main_table(paper_metrics_summary)
    write_json(paper_main_table, paper_metrics_dir / 'paper_main_table.json')
    (paper_metrics_dir / 'paper_main_table.md').write_text(render_paper_main_table_markdown(paper_main_table) + '\n')

    package_dir = output_root / 'package'
    package_dir.mkdir(exist_ok=True)
    readiness = build_g3_readiness(mega, robustness, casebook, metadata_summary)
    write_json(readiness, package_dir / 'g3_readiness.json')
    (package_dir / 'g3_readiness.md').write_text(render_g3_readiness_markdown(readiness) + '\n')
    (package_dir / 'g3_evidence_package.md').write_text(
        render_g3_package_markdown(
            mega_summary=mega,
            robustness_summary=robustness,
            casebook=casebook,
            statistics_summary=stats,
            paper_metrics_summary=paper_metrics_summary,
            metadata_summary=metadata_summary,
        ) + '\n'
    )

    g4_dir = output_root / 'g4'
    g4_dir.mkdir(exist_ok=True)
    (g4_dir / 'paper-outline.md').write_text(render_paper_outline(mega, readiness) + '\n')
    (g4_dir / 'intro-claim-stack.md').write_text(render_intro_claim_stack(mega, readiness) + '\n')
    (g4_dir / 'camera-ready-risk-list.md').write_text(render_camera_ready_risk_list(readiness) + '\n')
    (g4_dir / 'post-v1-extension-backlog.md').write_text(render_extension_backlog(mega) + '\n')
    (g4_dir / 'submission-readiness-summary.md').write_text(render_submission_readiness(readiness, mega) + '\n')

    print('expected_scene_count={}'.format(expected_scene_count()))
    print('actual_scene_count={}'.format(mega['scene_count']))
    print('all_scenes_pass={}'.format(mega['all_scenes_pass']))
    print('all_regimes_pass={}'.format(robustness['all_regimes_pass']))


if __name__ == "__main__":
    main()
