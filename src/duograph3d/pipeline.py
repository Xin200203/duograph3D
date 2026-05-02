from __future__ import annotations

from dataclasses import replace

from .contracts import FrameInput, MemoryObjectNode, ObjectStatus, PipelineConfig, SequenceRunResult, TemporalVariant
from .events import BRANCH_DUOGRAPH3D, EventLogger
from .evidence import EvidenceBuilder
from .layer1 import CurrentEvidenceGraphLayer
from .layer2 import CurrentToMemoryAssociationLayer
from .memory import ObjectGraphMemory


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
                logger.log(
                    sequence_id=sequence_id,
                    step_id=step_id,
                    branch_id=branch_id,
                    event_type="current_hypothesis_emit",
                    owner_component="layer-1",
                    hypothesis_id=hypothesis.hypothesis_id,
                    track_hint=hypothesis.track_hint,
                    ambiguity_flags=list(hypothesis.ambiguity_flags),
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
                    bbox_min=frag.bbox_min,
                    bbox_max=frag.bbox_max,
                    centroid=frag.centroid,
                    continuity_key_recent=frag.continuity_key_recent,
                    appearance_key_recent=frag.appearance_key_recent,
                    avg_support_size=frag.avg_support_size,
                    avg_depth_scale=frag.avg_depth_scale,
                    avg_geometry_support=frag.avg_geometry_support,
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
