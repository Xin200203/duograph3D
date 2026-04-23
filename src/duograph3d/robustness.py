from __future__ import annotations

from collections import Counter


def compare_suite_summaries(named_summaries: list[tuple[str, dict[str, object]]]) -> dict[str, object]:
    regime_rows: dict[str, dict[str, object]] = {}
    row_stability: dict[str, bool] = {}
    all_row_names: set[str] = set()
    scene_pass_counter: Counter[str] = Counter()

    for regime, summary in named_summaries:
        regime_rows[regime] = {
            "scene_count": summary["scene_count"],
            "all_scenes_pass": summary["all_scenes_pass"],
            "row_pass_counts": dict(summary["row_pass_counts"]),
            "row_total_counts": dict(summary["row_total_counts"]),
            "signature_counts": dict(summary["signature_counts"]),
        }
        all_row_names.update(summary["row_pass_counts"].keys())
        for row in summary["scene_rows"]:
            if row["all_rows_pass"]:
                scene_pass_counter[f"{regime}:{row['dataset']}:{row['scene']}"] += 1

    for row_name in sorted(all_row_names):
        row_stability[row_name] = all(
            regime_rows[regime]["row_pass_counts"].get(row_name, 0)
            == regime_rows[regime]["row_total_counts"].get(row_name, 0)
            for regime, _ in named_summaries
        )

    return {
        "regime_count": len(named_summaries),
        "regimes": regime_rows,
        "row_stability": row_stability,
        "all_regimes_pass": all(regime_rows[regime]["all_scenes_pass"] for regime, _ in named_summaries),
    }


def render_robustness_markdown(report: dict[str, object]) -> str:
    lines = [
        "# Robustness Summary — DuoGraph3D v1",
        "",
        f"Compared regimes: {', '.join(report['regimes'].keys())}",
        "",
        f"Overall robustness: **{'PASS' if report['all_regimes_pass'] else 'PARTIAL'}**",
        "",
        "| Observable | Stable across regimes |",
        "| --- | --- |",
    ]
    for row_name, stable in sorted(report["row_stability"].items()):
        lines.append(f"| `{row_name}` | {'Yes' if stable else 'No'} |")
    lines.extend([
        "",
        "## Regime breakdown",
        "",
        "| Regime | Scene count | All scenes pass |",
        "| --- | ---: | --- |",
    ])
    for regime, details in report["regimes"].items():
        lines.append(f"| {regime} | {details['scene_count']} | {'Yes' if details['all_scenes_pass'] else 'No'} |")
    lines.append("")
    return "\n".join(lines)
