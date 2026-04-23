from __future__ import annotations


def build_g3_readiness(
    mega_summary: dict[str, object],
    robustness_summary: dict[str, object],
    casebook: dict[str, object],
    metadata_summary: dict[str, object] | None = None,
) -> dict[str, object]:
    row_total = mega_summary["row_total_counts"]
    row_pass = mega_summary["row_pass_counts"]
    readiness = {
        "scene_count": mega_summary["scene_count"],
        "regime_count": robustness_summary["regime_count"],
        "all_scenes_pass": mega_summary["all_scenes_pass"],
        "all_regimes_pass": robustness_summary["all_regimes_pass"],
        "all_core_rows_pass": all(row_pass.get(name, 0) == total for name, total in row_total.items()),
        "representative_case_count": len(casebook.get("representatives", [])),
        "core_rows": {name: f"{row_pass.get(name, 0)}/{total}" for name, total in row_total.items()},
        "prototype_backed": True,
        "paper_grade": False,
        "metadata_grounded": bool(metadata_summary),
        "metadata_summary": metadata_summary or {},
        "remaining_gap": [
            "replace proxy object evidence with stronger object-level evidence derived from real observations",
            "upgrade rivals and counterfactuals from structural proxies to stronger realism",
            "add richer geometry-aware metrics beyond current proxy signals",
        ],
    }
    return readiness


def render_g3_readiness_markdown(readiness: dict[str, object]) -> str:
    lines = [
        "# G3 Readiness Summary — DuoGraph3D v1",
        "",
        f"Scene coverage: {readiness['scene_count']}",
        f"Regime coverage: {readiness['regime_count']}",
        f"All scenes pass: {'Yes' if readiness['all_scenes_pass'] else 'No'}",
        f"All regimes pass: {'Yes' if readiness['all_regimes_pass'] else 'No'}",
        f"All core rows pass: {'Yes' if readiness['all_core_rows_pass'] else 'No'}",
        f"Representative cases: {readiness['representative_case_count']}",
        f"Prototype-backed: {'Yes' if readiness['prototype_backed'] else 'No'}",
        f"Paper-grade: {'Yes' if readiness['paper_grade'] else 'No'}",
        "",
        "## Core row coverage",
        "",
        "| Signal | Coverage |",
        "| --- | ---: |",
    ]
    for name, coverage in sorted(readiness['core_rows'].items()):
        lines.append(f"| `{name}` | {coverage} |")
    lines.extend([
        "",
        "## Remaining gap to paper-grade evidence",
        "",
    ])
    for item in readiness['remaining_gap']:
        lines.append(f"- {item}")
    lines.append("")
    return "\n".join(lines)
