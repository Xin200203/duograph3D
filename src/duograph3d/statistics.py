from __future__ import annotations

from collections import defaultdict
from statistics import mean


def compute_row_statistics(mega_summary: dict[str, object]) -> dict[str, dict[str, object]]:
    row_values: dict[str, list[tuple[str, str, float]]] = defaultdict(list)
    for row in mega_summary["scene_rows"]:
        dataset = str(row["dataset"])
        scene = str(row["scene"])
        for row_name, info in row["rows"].items():
            row_values[row_name].append((dataset, scene, float(info["value"])))

    stats: dict[str, dict[str, object]] = {}
    for row_name, values in row_values.items():
        ordered = sorted(values, key=lambda item: (item[2], item[0], item[1]))
        min_dataset, min_scene, min_value = ordered[0]
        max_dataset, max_scene, max_value = ordered[-1]
        stats[row_name] = {
            "count": len(values),
            "mean": mean(value for _, _, value in values),
            "min": min_value,
            "max": max_value,
            "worst_scene": {"dataset": min_dataset, "scene": min_scene, "value": min_value},
            "best_scene": {"dataset": max_dataset, "scene": max_scene, "value": max_value},
        }
    return stats


def render_statistics_markdown(mega_summary: dict[str, object], stats: dict[str, dict[str, object]]) -> str:
    lines = [
        "# G3 Statistical Summary — DuoGraph3D v1",
        "",
        f"Scene coverage: {mega_summary['scene_count']} scenes",
        f"All scenes pass: {'Yes' if mega_summary['all_scenes_pass'] else 'No'}",
        "",
        "| Signal | Mean | Min | Max | Worst scene | Best scene |",
        "| --- | ---: | ---: | ---: | --- | --- |",
    ]
    for row_name, info in sorted(stats.items()):
        worst = info["worst_scene"]
        best = info["best_scene"]
        lines.append(
            f"| `{row_name}` | {info['mean']:.2f} | {info['min']:.2f} | {info['max']:.2f} | `{worst['dataset']}/{worst['scene']}` ({worst['value']:.2f}) | `{best['dataset']}/{best['scene']}` ({best['value']:.2f}) |"
        )
    lines.append("")
    return "\n".join(lines)
