from __future__ import annotations


def build_phase4_readiness(
    *,
    mega_summary: dict[str, object],
    robustness_summary: dict[str, object],
    observation_summary: dict[str, object],
    proxy_review: dict[str, object] | None = None,
    has_main_table_candidate: bool,
    has_ablation_table_candidate: bool,
    has_worst_best_analysis: bool,
    has_failure_casebook: bool,
    has_representative_casebook: bool,
    has_external_baseline_matrix: bool,
) -> dict[str, object]:
    readiness = {
        "scene_count": int(mega_summary.get("scene_count", 0)),
        "real_observation_report_coverage": int(observation_summary.get("report_coverage", 0)),
        "all_old_proxy_scenes_pass": bool(mega_summary.get("all_scenes_pass", False)),
        "all_old_proxy_regimes_pass": bool(robustness_summary.get("all_regimes_pass", False)),
        "has_main_table_candidate": has_main_table_candidate,
        "has_ablation_table_candidate": has_ablation_table_candidate,
        "has_worst_best_analysis": has_worst_best_analysis,
        "has_failure_casebook": has_failure_casebook,
        "has_representative_casebook": has_representative_casebook,
        "has_external_baseline_matrix": has_external_baseline_matrix,
        "legacy_proxy_reference_only_candidate": bool((proxy_review or {}).get("legacy_proxy_reference_only_candidate", False)),
    }
    readiness["candidate_package_complete"] = all(
        [
            readiness["real_observation_report_coverage"] > 0,
            has_main_table_candidate,
            has_ablation_table_candidate,
            has_worst_best_analysis,
            has_failure_casebook,
            has_representative_casebook,
            has_external_baseline_matrix,
        ]
    )
    readiness["paper_grade_candidate"] = (
        readiness["candidate_package_complete"]
        and (
            (
                readiness["all_old_proxy_scenes_pass"]
                and readiness["all_old_proxy_regimes_pass"]
            )
            or readiness["legacy_proxy_reference_only_candidate"]
        )
    )
    readiness["remaining_gap"] = []
    if not readiness["candidate_package_complete"]:
        readiness["remaining_gap"].append("candidate package artifacts are incomplete")
    if not readiness["all_old_proxy_scenes_pass"] and not readiness["legacy_proxy_reference_only_candidate"]:
        readiness["remaining_gap"].append("old proxy scene pass gate still fails")
    if not readiness["all_old_proxy_regimes_pass"] and not readiness["legacy_proxy_reference_only_candidate"]:
        readiness["remaining_gap"].append("old proxy regime pass gate still fails")
    if readiness["legacy_proxy_reference_only_candidate"]:
        readiness["remaining_gap"].append("legacy proxy gates have been downgraded to historical reference only")
    return readiness


def render_phase4_readiness_markdown(readiness: dict[str, object]) -> str:
    lines = [
        "# Phase 4 Readiness Summary",
        "",
        f"- Scene coverage: {readiness['scene_count']}",
        f"- Observation-grounded report coverage: {readiness['real_observation_report_coverage']}",
        f"- Main table candidate: {'Yes' if readiness['has_main_table_candidate'] else 'No'}",
        f"- Ablation table candidate: {'Yes' if readiness['has_ablation_table_candidate'] else 'No'}",
        f"- Worst/best analysis: {'Yes' if readiness['has_worst_best_analysis'] else 'No'}",
        f"- Failure casebook: {'Yes' if readiness['has_failure_casebook'] else 'No'}",
        f"- Representative casebook: {'Yes' if readiness['has_representative_casebook'] else 'No'}",
        f"- External baseline matrix: {'Yes' if readiness['has_external_baseline_matrix'] else 'No'}",
        f"- Old proxy scenes pass: {'Yes' if readiness['all_old_proxy_scenes_pass'] else 'No'}",
        f"- Old proxy regimes pass: {'Yes' if readiness['all_old_proxy_regimes_pass'] else 'No'}",
        f"- Legacy proxy gates are reference-only candidate: {'Yes' if readiness['legacy_proxy_reference_only_candidate'] else 'No'}",
        f"- Candidate package complete: {'Yes' if readiness['candidate_package_complete'] else 'No'}",
        f"- Paper-grade candidate: {'Yes' if readiness['paper_grade_candidate'] else 'No'}",
        "",
        "## Remaining gap",
        "",
    ]
    if readiness["remaining_gap"]:
        for item in readiness["remaining_gap"]:
            lines.append(f"- {item}")
    else:
        lines.append("- none")
    lines.append("")
    return "\n".join(lines)
