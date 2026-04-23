from __future__ import annotations

from collections import defaultdict

from .contracts import CurrentObjectHypothesis, EvidenceItem, mean_confidence


class CurrentEvidenceGraphLayer:
    def repair(self, evidence_items: list[EvidenceItem]) -> list[CurrentObjectHypothesis]:
        grouped: dict[str, list[EvidenceItem]] = defaultdict(list)
        for item in evidence_items:
            group_key = item.repair_group_id or f"{item.geometry_key}:{item.descriptor}"
            grouped[group_key].append(item)

        hypotheses: list[CurrentObjectHypothesis] = []
        for index, items in enumerate(grouped.values(), start=1):
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
                    hypothesis_id=f"hyp-{index}",
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
                    },
                )
            )
        return hypotheses
