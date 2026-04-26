from __future__ import annotations

import json
from pathlib import Path

from .observation_metrics import build_observation_grounded_metrics


INTERESTING_EVENTS = {
    "current_hypothesis_emit",
    "birth_commit",
    "association_commit",
    "reentry_commit",
    "memory_authority_used",
    "memory_relation_update",
}


def _load_json(path: str | Path) -> dict[str, object] | list[object]:
    return json.loads(Path(path).read_text())


def _event_excerpt(report: dict[str, object], *, branch_id: str = "duograph3d_full", limit: int = 8) -> list[dict[str, object]]:
    path = Path(report["branch_event_files"][branch_id])
    events = list(_load_json(path))  # type: ignore[arg-type]
    excerpt = [
        {
            "event_type": event["event_type"],
            "step_id": event["step_id"],
            "payload": event.get("payload", {}),
        }
        for event in events
        if event.get("event_type") in INTERESTING_EVENTS
    ]
    return excerpt[:limit]


def build_phase4_representative_casebook(
    report_paths: list[str],
    *,
    branch_id: str = "duograph3d_full",
) -> dict[str, object]:
    metric_rows = []
    report_lookup: dict[tuple[str, str], dict[str, object]] = {}
    for report_path in report_paths:
        report = _load_json(report_path)
        if not isinstance(report, dict):
            continue
        metrics = build_observation_grounded_metrics(report, branch_id=branch_id)
        metric_rows.append(metrics)
        report_lookup[(str(report["dataset"]), str(report["scene"]))] = report

    if not metric_rows:
        return {"cases": []}

    def pick(label: str, *, metric: str, mode: str) -> dict[str, object]:
        if mode == "max":
            row = max(metric_rows, key=lambda item: (float(item["rows"][metric]), str(item["dataset"]), str(item["scene"])))
        else:
            row = min(metric_rows, key=lambda item: (float(item["rows"][metric]), str(item["dataset"]), str(item["scene"])))
        report = report_lookup[(str(row["dataset"]), str(row["scene"]))]
        return {
            "label": label,
            "dataset": row["dataset"],
            "scene": row["scene"],
            "metric": metric,
            "value": row["rows"][metric],
            "observation_mode": row.get("observation_mode"),
            "event_excerpt": _event_excerpt(report, branch_id=branch_id),
        }

    cases = [
        pick("best_identity_stability", metric="identity_fragmentation_count", mode="min"),
        pick("best_track_consistency", metric="track_consistency_rate", mode="max"),
        pick("worst_fragmentation", metric="identity_fragmentation_count", mode="max"),
        pick("weakest_geometry_support", metric="geometry_support_mean", mode="min"),
    ]
    return {"cases": cases}


def render_phase4_casebook_markdown(casebook: dict[str, object]) -> str:
    lines = [
        "# Phase 4 Representative Casebook",
        "",
    ]
    for item in casebook["cases"]:
        lines.extend(
            [
                f"## {item['label']}",
                f"- Scene: `{item['dataset']}/{item['scene']}`",
                f"- Metric: `{item['metric']}` = `{item['value']}`",
                f"- Observation mode: `{item['observation_mode']}`",
                "- Event excerpt:",
            ]
        )
        for event in item["event_excerpt"]:
            lines.append(f"  - `{event['event_type']}` step={event['step_id']} payload={event['payload']}")
        lines.append("")
    return "\n".join(lines)
