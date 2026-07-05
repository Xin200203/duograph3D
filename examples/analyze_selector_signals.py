from __future__ import annotations

"""Offline calibration audit for GT-free export-hypothesis selection signals.

Walks archived run mirrors (merge_monitor_summary.json files), extracts one row
per (run, scene) pairing GT-free diagnostics with official gap metrics, then
answers the question that decides whether a multi-hypothesis carrier-authority
selector is feasible: *within a scene, do GT-free signals rank export variants
in the same order as the official evaluator?*

Standard library only.  Zero GPU.  Read-only over analysis/raw mirrors.

Usage:
  python3 examples/analyze_selector_signals.py --roots analysis/raw --output analysis/tmp/selector_signal_audit
"""

import argparse
import csv
import json
import math
from collections import defaultdict
from pathlib import Path


SIGNAL_COLUMNS = [
    "export_object_count",
    "post_merge_object_count",
    "fragmented_export_key_rate",
    "relabel_total",
    "blocked_relabel_total",
    "source_miss_total",
    "shape_fail_total",
    "low_clip_margin_rate",
    "low_confidence_mask_rate",
    "birth_no_candidate",
    "birth_below_threshold",
    "track_fragmentation_per_key",
    "detections_per_object_median",
    "points_per_object_median",
]

TARGET_COLUMNS = ["gap_miou", "gap_mf1score", "gap_fmiou"]

PARAM_COLUMNS = [
    "cg_merge_overlap_thresh",
    "geometry_repair_large_label_rules",
    "geometry_repair_keep_labels",
    "export_source",
]


def _median(values: list) -> float | None:
    cleaned = sorted(float(v) for v in values if isinstance(v, (int, float)))
    if not cleaned:
        return None
    mid = len(cleaned) // 2
    if len(cleaned) % 2:
        return cleaned[mid]
    return 0.5 * (cleaned[mid - 1] + cleaned[mid])


def _counter_total(value: object) -> float:
    if not isinstance(value, dict):
        return 0.0
    total = 0.0
    for count in value.values():
        try:
            total += float(count)
        except (TypeError, ValueError):
            continue
    return total


def _safe_rate(numerator: object, denominator: object) -> float | None:
    try:
        num = float(numerator)
        den = float(denominator)
    except (TypeError, ValueError):
        return None
    if den <= 0:
        return None
    return num / den


def extract_rows(summary_path: Path, raw_root: Path) -> list[dict]:
    try:
        data = json.loads(summary_path.read_text())
    except (json.JSONDecodeError, OSError):
        return []
    params = data.get("parameters", {}) if isinstance(data.get("parameters"), dict) else {}
    gap_by_scene = {}
    for row in data.get("gap_rows", []) or []:
        if isinstance(row, dict) and row.get("scene_id"):
            gap_by_scene[str(row["scene_id"])] = row
    rollup = data.get("monitor_rollup", {}) if isinstance(data.get("monitor_rollup"), dict) else {}
    rows: list[dict] = []
    scene_debugs = data.get("scene_debug", []) or []
    if isinstance(scene_debugs, dict):
        scene_debugs = [scene_debugs]
    for scene_debug in scene_debugs:
        if not isinstance(scene_debug, dict):
            continue
        scene = str(scene_debug.get("scene", ""))
        if not scene:
            continue
        export_monitor = scene_debug.get("export_monitor", {})
        if not isinstance(export_monitor, dict):
            export_monitor = {}
        repair_probe = export_monitor.get("geometry_repair_probe", {})
        if not isinstance(repair_probe, dict):
            repair_probe = {}
        gap = gap_by_scene.get(scene, {})
        detections_per_object = export_monitor.get("detections_per_exported_object", []) or []
        points_per_object = export_monitor.get("points_per_exported_object", []) or []
        kept = rollup.get("kept_observation_count")
        key_count = rollup.get("key_count")
        row = {
            "summary_path": str(summary_path.relative_to(raw_root)),
            "run_group": summary_path.relative_to(raw_root).parts[0],
            "variant": "/".join(summary_path.relative_to(raw_root).parts[1:-2]) or summary_path.parent.name,
            "pred_exp_name": data.get("pred_exp_name", ""),
            "scene": scene,
            # parameters that define the export hypothesis
            "cg_merge_overlap_thresh": params.get("cg_merge_overlap_thresh"),
            "geometry_repair_large_label_rules": params.get("geometry_repair_large_label_rules"),
            "geometry_repair_keep_labels": params.get("geometry_repair_keep_labels"),
            "export_source": params.get("export_source") or params.get("export_source_policy"),
            # GT-free signals
            "export_object_count": scene_debug.get("export_object_count"),
            "post_merge_object_count": export_monitor.get("post_merge_object_count"),
            "fragmented_export_key_rate": export_monitor.get("fragmented_export_key_rate"),
            "relabel_total": _counter_total(repair_probe.get("large_label_relabel_counts"))
            or _counter_total(repair_probe.get("relabel_counts")),
            "blocked_relabel_total": _counter_total(repair_probe.get("blocked_relabel_counts")),
            "source_miss_total": _counter_total(repair_probe.get("source_miss_counts")),
            "shape_fail_total": _counter_total(repair_probe.get("shape_fail_counts")),
            "low_clip_margin_rate": _safe_rate(rollup.get("low_clip_margin_count"), kept),
            "low_confidence_mask_rate": _safe_rate(rollup.get("low_confidence_mask_count"), rollup.get("raw_detection_count")),
            "birth_no_candidate": (rollup.get("birth_reasons") or {}).get("no_candidate") if isinstance(rollup.get("birth_reasons"), dict) else None,
            "birth_below_threshold": (rollup.get("birth_reasons") or {}).get("best_candidate_below_threshold") if isinstance(rollup.get("birth_reasons"), dict) else None,
            "track_fragmentation_per_key": _safe_rate(rollup.get("track_fragmentation"), key_count),
            "detections_per_object_median": _median(detections_per_object if isinstance(detections_per_object, list) else []),
            "points_per_object_median": _median(points_per_object if isinstance(points_per_object, list) else []),
            # targets (GT-dependent; used only for offline validation, never by the selector)
            "gap_miou": gap.get("gap_miou"),
            "gap_mf1score": gap.get("gap_mf1score"),
            "gap_fmiou": gap.get("gap_fmiou"),
        }
        rows.append(row)
    return rows


def _rank(values: list[float]) -> list[float]:
    order = sorted(range(len(values)), key=lambda i: values[i])
    ranks = [0.0] * len(values)
    i = 0
    while i < len(order):
        j = i
        while j + 1 < len(order) and values[order[j + 1]] == values[order[i]]:
            j += 1
        avg_rank = (i + j) / 2.0 + 1.0
        for k in range(i, j + 1):
            ranks[order[k]] = avg_rank
        i = j + 1
    return ranks


def spearman(xs: list[float], ys: list[float]) -> float | None:
    if len(xs) < 3 or len(xs) != len(ys):
        return None
    rx, ry = _rank(xs), _rank(ys)
    mx = sum(rx) / len(rx)
    my = sum(ry) / len(ry)
    cov = sum((a - mx) * (b - my) for a, b in zip(rx, ry))
    vx = math.sqrt(sum((a - mx) ** 2 for a in rx))
    vy = math.sqrt(sum((b - my) ** 2 for b in ry))
    if vx <= 0 or vy <= 0:
        return None
    return cov / (vx * vy)


def analyze(rows: list[dict]) -> dict:
    """Per-scene Spearman between each GT-free signal and gap_miou across variants."""
    by_scene: dict[str, list[dict]] = defaultdict(list)
    for row in rows:
        if row.get("gap_miou") is None:
            continue
        by_scene[row["scene"]].append(row)
    report: dict = {"per_scene_variant_counts": {s: len(v) for s, v in by_scene.items()}, "signals": {}}
    for signal in SIGNAL_COLUMNS:
        per_scene = {}
        for scene, scene_rows in by_scene.items():
            pairs = [
                (float(r[signal]), float(r["gap_miou"]))
                for r in scene_rows
                if isinstance(r.get(signal), (int, float)) and isinstance(r.get("gap_miou"), (int, float))
            ]
            # dedupe identical (signal, gap) rows from re-mirrored runs
            pairs = sorted(set(pairs))
            if len(pairs) >= 3:
                rho = spearman([p[0] for p in pairs], [p[1] for p in pairs])
                if rho is not None:
                    per_scene[scene] = {"rho": round(rho, 3), "n": len(pairs)}
        if per_scene:
            rhos = [v["rho"] for v in per_scene.values()]
            report["signals"][signal] = {
                "per_scene": per_scene,
                "mean_rho": round(sum(rhos) / len(rhos), 3),
                "scenes_with_abs_rho_ge_0_5": sum(1 for r in rhos if abs(r) >= 0.5),
            }
    return report


def _dedupe_variants(scene_rows: list[dict]) -> list[dict]:
    seen = set()
    unique = []
    for row in scene_rows:
        key = (
            row.get("pred_exp_name"),
            row.get("gap_miou"),
            row.get("export_object_count"),
            row.get("relabel_total"),
        )
        if key in seen:
            continue
        seen.add(key)
        unique.append(row)
    return unique


def regret_analysis(rows: list[dict]) -> dict:
    """Top-1 regret: if a GT-free policy picks one variant per scene, how far is it
    from the oracle-best variant?  This is the actual selector feasibility question."""

    def num(row: dict, key: str, default: float = 0.0) -> float:
        value = row.get(key)
        return float(value) if isinstance(value, (int, float)) else default

    policies = {
        "oracle_best": lambda rs: max(rs, key=lambda r: num(r, "gap_miou", -1e9)),
        "max_relabel_total": lambda rs: max(rs, key=lambda r: (num(r, "relabel_total"), num(r, "detections_per_object_median"))),
        "sparse_relabel_1_to_3": lambda rs: max(
            rs,
            key=lambda r: (
                1.0 if 1.0 <= num(r, "relabel_total") <= 3.0 else 0.0,
                -num(r, "fragmented_export_key_rate"),
                num(r, "detections_per_object_median"),
            ),
        ),
        "min_low_conf_mask_rate": lambda rs: min(rs, key=lambda r: num(r, "low_confidence_mask_rate", 1e9)),
        "max_export_objects": lambda rs: max(rs, key=lambda r: num(r, "export_object_count")),
        "min_fragmentation": lambda rs: min(rs, key=lambda r: num(r, "fragmented_export_key_rate", 1e9)),
        "no_repair_control": lambda rs: min(rs, key=lambda r: (num(r, "relabel_total"), -num(r, "gap_miou") * 0)),
    }
    by_scene: dict[str, list[dict]] = defaultdict(list)
    for row in rows:
        if isinstance(row.get("gap_miou"), (int, float)):
            by_scene[row["scene"]].append(row)
    result: dict = {}
    for name, pick in policies.items():
        per_scene = {}
        regrets = []
        for scene, scene_rows in by_scene.items():
            unique = _dedupe_variants(scene_rows)
            if len(unique) < 3:
                continue
            oracle = max(num(r, "gap_miou", -1e9) for r in unique)
            chosen = pick(unique)
            regret = oracle - num(chosen, "gap_miou")
            per_scene[scene] = {
                "regret_miou": round(regret, 3),
                "chosen_gap": round(num(chosen, "gap_miou"), 3),
                "oracle_gap": round(oracle, 3),
                "n_variants": len(unique),
            }
            regrets.append(regret)
        if regrets:
            result[name] = {
                "mean_regret": round(sum(regrets) / len(regrets), 3),
                "max_regret": round(max(regrets), 3),
                "per_scene": per_scene,
            }
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--roots", nargs="+", default=["analysis/raw"], type=Path)
    parser.add_argument("--output", type=Path, default=Path("analysis/tmp/selector_signal_audit"))
    args = parser.parse_args()

    all_rows: list[dict] = []
    for root in args.roots:
        root = root.resolve()
        for summary_path in sorted(root.rglob("merge_monitor_summary.json")):
            all_rows.extend(extract_rows(summary_path, root))

    args.output.mkdir(parents=True, exist_ok=True)
    tsv_path = args.output / "selector_signal_rows.tsv"
    columns = (
        ["summary_path", "run_group", "variant", "pred_exp_name", "scene"]
        + PARAM_COLUMNS
        + SIGNAL_COLUMNS
        + TARGET_COLUMNS
    )
    with tsv_path.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=columns, delimiter="\t", extrasaction="ignore")
        writer.writeheader()
        for row in all_rows:
            writer.writerow(row)

    report = analyze(all_rows)
    report["regret"] = regret_analysis(all_rows)
    report_path = args.output / "selector_signal_report.json"
    report_path.write_text(json.dumps(report, indent=2, sort_keys=True))
    print(f"rows={len(all_rows)} -> {tsv_path}")
    print(json.dumps({k: v for k, v in report.items() if k != "signals"}, indent=2))
    for signal, info in sorted(report.get("signals", {}).items(), key=lambda kv: -abs(kv[1]["mean_rho"])):
        print(f"{signal}: mean_rho={info['mean_rho']} strong_scenes={info['scenes_with_abs_rho_ge_0_5']}")


if __name__ == "__main__":
    main()
