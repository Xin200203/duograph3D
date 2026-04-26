from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class OfficialRun:
    method: str
    metrics_path: Path
    monitor_path: Path | None = None


def _read_json(path: str | Path) -> dict[str, object]:
    payload = json.loads(Path(path).read_text())
    if not isinstance(payload, dict):
        raise TypeError(f"expected JSON object: {path}")
    return payload


def _metric(metrics: dict[str, object], key: str) -> float:
    try:
        return float(metrics.get(key, 0.0))
    except (TypeError, ValueError):
        return 0.0


def _summary_mean(summary: dict[str, object], key: str) -> float:
    value = summary.get(key, {})
    if not isinstance(value, dict):
        return 0.0
    try:
        return float(value.get("mean", 0.0))
    except (TypeError, ValueError):
        return 0.0


def load_official_run(run: OfficialRun) -> dict[str, object]:
    metrics = _read_json(run.metrics_path)
    monitor = _read_json(run.monitor_path) if run.monitor_path is not None else {}
    counts = monitor.get("counts", {}) if isinstance(monitor.get("counts", {}), dict) else {}
    return {
        "method": run.method,
        "metrics_path": str(run.metrics_path),
        "monitor_path": str(run.monitor_path) if run.monitor_path is not None else "",
        "scene_count": int(counts.get("scenes", 0) or 0),
        "frame_count": int(counts.get("frames", 0) or 0),
        "all_ap": _metric(metrics, "all_ap"),
        "all_ap_50": _metric(metrics, "all_ap_50%"),
        "all_ap_25": _metric(metrics, "all_ap_25%"),
        "time": _metric(metrics, "time"),
        "data_time": _metric(metrics, "data_time"),
        "match_rate_mean": _summary_mean(monitor, "match_rate"),
        "birth_rate_mean": _summary_mean(monitor, "birth_rate"),
        "rescued_mean": _summary_mean(monitor, "rescued"),
        "topk_drop_mean": _summary_mean(monitor, "topk_drop"),
        "mem_size_kept_mean": _summary_mean(monitor, "mem_size_kept"),
    }


def compare_official_runs(*, baseline: OfficialRun, candidate: OfficialRun) -> dict[str, object]:
    baseline_row = load_official_run(baseline)
    candidate_row = load_official_run(candidate)
    deltas = {
        key: round(float(candidate_row[key]) - float(baseline_row[key]), 6)
        for key in ("all_ap", "all_ap_50", "all_ap_25", "match_rate_mean", "birth_rate_mean", "rescued_mean")
    }
    return {
        "baseline": baseline_row,
        "candidate": candidate_row,
        "delta": deltas,
        "candidate_beats_baseline": deltas["all_ap"] > 0 and deltas["all_ap_50"] > 0 and deltas["all_ap_25"] > 0,
    }


def render_official_comparison_markdown(comparison: dict[str, object]) -> str:
    baseline = comparison["baseline"]
    candidate = comparison["candidate"]
    delta = comparison["delta"]
    if not isinstance(baseline, dict) or not isinstance(candidate, dict) or not isinstance(delta, dict):
        raise TypeError("comparison payload is malformed")
    lines = [
        "# Official Evaluator Comparison",
        "",
        "| Method | Scenes | Frames | AP | AP50 | AP25 | Match rate mean | Birth rate mean | Rescue mean |",
        "| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    for row in (baseline, candidate):
        lines.append(
            "| {method} | {scene_count} | {frame_count} | {all_ap:.4f} | {all_ap_50:.4f} | {all_ap_25:.4f} | {match_rate_mean:.4f} | {birth_rate_mean:.4f} | {rescued_mean:.4f} |".format(
                **row
            )
        )
    lines.extend(
        [
            "",
            "| Delta | AP | AP50 | AP25 | Match rate mean | Birth rate mean | Rescue mean |",
            "| --- | ---: | ---: | ---: | ---: | ---: | ---: |",
            "| Candidate - baseline | {all_ap:+.4f} | {all_ap_50:+.4f} | {all_ap_25:+.4f} | {match_rate_mean:+.4f} | {birth_rate_mean:+.4f} | {rescued_mean:+.4f} |".format(
                **delta
            ),
            "",
            f"Candidate beats baseline on AP/AP50/AP25: **{comparison['candidate_beats_baseline']}**",
        ]
    )
    return "\n".join(lines)
