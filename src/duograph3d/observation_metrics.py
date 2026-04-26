from __future__ import annotations

import json
from collections import Counter, defaultdict
from pathlib import Path
from statistics import mean


ASSIGNMENT_EVENTS = {"birth_commit", "association_commit", "reentry_commit"}


def _load_json(path: str | Path) -> dict[str, object] | list[object]:
    return json.loads(Path(path).read_text())


def _assignment_rows(events: list[dict[str, object]]) -> list[tuple[str, str]]:
    rows: list[tuple[str, str]] = []
    for event in events:
        if event.get("event_type") not in ASSIGNMENT_EVENTS:
            continue
        payload = event.get("payload", {})
        if not isinstance(payload, dict):
            continue
        track_hint = str(payload.get("track_hint", ""))
        object_id = str(payload.get("object_id", ""))
        if track_hint and object_id:
            rows.append((track_hint, object_id))
    return rows


def build_observation_grounded_metrics(report: dict[str, object], *, branch_id: str = "duograph3d_full") -> dict[str, object]:
    summary = report["branches"][branch_id]
    event_path = Path(report["branch_event_files"][branch_id])
    events = list(_load_json(event_path))  # type: ignore[arg-type]
    assignments = _assignment_rows(events)

    track_to_objects: dict[str, list[str]] = defaultdict(list)
    object_to_tracks: dict[str, list[str]] = defaultdict(list)
    for track_hint, object_id in assignments:
        track_to_objects[track_hint].append(object_id)
        object_to_tracks[object_id].append(track_hint)

    track_majority_rates = []
    for object_ids in track_to_objects.values():
        counts = Counter(object_ids)
        track_majority_rates.append(max(counts.values()) / max(len(object_ids), 1))

    object_purity_rates = []
    for track_hints in object_to_tracks.values():
        counts = Counter(track_hints)
        object_purity_rates.append(max(counts.values()) / max(len(track_hints), 1))

    frame_count = max(int(report.get("frame_count", 0)), 1)
    frames_with_observations = int(report.get("frames_with_observations", 0))
    relation_edge_count = int(summary.get("memory_relation_edge_count", 0))
    memory_node_count = int(summary.get("memory_node_count", 0))
    relation_density = 0.0
    if memory_node_count >= 2:
        relation_density = relation_edge_count / max(memory_node_count * (memory_node_count - 1) / 2, 1)

    rows = {
        "identity_fragmentation_count": float(summary.get("track_fragmentation", 0)),
        "track_consistency_rate": round(mean(track_majority_rates), 3) if track_majority_rates else 0.0,
        "memory_object_purity": round(mean(object_purity_rates), 3) if object_purity_rates else 0.0,
        "real_observation_frame_rate": round(frames_with_observations / frame_count, 3),
        "relation_density": round(relation_density, 3),
        "geometry_support_mean": round(float(summary.get("avg_geometry_support", 0.0)), 3),
        "memory_relation_edge_count": float(relation_edge_count),
    }
    return {
        "dataset": report["dataset"],
        "scene": report["scene"],
        "branch_id": branch_id,
        "observation_mode": report.get("scene_metadata", {}).get("observation_mode"),
        "rows": rows,
    }


def summarize_observation_grounded_metrics(report_paths: list[str]) -> dict[str, object]:
    rows = []
    by_regime: dict[str, list[dict[str, object]]] = defaultdict(list)
    for report_path in report_paths:
        report = _load_json(report_path)
        if not isinstance(report, dict):
            continue
        metrics = build_observation_grounded_metrics(report)
        rows.append(metrics)
        by_regime[Path(report_path).parent.name].append(metrics)

    aggregate_values: dict[str, list[float]] = defaultdict(list)
    for row in rows:
        for name, value in row["rows"].items():
            aggregate_values[name].append(float(value))

    aggregate_rows = [
        {
            "metric": name,
            "count": len(values),
            "mean": round(mean(values), 3),
            "min": round(min(values), 3),
            "max": round(max(values), 3),
        }
        for name, values in sorted(aggregate_values.items())
    ]

    regime_rows = []
    for regime, regime_items in sorted(by_regime.items()):
        metric_values: dict[str, list[float]] = defaultdict(list)
        for item in regime_items:
            for name, value in item["rows"].items():
                metric_values[name].append(float(value))
        regime_rows.append(
            {
                "regime": regime,
                "report_coverage": len(regime_items),
                "metrics": {
                    name: {
                        "mean": round(mean(values), 3),
                        "min": round(min(values), 3),
                        "max": round(max(values), 3),
                    }
                    for name, values in sorted(metric_values.items())
                },
            }
        )
    return {
        "report_coverage": len(rows),
        "rows": rows,
        "aggregate_rows": aggregate_rows,
        "regime_rows": regime_rows,
    }


def render_observation_grounded_metrics_markdown(summary: dict[str, object]) -> str:
    lines = [
        "# Observation-Grounded Metrics Summary",
        "",
        f"- Report coverage: {summary['report_coverage']}",
        "",
        "| Metric | Mean | Min | Max |",
        "| --- | ---: | ---: | ---: |",
    ]
    for row in summary["aggregate_rows"]:
        lines.append(f"| `{row['metric']}` | {row['mean']:.3f} | {row['min']:.3f} | {row['max']:.3f} |")
    if summary.get("regime_rows"):
        lines.extend(["", "## By regime", ""])
        for regime in summary["regime_rows"]:
            lines.append(f"### {regime['regime']}")
            lines.append("")
            lines.append(f"- Report coverage: {regime['report_coverage']}")
            lines.append("")
            lines.append("| Metric | Mean | Min | Max |")
            lines.append("| --- | ---: | ---: | ---: |")
            for name, values in regime["metrics"].items():
                lines.append(f"| `{name}` | {values['mean']:.3f} | {values['min']:.3f} | {values['max']:.3f} |")
            lines.append("")
    return "\n".join(lines)
