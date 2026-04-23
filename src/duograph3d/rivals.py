from __future__ import annotations

from dataclasses import replace

from .contracts import (
    CurrentObjectHypothesis,
    EvidenceProvenance,
    FrameInput,
    PipelineConfig,
    SequenceRunResult,
    TemporalVariant,
)
from .events import BRANCH_COUNTERFACTUAL, BRANCH_DENSE_EXPORT, BRANCH_DUOGRAPH3D, BRANCH_SINGLE_LAYER, EventLogger
from .evidence import EvidenceBuilder
from .layer2 import CurrentToMemoryAssociationLayer
from .memory import ObjectGraphMemory
from .pipeline import DuoGraph3DPipeline


def _single_layer_hypothesis(index: int, item) -> CurrentObjectHypothesis:
    support_signals = {
        "support_size": item.support.support_size if item.support else 0.0,
        "depth_scale": item.support.depth_scale if item.support else 1.0,
        "geometry_support": item.support.geometry_support if item.support else 0.0,
        "continuity_key": item.support.continuity_key if item.support else "",
        "appearance_key": item.support.appearance_key if item.support else item.descriptor,
    }
    ambiguity_flags: tuple[str, ...] = ()
    if item.support and item.support.source_kind == "memory_propagation":
        ambiguity_flags = ("propagated_single_layer",)
    return CurrentObjectHypothesis(
        hypothesis_id=f"sl-{index}",
        descriptor=item.descriptor,
        geometry_key=item.geometry_key,
        confidence=item.confidence,
        evidence_ids=(item.evidence_id,),
        track_hint=item.repair_group_id or f"{item.geometry_key}:{item.descriptor}",
        ambiguity_flags=ambiguity_flags,
        provenance_counts={item.provenance.value: 1},
        support_signals=support_signals,
    )


class SingleLayerRival:
    def __init__(self, config: PipelineConfig | None = None) -> None:
        self.config = config or PipelineConfig()
        self.evidence_builder = EvidenceBuilder()
        self.layer2 = CurrentToMemoryAssociationLayer(self.config)

    def run_sequence(self, *, sequence_id: str, frames: list[FrameInput], temporal_variant: TemporalVariant) -> tuple[SequenceRunResult, EventLogger]:
        memory = ObjectGraphMemory()
        logger = EventLogger()
        decisions = []
        for step_id, frame in enumerate(frames, start=1):
            evidence = self.evidence_builder.build(frame, memory=memory, temporal_variant=temporal_variant)
            hypotheses = [_single_layer_hypothesis(index, item) for index, item in enumerate(evidence, start=1)]
            decisions.extend(
                self.layer2.update(
                    sequence_id=sequence_id,
                    step_id=step_id,
                    branch_id=BRANCH_SINGLE_LAYER,
                    hypotheses=hypotheses,
                    memory=memory,
                    logger=logger,
                )
            )
        return (
            SequenceRunResult(
                branch_id=BRANCH_SINGLE_LAYER,
                sequence_id=sequence_id,
                memory_nodes={key: replace(value) for key, value in memory.nodes.items()},
                event_count=len(logger.records),
                decisions=decisions,
            ),
            logger,
        )


class DenseAuthorityExportRival:
    def __init__(self, keepalive_misses: int = 2) -> None:
        self.keepalive_misses = keepalive_misses

    def run_sequence(self, *, sequence_id: str, frames: list[FrameInput], temporal_variant: TemporalVariant) -> tuple[SequenceRunResult, EventLogger]:
        logger = EventLogger()
        dense_state: dict[str, dict[str, object]] = {}
        for step_id, frame in enumerate(frames, start=1):
            seen_keys: set[str] = set()
            for obs in frame.observations:
                dense_key = obs.repair_group_id or obs.geometry_key
                seen_keys.add(dense_key)
                slot = dense_state.setdefault(
                    dense_key,
                    {
                        "descriptor": obs.descriptor,
                        "geometry_key": dense_key,
                        "last_seen_step": step_id,
                        "count": 0,
                        "miss_count": 0,
                    },
                )
                slot["descriptor"] = obs.descriptor
                slot["geometry_key"] = dense_key
                slot["last_seen_step"] = step_id
                slot["count"] = int(slot["count"]) + 1
                slot["miss_count"] = 0
                logger.log(
                    sequence_id=sequence_id,
                    step_id=step_id,
                    branch_id=BRANCH_DENSE_EXPORT,
                    event_type="dense_authority_update",
                    owner_component="dense",
                    geometry_key=dense_key,
                )
            for dense_key, slot in list(dense_state.items()):
                if dense_key in seen_keys:
                    continue
                slot["miss_count"] = int(slot.get("miss_count", 0)) + 1
                if slot["miss_count"] <= self.keepalive_misses:
                    logger.log(
                        sequence_id=sequence_id,
                        step_id=step_id,
                        branch_id=BRANCH_DENSE_EXPORT,
                        event_type="dense_keepalive",
                        owner_component="dense",
                        geometry_key=dense_key,
                        miss_count=slot["miss_count"],
                    )
                else:
                    logger.log(
                        sequence_id=sequence_id,
                        step_id=step_id,
                        branch_id=BRANCH_DENSE_EXPORT,
                        event_type="dense_retire",
                        owner_component="dense",
                        geometry_key=dense_key,
                    )
                    dense_state.pop(dense_key, None)
        exported_memory = ObjectGraphMemory()
        for dense_key, slot in dense_state.items():
            node = exported_memory.create_node(
                descriptor=str(slot["descriptor"]),
                geometry_key=str(slot["geometry_key"]),
                step_id=int(slot["last_seen_step"]),
            )
            node.register_support(EvidenceProvenance.CURRENT)
        return (
            SequenceRunResult(
                branch_id=BRANCH_DENSE_EXPORT,
                sequence_id=sequence_id,
                memory_nodes=exported_memory.snapshot(),
                event_count=len(logger.records),
                decisions=[],
            ),
            logger,
        )


class FullFairCounterfactual:
    def __init__(self, config: PipelineConfig | None = None) -> None:
        base = config or PipelineConfig()
        stronger = PipelineConfig(
            candidate_budget=max(base.candidate_budget, 8),
            association_threshold=max(base.association_threshold - 0.2, 0.8),
            occluded_after_misses=base.occluded_after_misses,
            dormant_after_misses=base.dormant_after_misses,
            retire_after_misses=base.retire_after_misses,
            propagation_keepalive_misses=max(base.propagation_keepalive_misses, 3),
        )
        self.single_layer = SingleLayerRival(stronger)

    def run_sequence(self, *, sequence_id: str, frames: list[FrameInput]) -> tuple[SequenceRunResult, EventLogger]:
        result, logger = self.single_layer.run_sequence(
            sequence_id=sequence_id,
            frames=frames,
            temporal_variant=TemporalVariant.DEVA_STYLE,
        )
        for record in logger.records:
            record.branch_id = BRANCH_COUNTERFACTUAL
        result.branch_id = BRANCH_COUNTERFACTUAL
        return result, logger


def run_all_branches(sequence_id: str, frames: list[FrameInput]) -> dict[str, tuple[SequenceRunResult, EventLogger]]:
    pipeline = DuoGraph3DPipeline()
    single = SingleLayerRival()
    dense = DenseAuthorityExportRival()
    counter = FullFairCounterfactual()
    return {
        BRANCH_DUOGRAPH3D: pipeline.run_sequence(sequence_id=sequence_id, frames=frames, temporal_variant=TemporalVariant.DEVA_STYLE),
        BRANCH_SINGLE_LAYER: single.run_sequence(sequence_id=sequence_id, frames=frames, temporal_variant=TemporalVariant.DEVA_STYLE),
        BRANCH_DENSE_EXPORT: dense.run_sequence(sequence_id=sequence_id, frames=frames, temporal_variant=TemporalVariant.NAIVE_FRAMEWISE),
        BRANCH_COUNTERFACTUAL: counter.run_sequence(sequence_id=sequence_id, frames=frames),
    }
