"""Unified shadow metrics reporter — Phase 甲.

Generates the four core monitoring tables (candidate recall, memory purity,
promotion/pending counts, carrier oracle gap) from a unified event stream JSONL
and the corresponding pipeline result snapshot.

This is the single entry point for Phase 甲 metric generation.
"""

from __future__ import annotations

from pathlib import Path
import json

from .candidate_metrics import (
    build_candidate_recall_table,
    CandidateRecallSummary,
    candidate_recall_summary_to_dict,
)
from .memory_purity import (
    build_memory_purity_table,
    MemoryPuritySummary,
    memory_purity_summary_to_dict,
)
from .carrier_metrics import (
    build_carrier_table,
    CarrierOracleSummary,
    carrier_summary_to_dict,
)
from .experiment_logger import load_event_stream


def generate_shadow_report(
    event_stream_path: str | Path,
    *,
    run_id: str = "",
    scene_id: str = "",
    output_dir: str | Path | None = None,
) -> dict[str, object]:
    """Generate the complete Phase 甲 shadow monitoring report.

    Args:
        event_stream_path: Path to the JSONL event stream file.
        run_id: Experiment run identifier.
        scene_id: Scene name (e.g., room0, room1).
        output_dir: If provided, write individual metric JSON files here.

    Returns:
        A dict with keys ``candidate_recall``, ``memory_purity``,
        ``carrier``, and ``meta`` containing the full monitoring report.
    """
    records = load_event_stream(event_stream_path)
    if not records:
        return {"error": f"Empty event stream: {event_stream_path}"}

    candidate = build_candidate_recall_table(records, run_id=run_id, scene_id=scene_id)
    purity = build_memory_purity_table(records, run_id=run_id, scene_id=scene_id)
    carrier = build_carrier_table(records, run_id=run_id, scene_id=scene_id)

    # Build promotion/pending counts from event stream
    promotion = _build_promotion_table(records, run_id=run_id, scene_id=scene_id)

    report = {
        "meta": {
            "run_id": run_id,
            "scene_id": scene_id,
            "event_count": len(records),
            "schema_version": "v2",
        },
        "candidate_recall": candidate_recall_summary_to_dict(candidate),
        "memory_purity": memory_purity_summary_to_dict(purity),
        "promotion_pending": promotion,
        "carrier": carrier_summary_to_dict(carrier),
    }

    if output_dir:
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)
        _write_json(output_dir / f"{scene_id}_candidate_recall.json", report["candidate_recall"])
        _write_json(output_dir / f"{scene_id}_memory_purity.json", report["memory_purity"])
        _write_json(output_dir / f"{scene_id}_promotion_pending.json", report["promotion_pending"])
        _write_json(output_dir / f"{scene_id}_carrier.json", report["carrier"])
        _write_json(output_dir / f"{scene_id}_shadow_report.json", report)

    return report


def _build_promotion_table(
    records: list[dict[str, object]],
    *,
    run_id: str = "",
    scene_id: str = "",
) -> dict[str, object]:
    """Build promotion/pending counts from event stream.

    Currently tracks tentative/promotion placeholders. Filled in
    detail during Phase 丙 (tentative/promotion/working-stable memory).
    """
    step_counts: dict[int, dict[str, int]] = {}
    total_births = 0
    total_associations = 0
    total_absorptions = 0
    total_reentries = 0

    for record in records:
        event_type = str(record.get("event_type", ""))
        step_id = int(record.get("step_id", 0) or 0)

        if step_id not in step_counts:
            step_counts[step_id] = {"births": 0, "associations": 0, "absorptions": 0, "reentries": 0}

        if event_type == "birth_commit":
            step_counts[step_id]["births"] += 1
            total_births += 1
        elif event_type == "association_commit":
            action = str(record.get("action", ""))
            if action == "reentry":
                step_counts[step_id]["reentries"] += 1
                total_reentries += 1
            else:
                step_counts[step_id]["associations"] += 1
                total_associations += 1
        elif event_type == "residual_absorption_commit":
            step_counts[step_id]["absorptions"] += 1
            total_absorptions += 1

    return {
        "run_id": run_id,
        "scene_id": scene_id,
        "total_births": total_births,
        "total_associations": total_associations,
        "total_absorptions": total_absorptions,
        "total_reentries": total_reentries,
        "step_counts": [
            {
                "step_id": step_id,
                "births": counts.get("births", 0),
                "associations": counts.get("associations", 0),
                "absorptions": counts.get("absorptions", 0),
                "reentries": counts.get("reentries", 0),
            }
            for step_id, counts in sorted(step_counts.items())
        ],
    }


def compare_shadow_reports(
    baseline: dict[str, object],
    candidate: dict[str, object],
) -> dict[str, object]:
    """Compare two shadow reports and produce a delta report."""
    deltas = {}

    # Candidate recall comparison
    base_cr = baseline.get("candidate_recall", {})
    cand_cr = candidate.get("candidate_recall", {})
    cr_delta = {}
    for key in ("birth_rate", "avg_best_score", "avg_score_margin",
                "no_candidate_count", "below_threshold_count", "weak_identity_count"):
        base_val = float(base_cr.get(key, 0) or 0)
        cand_val = float(cand_cr.get(key, 0) or 0)
        cr_delta[key] = round(cand_val - base_val, 4)
    deltas["candidate_recall"] = cr_delta

    # Memory purity comparison
    base_mp = baseline.get("memory_purity", {})
    cand_mp = candidate.get("memory_purity", {})
    mp_delta = {}
    for key in ("total_nodes_created", "nodes_active_final", "avg_detections_per_node",
                "total_births", "total_merges", "total_deaths"):
        base_val = float(base_mp.get(key, 0) or 0)
        cand_val = float(cand_mp.get(key, 0) or 0)
        mp_delta[key] = round(cand_val - base_val, 4)
    deltas["memory_purity"] = mp_delta

    # Promotion comparison
    base_pp = baseline.get("promotion_pending", {})
    cand_pp = candidate.get("promotion_pending", {})
    pp_delta = {}
    for key in ("total_births", "total_associations", "total_absorptions", "total_reentries"):
        base_val = float(base_pp.get(key, 0) or 0)
        cand_val = float(cand_pp.get(key, 0) or 0)
        pp_delta[key] = round(cand_val - base_val, 4)
    deltas["promotion_pending"] = pp_delta

    return {
        "baseline_run_id": baseline.get("meta", {}).get("run_id", ""),
        "candidate_run_id": candidate.get("meta", {}).get("run_id", ""),
        "deltas": deltas,
    }


def _write_json(path: Path, data: object) -> None:
    path.write_text(json.dumps(data, indent=2, default=str))
