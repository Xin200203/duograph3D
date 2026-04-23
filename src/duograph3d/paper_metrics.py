from __future__ import annotations

import json
from pathlib import Path
from statistics import mean


PAPER_METRIC_SPEC = {
    "identity_fragmentation_count": "duograph3d_full.track_fragmentation",
    "reentry_reduction": "max(temporal_none.reentries, temporal_naive_framewise.reentries) - temporal_deva_style.reentries",
    "ambiguity_correction_rate": "duograph3d_full.memory_authority_events / max(duograph3d_full.hypotheses_with_ambiguity, 1)",
    "authority_activation_rate": "duograph3d_full.memory_authority_events / max(frames_with_observations, 1)",
    "geometry_support_mean": "duograph3d_full.avg_geometry_support",
}


def build_paper_metrics(report: dict[str, object]) -> dict[str, object]:
    full = report["branches"]["duograph3d_full"]
    none_branch = report["temporal_triplet"]["temporal_none"]
    naive_branch = report["temporal_triplet"]["temporal_naive_framewise"]
    deva_branch = report["temporal_triplet"]["temporal_deva_style"]
    hypotheses_with_ambiguity = max(int(full.get("hypotheses_with_ambiguity", 0)), 1)
    frames_with_observations = max(int(report.get("frames_with_observations", 0)), 1)
    rows = {
        "identity_fragmentation_count": float(full.get("track_fragmentation", 0)),
        "reentry_reduction": float(max(none_branch["reentries"], naive_branch["reentries"]) - deva_branch["reentries"]),
        "ambiguity_correction_rate": round(float(full.get("memory_authority_events", 0)) / hypotheses_with_ambiguity, 3),
        "authority_activation_rate": round(float(full.get("memory_authority_events", 0)) / frames_with_observations, 3),
        "geometry_support_mean": round(float(full.get("avg_geometry_support", 0.0)), 3),
    }
    return {
        "dataset": report["dataset"],
        "scene": report["scene"],
        "rows": rows,
        "spec": PAPER_METRIC_SPEC,
    }


def summarize_paper_metrics(report_paths: list[str]) -> dict[str, object]:
    metrics_rows = []
    by_regime: dict[str, list[dict[str, object]]] = {}
    for report_path in report_paths:
        report = json.loads(Path(report_path).read_text())
        metrics = build_paper_metrics(report)
        metrics_rows.append(metrics)
        regime = Path(report_path).parent.name
        by_regime.setdefault(regime, []).append(metrics)
    by_name: dict[str, list[float]] = {}
    for row in metrics_rows:
        for name, value in row["rows"].items():
            by_name.setdefault(name, []).append(float(value))
    aggregate_rows = []
    for name, values in sorted(by_name.items()):
        aggregate_rows.append(
            {
                "metric": name,
                "count": len(values),
                "mean": round(mean(values), 3),
                "min": round(min(values), 3),
                "max": round(max(values), 3),
                "formula": PAPER_METRIC_SPEC[name],
            }
        )
    regime_rows = []
    for regime, rows in sorted(by_regime.items()):
        regime_values: dict[str, list[float]] = {}
        for row in rows:
            for name, value in row["rows"].items():
                regime_values.setdefault(name, []).append(float(value))
        regime_rows.append(
            {
                "regime": regime,
                "report_coverage": len(rows),
                "metrics": {
                    name: {
                        "mean": round(mean(values), 3),
                        "min": round(min(values), 3),
                        "max": round(max(values), 3),
                    }
                    for name, values in sorted(regime_values.items())
                },
            }
        )
    return {
        "report_coverage": len(metrics_rows),
        "rows": metrics_rows,
        "aggregate_rows": aggregate_rows,
        "regime_rows": regime_rows,
        "spec": PAPER_METRIC_SPEC,
    }


def render_paper_metrics_markdown(summary: dict[str, object]) -> str:
    lines = [
        "# Paper-facing Metrics Summary",
        "",
        f"- Report coverage: {summary['report_coverage']}",
        "",
        "| Metric | Mean | Min | Max | Formula |",
        "| --- | ---: | ---: | ---: | --- |",
    ]
    for row in summary["aggregate_rows"]:
        lines.append(
            f"| `{row['metric']}` | {row['mean']:.3f} | {row['min']:.3f} | {row['max']:.3f} | `{row['formula']}` |"
        )
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
                lines.append(
                    f"| `{name}` | {values['mean']:.3f} | {values['min']:.3f} | {values['max']:.3f} |"
                )
            lines.append("")
    lines.append("")
    return "\n".join(lines)
