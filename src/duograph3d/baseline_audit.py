from __future__ import annotations

import json
from collections import Counter, defaultdict
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class BaselineAuditSpec:
    baseline_id: str
    label: str
    family: str
    authority_owner: str
    temporal_mode: str
    faithfulness: str
    notes: str


INTERNAL_BASELINE_SPECS: dict[str, BaselineAuditSpec] = {
    "single_layer_rival": BaselineAuditSpec(
        baseline_id="single_layer_rival",
        label="Single-layer rival",
        family="internal_structural",
        authority_owner="memory",
        temporal_mode="deva_style",
        faithfulness="structural proxy",
        notes="Removes the current-evidence graph layer and commits per evidence item.",
    ),
    "dense_authority_export_rival": BaselineAuditSpec(
        baseline_id="dense_authority_export_rival",
        label="Dense-authority export rival",
        family="internal_structural",
        authority_owner="dense",
        temporal_mode="naive_framewise",
        faithfulness="structural proxy",
        notes="Dense owner keeps state through update/keepalive/retire and exports memory at the end.",
    ),
    "full_fair_counterfactual": BaselineAuditSpec(
        baseline_id="full_fair_counterfactual",
        label="Full fair counterfactual",
        family="internal_structural",
        authority_owner="memory",
        temporal_mode="deva_style",
        faithfulness="structural proxy",
        notes="Stronger single-layer counterfactual with larger candidate budget and lower threshold.",
    ),
    "temporal_none": BaselineAuditSpec(
        baseline_id="temporal_none",
        label="Temporal none",
        family="temporal_ablation",
        authority_owner="memory",
        temporal_mode="none",
        faithfulness="internal ablation",
        notes="No temporal propagation.",
    ),
    "temporal_naive_framewise": BaselineAuditSpec(
        baseline_id="temporal_naive_framewise",
        label="Temporal naive framewise",
        family="temporal_ablation",
        authority_owner="memory",
        temporal_mode="naive_framewise",
        faithfulness="internal ablation",
        notes="Framewise temporal carry without DEVA-style support propagation.",
    ),
    "temporal_deva_style": BaselineAuditSpec(
        baseline_id="temporal_deva_style",
        label="Temporal DEVA-style",
        family="temporal_ablation",
        authority_owner="memory",
        temporal_mode="deva_style",
        faithfulness="internal ablation",
        notes="DEVA-style propagation branch used for temporal comparison.",
    ),
}


def normalize_baseline_audit(report: dict[str, object]) -> dict[str, object]:
    scene = str(report["scene"])
    dataset = str(report["dataset"])
    rows: list[dict[str, object]] = []
    for baseline_id, summary in report.get("branches", {}).items():
        if baseline_id == "duograph3d_full":
            continue
        spec = INTERNAL_BASELINE_SPECS.get(
            baseline_id,
            BaselineAuditSpec(
                baseline_id=baseline_id,
                label=baseline_id,
                family="unknown",
                authority_owner="unknown",
                temporal_mode="unknown",
                faithfulness="unclassified",
                notes="No audit spec registered.",
            ),
        )
        rows.append(
            {
                "baseline_id": baseline_id,
                "label": spec.label,
                "family": spec.family,
                "authority_owner": spec.authority_owner,
                "temporal_mode": spec.temporal_mode,
                "faithfulness": spec.faithfulness,
                "memory_nodes": summary["memory_node_count"],
                "track_fragmentation": summary["track_fragmentation"],
                "memory_authority_events": summary["memory_authority_events"],
                "notes": spec.notes,
            }
        )
    for baseline_id, summary in report.get("temporal_triplet", {}).items():
        spec = INTERNAL_BASELINE_SPECS.get(
            baseline_id,
            BaselineAuditSpec(
                baseline_id=baseline_id,
                label=baseline_id,
                family="unknown_temporal",
                authority_owner="unknown",
                temporal_mode=baseline_id,
                faithfulness="unclassified",
                notes="No temporal audit spec registered.",
            ),
        )
        rows.append(
            {
                "baseline_id": baseline_id,
                "label": spec.label,
                "family": spec.family,
                "authority_owner": spec.authority_owner,
                "temporal_mode": spec.temporal_mode,
                "faithfulness": spec.faithfulness,
                "memory_nodes": summary["memory_node_count"],
                "track_fragmentation": summary["track_fragmentation"],
                "memory_authority_events": summary["memory_authority_events"],
                "notes": spec.notes,
            }
        )
    return {"dataset": dataset, "scene": scene, "rows": rows}


def render_baseline_audit_markdown(audit: dict[str, object]) -> str:
    lines = [
        "# Baseline Audit",
        "",
        f"- Dataset: {audit['dataset']}",
        f"- Scene: {audit['scene']}",
        "",
        "| Baseline | Family | Authority owner | Temporal | Faithfulness | Memory nodes | Fragmentation | Memory authority | Notes |",
        "| --- | --- | --- | --- | --- | ---: | ---: | ---: | --- |",
    ]
    for row in audit["rows"]:
        lines.append(
            f"| {row['label']} | {row['family']} | {row['authority_owner']} | {row['temporal_mode']} | {row['faithfulness']} | "
            f"{row['memory_nodes']} | {row['track_fragmentation']} | {row['memory_authority_events']} | {row['notes']} |"
        )
    lines.append("")
    return "\n".join(lines)


def summarize_baseline_audits(report_paths: list[str]) -> dict[str, object]:
    baseline_counts: dict[str, int] = Counter()
    family_counts: dict[str, int] = Counter()
    aggregate: dict[str, dict[str, float]] = defaultdict(lambda: {"memory_nodes": 0.0, "track_fragmentation": 0.0, "memory_authority_events": 0.0})
    scenes: set[tuple[str, str]] = set()
    report_count = 0
    for report_path in report_paths:
        report = json.loads(Path(report_path).read_text())
        audit = normalize_baseline_audit(report)
        report_count += 1
        scenes.add((str(audit["dataset"]), str(audit["scene"])))
        for row in audit["rows"]:
            baseline_id = str(row["baseline_id"])
            baseline_counts[baseline_id] += 1
            family_counts[str(row["family"])] += 1
            aggregate[baseline_id]["memory_nodes"] += float(row["memory_nodes"])
            aggregate[baseline_id]["track_fragmentation"] += float(row["track_fragmentation"])
            aggregate[baseline_id]["memory_authority_events"] += float(row["memory_authority_events"])
    rows: list[dict[str, object]] = []
    for baseline_id, count in sorted(baseline_counts.items()):
        spec = INTERNAL_BASELINE_SPECS.get(baseline_id)
        sums = aggregate[baseline_id]
        rows.append(
            {
                "baseline_id": baseline_id,
                "label": spec.label if spec else baseline_id,
                "family": spec.family if spec else "unknown",
                "count": count,
                "avg_memory_nodes": round(sums["memory_nodes"] / count, 2),
                "avg_track_fragmentation": round(sums["track_fragmentation"] / count, 2),
                "avg_memory_authority_events": round(sums["memory_authority_events"] / count, 2),
            }
        )
    return {
        "report_count": report_count,
        "unique_scene_count": len(scenes),
        "family_counts": dict(family_counts),
        "rows": rows,
    }


def render_baseline_audit_summary_markdown(summary: dict[str, object]) -> str:
    lines = [
        "# Baseline Audit Summary",
        "",
        f"- Report coverage: {summary['report_count']}",
        f"- Unique scene coverage: {summary['unique_scene_count']}",
        "",
        "## Baseline aggregates",
        "",
        "| Baseline | Family | Coverage | Avg memory nodes | Avg fragmentation | Avg memory authority |",
        "| --- | --- | ---: | ---: | ---: | ---: |",
    ]
    for row in summary["rows"]:
        lines.append(
            f"| {row['label']} | {row['family']} | {row['count']} | {row['avg_memory_nodes']:.2f} | {row['avg_track_fragmentation']:.2f} | {row['avg_memory_authority_events']:.2f} |"
        )
    lines.append("")
    return "\n".join(lines)
