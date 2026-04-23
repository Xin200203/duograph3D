from __future__ import annotations

from dataclasses import dataclass, field, asdict


@dataclass(frozen=True)
class BaselineLaneResult:
    baseline_id: str
    label: str
    dataset: str
    scene: str
    family: str
    faithfulness: str
    primary_metric_name: str
    primary_metric_value: float
    metrics: dict[str, float] = field(default_factory=dict)
    notes: list[str] = field(default_factory=list)


def normalize_baseline_lane(
    *,
    baseline_id: str,
    label: str,
    dataset: str,
    scene: str,
    family: str,
    faithfulness: str,
    primary_metric_name: str,
    primary_metric_value: float,
    metrics: dict[str, float] | None = None,
    notes: list[str] | None = None,
) -> dict[str, object]:
    lane = BaselineLaneResult(
        baseline_id=baseline_id,
        label=label,
        dataset=dataset,
        scene=scene,
        family=family,
        faithfulness=faithfulness,
        primary_metric_name=primary_metric_name,
        primary_metric_value=primary_metric_value,
        metrics=metrics or {},
        notes=notes or [],
    )
    return asdict(lane)


def render_baseline_lane_markdown(lane: dict[str, object]) -> str:
    lines = [
        "# Baseline Lane Result",
        "",
        f"- Baseline: {lane['label']} (`{lane['baseline_id']}`)",
        f"- Dataset: {lane['dataset']}",
        f"- Scene: {lane['scene']}",
        f"- Family: {lane['family']}",
        f"- Faithfulness: {lane['faithfulness']}",
        f"- Primary metric: {lane['primary_metric_name']} = {lane['primary_metric_value']}",
        "",
    ]
    metrics = lane.get("metrics", {})
    if metrics:
        lines.extend([
            "## Metrics",
            "",
            "| Name | Value |",
            "| --- | ---: |",
        ])
        for name, value in sorted(metrics.items()):
            lines.append(f"| `{name}` | {value} |")
        lines.append("")
    notes = lane.get("notes", [])
    if notes:
        lines.append("## Notes")
        lines.append("")
        for note in notes:
            lines.append(f"- {note}")
        lines.append("")
    return "\n".join(lines)
