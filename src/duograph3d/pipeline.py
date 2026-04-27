from __future__ import annotations

from dataclasses import replace

from .contracts import FrameInput, PipelineConfig, SequenceRunResult, TemporalVariant
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
        result = SequenceRunResult(
            branch_id=branch_id,
            sequence_id=sequence_id,
            memory_nodes={key: replace(value) for key, value in memory.nodes.items()},
            event_count=len(logger.records),
            decisions=all_decisions,
            relation_edges=memory.relation_snapshot(),
        )
        return result, logger
