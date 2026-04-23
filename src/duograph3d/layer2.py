from __future__ import annotations

from .contracts import (
    AssociationDecision,
    CurrentObjectHypothesis,
    EvidenceProvenance,
    ObjectStatus,
    PipelineConfig,
)
from .events import EventLogger
from .memory import ObjectGraphMemory


class CurrentToMemoryAssociationLayer:
    def __init__(self, config: PipelineConfig | None = None) -> None:
        self.config = config or PipelineConfig()

    @staticmethod
    def _float_signal(hypothesis: CurrentObjectHypothesis, key: str, default: float) -> float:
        value = hypothesis.support_signals.get(key, default)
        try:
            return float(value)
        except (TypeError, ValueError):
            return default

    @staticmethod
    def _str_signal(hypothesis: CurrentObjectHypothesis, key: str) -> str:
        value = hypothesis.support_signals.get(key, "")
        return str(value) if value is not None else ""

    @staticmethod
    def _blend(previous: float, current: float) -> float:
        if previous <= 0:
            return current
        return round((previous * 0.6) + (current * 0.4), 3)

    def _update_node_support(self, node, hypothesis: CurrentObjectHypothesis) -> None:
        continuity_key = self._str_signal(hypothesis, "continuity_key")
        appearance_key = self._str_signal(hypothesis, "appearance_key")
        if continuity_key:
            node.continuity_key_recent = continuity_key
        if appearance_key:
            node.appearance_key_recent = appearance_key
        node.avg_support_size = self._blend(node.avg_support_size, self._float_signal(hypothesis, "support_size", 0.0))
        node.avg_depth_scale = self._blend(node.avg_depth_scale, self._float_signal(hypothesis, "depth_scale", 1.0))
        node.avg_geometry_support = self._blend(
            node.avg_geometry_support,
            self._float_signal(hypothesis, "geometry_support", 0.0),
        )

    def _score(
        self,
        hypothesis: CurrentObjectHypothesis,
        object_id: str,
        node_descriptor: str,
        node_geometry: str,
        *,
        continuity_key: str,
        appearance_key: str,
        support_size: float,
        depth_scale: float,
        geometry_support: float,
        node_continuity_key: str,
        node_appearance_key: str,
        node_support_size: float,
        node_depth_scale: float,
        node_geometry_support: float,
    ) -> tuple[float, bool]:
        score = 0.0
        strong_identity_match = False
        if hypothesis.geometry_key == node_geometry:
            score += 0.8
            strong_identity_match = True
        if hypothesis.descriptor == node_descriptor:
            score += 0.55
        score += min(hypothesis.confidence, 1.0) * 0.2
        if hypothesis.provenance_counts.get(EvidenceProvenance.PROPAGATED.value):
            score += 0.1
        if continuity_key and continuity_key == node_continuity_key:
            score += 0.45
            strong_identity_match = True
        if appearance_key and appearance_key == node_appearance_key:
            score += 0.3
        if node_support_size > 0 and support_size > 0:
            score += max(0.0, 0.12 - abs(node_support_size - support_size) * 0.2)
        if node_depth_scale > 0 and depth_scale > 0:
            score += max(0.0, 0.12 - abs(node_depth_scale - depth_scale) * 0.2)
        if node_geometry_support > 0 and geometry_support > 0:
            score += max(0.0, 0.08 - abs(node_geometry_support - geometry_support) * 0.2)
        return score, strong_identity_match

    def update(
        self,
        *,
        sequence_id: str,
        step_id: int,
        branch_id: str,
        hypotheses: list[CurrentObjectHypothesis],
        memory: ObjectGraphMemory,
        logger: EventLogger,
    ) -> list[AssociationDecision]:
        decisions: list[AssociationDecision] = []
        matched_ids: set[str] = set()
        for hypothesis in hypotheses:
            continuity_key = self._str_signal(hypothesis, "continuity_key")
            appearance_key = self._str_signal(hypothesis, "appearance_key")
            support_size = self._float_signal(hypothesis, "support_size", 0.0)
            depth_scale = self._float_signal(hypothesis, "depth_scale", 1.0)
            geometry_support = self._float_signal(hypothesis, "geometry_support", 0.0)
            candidates = [
                candidate
                for candidate in memory.candidate_nodes(hypothesis.geometry_key, self.config.candidate_budget)
                if candidate.object_id not in matched_ids
            ]
            best_id = None
            best_score = -1.0
            best_has_identity = False
            for candidate in candidates:
                score, has_identity = self._score(
                    hypothesis,
                    candidate.object_id,
                    candidate.descriptor_fused,
                    candidate.geometry_key,
                    continuity_key=continuity_key,
                    appearance_key=appearance_key,
                    support_size=support_size,
                    depth_scale=depth_scale,
                    geometry_support=geometry_support,
                    node_continuity_key=candidate.continuity_key_recent,
                    node_appearance_key=candidate.appearance_key_recent,
                    node_support_size=candidate.avg_support_size,
                    node_depth_scale=candidate.avg_depth_scale,
                    node_geometry_support=candidate.avg_geometry_support,
                )
                if score > best_score:
                    best_score = score
                    best_id = candidate.object_id
                    best_has_identity = has_identity
            if best_id is not None and best_score >= self.config.association_threshold and best_has_identity:
                node = memory.nodes[best_id]
                action = "associate"
                if node.status in {ObjectStatus.OCCLUDED, ObjectStatus.DORMANT}:
                    node.reentry_count += 1
                    action = "reentry"
                    logger.log(
                        sequence_id=sequence_id,
                        step_id=step_id,
                        branch_id=branch_id,
                        event_type="reentry_commit",
                        owner_component="layer-2",
                        object_id=node.object_id,
                        hypothesis_id=hypothesis.hypothesis_id,
                        track_hint=hypothesis.track_hint,
                    )
                node.status = ObjectStatus.ACTIVE
                node.last_seen_step = step_id
                node.miss_count = 0
                node.descriptor_recent = hypothesis.descriptor
                node.descriptor_fused = hypothesis.descriptor
                self._update_node_support(node, hypothesis)
                node.register_support(
                    EvidenceProvenance.PROPAGATED
                    if hypothesis.provenance_counts.get(EvidenceProvenance.PROPAGATED.value)
                    else EvidenceProvenance.CURRENT
                )
                if hypothesis.ambiguity_flags:
                    logger.log(
                        sequence_id=sequence_id,
                        step_id=step_id,
                        branch_id=branch_id,
                        event_type="memory_authority_used",
                        owner_component="memory",
                        object_id=node.object_id,
                        track_hint=hypothesis.track_hint,
                        ambiguity_flags=list(hypothesis.ambiguity_flags),
                    )
                logger.log(
                    sequence_id=sequence_id,
                    step_id=step_id,
                    branch_id=branch_id,
                    event_type="association_commit",
                    owner_component="layer-2",
                    object_id=node.object_id,
                    hypothesis_id=hypothesis.hypothesis_id,
                    track_hint=hypothesis.track_hint,
                    score=best_score,
                )
                matched_ids.add(node.object_id)
                decisions.append(
                    AssociationDecision(
                        hypothesis_id=hypothesis.hypothesis_id,
                        action=action,
                        object_id=node.object_id,
                        score=best_score,
                        reason="best_candidate_above_threshold",
                        track_hint=hypothesis.track_hint,
                    )
                )
            else:
                node = memory.create_node(
                    descriptor=hypothesis.descriptor,
                    geometry_key=hypothesis.geometry_key,
                    step_id=step_id,
                )
                node.register_support(
                    EvidenceProvenance.PROPAGATED
                    if hypothesis.provenance_counts.get(EvidenceProvenance.PROPAGATED.value)
                    else EvidenceProvenance.CURRENT
                )
                self._update_node_support(node, hypothesis)
                if hypothesis.ambiguity_flags:
                    logger.log(
                        sequence_id=sequence_id,
                        step_id=step_id,
                        branch_id=branch_id,
                        event_type="memory_authority_used",
                        owner_component="memory",
                        object_id=node.object_id,
                        track_hint=hypothesis.track_hint,
                        ambiguity_flags=list(hypothesis.ambiguity_flags),
                        reason="ambiguous_birth_resolution",
                    )
                logger.log(
                    sequence_id=sequence_id,
                    step_id=step_id,
                    branch_id=branch_id,
                    event_type="birth_commit",
                    owner_component="layer-2",
                    object_id=node.object_id,
                    hypothesis_id=hypothesis.hypothesis_id,
                    track_hint=hypothesis.track_hint,
                )
                matched_ids.add(node.object_id)
                decisions.append(
                    AssociationDecision(
                        hypothesis_id=hypothesis.hypothesis_id,
                        action="birth",
                        object_id=node.object_id,
                        score=max(best_score, 0.0),
                        reason="no_candidate_above_threshold",
                        track_hint=hypothesis.track_hint,
                    )
                )
        for node in memory.nodes.values():
            if node.object_id in matched_ids or node.status is ObjectStatus.RETIRED:
                continue
            node.miss_count += 1
            if node.miss_count >= self.config.retire_after_misses:
                node.status = ObjectStatus.RETIRED
                logger.log(
                    sequence_id=sequence_id,
                    step_id=step_id,
                    branch_id=branch_id,
                    event_type="death_commit",
                    owner_component="layer-2",
                    object_id=node.object_id,
                )
            elif node.miss_count >= self.config.dormant_after_misses:
                node.status = ObjectStatus.DORMANT
            elif node.miss_count >= self.config.occluded_after_misses:
                node.status = ObjectStatus.OCCLUDED
        return decisions
