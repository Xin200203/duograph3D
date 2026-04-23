from __future__ import annotations

from collections import Counter


def merge_suite_summaries(summaries: list[dict[str, object]]) -> dict[str, object]:
    dataset_counts: Counter[str] = Counter()
    row_pass_counts: Counter[str] = Counter()
    row_total_counts: Counter[str] = Counter()
    signature_counts: Counter[str] = Counter()
    scene_rows: list[dict[str, object]] = []

    for summary in summaries:
        dataset_counts.update(summary.get("dataset_counts", {}))
        row_pass_counts.update(summary.get("row_pass_counts", {}))
        row_total_counts.update(summary.get("row_total_counts", {}))
        signature_counts.update(summary.get("signature_counts", {}))
        scene_rows.extend(summary.get("scene_rows", []))

    return {
        "scene_count": sum(summary.get("scene_count", 0) for summary in summaries),
        "dataset_counts": dict(dataset_counts),
        "row_pass_counts": dict(row_pass_counts),
        "row_total_counts": dict(row_total_counts),
        "signature_counts": dict(signature_counts),
        "all_scenes_pass": all(summary.get("all_scenes_pass", False) for summary in summaries),
        "scene_rows": scene_rows,
    }
