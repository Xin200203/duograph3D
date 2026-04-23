from __future__ import annotations

import json
from pathlib import Path
from typing import Iterable


def load_json(path: str | Path) -> dict[str, object] | list[object]:
    return json.loads(Path(path).read_text())


def _summary_filename(dataset: str, scene: str) -> str:
    return f"g2_summary_{dataset}_{scene}.json"


def _event_filename(dataset: str, scene: str, branch_id: str) -> str:
    return f"events_{dataset}_{scene}_{branch_id}.json"


def find_scene_summary(scene_row: dict[str, object], suite_dirs: Iterable[str | Path]) -> tuple[Path, Path]:
    dataset = str(scene_row["dataset"])
    scene = str(scene_row["scene"])
    filename = _summary_filename(dataset, scene)
    for suite_dir in suite_dirs:
        candidate = Path(suite_dir) / filename
        if candidate.exists():
            return Path(suite_dir), candidate
    raise FileNotFoundError(filename)


def _load_events(suite_dir: Path, dataset: str, scene: str, branch_id: str) -> list[dict[str, object]]:
    path = suite_dir / _event_filename(dataset, scene, branch_id)
    if not path.exists():
        return []
    return list(load_json(path))  # type: ignore[arg-type]


def _interesting_events(events: list[dict[str, object]]) -> list[dict[str, object]]:
    keep = {"memory_authority_used", "reentry_commit", "birth_commit", "association_commit", "temporal_propagation_used"}
    chosen = [event for event in events if event.get("event_type") in keep]
    return chosen[:8]


def build_casebook(mega_summary: dict[str, object], suite_dirs: Iterable[str | Path]) -> dict[str, object]:
    scene_rows = list(mega_summary["scene_rows"])
    signals = [
        "identity_churn_proxy",
        "reentry_recovery_proxy",
        "memory_authority_usage",
        "counterfactual_divergence_proxy",
        "dense_authority_gap_proxy",
    ]
    representatives = []
    for signal in signals:
        best = max(
            scene_rows,
            key=lambda row: (row["rows"][signal]["value"], str(row["dataset"]), str(row["scene"])),
        )
        suite_dir, summary_path = find_scene_summary(best, suite_dirs)
        dataset = str(best["dataset"])
        scene = str(best["scene"])
        duograph_events = _load_events(suite_dir, dataset, scene, "duograph3d_full")
        single_events = _load_events(suite_dir, dataset, scene, "single_layer_rival")
        counter_events = _load_events(suite_dir, dataset, scene, "full_fair_counterfactual")
        representatives.append(
            {
                "signal": signal,
                "dataset": dataset,
                "scene": scene,
                "value": best["rows"][signal]["value"],
                "detail": best["rows"][signal].get("detail", ""),
                "suite_dir": str(suite_dir),
                "summary_path": str(summary_path),
                "duograph_events": _interesting_events(duograph_events),
                "single_layer_events": _interesting_events(single_events),
                "counterfactual_events": _interesting_events(counter_events),
            }
        )
    return {
        "scene_count": mega_summary["scene_count"],
        "all_scenes_pass": mega_summary["all_scenes_pass"],
        "representatives": representatives,
    }


def render_casebook_markdown(casebook: dict[str, object]) -> str:
    lines = [
        "# G3 Casebook — DuoGraph3D v1",
        "",
        f"Scene coverage: {casebook['scene_count']} scenes",
        f"Overall pass: {'Yes' if casebook['all_scenes_pass'] else 'No'}",
        "",
    ]
    for item in casebook["representatives"]:
        lines.extend(
            [
                f"## {item['signal']}",
                f"- Scene: `{item['dataset']}/{item['scene']}`",
                f"- Value: `{item['value']}`",
                f"- Detail: {item['detail']}",
                f"- Source summary: `{Path(item['summary_path']).name}`",
                "- DuoGraph3D event excerpt:",
            ]
        )
        for event in item["duograph_events"]:
            lines.append(f"  - `{event['event_type']}` step={event['step_id']} payload={event['payload']}")
        lines.append("- Single-layer event excerpt:")
        for event in item["single_layer_events"]:
            lines.append(f"  - `{event['event_type']}` step={event['step_id']} payload={event['payload']}")
        lines.append("- Counterfactual event excerpt:")
        for event in item["counterfactual_events"]:
            lines.append(f"  - `{event['event_type']}` step={event['step_id']} payload={event['payload']}")
        lines.append("")
    return "\n".join(lines)
