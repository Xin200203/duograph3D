from __future__ import annotations

from collections import Counter
from pathlib import Path


def aggregate_g2_summaries(summaries: list[dict[str, object]]) -> dict[str, object]:
    row_pass_counts: dict[str, int] = Counter()
    row_total_counts: dict[str, int] = Counter()
    signature_counts: dict[str, int] = Counter()
    dataset_counter: dict[str, int] = Counter()
    scene_rows: list[dict[str, object]] = []

    for summary in summaries:
        dataset = str(summary["dataset"])
        scene = str(summary["scene"])
        dataset_counter[dataset] += 1
        rows = summary["rows"]
        compact_rows: dict[str, dict[str, object]] = {}
        for row_name, row in rows.items():
            row_total_counts[row_name] += 1
            if row["pass"]:
                row_pass_counts[row_name] += 1
            compact_rows[row_name] = {
                "pass": row["pass"],
                "value": row["value"],
                "detail": row["detail"],
            }
        for signature in summary["failure_signatures"]:
            if signature["triggered"]:
                signature_counts[signature["name"]] += 1
        scene_rows.append(
            {
                "dataset": dataset,
                "scene": scene,
                "all_rows_pass": summary["all_rows_pass"],
                "rows": compact_rows,
            }
        )

    return {
        "scene_count": len(summaries),
        "dataset_counts": dict(dataset_counter),
        "row_pass_counts": dict(row_pass_counts),
        "row_total_counts": dict(row_total_counts),
        "signature_counts": dict(signature_counts),
        "all_scenes_pass": all(summary["all_rows_pass"] for summary in summaries),
        "scene_rows": scene_rows,
    }


def render_g2_table_markdown(aggregate: dict[str, object], source_paths: list[str]) -> str:
    lines = [
        "# G2 Evidence Table — DuoGraph3D v1",
        "",
        "Date: 2026-04-21",
        "Parent plan: `.omx/plans/ralplan-duograph3d-initial.md`",
        "Purpose: current implementation-backed G2 status across bounded-slice experiments.",
        "",
        f"Source summaries: {', '.join(f'`{Path(path).name}`' for path in source_paths)}",
        "",
        f"Overall: **{'PASS' if aggregate['all_scenes_pass'] else 'PARTIAL'}** across {aggregate['scene_count']} scenes.",
        "",
        "| Observable | Status | Coverage | Notes |",
        "| --- | --- | --- | --- |",
    ]
    row_labels = {
        "identity_churn_proxy": "Identity churn",
        "reentry_recovery_proxy": "Re-entry recovery",
        "memory_authority_usage": "Memory-authority usage",
        "counterfactual_divergence_proxy": "Counterfactual divergence",
        "dense_authority_gap_proxy": "Dense-authority gap",
    }
    for row_name, label in row_labels.items():
        passed = aggregate["row_pass_counts"].get(row_name, 0)
        total = aggregate["row_total_counts"].get(row_name, 0)
        status = "Pass" if passed == total and total > 0 else "Partial"
        lines.append(f"| {label} | {status} | {passed}/{total} scenes | `{row_name}` |")
    lines.extend([
        "",
        "## Failure signatures observed",
        "",
        "| Signature | Count |",
        "| --- | ---: |",
    ])
    for name, count in sorted(aggregate["signature_counts"].items()):
        lines.append(f"| `{name}` | {count} |")
    lines.extend([
        "",
        "## Scene breakdown",
        "",
        "| Dataset | Scene | Overall | Identity | Re-entry | Memory | Counterfactual | Dense-authority |",
        "| --- | --- | --- | --- | --- | --- | --- | --- |",
    ])
    for row in aggregate["scene_rows"]:
        rows = row["rows"]
        def mark(name: str) -> str:
            return "✓" if rows[name]["pass"] else "✗"
        lines.append(
            f"| {row['dataset']} | {row['scene']} | {'✓' if row['all_rows_pass'] else '✗'} | {mark('identity_churn_proxy')} | {mark('reentry_recovery_proxy')} | {mark('memory_authority_usage')} | {mark('counterfactual_divergence_proxy')} | {mark('dense_authority_gap_proxy')} |"
        )
    lines.append("")
    return "\n".join(lines)
