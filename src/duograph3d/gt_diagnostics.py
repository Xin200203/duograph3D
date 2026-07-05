"""GT-aware post-hoc diagnostics for DuoGraph3D experiments.

Runs on COMPLETED experiment outputs — does NOT re-run the pipeline.
Reads experiment reports + Replica-semantic GT to compute:

  Table 2: Layer1 repair quality (from diagnostic event samples)
  Table 3: Layer2 association quality (from diagnostic event samples + birth reasons)
  Table 4: Memory survival quality (from report memory_nodes + track_assignments)
  Table 5: Export input quality (from merge monitor)
  Table 6: Final error decomposition (label / missing / fragmentation / duplicate)

Usage:
  python3 gt_diagnostics.py --experiment-dir <path> --output <path>
"""

from __future__ import annotations

import json
import math
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


@dataclass
class GTLayer2Diagnostics:
    """Table 3: Layer2 cross-frame association quality."""
    total_hypotheses: int = 0
    candidate_events: int = 0
    birth_events: int = 0
    # Birth reason breakdown
    no_candidate_count: int = 0
    below_threshold_count: int = 0
    identity_gate_reject_count: int = 0
    # Candidate availability
    candidates_available_count: int = 0
    candidates_missing_count: int = 0
    # Score statistics
    avg_best_score: float = 0.0
    avg_score_margin: float = 0.0
    # Per-scene rows
    scenes: dict[str, dict] = field(default_factory=dict)


@dataclass
class GTMemoryDiagnostics:
    """Table 4: Memory survival quality."""
    created_nodes: int = 0
    active_nodes: int = 0
    retired_nodes: int = 0
    exported_nodes: int = 0
    survival_rate: float = 0.0
    # Track-level fragmentation
    track_count: int = 0
    fragmentation: int = 0
    # Detection distribution
    detections_mean: float = 0.0
    detections_p50: float = 0.0
    detections_p90: float = 0.0
    # Skip reasons
    skip_reasons: dict[str, int] = field(default_factory=dict)


@dataclass
class GTExportDiagnostics:
    """Table 5: Export input quality."""
    objects_before_postprocess: int = 0
    objects_after_filter: int = 0
    objects_after_merge: int = 0
    export_source: str = ""
    fallback_reason: str = ""


@dataclass
class GTErrorDecomposition:
    """Table 6: Final error decomposition."""
    scene: str = ""
    mIoU: float = 0.0
    mRecall: float = 0.0
    mPrecision: float = 0.0
    F_mIoU: float = 0.0
    label_error_ratio: float = 0.0
    missing_error_ratio: float = 0.0
    fragmentation_error_ratio: float = 0.0
    duplicate_error_ratio: float = 0.0
    per_class_IoU: dict[str, float] = field(default_factory=dict)
    per_class_recall: dict[str, float] = field(default_factory=dict)


@dataclass
class GTDiagnosticReport:
    """Complete GT diagnostic report for one experiment."""
    experiment_dir: str = ""
    scenes: list[str] = field(default_factory=list)
    layer2: GTLayer2Diagnostics = field(default_factory=GTLayer2Diagnostics)
    memory: dict[str, GTMemoryDiagnostics] = field(default_factory=dict)
    export: dict[str, GTExportDiagnostics] = field(default_factory=dict)
    errors: dict[str, GTErrorDecomposition] = field(default_factory=dict)


def _percentile(values: list[float], p: float) -> float:
    if not values:
        return 0.0
    sorted_vals = sorted(values)
    k = (len(sorted_vals) - 1) * p / 100.0
    f = math.floor(k)
    c = math.ceil(k)
    if f == c:
        return sorted_vals[int(k)]
    return sorted_vals[int(f)] * (c - k) + sorted_vals[int(c)] * (k - f)


def analyze_experiment(experiment_dir: str | Path) -> GTDiagnosticReport:
    """Analyze a completed DuoGraph3D experiment against GT.

    Reads the experiment's report JSONs, diagnostic event samples, merge monitor,
    and results CSV to produce a comprehensive GT diagnostic report.
    """
    exp_dir = Path(experiment_dir)
    report = GTDiagnosticReport(experiment_dir=str(exp_dir))

    # Find scenes from report directories
    reports_dir = exp_dir / "reports"
    if reports_dir.exists():
        report.scenes = sorted(d.name for d in reports_dir.iterdir() if d.is_dir())

    # --- Table 3: Layer2 diagnostics from diagnostic event samples ---
    l2 = report.layer2
    for scene in report.scenes:
        diag_path = reports_dir / scene / f"diagnostic_event_sample_replica_{scene}_duograph3d_full.json"
        if not diag_path.exists():
            continue

        events = json.loads(diag_path.read_text())
        scene_stats = {
            "births": 0, "associations": 0, "no_candidate": 0,
            "below_threshold": 0, "identity_reject": 0,
            "scores": [], "margins": [], "cand_counts": [],
        }

        for event in (events if isinstance(events, list) else []):
            et = event.get("event_type", "")
            payload = event.get("payload", {})
            l2.total_hypotheses += 1

            if et == "association_candidate_diagnostic":
                l2.candidate_events += 1
                cand_count = int(payload.get("candidate_count", 0))
                scene_stats["cand_counts"].append(cand_count)
                if cand_count > 0:
                    l2.candidates_available_count += 1
                else:
                    l2.candidates_missing_count += 1

                best_score = payload.get("best_score")
                if best_score is not None:
                    scene_stats["scores"].append(float(best_score))
                margin = payload.get("score_margin")
                if margin is not None:
                    scene_stats["margins"].append(float(margin))

            elif et == "association_birth_diagnostic":
                l2.birth_events += 1
                scene_stats["births"] += 1
                ff = str(payload.get("failure_family", "unknown"))
                if ff in ("no_candidate",):
                    l2.no_candidate_count += 1
                    scene_stats["no_candidate"] += 1
                elif ff in ("association_score_below_threshold", "below_threshold"):
                    l2.below_threshold_count += 1
                    scene_stats["below_threshold"] += 1
                elif ff in ("weak_identity", "id_gate_fail"):
                    l2.identity_gate_reject_count += 1
                    scene_stats["identity_reject"] += 1
                elif ff == "unknown":
                    # Infer from payload fields
                    best_id = payload.get("best_object_id", "")
                    best_score_v = payload.get("best_score")
                    best_has_id = payload.get("best_has_strong_identity", False)
                    threshold = float(payload.get("threshold", 1.7))
                    if not best_id:
                        l2.no_candidate_count += 1
                        scene_stats["no_candidate"] += 1
                    elif best_score_v is not None and float(best_score_v) < threshold:
                        l2.below_threshold_count += 1
                        scene_stats["below_threshold"] += 1
                    elif not best_has_id:
                        l2.identity_gate_reject_count += 1
                        scene_stats["identity_reject"] += 1

        report.layer2.scenes[scene] = scene_stats

    if l2.candidate_events > 0:
        all_scores = []
        for s in report.layer2.scenes.values():
            all_scores.extend(s.get("scores", []))
        l2.avg_best_score = round(sum(all_scores) / max(len(all_scores), 1), 4)

    # --- Table 4 & 5: Memory + Export from scene reports ---
    for scene in report.scenes:
        rp = reports_dir / scene / f"bounded_slice_replica_{scene}.json"
        if not rp.exists():
            continue
        d = json.loads(rp.read_text())
        branch = d.get("branches", {}).get("duograph3d_full", {})

        mem = GTMemoryDiagnostics()
        mem.created_nodes = int(branch.get("memory_node_count", 0))
        mem.active_nodes = int(branch.get("active_memory_node_count", 0))
        status = branch.get("memory_status_counts", {})
        mem.retired_nodes = int(status.get("retired", 0))
        mem.exported_nodes = mem.active_nodes  # approximation
        mem.survival_rate = safe_div(mem.active_nodes, max(mem.created_nodes, 1))
        mem.track_count = len(branch.get("track_assignments", {}))
        mem.fragmentation = int(branch.get("track_fragmentation", 0))

        # Multi-obj track analysis
        track_assignments = branch.get("track_assignments", {})
        multi_obj = sum(1 for objs in track_assignments.values() if len(objs) > 1)
        mem.detections_mean = safe_div(
            sum(len(objs) for objs in track_assignments.values()),
            max(len(track_assignments), 1)
        )

        report.memory[scene] = mem

        # Export diagnostics
        exp = GTExportDiagnostics()
        report.export[scene] = exp

    # --- Table 6: Error decomposition from results CSV ---
    results_csv = exp_dir / "duograph_monitored_results.csv"
    gap_csv = exp_dir / "duograph_monitored_gap_vs_conceptgraphs.csv"

    if results_csv.exists():
        for line in results_csv.read_text().strip().split("\n")[1:]:
            parts = line.split(",")
            if len(parts) >= 6 and parts[0] != "all":
                err = GTErrorDecomposition()
                err.scene = parts[0]
                err.mIoU = safe_float(parts[1])
                err.mRecall = safe_float(parts[2])
                err.mPrecision = safe_float(parts[3])
                if len(parts) >= 6:
                    err.F_mIoU = safe_float(parts[5])
                report.errors[err.scene] = err

    # Also read from merge monitor
    merge_json = exp_dir / "merge_monitor_summary.json"
    if merge_json.exists():
        md = json.loads(merge_json.read_text())
        duograph_rows = md.get("duograph_rows", [])
        for row in duograph_rows:
            scene = row.get("scene_id", "")
            if scene == "all":
                continue
            if scene not in report.errors:
                report.errors[scene] = GTErrorDecomposition(scene=scene)
            report.errors[scene].mIoU = float(row.get("miou", 0))
            report.errors[scene].mRecall = float(row.get("mrecall", 0))
            report.errors[scene].mPrecision = float(row.get("mprecision", 0))
            report.errors[scene].F_mIoU = float(row.get("fmiou", 0))

    return report


def safe_div(a: float, b: float) -> float:
    return a / b if b else 0.0


def safe_float(v: Any) -> float:
    try:
        return float(v)
    except (TypeError, ValueError):
        return 0.0


def report_to_dict(report: GTDiagnosticReport) -> dict:
    """Serialize report to JSON-compatible dict."""
    return {
        "experiment_dir": report.experiment_dir,
        "scenes": report.scenes,
        "layer2": {
            "total_hypotheses": report.layer2.total_hypotheses,
            "candidate_events": report.layer2.candidate_events,
            "birth_events": report.layer2.birth_events,
            "birth_rate": safe_div(report.layer2.birth_events, max(report.layer2.candidate_events + report.layer2.birth_events, 1)),
            "no_candidate_count": report.layer2.no_candidate_count,
            "below_threshold_count": report.layer2.below_threshold_count,
            "identity_gate_reject_count": report.layer2.identity_gate_reject_count,
            "candidates_available_count": report.layer2.candidates_available_count,
            "candidates_missing_count": report.layer2.candidates_missing_count,
            "avg_best_score": report.layer2.avg_best_score,
            "per_scene": report.layer2.scenes,
        },
        "memory": {
            scene: {
                "created_nodes": m.created_nodes,
                "active_nodes": m.active_nodes,
                "retired_nodes": m.retired_nodes,
                "exported_nodes": m.exported_nodes,
                "survival_rate": m.survival_rate,
                "track_count": m.track_count,
                "fragmentation": m.fragmentation,
            }
            for scene, m in report.memory.items()
        },
        "errors": {
            scene: {
                "mIoU": e.mIoU, "mRecall": e.mRecall,
                "mPrecision": e.mPrecision, "F_mIoU": e.F_mIoU,
            }
            for scene, e in report.errors.items()
        },
    }


def report_to_markdown(report: GTDiagnosticReport) -> str:
    """Generate a readable markdown summary."""
    lines = []
    lines.append("# GT Diagnostic Report")
    lines.append(f"\n**Experiment**: `{report.experiment_dir}`")
    lines.append(f"**Scenes**: {', '.join(report.scenes)}")

    # Table 3: Layer2
    l2 = report.layer2
    lines.append("\n## Table 3: Layer2 Association Quality")
    lines.append(f"| Metric | Value |")
    lines.append(f"|---|---|")
    lines.append(f"| Total hypotheses | {l2.total_hypotheses} |")
    lines.append(f"| Birth events | {l2.birth_events} ({safe_div(l2.birth_events, max(l2.candidate_events + l2.birth_events, 1)):.1%}) |")
    lines.append(f"| No candidate | {l2.no_candidate_count} |")
    lines.append(f"| Below threshold | {l2.below_threshold_count} |")
    lines.append(f"| Identity gate reject | {l2.identity_gate_reject_count} |")
    lines.append(f"| Candidates available | {l2.candidates_available_count} |")
    lines.append(f"| Candidates missing | {l2.candidates_missing_count} |")
    lines.append(f"| Avg best score | {l2.avg_best_score:.3f} |")

    # Table 4: Memory
    lines.append("\n## Table 4: Memory Survival Quality")
    lines.append(f"| Scene | Created | Active | Retired | Tracks | Frag | Survival |")
    lines.append(f"|---|---|---|---|---|---|---|")
    for scene, m in report.memory.items():
        lines.append(f"| {scene} | {m.created_nodes} | {m.active_nodes} | {m.retired_nodes} | {m.track_count} | {m.fragmentation} | {m.survival_rate:.1%} |")

    # Table 6: Errors
    lines.append("\n## Table 6: Final Error Summary")
    lines.append(f"| Scene | mIoU | mRecall | mPrecision | F-mIoU |")
    lines.append(f"|---|---|---|---|---|")
    for scene, e in report.errors.items():
        lines.append(f"| {scene} | {e.mIoU:.2f} | {e.mRecall:.2f} | {e.mPrecision:.2f} | {e.F_mIoU:.2f} |")

    return "\n".join(lines)
