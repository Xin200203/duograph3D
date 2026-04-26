from __future__ import annotations

from collections import Counter, defaultdict
from statistics import mean

from .contracts import SequenceRunResult
from .events import EventLogger


def _track_fragmentation(logger: EventLogger) -> tuple[int, dict[str, list[str]]]:
    track_to_objects: dict[str, set[str]] = defaultdict(set)
    for record in logger.records:
        if record.event_type not in {"birth_commit", "association_commit", "reentry_commit"}:
            continue
        track_hint = str(record.payload.get("track_hint", ""))
        object_id = str(record.payload.get("object_id", ""))
        if not track_hint or not object_id:
            continue
        track_to_objects[track_hint].add(object_id)
    fragmentation = sum(max(len(object_ids) - 1, 0) for object_ids in track_to_objects.values())
    return fragmentation, {track: sorted(object_ids) for track, object_ids in track_to_objects.items()}


def summarize_run(result: SequenceRunResult, logger: EventLogger) -> dict[str, object]:
    node_status_counts = Counter(node.status.value for node in result.memory_nodes.values())
    track_fragmentation, track_assignments = _track_fragmentation(logger)
    nodes = list(result.memory_nodes.values())
    return {
        "branch_id": result.branch_id,
        "sequence_id": result.sequence_id,
        "event_count": len(logger.records),
        "decision_count": len(result.decisions),
        "memory_node_count": len(result.memory_nodes),
        "memory_status_counts": dict(node_status_counts),
        "births": logger.count("birth_commit"),
        "deaths": logger.count("death_commit"),
        "reentries": logger.count("reentry_commit"),
        "temporal_events": logger.count("temporal_propagation_used"),
        "memory_authority_events": logger.count("memory_authority_used"),
        "fairness_exceptions": logger.count("fairness_exception"),
        "hypotheses_with_ambiguity": sum(
            1
            for record in logger.filter(event_type="current_hypothesis_emit")
            if record.payload.get("ambiguity_flags")
        ),
        "track_fragmentation": track_fragmentation,
        "track_assignments": track_assignments,
        "memory_relation_edge_count": len(result.relation_edges),
        "avg_geometry_support": round(mean(node.avg_geometry_support for node in nodes), 3) if nodes else 0.0,
        "avg_support_size": round(mean(node.avg_support_size for node in nodes), 3) if nodes else 0.0,
        "avg_depth_scale": round(mean(node.avg_depth_scale for node in nodes), 3) if nodes else 0.0,
    }


def serialize_records(logger: EventLogger) -> list[dict[str, object]]:
    return [
        {
            "sequence_id": record.sequence_id,
            "step_id": record.step_id,
            "branch_id": record.branch_id,
            "event_type": record.event_type,
            "owner_component": record.owner_component,
            "payload": record.payload,
        }
        for record in logger.records
    ]
