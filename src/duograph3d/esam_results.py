from __future__ import annotations

import json
from pathlib import Path

from .baseline_adapter import normalize_baseline_lane


def _load_json(path: str | Path) -> dict[str, object]:
    return json.loads(Path(path).read_text())


def summarize_esam_scannet_output(
    *,
    metric_json: str | Path,
    online_monitor_summary_json: str | Path,
    executed_repo_root: str | Path,
) -> dict[str, object]:
    metric_payload = _load_json(metric_json)
    monitor_payload = _load_json(online_monitor_summary_json)
    counts = monitor_payload.get("counts", {})
    match_rate = monitor_payload.get("match_rate", {})
    birth_rate = monitor_payload.get("birth_rate", {})
    mem_size_full = monitor_payload.get("mem_size_full", {})
    mem_size_kept = monitor_payload.get("mem_size_kept", {})
    return {
        "baseline_id": "esam_official_scannet_mv",
        "label": "EmbodiedSAM official ScanNet-MV",
        "dataset": "scannet",
        "scene_scope": "fullval",
        "executed_repo_root": str(executed_repo_root),
        "metric_json": str(metric_json),
        "online_monitor_summary_json": str(online_monitor_summary_json),
        "all_ap": float(metric_payload.get("all_ap", 0.0)),
        "all_ap_50": float(metric_payload.get("all_ap_50%", 0.0)),
        "all_ap_25": float(metric_payload.get("all_ap_25%", 0.0)),
        "eval_time": float(metric_payload.get("time", 0.0)),
        "counts": {
            "scenes": int(counts.get("scenes", 0)),
            "frames": int(counts.get("frames", 0)),
        },
        "match_rate_mean": float(match_rate.get("mean", 0.0)),
        "birth_rate_mean": float(birth_rate.get("mean", 0.0)),
        "mem_size_full_mean": float(mem_size_full.get("mean", 0.0)),
        "mem_size_kept_mean": float(mem_size_kept.get("mean", 0.0)),
    }


def esam_summary_as_lane(summary: dict[str, object]) -> dict[str, object]:
    return normalize_baseline_lane(
        baseline_id=str(summary["baseline_id"]),
        label=str(summary["label"]),
        dataset=str(summary["dataset"]),
        scene=str(summary["scene_scope"]),
        family="external_official_family",
        faithfulness="official_family_fork_executed",
        primary_metric_name="all_ap",
        primary_metric_value=float(summary["all_ap"]),
        metrics={
            "all_ap": float(summary["all_ap"]),
            "all_ap_50": float(summary["all_ap_50"]),
            "all_ap_25": float(summary["all_ap_25"]),
            "match_rate_mean": float(summary["match_rate_mean"]),
            "birth_rate_mean": float(summary["birth_rate_mean"]),
            "mem_size_full_mean": float(summary["mem_size_full_mean"]),
            "mem_size_kept_mean": float(summary["mem_size_kept_mean"]),
            "scene_count": float(summary["counts"]["scenes"]),
            "frame_count": float(summary["counts"]["frames"]),
        },
        notes=[
            f"Executed artifact root: {summary['executed_repo_root']}",
            "Official ESAM repository provides the evaluation configuration family; executed result currently comes from the documented ESAM-family local fork lane.",
        ],
    )


def render_esam_output_markdown(summary: dict[str, object]) -> str:
    lines = [
        "# ESAM Output Summary",
        "",
        f"- Baseline: {summary['label']}",
        f"- Dataset: {summary['dataset']}",
        f"- Scene scope: {summary['scene_scope']}",
        f"- Executed repo root: {summary['executed_repo_root']}",
        f"- Metric JSON: {summary['metric_json']}",
        f"- Online monitor summary: {summary['online_monitor_summary_json']}",
        "",
        "| Metric | Value |",
        "| --- | ---: |",
        f"| `all_ap` | {summary['all_ap']:.4f} |",
        f"| `all_ap_50` | {summary['all_ap_50']:.4f} |",
        f"| `all_ap_25` | {summary['all_ap_25']:.4f} |",
        f"| `match_rate_mean` | {summary['match_rate_mean']:.4f} |",
        f"| `birth_rate_mean` | {summary['birth_rate_mean']:.4f} |",
        f"| `mem_size_full_mean` | {summary['mem_size_full_mean']:.4f} |",
        f"| `mem_size_kept_mean` | {summary['mem_size_kept_mean']:.4f} |",
        f"| `scene_count` | {summary['counts']['scenes']} |",
        f"| `frame_count` | {summary['counts']['frames']} |",
        f"| `eval_time` | {summary['eval_time']:.4f} |",
        "",
    ]
    return "\n".join(lines)
