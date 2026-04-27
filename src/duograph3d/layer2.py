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

    @staticmethod
    def _compatibility(current: float, previous: float, *, max_delta: float, max_score: float) -> float:
        if current <= 0 or previous <= 0:
            return 0.0
        delta = abs(previous - current)
        if delta > max_delta:
            return 0.0
        return round(max(max_score * (1.0 - delta / max_delta), 0.0), 4)

    def _geometry_profile_consistency(
        self,
        *,
        support_size: float,
        depth_scale: float,
        geometry_support: float,
        node_support_size: float,
        node_depth_scale: float,
        node_geometry_support: float,
    ) -> float:
        return round(
            self._compatibility(support_size, node_support_size, max_delta=0.2, max_score=0.18)
            + self._compatibility(depth_scale, node_depth_scale, max_delta=0.3, max_score=0.18)
            + self._compatibility(geometry_support, node_geometry_support, max_delta=0.25, max_score=0.14),
            4,
        )

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
        score, strong_identity_match, _components = self._score_with_components(
            hypothesis,
            object_id,
            node_descriptor,
            node_geometry,
            continuity_key=continuity_key,
            appearance_key=appearance_key,
            support_size=support_size,
            depth_scale=depth_scale,
            geometry_support=geometry_support,
            node_continuity_key=node_continuity_key,
            node_appearance_key=node_appearance_key,
            node_support_size=node_support_size,
            node_depth_scale=node_depth_scale,
            node_geometry_support=node_geometry_support,
        )
        return score, strong_identity_match

    def _score_with_components(
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
    ) -> tuple[float, bool, dict[str, object]]:
        score = 0.0
        strong_identity_match = False
        geometry_key_score = 0.0
        if hypothesis.geometry_key == node_geometry:
            geometry_key_score = 0.8
            score += geometry_key_score
            strong_identity_match = True
        descriptor_score = 0.0
        if hypothesis.descriptor == node_descriptor:
            descriptor_score = 0.55
            score += descriptor_score
        confidence_score = min(hypothesis.confidence, 1.0) * 0.2
        score += confidence_score
        temporal_score = 0.0
        propagation_score = 0.0
        if hypothesis.provenance_counts.get(EvidenceProvenance.PROPAGATED.value):
            propagation_score = 0.1
            temporal_score += propagation_score
        continuity_score = 0.0
        if continuity_key and continuity_key == node_continuity_key:
            continuity_score = 0.45
            temporal_score += continuity_score
            strong_identity_match = True
        appearance_score = 0.0
        if appearance_key and appearance_key == node_appearance_key:
            appearance_score = 0.3
            temporal_score += appearance_score
        geometry_profile_score = self._geometry_profile_consistency(
            support_size=support_size,
            depth_scale=depth_scale,
            geometry_support=geometry_support,
            node_support_size=node_support_size,
            node_depth_scale=node_depth_scale,
            node_geometry_support=node_geometry_support,
        )
        continuity_profile_penalty = 0.0
        if not (hypothesis.geometry_key == node_geometry) and continuity_key and continuity_key == node_continuity_key and geometry_profile_score == 0.0:
            old_temporal_score = temporal_score
            temporal_score = max(temporal_score - 0.2, 0.0)
            continuity_profile_penalty = round(old_temporal_score - temporal_score, 4)
            strong_identity_match = False
        history_candidate_score = 0.0
        history_candidate_affinity = 0.0
        history_candidate_margin = 0.0
        for candidate in hypothesis.history_candidates:
            if candidate.object_id != object_id:
                continue
            history_candidate_affinity = max(history_candidate_affinity, candidate.affinity)
            history_candidate_margin = max(history_candidate_margin, candidate.margin)
            if candidate.affinity >= self.config.layer2_history_identity_threshold:
                history_candidate_score = max(history_candidate_score, min(candidate.affinity * 0.65, 0.65))
                strong_identity_match = True
        score += temporal_score
        score += geometry_profile_score
        score += history_candidate_score
        components = {
            "geometry_key": geometry_key_score,
            "descriptor": descriptor_score,
            "confidence": round(confidence_score, 4),
            "propagation": propagation_score,
            "continuity": continuity_score,
            "appearance": appearance_score,
            "geometry_profile": geometry_profile_score,
            "continuity_profile_penalty": continuity_profile_penalty,
            "temporal_total": round(temporal_score, 4),
            "history_candidate": round(history_candidate_score, 4),
            "history_affinity": round(history_candidate_affinity, 4),
            "history_margin": round(history_candidate_margin, 4),
        }
        return score, strong_identity_match, components

    @staticmethod
    def _birth_reason(best_id: str | None, best_score: float, best_has_identity: bool, threshold: float) -> str:
        if best_id is None:
            return "no_candidate"
        if best_score < threshold:
            return "best_candidate_below_threshold"
        if not best_has_identity:
            return "best_candidate_without_strong_identity"
        return "no_candidate_above_threshold"

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
        current_step_object_ids: list[str] = []
        for hypothesis in hypotheses:
            continuity_key = self._str_signal(hypothesis, "continuity_key")
            appearance_key = self._str_signal(hypothesis, "appearance_key")
            support_size = self._float_signal(hypothesis, "support_size", 0.0)
            depth_scale = self._float_signal(hypothesis, "depth_scale", 1.0)
            geometry_support = self._float_signal(hypothesis, "geometry_support", 0.0)
            history_object_ids = tuple(
                candidate.object_id
                for candidate in hypothesis.history_candidates
                if candidate.affinity >= self.config.history_candidate_affinity_threshold
            )
            candidates = [
                candidate
                for candidate in memory.candidate_nodes(
                    hypothesis.geometry_key,
                    self.config.candidate_budget,
                    history_object_ids=history_object_ids,
                )
            ]
            best_id = None
            best_score = -1.0
            best_has_identity = False
            candidate_scores: list[dict[str, object]] = []
            for candidate in candidates:
                score, has_identity, components = self._score_with_components(
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
                relation_bonus = sum(
                    memory.relation_bonus(candidate.object_id, current_object_id) * 0.25
                    for current_object_id in current_step_object_ids
                )
                score += relation_bonus
                if self.config.emit_association_diagnostics:
                    candidate_scores.append(
                        {
                            "object_id": candidate.object_id,
                            "score": round(score, 4),
                            "has_strong_identity": has_identity,
                            "status": candidate.status.value,
                            "node_geometry_key": candidate.geometry_key,
                            "node_descriptor": candidate.descriptor_fused,
                            "node_continuity_key": candidate.continuity_key_recent,
                            "node_appearance_key": candidate.appearance_key_recent,
                            "relation_bonus": round(relation_bonus, 4),
                            "components": components,
                        }
                    )
                if score > best_score:
                    best_score = score
                    best_id = candidate.object_id
                    best_has_identity = has_identity
            if self.config.emit_association_diagnostics:
                candidate_scores.sort(key=lambda item: float(item["score"]), reverse=True)
                second_score = float(candidate_scores[1]["score"]) if len(candidate_scores) > 1 else None
                logger.log(
                    sequence_id=sequence_id,
                    step_id=step_id,
                    branch_id=branch_id,
                    event_type="association_candidate_diagnostic",
                    owner_component="layer-2",
                    hypothesis_id=hypothesis.hypothesis_id,
                    track_hint=hypothesis.track_hint,
                    candidate_count=len(candidates),
                    candidate_budget=self.config.candidate_budget,
                    threshold=self.config.association_threshold,
                    best_object_id=best_id or "",
                    best_score=round(best_score, 4) if best_id is not None else None,
                    second_score=second_score,
                    score_margin=round(best_score - second_score, 4) if second_score is not None else None,
                    best_has_strong_identity=best_has_identity,
                    top_candidates=candidate_scores[: max(self.config.association_diagnostics_top_k, 0)],
                )
            if best_id is not None and best_score >= self.config.association_threshold:
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
                self._update_node_support(node, hypothesis)
                memory.fuse_hypothesis(node, hypothesis, step_id=step_id)
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
                if node.object_id not in current_step_object_ids:
                    current_step_object_ids.append(node.object_id)
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
                birth_reason = self._birth_reason(
                    best_id,
                    best_score,
                    best_has_identity,
                    self.config.association_threshold,
                )
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
                memory.fuse_hypothesis(node, hypothesis, step_id=step_id)
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
                if self.config.emit_association_diagnostics:
                    logger.log(
                        sequence_id=sequence_id,
                        step_id=step_id,
                        branch_id=branch_id,
                        event_type="association_birth_diagnostic",
                        owner_component="layer-2",
                        object_id=node.object_id,
                        hypothesis_id=hypothesis.hypothesis_id,
                        track_hint=hypothesis.track_hint,
                        reason=birth_reason,
                        best_object_id=best_id or "",
                        best_score=round(best_score, 4) if best_id is not None else None,
                        best_has_strong_identity=best_has_identity,
                        threshold=self.config.association_threshold,
                    )
                matched_ids.add(node.object_id)
                if node.object_id not in current_step_object_ids:
                    current_step_object_ids.append(node.object_id)
                decisions.append(
                    AssociationDecision(
                        hypothesis_id=hypothesis.hypothesis_id,
                        action="birth",
                        object_id=node.object_id,
                        score=max(best_score, 0.0),
                        reason=birth_reason,
                        track_hint=hypothesis.track_hint,
                    )
                )
        relation_edge_count_before = len(memory.relation_edges)
        memory.register_co_visibility(current_step_object_ids, step_id=step_id)
        if len(memory.relation_edges) > relation_edge_count_before:
            logger.log(
                sequence_id=sequence_id,
                step_id=step_id,
                branch_id=branch_id,
                event_type="memory_relation_update",
                owner_component="memory",
                relation_edge_count=len(memory.relation_edges),
            )
        if (
            self.config.enable_object_consolidation
            and self.config.object_merge_interval > 0
            and step_id % self.config.object_merge_interval == 0
        ):
            consolidation = memory.consolidate_objects()
            if consolidation["merges"] or consolidation["filtered_object_ids"] or consolidation["denoise"].get("objects_capped", 0):
                logger.log(
                    sequence_id=sequence_id,
                    step_id=step_id,
                    branch_id=branch_id,
                    event_type="memory_object_consolidation",
                    owner_component="memory",
                    **consolidation,
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
