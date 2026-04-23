from __future__ import annotations

import json
from pathlib import Path


def build_external_comparison(
    duo_summary: dict[str, object],
    deva_summary: dict[str, object],
) -> dict[str, object]:
    duo_rows = {
        f"{row['dataset']}/{row['scene']}": row["rows"]
        for row in duo_summary.get("rows", [])
    }
    deva_rows = {f"replica/{row['scene']}": row for row in deva_summary.get("rows", [])}
    keys = sorted(set(duo_rows) | set(deva_rows))
    rows: list[dict[str, object]] = []
    for key in keys:
        duo = duo_rows.get(key, {})
        deva = deva_rows.get(key, {})
        rows.append(
            {
                "scene_key": key,
                "duo_identity_fragmentation_count": duo.get("identity_fragmentation_count"),
                "duo_reentry_reduction": duo.get("reentry_reduction"),
                "duo_authority_activation_rate": duo.get("authority_activation_rate"),
                "deva_avg_segments_per_frame": deva.get("avg_segments_per_frame"),
                "deva_unique_track_ids": deva.get("unique_track_ids"),
                "deva_frames_with_segments": deva.get("frames_with_segments"),
            }
        )
    active_deva = sum(1 for row in rows if (row["deva_frames_with_segments"] or 0) > 0)
    return {
        "scene_count": len(rows),
        "deva_active_scene_count": active_deva,
        "rows": rows,
    }


def load_json(path: str | Path) -> dict[str, object]:
    return json.loads(Path(path).read_text())


def render_external_comparison_markdown(summary: dict[str, object]) -> str:
    lines = [
        "# External Comparison Seed Table",
        "",
        f"- Scene count: {summary['scene_count']}",
        f"- DEVA active scenes: {summary['deva_active_scene_count']}",
        "",
        "| Scene | Duo identity frag | Duo reentry reduction | Duo authority activation | DEVA avg seg/frame | DEVA unique tracks | DEVA active frames |",
        "| --- | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    for row in summary["rows"]:
        def fmt(value: object) -> str:
            if value is None:
                return "n/a"
            if isinstance(value, float):
                return f"{value:.3f}"
            return str(value)
        lines.append(
            f"| {row['scene_key']} | {fmt(row['duo_identity_fragmentation_count'])} | {fmt(row['duo_reentry_reduction'])} | "
            f"{fmt(row['duo_authority_activation_rate'])} | {fmt(row['deva_avg_segments_per_frame'])} | "
            f"{fmt(row['deva_unique_track_ids'])} | {fmt(row['deva_frames_with_segments'])} |"
        )
    lines.append("")
    return "\n".join(lines)
