from __future__ import annotations

from collections import defaultdict

from .contracts import CurrentObjectHypothesis, EvidenceItem, mean_confidence


class CurrentEvidenceGraphLayer:
    @staticmethod
    def _float_support(item: EvidenceItem, key: str, default: float) -> float:
        if item.support is None:
            return default
        value = getattr(item.support, key, default)
        try:
            return float(value)
        except (TypeError, ValueError):
            return default

    @staticmethod
    def _str_support(item: EvidenceItem, key: str) -> str:
        if item.support is None:
            return ""
        value = getattr(item.support, key, "")
        return str(value) if value is not None else ""

    def _edge_score(self, left: EvidenceItem, right: EvidenceItem) -> tuple[float, list[str]]:
        score = 0.0
        reasons: list[str] = []
        if left.repair_group_id and left.repair_group_id == right.repair_group_id:
            score += 0.75
            reasons.append("shared_repair_group")
        left_continuity = self._str_support(left, "continuity_key")
        right_continuity = self._str_support(right, "continuity_key")
        if left_continuity and left_continuity == right_continuity:
            score += 0.7
            reasons.append("continuity_match")
        left_appearance = self._str_support(left, "appearance_key")
        right_appearance = self._str_support(right, "appearance_key")
        if left_appearance and left_appearance == right_appearance:
            score += 0.35
            reasons.append("appearance_match")
        if left.descriptor == right.descriptor:
            score += 0.2
            reasons.append("descriptor_match")
        geometry_profile_score = self._geometry_profile_consistency(
            support_size=self._float_support(left, "support_size", 0.0),
            depth_scale=self._float_support(left, "depth_scale", 1.0),
            geometry_support=self._float_support(left, "geometry_support", 0.0),
            node_support_size=self._float_support(right, "support_size", 0.0),
            node_depth_scale=self._float_support(right, "depth_scale", 1.0),
            node_geometry_support=self._float_support(right, "geometry_support", 0.0),
        )
        if geometry_profile_score > 0:
            score += geometry_profile_score
            reasons.append("geometry_profile_consistent")
        if left.geometry_key == right.geometry_key:
            score += 0.45
            reasons.append("geometry_key_match")
        return score, reasons

    @staticmethod
    def _geometry_profile_consistency(
        *,
        support_size: float,
        depth_scale: float,
        geometry_support: float,
        node_support_size: float,
        node_depth_scale: float,
        node_geometry_support: float,
    ) -> float:
        deltas: list[tuple[float, float]] = []
        if support_size > 0 and node_support_size > 0:
            deltas.append((abs(node_support_size - support_size), 0.2))
        if depth_scale > 0 and node_depth_scale > 0:
            deltas.append((abs(node_depth_scale - depth_scale), 0.3))
        if geometry_support > 0 and node_geometry_support > 0:
            deltas.append((abs(node_geometry_support - geometry_support), 0.25))
        if not deltas:
            return 0.0
        normalized = [max(0.0, 1.0 - delta / max_delta) for delta, max_delta in deltas if delta <= max_delta]
        if not normalized:
            return 0.0
        return round(sum(normalized) / len(normalized) * 0.35, 4)

    def repair(self, evidence_items: list[EvidenceItem]) -> list[CurrentObjectHypothesis]:
        grouped: dict[str, list[EvidenceItem]] = defaultdict(list)
        for item in evidence_items:
            continuity_key = self._str_support(item, "continuity_key")
            group_key = item.repair_group_id or continuity_key or f"{item.geometry_key}:{item.descriptor}"
            grouped[group_key].append(item)

        hypotheses: list[CurrentObjectHypothesis] = []
        component_index = 1
        for items in grouped.values():
            adjacency: dict[int, set[int]] = {index: {index} for index in range(len(items))}
            edge_reasons: dict[tuple[int, int], list[str]] = {}
            for left_index, left_item in enumerate(items):
                for right_index in range(left_index + 1, len(items)):
                    score, reasons = self._edge_score(left_item, items[right_index])
                    if score >= 0.9:
                        adjacency[left_index].add(right_index)
                        adjacency[right_index].add(left_index)
                        edge_reasons[(left_index, right_index)] = reasons

            visited: set[int] = set()
            components: list[list[EvidenceItem]] = []
            component_reason_sets: list[list[str]] = []
            for start_index in range(len(items)):
                if start_index in visited:
                    continue
                stack = [start_index]
                component_indices: list[int] = []
                reason_bucket: list[str] = []
                while stack:
                    current_index = stack.pop()
                    if current_index in visited:
                        continue
                    visited.add(current_index)
                    component_indices.append(current_index)
                    for neighbor_index in sorted(adjacency[current_index]):
                        if neighbor_index == current_index:
                            continue
                        reason_bucket.extend(edge_reasons.get((min(current_index, neighbor_index), max(current_index, neighbor_index)), []))
                        if neighbor_index not in visited:
                            stack.append(neighbor_index)
                components.append([items[index] for index in sorted(component_indices)])
                component_reason_sets.append(sorted(set(reason_bucket)))

            for items, repair_reasons in zip(components, component_reason_sets):
                descriptors = {item.descriptor for item in items}
                geometries = {item.geometry_key for item in items}
                ambiguity_flags: list[str] = []
                if len(descriptors) > 1:
                    ambiguity_flags.append("descriptor_conflict")
                if len(geometries) > 1:
                    ambiguity_flags.append("geometry_conflict")
                provenance_counts: dict[str, int] = defaultdict(int)
                for item in items:
                    provenance_counts[item.provenance.value] += 1
                support_sizes = [item.support.support_size for item in items if item.support]
                depth_scales = [item.support.depth_scale for item in items if item.support]
                geometry_supports = [item.support.geometry_support for item in items if item.support]
                continuity_keys = [item.support.continuity_key for item in items if item.support and item.support.continuity_key]
                appearance_keys = [item.support.appearance_key for item in items if item.support and item.support.appearance_key]
                if depth_scales and max(depth_scales) - min(depth_scales) > 0.25:
                    ambiguity_flags.append("support_scale_conflict")
                representative = max(items, key=lambda item: item.confidence)
                hypotheses.append(
                    CurrentObjectHypothesis(
                        hypothesis_id=f"hyp-{component_index}",
                        descriptor=representative.descriptor,
                        geometry_key=representative.geometry_key,
                        confidence=mean_confidence(item.confidence for item in items),
                        evidence_ids=tuple(item.evidence_id for item in items),
                        track_hint=representative.repair_group_id or f"{representative.geometry_key}:{representative.descriptor}",
                        ambiguity_flags=tuple(ambiguity_flags),
                        provenance_counts=dict(provenance_counts),
                        support_signals={
                            "support_size": mean_confidence(support_sizes) if support_sizes else 0.0,
                            "depth_scale": mean_confidence(depth_scales) if depth_scales else 1.0,
                            "geometry_support": mean_confidence(geometry_supports) if geometry_supports else 0.0,
                            "continuity_key": continuity_keys[0] if continuity_keys else "",
                            "appearance_key": appearance_keys[0] if appearance_keys else representative.descriptor,
                            "repair_edge_count": max(len(items) - 1, 0),
                            "repair_reasons": tuple(repair_reasons),
                        },
                    )
                )
                component_index += 1
        return hypotheses
