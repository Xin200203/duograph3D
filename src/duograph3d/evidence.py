from __future__ import annotations

from .contracts import EvidenceItem, EvidenceProvenance, FrameInput, ObservationSupport, PipelineConfig, TemporalVariant
from .memory import ObjectGraphMemory


class EvidenceBuilder:
    def __init__(self, config: PipelineConfig | None = None) -> None:
        self.config = config or PipelineConfig()

    def build(
        self,
        frame: FrameInput,
        *,
        memory: ObjectGraphMemory,
        temporal_variant: TemporalVariant,
    ) -> list[EvidenceItem]:
        evidence: list[EvidenceItem] = []
        seen_geometry = {obs.geometry_key for obs in frame.observations}
        seen_continuity = {
            obs.support.continuity_key
            for obs in frame.observations
            if obs.support and obs.support.continuity_key
        }
        for obs in frame.observations:
            evidence.append(
                EvidenceItem(
                    evidence_id=f"{frame.frame_id}:{obs.observation_id}",
                    descriptor=obs.descriptor,
                    geometry_key=obs.geometry_key,
                    confidence=obs.confidence,
                    provenance=EvidenceProvenance.CURRENT,
                    source_observation_ids=(obs.observation_id,),
                    support_tokens=obs.support_tokens,
                    repair_group_id=obs.repair_group_id,
                    support=obs.support,
                )
            )
        if temporal_variant is TemporalVariant.DEVA_STYLE:
            for node in memory.nodes.values():
                if node.status.value == "retired":
                    continue
                if node.geometry_key in seen_geometry:
                    continue
                if node.continuity_key_recent and node.continuity_key_recent in seen_continuity:
                    continue
                if node.miss_count > self.config.propagation_keepalive_misses:
                    continue
                evidence.append(
                    EvidenceItem(
                        evidence_id=f"{frame.frame_id}:prop:{node.object_id}",
                        descriptor=node.descriptor_recent,
                        geometry_key=node.geometry_key,
                        confidence=0.55,
                        provenance=EvidenceProvenance.PROPAGATED,
                        source_observation_ids=(),
                        support_tokens=("carry_over",),
                        repair_group_id=node.continuity_key_recent or node.object_id,
                        memory_hint_id=node.object_id,
                        support=ObservationSupport(
                            proposal_id=f"memory:{node.object_id}",
                            frame_token=frame.frame_id,
                            pose_token=f"memory-step:{node.last_seen_step}",
                            source_kind="memory_propagation",
                            support_size=node.avg_support_size,
                            depth_scale=node.avg_depth_scale,
                            appearance_key=node.appearance_key_recent or node.descriptor_recent,
                            continuity_key=node.continuity_key_recent or node.object_id,
                            geometry_support=node.avg_geometry_support,
                        ),
                    )
                )
        return evidence
