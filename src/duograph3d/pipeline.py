from __future__ import annotations

from collections import Counter
from dataclasses import replace
import math

from .contracts import FrameInput, MemoryObjectNode, ObjectStatus, PipelineConfig, SequenceRunResult, TemporalVariant
from .events import BRANCH_DUOGRAPH3D, EventLogger
from .evidence import EvidenceBuilder
from .layer1 import CurrentEvidenceGraphLayer
from .layer2 import CurrentToMemoryAssociationLayer
from .memory import ObjectGraphMemory


def _distribution_entropy(distribution: dict[str, float]) -> float | None:
    values = [float(value) for value in distribution.values() if float(value) > 0.0]
    if not values:
        return None
    total = sum(values)
    if total <= 0.0:
        return None
    return round(-sum((value / total) * math.log(value / total, 2) for value in values), 6)


def _distribution_top_share(distribution: dict[str, float]) -> float | None:
    values = [float(value) for value in distribution.values() if float(value) > 0.0]
    if not values:
        return None
    total = sum(values)
    if total <= 0.0:
        return None
    return round(max(values) / total, 6)


class DuoGraph3DPipeline:
    def __init__(self, config: PipelineConfig | None = None) -> None:
        self.config = config or PipelineConfig()
        self.evidence_builder = EvidenceBuilder(self.config)
        self.layer1 = CurrentEvidenceGraphLayer(self.config)
        self.layer2 = CurrentToMemoryAssociationLayer(self.config)

    def run_sequence(
        self,
        *,
        sequence_id: str,
        frames: list[FrameInput],
        temporal_variant: TemporalVariant,
        branch_id: str = BRANCH_DUOGRAPH3D,
    ) -> tuple[SequenceRunResult, EventLogger]:
        memory = ObjectGraphMemory(self.config)
        logger = EventLogger()
        all_decisions = []
        for step_id, frame in enumerate(frames, start=1):
            logger.log(
                sequence_id=sequence_id,
                step_id=step_id,
                branch_id=branch_id,
                event_type="comparison_slice_start",
                owner_component="pipeline",
                frame_id=frame.frame_id,
                temporal_variant=temporal_variant.value,
            )
            evidence = self.evidence_builder.build(frame, memory=memory, temporal_variant=temporal_variant)
            for item in evidence:
                if item.provenance.value == "propagated":
                    logger.log(
                        sequence_id=sequence_id,
                        step_id=step_id,
                        branch_id=branch_id,
                        event_type="temporal_propagation_used",
                        owner_component="temporal",
                        evidence_id=item.evidence_id,
                    )
            hypotheses = self.layer1.repair(evidence)
            for hypothesis in hypotheses:
                label_distribution = dict(hypothesis.label_distribution)
                component_geometry_keys = tuple(
                    hypothesis.support_signals.get("component_geometry_keys") or ()
                )
                payload = hypothesis.object_payload
                logger.log(
                    sequence_id=sequence_id,
                    step_id=step_id,
                    branch_id=branch_id,
                    event_type="current_hypothesis_emit",
                    owner_component="layer-1",
                    hypothesis_id=hypothesis.hypothesis_id,
                    track_hint=hypothesis.track_hint,
                    ambiguity_flags=list(hypothesis.ambiguity_flags),
                    evidence_count=len(hypothesis.evidence_ids),
                    evidence_ids=list(hypothesis.evidence_ids),
                    geometry_key=hypothesis.geometry_key,
                    component_geometry_keys=list(component_geometry_keys),
                    component_geometry_key_count=len(component_geometry_keys),
                    merge_reasons=list(hypothesis.merge_reasons),
                    neg_edge_count=len(hypothesis.neg_edge_ids),
                    neg_edge_ids=list(hypothesis.neg_edge_ids),
                    label_distribution=label_distribution,
                    label_entropy=_distribution_entropy(label_distribution),
                    label_top_share=_distribution_top_share(label_distribution),
                    label_bucket_count=len(hypothesis.label_buckets),
                    payload_label=payload.label if payload is not None else "",
                    payload_detection_count=payload.detection_count if payload is not None else 0,
                    payload_mask_area=payload.mask_area if payload is not None else 0.0,
                )
            if self.config.emit_association_diagnostics:
                evidence_counts = [len(hypothesis.evidence_ids) for hypothesis in hypotheses]
                geometry_key_counts = [
                    len(tuple(hypothesis.support_signals.get("component_geometry_keys") or ()))
                    for hypothesis in hypotheses
                ]
                merge_reason_counts: Counter[str] = Counter()
                payload_label_counts: Counter[str] = Counter()
                neg_edge_count = 0
                for hypothesis in hypotheses:
                    merge_reason_counts.update(str(reason) for reason in hypothesis.merge_reasons)
                    neg_edge_count += len(hypothesis.neg_edge_ids)
                    payload = hypothesis.object_payload
                    if payload is not None and payload.label:
                        payload_label_counts[payload.label] += 1
                provenance_counts = Counter(item.provenance.value for item in evidence)
                logger.log(
                    sequence_id=sequence_id,
                    step_id=step_id,
                    branch_id=branch_id,
                    event_type="layer1_frame_summary",
                    owner_component="layer-1",
                    frame_id=frame.frame_id,
                    observation_count=len(frame.observations),
                    evidence_count=len(evidence),
                    evidence_provenance_counts=dict(provenance_counts),
                    hypothesis_count=len(hypotheses),
                    evidence_per_hypothesis_mean=round(sum(evidence_counts) / max(len(evidence_counts), 1), 4)
                    if evidence_counts
                    else 0.0,
                    evidence_per_hypothesis_max=max(evidence_counts) if evidence_counts else 0,
                    geometry_keys_per_hypothesis_mean=round(sum(geometry_key_counts) / max(len(geometry_key_counts), 1), 4)
                    if geometry_key_counts
                    else 0.0,
                    geometry_keys_per_hypothesis_max=max(geometry_key_counts) if geometry_key_counts else 0,
                    singleton_hypothesis_count=sum(1 for value in evidence_counts if value == 1),
                    merge_reason_counts=dict(merge_reason_counts),
                    neg_edge_count=neg_edge_count,
                    top_payload_labels=payload_label_counts.most_common(10),
                )
            all_decisions.extend(
                self.layer2.update(
                    sequence_id=sequence_id,
                    step_id=step_id,
                    branch_id=branch_id,
                    hypotheses=hypotheses,
                    memory=memory,
                    logger=logger,
                )
            )
            logger.log(
                sequence_id=sequence_id,
                step_id=step_id,
                branch_id=branch_id,
                event_type="comparison_slice_end",
                owner_component="pipeline",
                frame_id=frame.frame_id,
            )
        if self.config.enable_object_consolidation:
            consolidation = memory.consolidate_objects()
            if consolidation["merges"] or consolidation["filtered_object_ids"] or consolidation["denoise"].get("objects_capped", 0):
                logger.log(
                    sequence_id=sequence_id,
                    step_id=len(frames),
                    branch_id=branch_id,
                    event_type="memory_object_consolidation",
                    owner_component="memory",
                    **consolidation,
                )
        nodes_snapshot = {key: replace(value) for key, value in memory.nodes.items()}
        # Phase 丙 fix: export tentative fragments alongside confirmed nodes.
        # Tentative fragments with >= 1 hit carry useful geometry/semantic state
        # even if they haven't reached the promotion threshold.
        if self.config.enable_tentative_fragments:
            for fid, frag in memory.tentative_fragments.items():
                if frag.absorbed_into_id or frag.hits < 1:
                    continue
                # Build a minimal point set from fragment centroid so export doesn't crash.
                # Tentative fragments accumulate features but not raw 3D points;
                # we use the centroid to create a tiny bounding box for export.
                if len(frag.centroid) == 3:
                    cx, cy, cz = frag.centroid[0], frag.centroid[1], frag.centroid[2]
                    eps = 0.01
                    pseudo_points = tuple(
                        (cx + dx * eps, cy + dy * eps, cz + dz * eps)
                        for dx, dy, dz in [(1,1,1),(-1,1,1),(1,-1,1),(1,1,-1),(-1,-1,1),(-1,1,-1),(1,-1,-1),(-1,-1,-1)]
                    )
                else:
                    pseudo_points = tuple((float(i)*0.01, 0.0, 0.0) for i in range(8))
                pseudo = MemoryObjectNode(
                    object_id=fid,
                    descriptor_fused=frag.descriptor,
                    descriptor_recent=frag.descriptor,
                    geometry_key=frag.geometry_key,
                    status=ObjectStatus.ACTIVE,
                    birth_step=frag.birth_step,
                    last_seen_step=frag.last_seen_step,
                    miss_count=frag.miss_count,
                    detection_count=frag.detection_count,
                    confidence_sum=frag.confidence_sum,
                    mask_area_sum=frag.mask_area_sum,
                    class_counts=dict(frag.class_counts),
                    clip_feature=frag.clip_feature,
                    text_feature=frag.text_feature,
                    bbox_min=frag.bbox_min if len(frag.bbox_min) == 3 else tuple(c - eps for c in (cx, cy, cz)),
                    bbox_max=frag.bbox_max if len(frag.bbox_max) == 3 else tuple(c + eps for c in (cx, cy, cz)),
                    centroid=frag.centroid,
                    continuity_key_recent=frag.continuity_key_recent,
                    appearance_key_recent=frag.appearance_key_recent,
                    avg_support_size=frag.avg_support_size,
                    avg_depth_scale=frag.avg_depth_scale,
                    avg_geometry_support=frag.avg_geometry_support,
                    sampled_points=pseudo_points,
                    sampled_colors=tuple((0.5, 0.5, 0.5) for _ in range(8)),
                )
                nodes_snapshot[fid] = pseudo
        result = SequenceRunResult(
            branch_id=branch_id,
            sequence_id=sequence_id,
            memory_nodes=nodes_snapshot,
            event_count=len(logger.records),
            decisions=all_decisions,
            relation_edges=memory.relation_snapshot(),
        )
        return result, logger
