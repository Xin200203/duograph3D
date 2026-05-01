"""Carrier / export oracle gap metrics — Phase 甲 monitoring table.

Tracks export decisions and computes oracle-gap diagnostics by comparing
the chosen export carrier against available alternatives.
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class CarrierChoiceRow:
    """One row in the carrier choice monitoring table."""
    entity_id: str = ""
    scene_id: str = ""
    chosen_source: str = ""
    fallback_reason: str = ""
    memory_object_count: int = 0
    key_object_count: int = 0
    memory_point_count: int = 0
    key_point_budget: int = 0
    memory_key_ratio: float = 0.0
    memory_point_ratio: float = 0.0


@dataclass
class CarrierOracleSummary:
    """Export carrier choice and oracle gap summary."""
    run_id: str = ""
    scene_id: str = ""
    export_source_selected: str = ""
    export_source_strategy: str = ""
    fallback_reason: str = ""
    memory_object_count: int = 0
    key_object_count: int = 0
    memory_key_ratio: float = 0.0
    memory_point_ratio: float = 0.0
    coverage_verdict: str = ""
    rows: list[CarrierChoiceRow] = field(default_factory=list)


def _coerce_str(value: object, default: str = "") -> str:
    if value is None: return default
    return str(value)


def _coerce_int(value: object, default: int = 0) -> int:
    try: return int(value)
    except (TypeError, ValueError): return default


def _coerce_float(value: object, default: float = 0.0) -> float:
    try: return float(value)
    except (TypeError, ValueError): return default


def build_carrier_table(
    event_stream: list[dict[str, object]],
    *,
    run_id: str = "",
    scene_id: str = "",
) -> CarrierOracleSummary:
    """Build the carrier/export choice monitoring table."""
    summary = CarrierOracleSummary(run_id=run_id, scene_id=scene_id)

    for record in event_stream:
        event_type = _coerce_str(record.get("event_type"))

        if event_type == "export_source_selected":
            summary.export_source_selected = _coerce_str(record.get("selected_source"))
            summary.export_source_strategy = _coerce_str(record.get("requested_source"))
            summary.fallback_reason = _coerce_str(record.get("fallback_reason"))
            summary.memory_object_count = _coerce_int(record.get("memory_object_count"))
            summary.key_object_count = _coerce_int(record.get("key_object_count"))
            summary.memory_key_ratio = _coerce_float(record.get("memory_key_ratio"))
            summary.memory_point_ratio = _coerce_float(record.get("memory_point_ratio"))

        elif event_type == "memory_export_diagnostic":
            row = CarrierChoiceRow(
                entity_id=_coerce_str(record.get("entity_id")),
                scene_id=scene_id,
                chosen_source=_coerce_str(record.get("chosen_source")),
                fallback_reason=_coerce_str(record.get("fallback_reason")),
                memory_object_count=_coerce_int(record.get("memory_object_count")),
                key_object_count=_coerce_int(record.get("key_object_count")),
                memory_point_count=_coerce_int(record.get("memory_point_count")),
                key_point_budget=_coerce_int(record.get("key_point_budget")),
                memory_key_ratio=_coerce_float(record.get("memory_key_ratio")),
                memory_point_ratio=_coerce_float(record.get("memory_point_ratio")),
            )
            summary.rows.append(row)

    # Coverage verdict
    if summary.fallback_reason == "memory_coverage_pass":
        summary.coverage_verdict = "pass"
    elif summary.fallback_reason and summary.fallback_reason.startswith("forced"):
        summary.coverage_verdict = "forced"
    elif summary.fallback_reason:
        summary.coverage_verdict = "fallback"
    else:
        summary.coverage_verdict = "unknown"

    return summary


def carrier_summary_to_dict(summary: CarrierOracleSummary) -> dict[str, object]:
    """Convert summary to JSON-serializable dict."""
    return {
        "run_id": summary.run_id,
        "scene_id": summary.scene_id,
        "export_source_selected": summary.export_source_selected,
        "export_source_strategy": summary.export_source_strategy,
        "fallback_reason": summary.fallback_reason,
        "memory_object_count": summary.memory_object_count,
        "key_object_count": summary.key_object_count,
        "memory_key_ratio": summary.memory_key_ratio,
        "memory_point_ratio": summary.memory_point_ratio,
        "coverage_verdict": summary.coverage_verdict,
        "rows": [
            {
                "entity_id": r.entity_id,
                "chosen_source": r.chosen_source,
                "fallback_reason": r.fallback_reason,
                "memory_object_count": r.memory_object_count,
                "key_object_count": r.key_object_count,
                "memory_key_ratio": r.memory_key_ratio,
                "memory_point_ratio": r.memory_point_ratio,
            }
            for r in summary.rows
        ],
    }
