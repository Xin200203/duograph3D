from __future__ import annotations


def render_g3_package_markdown(
    *,
    mega_summary: dict[str, object],
    robustness_summary: dict[str, object],
    casebook: dict[str, object],
    statistics_summary: dict[str, dict[str, object]],
    paper_metrics_summary: dict[str, object] | None = None,
    metadata_summary: dict[str, object] | None = None,
) -> str:
    lines = [
        "# G3 Evidence Package — DuoGraph3D v1",
        "",
        f"Mega scene coverage: {mega_summary['scene_count']} scenes",
        f"Global robustness regimes: {robustness_summary['regime_count']}",
        f"All scenes pass: {'Yes' if mega_summary['all_scenes_pass'] else 'No'}",
        f"All regimes pass: {'Yes' if robustness_summary['all_regimes_pass'] else 'No'}",
        f"Representative cases: {len(casebook['representatives'])}",
        f"Metadata-grounded scenes: {metadata_summary['unique_scene_count']}" if metadata_summary else 'Metadata-grounded scenes: n/a',
        "",
        "## Core claim axes",
        "",
        "| Signal | Coverage |",
        "| --- | ---: |",
    ]
    for signal, count in sorted(mega_summary['row_pass_counts'].items()):
        total = mega_summary['row_total_counts'][signal]
        lines.append(f"| `{signal}` | {count}/{total} |")
    lines.extend(
        [
            "",
            "## Global robustness summary",
            "",
            "| Regime | Scene count | All scenes pass |",
            "| --- | ---: | --- |",
        ]
    )
    for regime, details in robustness_summary['regimes'].items():
        lines.append(
            f"| {regime} | {details['scene_count']} | {'Yes' if details['all_scenes_pass'] else 'No'} |"
        )
    lines.extend(
        [
            "",
            "## Statistical summary",
            "",
            "| Signal | Mean | Min | Max | Worst scene | Best scene |",
            "| --- | ---: | ---: | ---: | --- | --- |",
        ]
    )
    for signal, info in sorted(statistics_summary.items()):
        worst = info['worst_scene']
        best = info['best_scene']
        lines.append(
            f"| `{signal}` | {info['mean']:.2f} | {info['min']:.2f} | {info['max']:.2f} | `{worst['dataset']}/{worst['scene']}` ({worst['value']:.2f}) | `{best['dataset']}/{best['scene']}` ({best['value']:.2f}) |"
        )
    if paper_metrics_summary:
        lines.extend([
            "",
            "## Paper-facing metrics",
            "",
            "| Metric | Mean | Min | Max |",
            "| --- | ---: | ---: | ---: |",
        ])
        for row in paper_metrics_summary.get("aggregate_rows", []):
            lines.append(
                f"| `{row['metric']}` | {row['mean']:.3f} | {row['min']:.3f} | {row['max']:.3f} |"
            )
    if metadata_summary:
        lines.extend([
            "",
            "## Metadata grounding summary",
            "",
            f"- Unique scenes: {metadata_summary['unique_scene_count']}",
            f"- Replica mesh coverage: {metadata_summary['replica_mesh_coverage']}/{metadata_summary['replica_scene_count']}",
            f"- ScanNet label-mesh coverage: {metadata_summary['scannet_label_mesh_coverage']}/{metadata_summary['scannet_scene_count']}",
            f"- Avg object-template count: {metadata_summary['avg_template_count']:.2f}",
            "",
        ])
    lines.extend(
        [
            "",
            "## Representative casebook signals",
            "",
            "| Signal | Scene | Value | Detail |",
            "| --- | --- | ---: | --- |",
        ]
    )
    for item in casebook['representatives']:
        lines.append(
            f"| `{item['signal']}` | `{item['dataset']}/{item['scene']}` | {item['value']} | {item['detail']} |"
        )
    lines.append("")
    return "\n".join(lines)
