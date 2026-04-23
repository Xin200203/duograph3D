from __future__ import annotations

import json
from pathlib import Path


def summarize_deva_contract(output_root: str | Path) -> dict[str, object]:
    output_root = Path(output_root)
    img_root = output_root / "img_path"
    mask_root = output_root / "mask_path"
    scene_rows: list[dict[str, object]] = []
    total_frames = 0
    total_json = 0
    total_png = 0
    all_frames_matched = True
    all_scene_json_fields_present = True
    for scene_dir in sorted(img_root.iterdir() if img_root.exists() else []):
        if not scene_dir.is_dir():
            continue
        scene = scene_dir.name
        image_files = sorted(scene_dir.glob("*.jpg"))
        mask_scene_dir = mask_root / scene
        png_files = sorted(mask_scene_dir.glob("*.png"))
        json_files = sorted(mask_scene_dir.glob("*.json"))
        image_stems = {path.stem for path in image_files}
        png_stems = {path.stem for path in png_files}
        json_stems = {path.stem for path in json_files}
        matched = image_stems == png_stems == json_stems
        all_frames_matched = all_frames_matched and matched
        total_frames += len(image_files)
        total_png += len(png_files)
        total_json += len(json_files)
        segment_lists = [json.loads(path.read_text()) for path in json_files]
        segment_counts = [len(segments) for segments in segment_lists]
        all_have_bbox = all(
            all("bbox" in segment for segment in segments)
            for segments in segment_lists
        ) if segment_lists else False
        all_have_mask_area = all(
            all("mask_area" in segment for segment in segments)
            for segments in segment_lists
        ) if segment_lists else False
        scene_json_fields_present = all_have_bbox and all_have_mask_area
        all_scene_json_fields_present = all_scene_json_fields_present and scene_json_fields_present
        scene_rows.append(
            {
                "scene": scene,
                "image_frames": len(image_files),
                "png_masks": len(png_files),
                "json_masks": len(json_files),
                "all_stems_match": matched,
                "min_segment_count": min(segment_counts) if segment_counts else 0,
                "max_segment_count": max(segment_counts) if segment_counts else 0,
                "all_have_bbox": all_have_bbox,
                "all_have_mask_area": all_have_mask_area,
            }
        )
    return {
        "scene_count": len(scene_rows),
        "total_frames": total_frames,
        "total_png": total_png,
        "total_json": total_json,
        "all_frames_matched": all_frames_matched,
        "all_scene_json_fields_present": all_scene_json_fields_present,
        "scene_rows": scene_rows,
    }


def render_deva_readiness_markdown(summary: dict[str, object]) -> str:
    lines = [
        "# DEVA Contract Readiness",
        "",
        f"- Scene count: {summary['scene_count']}",
        f"- Total image frames: {summary['total_frames']}",
        f"- Total PNG masks: {summary['total_png']}",
        f"- Total JSON masks: {summary['total_json']}",
        f"- All frame stems matched: {'Yes' if summary['all_frames_matched'] else 'No'}",
        f"- All scene JSON fields present: {'Yes' if summary['all_scene_json_fields_present'] else 'No'}",
        "",
        "| Scene | Image frames | PNG masks | JSON masks | Stems match | Min segs | Max segs | All bbox | All mask-area |",
        "| --- | ---: | ---: | ---: | --- | ---: | ---: | --- | --- |",
    ]
    for row in summary["scene_rows"]:
        lines.append(
            f"| {row['scene']} | {row['image_frames']} | {row['png_masks']} | {row['json_masks']} | "
            f"{'Yes' if row['all_stems_match'] else 'No'} | {row['min_segment_count']} | {row['max_segment_count']} | "
            f"{'Yes' if row['all_have_bbox'] else 'No'} | {'Yes' if row['all_have_mask_area'] else 'No'} |"
        )
    lines.append("")
    return "\n".join(lines)
