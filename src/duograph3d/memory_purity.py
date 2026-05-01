"""Memory purity metrics — Phase 甲 monitoring table.

Processes birth, association, absorption, merge, and consolidation events
from the event stream to compute per-node purity and stability statistics.
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field


@dataclass
class MemoryPurityRow:
    """One row in the memory purity monitoring table."""
    object_id: str = ""
    status: str = ""
    birth_step: int = 0
    last_seen_step: int = 0
    detection_count: int = 0
    n_associations: int = 0
    n_absorptions: int = 0
    n_merges_in: int = 0
    n_conflicts: int = 0
    ambiguity_flags: list[str] = field(default_factory=list)
    failure_tags: list[str] = field(default_factory=list)
    is_retired: bool = False
    retired_by: str = ""


@dataclass
class MemoryPuritySummary:
    """Aggregated memory purity summary across a run."""
    run_id: str = ""
    scene_id: str = ""
    total_nodes_created: int = 0
    total_nodes_retired: int = 0
    nodes_active_final: int = 0
    nodes_dormant_final: int = 0
    nodes_retired_final: int = 0
    total_associations: int = 0
    total_absorptions: int = 0
    total_births: int = 0
    total_merges: int = 0
    total_deaths: int = 0
    avg_detections_per_node: float = 0.0
    rows: list[MemoryPurityRow] = field(default_factory=list)


def _coerce_str(value: object, default: str = "") -> str:
    if value is None: return default
    return str(value)


def _coerce_int(value: object, default: int = 0) -> int:
    try: return int(value)
    except (TypeError, ValueError): return default


def _coerce_list(value: object, default: list | None = None) -> list:
    if default is None: default = []
    if isinstance(value, (list, tuple)): return list(value)
    return default


def build_memory_purity_table(
    event_stream: list[dict[str, object]],
    *,
    run_id: str = "",
    scene_id: str = "",
) -> MemoryPuritySummary:
    """Build the memory purity monitoring table from an event stream."""
    summary = MemoryPuritySummary(run_id=run_id, scene_id=scene_id)
    node_state: dict[str, dict] = defaultdict(lambda: {
        "n_associations": 0, "n_absorptions": 0, "n_merges_in": 0, "n_conflicts": 0,
        "ambiguity_flags": [], "failure_tags": [],
    })

    for record in event_stream:
        event_type = _coerce_str(record.get("event_type"))

        if event_type == "birth_commit":
            summary.total_births += 1
            oid = _coerce_str(record.get("object_id"))
            step = _coerce_int(record.get("step_id"))
            node_state[oid]["birth_step"] = step
            node_state[oid]["status"] = "active"
            flags = _coerce_list(record.get("ambiguity_flags"))
            if flags:
                node_state[oid]["ambiguity_flags"].extend(flags)

        elif event_type == "association_commit":
            summary.total_associations += 1
            oid = _coerce_str(record.get("object_id"))
            node_state[oid]["n_associations"] += 1
            node_state[oid]["status"] = "active"

        elif event_type == "residual_absorption_commit":
            summary.total_absorptions += 1
            oid = _coerce_str(record.get("object_id"))
            node_state[oid]["n_absorptions"] += 1

        elif event_type == "death_commit":
            summary.total_deaths += 1
            oid = _coerce_str(record.get("object_id"))
            node_state[oid]["status"] = "retired"
            node_state[oid]["retired_by"] = "miss_count_exceeded"

        elif event_type == "memory_authority_used":
            oid = _coerce_str(record.get("object_id"))
            node_state[oid]["n_conflicts"] += 1

        elif event_type == "memory_object_consolidation":
            merges = record.get("merges", [])
            if isinstance(merges, list):
                summary.total_merges += len(merges)
                for merge in merges:
                    if isinstance(merge, dict):
                        source_id = _coerce_str(merge.get("source_object_id"))
                        node_state[source_id]["n_merges_in"] += 1
                        node_state[source_id]["status"] = "retired"
                        node_state[source_id]["retired_by"] = "merged_into_duplicate"
            filtered = _coerce_list(record.get("filtered_object_ids"))
            for fid in filtered:
                node_state[_coerce_str(fid)]["status"] = "retired"
                node_state[_coerce_str(fid)]["retired_by"] = "filtered_low_detection"

    # Build rows
    for oid, state in sorted(node_state.items()):
        row = MemoryPurityRow(
            object_id=oid,
            status=_coerce_str(state.get("status", "")),
            birth_step=_coerce_int(state.get("birth_step")),
            last_seen_step=_coerce_int(state.get("last_seen_step")),
            n_associations=_coerce_int(state.get("n_associations")),
            n_absorptions=_coerce_int(state.get("n_absorptions")),
            n_merges_in=_coerce_int(state.get("n_merges_in")),
            n_conflicts=_coerce_int(state.get("n_conflicts")),
            ambiguity_flags=_coerce_list(state.get("ambiguity_flags")),
            is_retired=state.get("status") == "retired",
            retired_by=_coerce_str(state.get("retired_by")),
        )
        summary.rows.append(row)

        status = state.get("status", "")
        if status == "active":
            summary.nodes_active_final += 1
        elif status == "dormant":
            summary.nodes_dormant_final += 1
        elif status == "retired":
            summary.nodes_retired_final += 1

    summary.total_nodes_created = len(node_state)
    summary.total_nodes_retired = summary.nodes_retired_final

    avg_assoc_per_node = (
        sum(r.n_associations + r.n_absorptions for r in summary.rows)
        / max(len(summary.rows), 1)
    )
    summary.avg_detections_per_node = round(avg_assoc_per_node, 2)

    return summary


def memory_purity_summary_to_dict(summary: MemoryPuritySummary) -> dict[str, object]:
    """Convert summary to JSON-serializable dict."""
    return {
        "run_id": summary.run_id,
        "scene_id": summary.scene_id,
        "total_nodes_created": summary.total_nodes_created,
        "total_nodes_retired": summary.total_nodes_retired,
        "nodes_active_final": summary.nodes_active_final,
        "nodes_dormant_final": summary.nodes_dormant_final,
        "nodes_retired_final": summary.nodes_retired_final,
        "total_associations": summary.total_associations,
        "total_absorptions": summary.total_absorptions,
        "total_births": summary.total_births,
        "total_merges": summary.total_merges,
        "total_deaths": summary.total_deaths,
        "avg_detections_per_node": summary.avg_detections_per_node,
        "rows": [
            {
                "object_id": r.object_id,
                "status": r.status,
                "birth_step": r.birth_step,
                "n_associations": r.n_associations,
                "n_absorptions": r.n_absorptions,
                "n_merges_in": r.n_merges_in,
                "n_conflicts": r.n_conflicts,
                "is_retired": r.is_retired,
                "retired_by": r.retired_by,
            }
            for r in summary.rows
        ],
    }
