"""Candidate recall metrics — Phase 甲 monitoring table.

Processes ``association_candidate_diagnostic`` and ``association_birth_diagnostic``
events from the unified event stream to compute per-hypothesis candidate recall
statistics.
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field


@dataclass
class CandidateRecallRow:
    """One row in the candidate recall monitoring table."""
    run_id: str = ""
    scene_id: str = ""
    frame_id: int = 0
    step_id: int = 0
    hypothesis_id: str = ""
    track_hint: str = ""
    cand_budget: int = 0
    cand_count_raw: int = 0
    cand_count_top_b: int = 0
    best_object_id: str = ""
    best_score: float = 0.0
    second_score: float | None = None
    score_margin: float = 0.0
    best_has_strong_identity: bool = False
    threshold: float = 0.0
    action: str = ""
    birth_reason: str = ""
    failure_family: str = ""
    miss_bucket: str = ""
    top_candidate_ids: list[str] = field(default_factory=list)


@dataclass
class CandidateRecallSummary:
    """Aggregated candidate recall summary across a run."""
    run_id: str = ""
    scene_id: str = ""
    total_hypotheses: int = 0
    association_count: int = 0
    absorption_count: int = 0
    birth_count: int = 0
    # Candidate availability
    no_candidate_count: int = 0
    candidates_available_count: int = 0
    # Birth failure decomposition
    below_threshold_count: int = 0
    weak_identity_count: int = 0
    semantic_gate_low_count: int = 0
    spatial_overlap_gate_low_count: int = 0
    unrepaired_birth_count: int = 0
    # Score statistics
    avg_best_score: float = 0.0
    avg_score_margin: float = 0.0
    # Raw rows for downstream analysis
    rows: list[CandidateRecallRow] = field(default_factory=list)


def _coerce_float(value: object, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _coerce_int(value: object, default: int = 0) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _coerce_str(value: object, default: str = "") -> str:
    if value is None:
        return default
    return str(value)


def build_candidate_recall_table(
    event_stream: list[dict[str, object]],
    *,
    run_id: str = "",
    scene_id: str = "",
) -> CandidateRecallSummary:
    """Build the candidate recall monitoring table from an event stream.

    Extracts per-hypothesis candidate availability, score ranking, and
    birth-failure decomposition from association diagnostic events.
    """
    summary = CandidateRecallSummary(run_id=run_id, scene_id=scene_id)
    rows: list[CandidateRecallRow] = []

    for record in event_stream:
        event_type = _coerce_str(record.get("event_type"))
        if event_type not in ("association_candidate_diagnostic", "association_birth_diagnostic"):
            continue

        step_id = _coerce_int(record.get("step_id"))
        hypothesis_id = _coerce_str(record.get("hypothesis_id"))
        track_hint = _coerce_str(record.get("track_hint"))
        cand_budget = _coerce_int(record.get("candidate_budget"))
        cand_count = _coerce_int(record.get("candidate_count"))
        best_id = _coerce_str(record.get("best_object_id"))
        best_score = _coerce_float(record.get("best_score"))
        second_score = record.get("second_score")
        second_score = _coerce_float(second_score) if second_score is not None else None
        score_margin = _coerce_float(record.get("score_margin"))
        best_has_identity = bool(record.get("best_has_strong_identity", False))
        threshold = _coerce_float(record.get("threshold"))

        top_candidates = record.get("top_candidates", [])
        if isinstance(top_candidates, list):
            top_candidate_ids = [_coerce_str(c.get("object_id", "")) if isinstance(c, dict) else str(c) for c in top_candidates]
        else:
            top_candidate_ids = []

        birth_reason = _coerce_str(record.get("reason", ""))
        failure_family = _coerce_str(record.get("failure_family", ""))

        # Determine action and miss bucket
        if event_type == "association_birth_diagnostic":
            action = "birth"
            miss_bucket = failure_family or birth_reason
        elif best_id and best_score >= threshold and best_has_identity:
            action = "associate"
            miss_bucket = ""
        elif best_id and best_score >= threshold and not best_has_identity:
            action = "birth"
            miss_bucket = "id_gate_fail"
        elif best_id and best_score < threshold:
            action = "birth"
            miss_bucket = "low_score"
        else:
            action = "birth"
            miss_bucket = "no_candidate"

        row = CandidateRecallRow(
            run_id=run_id,
            scene_id=scene_id,
            step_id=step_id,
            hypothesis_id=hypothesis_id,
            track_hint=track_hint,
            cand_budget=cand_budget,
            cand_count_raw=cand_count,
            cand_count_top_b=len(top_candidate_ids),
            best_object_id=best_id,
            best_score=best_score,
            second_score=second_score,
            score_margin=score_margin,
            best_has_strong_identity=best_has_identity,
            threshold=threshold,
            action=action,
            birth_reason=birth_reason,
            failure_family=failure_family,
            miss_bucket=miss_bucket,
            top_candidate_ids=top_candidate_ids,
        )
        rows.append(row)

        # Update summary counters
        summary.total_hypotheses += 1
        if action == "associate":
            summary.association_count += 1
        elif action == "absorb":
            summary.absorption_count += 1
        else:
            summary.birth_count += 1

        if miss_bucket == "no_candidate":
            summary.no_candidate_count += 1
        elif miss_bucket == "low_score":
            summary.below_threshold_count += 1
        elif miss_bucket in ("weak_identity", "id_gate_fail"):
            summary.weak_identity_count += 1
        elif miss_bucket == "semantic_gate_low":
            summary.semantic_gate_low_count += 1
        elif miss_bucket == "spatial_overlap_gate_low":
            summary.spatial_overlap_gate_low_count += 1
        elif miss_bucket == "unrepaired_birth":
            summary.unrepaired_birth_count += 1

        if best_id:
            summary.candidates_available_count += 1

    summary.rows = rows
    if rows:
        summary.avg_best_score = round(
            sum(r.best_score for r in rows) / len(rows), 4
        )
        summary.avg_score_margin = round(
            sum(r.score_margin for r in rows) / len(rows), 4
        )

    return summary


def candidate_recall_summary_to_dict(summary: CandidateRecallSummary) -> dict[str, object]:
    """Convert summary to JSON-serializable dict."""
    return {
        "run_id": summary.run_id,
        "scene_id": summary.scene_id,
        "total_hypotheses": summary.total_hypotheses,
        "association_count": summary.association_count,
        "absorption_count": summary.absorption_count,
        "birth_count": summary.birth_count,
        "birth_rate": round(summary.birth_count / max(summary.total_hypotheses, 1), 4),
        "no_candidate_count": summary.no_candidate_count,
        "candidates_available_count": summary.candidates_available_count,
        "below_threshold_count": summary.below_threshold_count,
        "weak_identity_count": summary.weak_identity_count,
        "semantic_gate_low_count": summary.semantic_gate_low_count,
        "spatial_overlap_gate_low_count": summary.spatial_overlap_gate_low_count,
        "unrepaired_birth_count": summary.unrepaired_birth_count,
        "avg_best_score": summary.avg_best_score,
        "avg_score_margin": summary.avg_score_margin,
        "rows": [
            {
                "step_id": r.step_id,
                "hypothesis_id": r.hypothesis_id,
                "track_hint": r.track_hint,
                "cand_count_raw": r.cand_count_raw,
                "cand_count_top_b": r.cand_count_top_b,
                "best_object_id": r.best_object_id,
                "best_score": r.best_score,
                "score_margin": r.score_margin,
                "action": r.action,
                "miss_bucket": r.miss_bucket,
                "failure_family": r.failure_family,
            }
            for r in summary.rows
        ],
    }
