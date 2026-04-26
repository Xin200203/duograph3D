from __future__ import annotations

from statistics import mean


DEFAULT_MAIN_TABLE_METRICS = (
    "identity_fragmentation_count",
    "track_consistency_rate",
    "real_observation_frame_rate",
    "geometry_support_mean",
)

METRIC_DIRECTION = {
    "identity_fragmentation_count": "lower_better",
    "track_consistency_rate": "higher_better",
    "memory_object_purity": "higher_better",
    "real_observation_frame_rate": "higher_better",
    "relation_density": "higher_better",
    "memory_relation_edge_count": "higher_better",
    "geometry_support_mean": "higher_better",
}


def build_phase4_main_table(
    summary: dict[str, object],
    *,
    metrics: tuple[str, ...] = DEFAULT_MAIN_TABLE_METRICS,
) -> dict[str, object]:
    rows = []
    for regime_row in summary.get("regime_rows", []):
        rows.append(
            {
                "regime": regime_row["regime"],
                "report_coverage": regime_row["report_coverage"],
                "metrics": {
                    metric: regime_row["metrics"].get(metric, {"mean": None, "min": None, "max": None})
                    for metric in metrics
                },
            }
        )
    return {
        "metrics": list(metrics),
        "rows": rows,
    }


def build_phase4_ablation_table(
    summary: dict[str, object],
    *,
    baseline_regime: str = "phase4_baseline",
    metrics: tuple[str, ...] = DEFAULT_MAIN_TABLE_METRICS,
) -> dict[str, object]:
    regime_map = {row["regime"]: row for row in summary.get("regime_rows", [])}
    baseline = regime_map.get(baseline_regime)
    rows = []
    for regime, regime_row in sorted(regime_map.items()):
        if regime == baseline_regime:
            continue
        metric_deltas = {}
        for metric in metrics:
            baseline_mean = baseline["metrics"].get(metric, {}).get("mean") if baseline else None
            regime_mean = regime_row["metrics"].get(metric, {}).get("mean")
            if baseline_mean is None or regime_mean is None:
                delta = None
            elif METRIC_DIRECTION.get(metric) == "lower_better":
                delta = round(float(baseline_mean) - float(regime_mean), 3)
            else:
                delta = round(float(regime_mean) - float(baseline_mean), 3)
            metric_deltas[metric] = {
                "baseline_mean": baseline_mean,
                "regime_mean": regime_mean,
                "delta_vs_baseline": delta,
            }
        rows.append(
            {
                "regime": regime,
                "report_coverage": regime_row["report_coverage"],
                "metrics": metric_deltas,
            }
        )
    return {
        "baseline_regime": baseline_regime,
        "metrics": list(metrics),
        "rows": rows,
    }


def render_phase4_main_table_markdown(table: dict[str, object]) -> str:
    metrics = table["metrics"]
    lines = [
        "# Phase 4 Main Table Candidate",
        "",
        "| Regime | Coverage | " + " | ".join(f"`{metric}`" for metric in metrics) + " |",
        "| --- | ---: | " + " | ".join("---:" for _ in metrics) + " |",
    ]
    for row in table["rows"]:
        metric_values = []
        for metric in metrics:
            mean_value = row["metrics"][metric]["mean"]
            metric_values.append(f"{mean_value:.3f}" if mean_value is not None else "n/a")
        lines.append(f"| {row['regime']} | {row['report_coverage']} | " + " | ".join(metric_values) + " |")
    lines.append("")
    return "\n".join(lines)


def render_phase4_ablation_table_markdown(table: dict[str, object]) -> str:
    metrics = table["metrics"]
    lines = [
        "# Phase 4 Ablation Table Candidate",
        "",
        f"- Baseline regime: `{table['baseline_regime']}`",
        "",
        "| Regime | Coverage | " + " | ".join(f"`{metric}` Δ vs baseline" for metric in metrics) + " |",
        "| --- | ---: | " + " | ".join("---:" for _ in metrics) + " |",
    ]
    for row in table["rows"]:
        values = []
        for metric in metrics:
            delta = row["metrics"][metric]["delta_vs_baseline"]
            values.append(f"{delta:+.3f}" if delta is not None else "n/a")
        lines.append(f"| {row['regime']} | {row['report_coverage']} | " + " | ".join(values) + " |")
    lines.append("")
    return "\n".join(lines)


def build_worst_best_analysis(
    summary: dict[str, object],
    *,
    metrics: tuple[str, ...] = DEFAULT_MAIN_TABLE_METRICS,
) -> dict[str, object]:
    rows = summary.get("rows", [])
    analysis_rows = []
    for metric in metrics:
        direction = METRIC_DIRECTION.get(metric, "higher_better")
        ordered = sorted(
            rows,
            key=lambda row: (
                float(row["rows"][metric]),
                str(row["dataset"]),
                str(row["scene"]),
            ),
            reverse=(direction == "higher_better"),
        )
        best = ordered[0]
        worst = ordered[-1]
        analysis_rows.append(
            {
                "metric": metric,
                "direction": direction,
                "best": {
                    "dataset": best["dataset"],
                    "scene": best["scene"],
                    "value": best["rows"][metric],
                    "observation_mode": best.get("observation_mode"),
                },
                "worst": {
                    "dataset": worst["dataset"],
                    "scene": worst["scene"],
                    "value": worst["rows"][metric],
                    "observation_mode": worst.get("observation_mode"),
                },
            }
        )
    return {"rows": analysis_rows}


def render_worst_best_markdown(analysis: dict[str, object]) -> str:
    lines = [
        "# Phase 4 Worst/Best Analysis",
        "",
        "| Metric | Best scene | Best value | Worst scene | Worst value |",
        "| --- | --- | ---: | --- | ---: |",
    ]
    for row in analysis["rows"]:
        best = row["best"]
        worst = row["worst"]
        lines.append(
            f"| `{row['metric']}` | `{best['dataset']}/{best['scene']}` | {float(best['value']):.3f} | "
            f"`{worst['dataset']}/{worst['scene']}` | {float(worst['value']):.3f} |"
        )
    lines.append("")
    return "\n".join(lines)


def build_failure_casebook(summary: dict[str, object], *, top_k: int = 5) -> dict[str, object]:
    rows = summary.get("rows", [])
    if not rows:
        return {"rows": []}
    frag_values = [float(row["rows"]["identity_fragmentation_count"]) for row in rows]
    consistency_values = [float(row["rows"]["track_consistency_rate"]) for row in rows]
    observation_values = [float(row["rows"]["real_observation_frame_rate"]) for row in rows]
    geometry_values = [float(row["rows"]["geometry_support_mean"]) for row in rows]

    frag_max = max(frag_values) or 1.0

    case_rows = []
    for row in rows:
        fragmentation = float(row["rows"]["identity_fragmentation_count"])
        consistency = float(row["rows"]["track_consistency_rate"])
        observation_rate = float(row["rows"]["real_observation_frame_rate"])
        geometry = float(row["rows"]["geometry_support_mean"])
        severity = (
            (fragmentation / frag_max) * 0.4
            + (1.0 - consistency) * 0.25
            + (1.0 - observation_rate) * 0.2
            + (1.0 - geometry) * 0.15
        )
        case_rows.append(
            {
                "dataset": row["dataset"],
                "scene": row["scene"],
                "observation_mode": row.get("observation_mode"),
                "severity": round(severity, 3),
                "identity_fragmentation_count": fragmentation,
                "track_consistency_rate": consistency,
                "real_observation_frame_rate": observation_rate,
                "geometry_support_mean": geometry,
            }
        )
    case_rows.sort(key=lambda row: (-row["severity"], row["dataset"], row["scene"]))
    return {"rows": case_rows[:top_k]}


def render_failure_casebook_markdown(casebook: dict[str, object]) -> str:
    lines = [
        "# Phase 4 Failure Casebook",
        "",
        "| Scene | Severity | Fragmentation | Track consistency | Observation frame rate | Geometry support |",
        "| --- | ---: | ---: | ---: | ---: | ---: |",
    ]
    for row in casebook["rows"]:
        lines.append(
            f"| `{row['dataset']}/{row['scene']}` | {row['severity']:.3f} | {row['identity_fragmentation_count']:.3f} | "
            f"{row['track_consistency_rate']:.3f} | {row['real_observation_frame_rate']:.3f} | {row['geometry_support_mean']:.3f} |"
        )
    lines.append("")
    return "\n".join(lines)
