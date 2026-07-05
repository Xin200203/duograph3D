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


def _geometry_key_assignments(logger: EventLogger) -> dict[str, list[str]]:
    key_to_objects: dict[str, set[str]] = defaultdict(set)
    for record in logger.records:
        if record.event_type not in {"birth_commit", "association_commit", "reentry_commit"}:
            continue
        object_id = str(record.payload.get("object_id", ""))
        if not object_id:
            continue
        geometry_keys = record.payload.get("geometry_keys")
        if isinstance(geometry_keys, (list, tuple)):
            keys = [str(key) for key in geometry_keys if str(key)]
        else:
            geometry_key = str(record.payload.get("geometry_key", ""))
            keys = [geometry_key] if geometry_key else []
        for key in keys:
            key_to_objects[key].add(object_id)
    return {key: sorted(object_ids) for key, object_ids in key_to_objects.items()}


def _geometry_key_assignment_counts(logger: EventLogger) -> dict[str, dict[str, int]]:
    key_to_object_counts: dict[str, Counter[str]] = defaultdict(Counter)
    for record in logger.records:
        if record.event_type not in {"birth_commit", "association_commit", "reentry_commit"}:
            continue
        object_id = str(record.payload.get("object_id", ""))
        if not object_id:
            continue
        geometry_keys = record.payload.get("geometry_keys")
        if isinstance(geometry_keys, (list, tuple)):
            keys = [str(key) for key in geometry_keys if str(key)]
        else:
            geometry_key = str(record.payload.get("geometry_key", ""))
            keys = [geometry_key] if geometry_key else []
        for key in keys:
            key_to_object_counts[key][object_id] += 1
    return {key: dict(counter) for key, counter in key_to_object_counts.items()}


def _payload_counter(value: object) -> Counter[str]:
    counter: Counter[str] = Counter()
    if not isinstance(value, dict):
        return counter
    for key, count in value.items():
        try:
            counter[str(key)] += int(count)
        except (TypeError, ValueError):
            continue
    return counter


def _association_frame_rollup(logger: EventLogger) -> tuple[dict[str, object], list[dict[str, object]]]:
    records = list(logger.filter(event_type="association_frame_summary"))
    action_counts: Counter[str] = Counter()
    reason_counts: Counter[str] = Counter()
    birth_reason_counts: Counter[str] = Counter()
    birth_failure_family_counts: Counter[str] = Counter()
    candidate_totals: list[float] = []
    candidate_means: list[float] = []
    candidate_max_values: list[int] = []
    zero_candidate_counts: list[int] = []
    candidate_margin_means: list[float] = []
    memory_node_counts_after: list[int] = []
    memory_node_deltas: list[int] = []
    relation_edge_deltas: list[int] = []
    hypothesis_counts: list[int] = []
    decision_counts: list[int] = []
    final_status_counts: dict[str, int] = {}

    for record in records:
        payload = record.payload
        action_counts.update(_payload_counter(payload.get("action_counts")))
        reason_counts.update(_payload_counter(payload.get("reason_counts")))
        birth_reason_counts.update(_payload_counter(payload.get("birth_reason_counts")))
        birth_failure_family_counts.update(_payload_counter(payload.get("birth_failure_family_counts")))
        hypothesis_counts.append(int(payload.get("hypothesis_count", 0) or 0))
        decision_counts.append(int(payload.get("decision_count", 0) or 0))
        candidate_totals.append(float(payload.get("candidate_total", 0) or 0.0))
        candidate_means.append(float(payload.get("candidate_mean", 0) or 0.0))
        candidate_max_values.append(int(payload.get("candidate_max", 0) or 0))
        zero_candidate_counts.append(int(payload.get("zero_candidate_count", 0) or 0))
        margin = payload.get("candidate_margin_mean")
        if margin is not None:
            candidate_margin_means.append(float(margin))
        memory_node_counts_after.append(int(payload.get("memory_node_count_after", 0) or 0))
        memory_node_deltas.append(int(payload.get("memory_node_count_delta", 0) or 0))
        relation_edge_deltas.append(int(payload.get("relation_edge_count_delta", 0) or 0))
        status_counts = payload.get("memory_status_counts_after")
        if isinstance(status_counts, dict):
            final_status_counts = {str(key): int(value) for key, value in status_counts.items()}

    rollup = {
        "frame_count": len(records),
        "hypothesis_count_total": sum(hypothesis_counts),
        "decision_count_total": sum(decision_counts),
        "action_counts": dict(action_counts),
        "reason_counts": dict(reason_counts),
        "birth_reason_counts": dict(birth_reason_counts),
        "birth_failure_family_counts": dict(birth_failure_family_counts),
        "candidate_total": round(sum(candidate_totals), 4),
        "candidate_mean_per_frame": round(mean(candidate_means), 4) if candidate_means else 0.0,
        "candidate_max": max(candidate_max_values) if candidate_max_values else 0,
        "zero_candidate_count_total": sum(zero_candidate_counts),
        "candidate_margin_mean_per_frame": round(mean(candidate_margin_means), 4) if candidate_margin_means else None,
        "memory_node_count_max": max(memory_node_counts_after) if memory_node_counts_after else 0,
        "memory_node_count_final": memory_node_counts_after[-1] if memory_node_counts_after else 0,
        "memory_node_delta_total": sum(memory_node_deltas),
        "memory_status_counts_final": final_status_counts,
        "relation_edge_delta_total": sum(relation_edge_deltas),
    }
    samples = [
        {
            "step_id": record.step_id,
            "hypothesis_count": record.payload.get("hypothesis_count", 0),
            "decision_count": record.payload.get("decision_count", 0),
            "action_counts": record.payload.get("action_counts", {}),
            "candidate_total": record.payload.get("candidate_total", 0),
            "candidate_mean": record.payload.get("candidate_mean", 0.0),
            "zero_candidate_count": record.payload.get("zero_candidate_count", 0),
            "memory_node_count_before": record.payload.get("memory_node_count_before", 0),
            "memory_node_count_after": record.payload.get("memory_node_count_after", 0),
            "memory_status_counts_after": record.payload.get("memory_status_counts_after", {}),
        }
        for record in records[:10]
    ]
    return rollup, samples


def _layer1_frame_rollup(logger: EventLogger) -> tuple[dict[str, object], list[dict[str, object]]]:
    records = list(logger.filter(event_type="layer1_frame_summary"))
    provenance_counts: Counter[str] = Counter()
    merge_reason_counts: Counter[str] = Counter()
    payload_label_counts: Counter[str] = Counter()
    observation_counts: list[int] = []
    evidence_counts: list[int] = []
    hypothesis_counts: list[int] = []
    evidence_per_hypothesis_means: list[float] = []
    evidence_per_hypothesis_max_values: list[int] = []
    geometry_keys_per_hypothesis_means: list[float] = []
    geometry_keys_per_hypothesis_max_values: list[int] = []
    singleton_hypothesis_counts: list[int] = []
    neg_edge_counts: list[int] = []

    for record in records:
        payload = record.payload
        provenance_counts.update(_payload_counter(payload.get("evidence_provenance_counts")))
        merge_reason_counts.update(_payload_counter(payload.get("merge_reason_counts")))
        top_labels = payload.get("top_payload_labels")
        if isinstance(top_labels, list):
            for entry in top_labels:
                if not isinstance(entry, (list, tuple)) or len(entry) != 2:
                    continue
                label, count = entry
                try:
                    payload_label_counts[str(label)] += int(count)
                except (TypeError, ValueError):
                    continue
        observation_counts.append(int(payload.get("observation_count", 0) or 0))
        evidence_counts.append(int(payload.get("evidence_count", 0) or 0))
        hypothesis_counts.append(int(payload.get("hypothesis_count", 0) or 0))
        evidence_per_hypothesis_means.append(float(payload.get("evidence_per_hypothesis_mean", 0.0) or 0.0))
        evidence_per_hypothesis_max_values.append(int(payload.get("evidence_per_hypothesis_max", 0) or 0))
        geometry_keys_per_hypothesis_means.append(float(payload.get("geometry_keys_per_hypothesis_mean", 0.0) or 0.0))
        geometry_keys_per_hypothesis_max_values.append(int(payload.get("geometry_keys_per_hypothesis_max", 0) or 0))
        singleton_hypothesis_counts.append(int(payload.get("singleton_hypothesis_count", 0) or 0))
        neg_edge_counts.append(int(payload.get("neg_edge_count", 0) or 0))

    rollup = {
        "frame_count": len(records),
        "observation_count_total": sum(observation_counts),
        "evidence_count_total": sum(evidence_counts),
        "hypothesis_count_total": sum(hypothesis_counts),
        "evidence_provenance_counts": dict(provenance_counts),
        "evidence_per_hypothesis_mean_per_frame": round(mean(evidence_per_hypothesis_means), 4)
        if evidence_per_hypothesis_means
        else 0.0,
        "evidence_per_hypothesis_max": max(evidence_per_hypothesis_max_values)
        if evidence_per_hypothesis_max_values
        else 0,
        "geometry_keys_per_hypothesis_mean_per_frame": round(mean(geometry_keys_per_hypothesis_means), 4)
        if geometry_keys_per_hypothesis_means
        else 0.0,
        "geometry_keys_per_hypothesis_max": max(geometry_keys_per_hypothesis_max_values)
        if geometry_keys_per_hypothesis_max_values
        else 0,
        "singleton_hypothesis_count_total": sum(singleton_hypothesis_counts),
        "merge_reason_counts": dict(merge_reason_counts),
        "neg_edge_count_total": sum(neg_edge_counts),
        "top_payload_labels": payload_label_counts.most_common(15),
    }
    samples = [
        {
            "step_id": record.step_id,
            "frame_id": record.payload.get("frame_id", ""),
            "observation_count": record.payload.get("observation_count", 0),
            "evidence_count": record.payload.get("evidence_count", 0),
            "hypothesis_count": record.payload.get("hypothesis_count", 0),
            "evidence_per_hypothesis_mean": record.payload.get("evidence_per_hypothesis_mean", 0.0),
            "evidence_per_hypothesis_max": record.payload.get("evidence_per_hypothesis_max", 0),
            "geometry_keys_per_hypothesis_mean": record.payload.get("geometry_keys_per_hypothesis_mean", 0.0),
            "geometry_keys_per_hypothesis_max": record.payload.get("geometry_keys_per_hypothesis_max", 0),
            "singleton_hypothesis_count": record.payload.get("singleton_hypothesis_count", 0),
            "merge_reason_counts": record.payload.get("merge_reason_counts", {}),
            "top_payload_labels": record.payload.get("top_payload_labels", []),
        }
        for record in records[:10]
    ]
    return rollup, samples


def summarize_run(result: SequenceRunResult, logger: EventLogger) -> dict[str, object]:
    node_status_counts = Counter(node.status.value for node in result.memory_nodes.values())
    track_fragmentation, track_assignments = _track_fragmentation(logger)
    geometry_key_assignments = _geometry_key_assignments(logger)
    geometry_key_assignment_counts = _geometry_key_assignment_counts(logger)
    layer1_frame_rollup, layer1_frame_summaries_sample = _layer1_frame_rollup(logger)
    association_frame_rollup, association_frame_summaries_sample = _association_frame_rollup(logger)
    nodes = list(result.memory_nodes.values())
    active_nodes = [node for node in nodes if node.status.value != "retired"]
    return {
        "branch_id": result.branch_id,
        "sequence_id": result.sequence_id,
        "event_count": len(logger.records),
        "decision_count": len(result.decisions),
        "memory_node_count": len(result.memory_nodes),
        "active_memory_node_count": len(active_nodes),
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
        "geometry_key_assignments": geometry_key_assignments,
        "geometry_key_assignment_counts": geometry_key_assignment_counts,
        "memory_relation_edge_count": len(result.relation_edges),
        "memory_object_consolidation_events": logger.count("memory_object_consolidation"),
        "merged_memory_node_count": sum(1 for node in nodes if "merged_into_duplicate_object" in node.failure_tags),
        "object_payload_node_count": sum(1 for node in nodes if node.point_count > 0 or node.clip_feature),
        "avg_detection_count": round(mean(node.detection_count for node in active_nodes), 3) if active_nodes else 0.0,
        "avg_geometry_support": round(mean(node.avg_geometry_support for node in nodes), 3) if nodes else 0.0,
        "avg_support_size": round(mean(node.avg_support_size for node in nodes), 3) if nodes else 0.0,
        "avg_depth_scale": round(mean(node.avg_depth_scale for node in nodes), 3) if nodes else 0.0,
        "layer1_frame_rollup": layer1_frame_rollup,
        "layer1_frame_summaries_sample": layer1_frame_summaries_sample,
        "association_frame_rollup": association_frame_rollup,
        "association_frame_summaries_sample": association_frame_summaries_sample,
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
