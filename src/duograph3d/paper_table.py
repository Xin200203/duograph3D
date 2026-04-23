from __future__ import annotations


DEFAULT_MAIN_TABLE_REGIMES = (
    "outputs_large_baseline",
    "outputs_large_stress",
    "outputs_burst_large",
    "outputs_random_large_seed7",
    "outputs_holdout_baseline",
)

DEFAULT_MAIN_TABLE_METRICS = (
    "identity_fragmentation_count",
    "reentry_reduction",
    "ambiguity_correction_rate",
    "authority_activation_rate",
    "geometry_support_mean",
)


def build_paper_main_table(
    summary: dict[str, object],
    *,
    regimes: tuple[str, ...] = DEFAULT_MAIN_TABLE_REGIMES,
    metrics: tuple[str, ...] = DEFAULT_MAIN_TABLE_METRICS,
) -> dict[str, object]:
    regime_map = {row["regime"]: row for row in summary.get("regime_rows", [])}
    rows = []
    for regime in regimes:
        row = regime_map.get(regime)
        if row is None:
            continue
        metric_values = row["metrics"]
        rows.append(
            {
                "regime": regime,
                "report_coverage": row["report_coverage"],
                "metrics": {
                    metric: metric_values.get(metric, {"mean": None, "min": None, "max": None})
                    for metric in metrics
                },
            }
        )
    return {"regimes": list(regimes), "metrics": list(metrics), "rows": rows}


def render_paper_main_table_markdown(table: dict[str, object]) -> str:
    header_metrics = table["metrics"]
    header = " | ".join(f"`{metric}`" for metric in header_metrics)
    separator = " | ".join("---:" for _ in header_metrics)
    lines = [
        "# Paper Main Table (Prototype-backed)",
        "",
        "| Regime | Coverage | " + header + " |",
        "| --- | ---: | " + separator + " |",
    ]
    for row in table["rows"]:
        metric_text = " | ".join(
            f"{row['metrics'][metric]['mean']:.3f}" if row["metrics"][metric]["mean"] is not None else "n/a"
            for metric in header_metrics
        )
        lines.append(f"| {row['regime']} | {row['report_coverage']} | {metric_text} |")
    lines.append("")
    return "\n".join(lines)
