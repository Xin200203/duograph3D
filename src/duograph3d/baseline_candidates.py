from __future__ import annotations

import json
from collections import defaultdict
from pathlib import Path

from .baseline_adapter import normalize_baseline_lane


def build_candidate_lanes(report: dict[str, object]) -> list[dict[str, object]]:
    dataset = str(report["dataset"])
    scene = str(report["scene"])
    branches = report["branches"]
    candidates: list[dict[str, object]] = []
    counter = branches.get("full_fair_counterfactual")
    if counter:
        candidates.append(
            normalize_baseline_lane(
                baseline_id="temporal_only_strong_candidate",
                label="Temporal-only strong candidate",
                dataset=dataset,
                scene=scene,
                family="strong_internal_candidate",
                faithfulness="adapter_wrapped_internal",
                primary_metric_name="track_fragmentation",
                primary_metric_value=float(counter["track_fragmentation"]),
                metrics={
                    "track_fragmentation": float(counter["track_fragmentation"]),
                    "memory_node_count": float(counter["memory_node_count"]),
                    "memory_authority_events": float(counter["memory_authority_events"]),
                },
                notes=["Derived from the full fair counterfactual branch as a stronger temporal-only comparison candidate."],
            )
        )
    dense = branches.get("dense_authority_export_rival")
    if dense:
        candidates.append(
            normalize_baseline_lane(
                baseline_id="dense_owner_strong_candidate",
                label="Dense-owner strong candidate",
                dataset=dataset,
                scene=scene,
                family="strong_internal_candidate",
                faithfulness="adapter_wrapped_internal",
                primary_metric_name="memory_node_count",
                primary_metric_value=float(dense["memory_node_count"]),
                metrics={
                    "track_fragmentation": float(dense["track_fragmentation"]),
                    "memory_node_count": float(dense["memory_node_count"]),
                    "memory_authority_events": float(dense["memory_authority_events"]),
                },
                notes=["Derived from the dense-authority export branch as a stronger dense-owner comparison candidate."],
            )
        )
    return candidates


def summarize_candidate_lanes(report_paths: list[str]) -> dict[str, object]:
    coverage = 0
    rows_by_id: dict[str, list[dict[str, object]]] = defaultdict(list)
    for report_path in report_paths:
        report = json.loads(Path(report_path).read_text())
        lanes = build_candidate_lanes(report)
        coverage += 1
        for lane in lanes:
            rows_by_id[str(lane["baseline_id"])].append(lane)
    summary_rows: list[dict[str, object]] = []
    for baseline_id, lanes in sorted(rows_by_id.items()):
        summary_rows.append(
            {
                "baseline_id": baseline_id,
                "label": lanes[0]["label"],
                "family": lanes[0]["family"],
                "coverage": len(lanes),
                "avg_primary_metric_value": round(
                    sum(float(lane["primary_metric_value"]) for lane in lanes) / max(len(lanes), 1),
                    2,
                ),
            }
        )
    return {"report_coverage": coverage, "rows": summary_rows}


def render_candidate_lane_summary_markdown(summary: dict[str, object]) -> str:
    lines = [
        "# Stronger Baseline Candidate Summary",
        "",
        f"- Report coverage: {summary['report_coverage']}",
        "",
        "| Candidate lane | Family | Coverage | Avg primary metric |",
        "| --- | --- | ---: | ---: |",
    ]
    for row in summary["rows"]:
        lines.append(
            f"| {row['label']} | {row['family']} | {row['coverage']} | {row['avg_primary_metric_value']:.2f} |"
        )
    lines.append("")
    return "\n".join(lines)
