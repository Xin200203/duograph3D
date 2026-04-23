from __future__ import annotations

import json
from pathlib import Path
from statistics import mean

from .baseline_adapter import normalize_baseline_lane


def summarize_deva_output(output_root: str | Path) -> dict[str, object]:
    output_root = Path(output_root)
    json_dir = output_root / "JSONFiles"
    scene_rows = []
    for json_path in sorted(json_dir.glob("*.json")):
        payload = json.loads(json_path.read_text())
        annotations = payload.get("annotations", [])
        segment_counts = [len(frame.get("segments_info", [])) for frame in annotations]
        areas = [
            float(segment.get("area", 0))
            for frame in annotations
            for segment in frame.get("segments_info", [])
        ]
        unique_ids = sorted(
            {
                int(segment.get("id"))
                for frame in annotations
                for segment in frame.get("segments_info", [])
                if "id" in segment
            }
        )
        scene_rows.append(
            {
                "scene": json_path.stem,
                "frame_count": len(annotations),
                "frames_with_segments": sum(1 for count in segment_counts if count > 0),
                "avg_segments_per_frame": round(mean(segment_counts), 3) if segment_counts else 0.0,
                "unique_track_ids": len(unique_ids),
                "avg_area": round(mean(areas), 3) if areas else 0.0,
                "min_area": round(min(areas), 3) if areas else 0.0,
                "max_area": round(max(areas), 3) if areas else 0.0,
            }
        )
    aggregate = {
        "scene_count": len(scene_rows),
        "rows": scene_rows,
        "mean_segments_per_frame": round(mean(row["avg_segments_per_frame"] for row in scene_rows), 3) if scene_rows else 0.0,
        "mean_unique_track_ids": round(mean(row["unique_track_ids"] for row in scene_rows), 3) if scene_rows else 0.0,
    }
    return aggregate


def deva_scene_as_lane(scene_row: dict[str, object], *, dataset: str = "replica") -> dict[str, object]:
    return normalize_baseline_lane(
        baseline_id="deva_official_offline",
        label="DEVA official offline",
        dataset=dataset,
        scene=scene_row["scene"],
        family="external_official_target",
        faithfulness="official_repo_executed",
        primary_metric_name="avg_segments_per_frame",
        primary_metric_value=float(scene_row["avg_segments_per_frame"]),
        metrics={
            "frame_count": float(scene_row["frame_count"]),
            "frames_with_segments": float(scene_row["frames_with_segments"]),
            "avg_segments_per_frame": float(scene_row["avg_segments_per_frame"]),
            "unique_track_ids": float(scene_row["unique_track_ids"]),
            "avg_area": float(scene_row["avg_area"]),
        },
        notes=["Derived from executed DEVA JSONFiles output over the DuoGraph3D-exported offline contract."],
    )


def render_deva_output_markdown(summary: dict[str, object]) -> str:
    lines = [
        "# DEVA Output Summary",
        "",
        f"- Scene count: {summary['scene_count']}",
        f"- Mean segments per frame: {summary['mean_segments_per_frame']:.3f}",
        f"- Mean unique track ids: {summary['mean_unique_track_ids']:.3f}",
        "",
        "| Scene | Frames | Frames with segments | Avg segments/frame | Unique track ids | Avg area | Min area | Max area |",
        "| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    for row in summary["rows"]:
        lines.append(
            f"| {row['scene']} | {row['frame_count']} | {row['frames_with_segments']} | {row['avg_segments_per_frame']:.3f} | "
            f"{row['unique_track_ids']} | {row['avg_area']:.3f} | {row['min_area']:.3f} | {row['max_area']:.3f} |"
        )
    lines.append("")
    return "\n".join(lines)
