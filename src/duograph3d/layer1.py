from __future__ import annotations

from collections import Counter, defaultdict

from .contracts import CurrentObjectHypothesis, EvidenceItem, HistoryCandidate, ObjectObservationPayload, PipelineConfig, mean_confidence


class CurrentEvidenceGraphLayer:
    def __init__(self, config: PipelineConfig | None = None) -> None:
        self.config = config or PipelineConfig()

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

    def _usable_history_candidates(self, item: EvidenceItem) -> tuple[HistoryCandidate, ...]:
        usable = [
            candidate
            for candidate in item.history_candidates
            if candidate.affinity >= self.config.history_candidate_affinity_threshold
            and candidate.margin >= self.config.history_candidate_margin_threshold
            and candidate.spatial_score >= self.config.layer1_history_min_spatial_score
            and candidate.semantic_score >= self.config.layer1_history_min_semantic_score
            and candidate.visual_score >= self.config.layer1_history_min_visual_score
            and candidate.size_score >= self.config.layer1_history_min_size_score
        ]
        usable.sort(key=lambda candidate: candidate.affinity, reverse=True)
        return tuple(usable)

    def _shared_history_boost(self, left: EvidenceItem, right: EvidenceItem) -> tuple[float, list[str]]:
        left_candidates = {candidate.object_id: candidate for candidate in self._usable_history_candidates(left)}
        if not left_candidates:
            return 0.0, []
        best_score = 0.0
        best_id = ""
        for candidate in self._usable_history_candidates(right):
            if candidate.object_id not in left_candidates:
                continue
            shared_strength = min(left_candidates[candidate.object_id].affinity, candidate.affinity)
            if shared_strength > best_score:
                best_score = shared_strength
                best_id = candidate.object_id
        if not best_id:
            return 0.0, []
        return round(self.config.layer1_history_shared_boost * best_score, 4), ["shared_history_object"]

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
        history_score, history_reasons = self._shared_history_boost(left, right)
        if history_score > 0:
            score += history_score
            reasons.extend(history_reasons)
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

    def _candidate_pair_indices(self, evidence_items: list[EvidenceItem]) -> set[tuple[int, int]]:
        buckets: dict[str, list[int]] = defaultdict(list)
        for index, item in enumerate(evidence_items):
            continuity_key = self._str_support(item, "continuity_key")
            group_key = item.repair_group_id or continuity_key or f"{item.geometry_key}:{item.descriptor}"
            buckets[f"group:{group_key}"].append(index)
            for candidate in self._usable_history_candidates(item):
                buckets[f"history:{candidate.object_id}"].append(index)
        pairs: set[tuple[int, int]] = set()
        for bucket_indices in buckets.values():
            if len(bucket_indices) < 2:
                continue
            for left_offset, left_index in enumerate(bucket_indices):
                for right_index in bucket_indices[left_offset + 1 :]:
                    pairs.add((min(left_index, right_index), max(left_index, right_index)))
        return pairs

    @staticmethod
    def _as_float_tuple(values: object) -> tuple[float, ...]:
        if values is None:
            return ()
        try:
            raw_values = list(values)  # type: ignore[arg-type]
        except TypeError:
            return ()
        result: list[float] = []
        for value in raw_values:
            try:
                result.append(float(value))
            except (TypeError, ValueError):
                return ()
        return tuple(result)

    @classmethod
    def _feature_mean(cls, payloads: list[ObjectObservationPayload], key: str) -> tuple[float, ...]:
        features = [cls._as_float_tuple(getattr(payload, key, ())) for payload in payloads]
        features = [feature for feature in features if feature]
        if not features:
            return ()
        dim = len(features[0])
        compatible = [feature for feature in features if len(feature) == dim]
        if not compatible:
            return ()
        return tuple(round(sum(feature[index] for feature in compatible) / len(compatible), 6) for index in range(dim))

    @staticmethod
    def _bbox_from_points(points: tuple[tuple[float, float, float], ...]) -> tuple[tuple[float, float, float], tuple[float, float, float]]:
        return (
            tuple(min(point[index] for point in points) for index in range(3)),
            tuple(max(point[index] for point in points) for index in range(3)),
        )  # type: ignore[return-value]

    @classmethod
    def _merge_payloads(cls, items: list[EvidenceItem]) -> ObjectObservationPayload | None:
        payloads = [item.object_payload for item in items if item.object_payload is not None]
        if not payloads:
            return None
        label_counts = Counter(payload.label for payload in payloads if payload.label)
        label = label_counts.most_common(1)[0][0] if label_counts else ""
        points: list[tuple[float, float, float]] = []
        colors: list[tuple[float, float, float]] = []
        centroids: list[tuple[float, float, float]] = []
        bbox_mins: list[tuple[float, ...]] = []
        bbox_maxs: list[tuple[float, ...]] = []
        mask_area = 0.0
        detection_count = 0
        for payload in payloads:
            for point in payload.points_sample:
                coords = cls._as_float_tuple(point)
                if len(coords) == 3:
                    points.append((coords[0], coords[1], coords[2]))
            for color in payload.colors_sample:
                values = cls._as_float_tuple(color)
                if len(values) == 3:
                    colors.append((values[0], values[1], values[2]))
            centroid = cls._as_float_tuple(payload.centroid)
            if len(centroid) == 3:
                centroids.append((centroid[0], centroid[1], centroid[2]))
            bbox_min = cls._as_float_tuple(payload.bbox_min)
            bbox_max = cls._as_float_tuple(payload.bbox_max)
            if len(bbox_min) == 3 and len(bbox_max) == 3:
                bbox_mins.append(bbox_min)
                bbox_maxs.append(bbox_max)
            mask_area += float(payload.mask_area or 0.0)
            detection_count += max(int(payload.detection_count or 1), 1)
        if not bbox_mins and points:
            bbox_min, bbox_max = cls._bbox_from_points(tuple(points))
        elif bbox_mins:
            bbox_min = tuple(min(values[index] for values in bbox_mins) for index in range(3))
            bbox_max = tuple(max(values[index] for values in bbox_maxs) for index in range(3))
        else:
            bbox_min, bbox_max = (), ()
        if centroids:
            centroid_out: tuple[float, ...] = tuple(round(sum(values[index] for values in centroids) / len(centroids), 6) for index in range(3))
        elif points:
            centroid_out = tuple(round(sum(point[index] for point in points) / len(points), 6) for index in range(3))
        else:
            centroid_out = ()
        return ObjectObservationPayload(
            label=label,
            points_sample=tuple(points),
            colors_sample=tuple(colors),
            bbox_min=bbox_min,
            bbox_max=bbox_max,
            centroid=centroid_out,
            clip_feature=cls._feature_mean(payloads, "clip_feature"),
            text_feature=cls._feature_mean(payloads, "text_feature"),
            mask_area=mask_area,
            detection_count=max(detection_count, 1),
        )

    def _aggregate_history_candidates(self, items: list[EvidenceItem]) -> tuple[HistoryCandidate, ...]:
        by_object: dict[str, list[HistoryCandidate]] = defaultdict(list)
        for item in items:
            for candidate in item.history_candidates:
                by_object[candidate.object_id].append(candidate)
        aggregated: list[HistoryCandidate] = []
        for object_id, candidates in by_object.items():
            best = max(candidates, key=lambda candidate: candidate.affinity)
            aggregated.append(
                HistoryCandidate(
                    object_id=object_id,
                    affinity=best.affinity,
                    spatial_score=best.spatial_score,
                    visual_score=best.visual_score,
                    semantic_score=best.semantic_score,
                    recency_score=best.recency_score,
                    size_score=best.size_score,
                    margin=best.margin,
                    source="layer1_aggregate",
                    strong=any(candidate.strong for candidate in candidates),
                )
            )
        aggregated.sort(key=lambda candidate: candidate.affinity, reverse=True)
        return tuple(aggregated[: self.config.history_candidate_top_k])

    def repair(self, evidence_items: list[EvidenceItem]) -> list[CurrentObjectHypothesis]:
        if not evidence_items:
            return []
        adjacency: dict[int, set[int]] = {index: {index} for index in range(len(evidence_items))}
        edge_reasons: dict[tuple[int, int], list[str]] = {}
        for left_index, right_index in self._candidate_pair_indices(evidence_items):
            score, reasons = self._edge_score(evidence_items[left_index], evidence_items[right_index])
            if score >= self.config.layer1_merge_threshold:
                adjacency[left_index].add(right_index)
                adjacency[right_index].add(left_index)
                edge_reasons[(left_index, right_index)] = reasons

        visited: set[int] = set()
        components: list[list[EvidenceItem]] = []
        component_reason_sets: list[list[str]] = []
        for start_index in range(len(evidence_items)):
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
            components.append([evidence_items[index] for index in sorted(component_indices)])
            component_reason_sets.append(sorted(set(reason_bucket)))

        hypotheses: list[CurrentObjectHypothesis] = []
        for component_index, (items, repair_reasons) in enumerate(zip(components, component_reason_sets), start=1):
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
            history_candidates = self._aggregate_history_candidates(items)
            top_history = history_candidates[0] if history_candidates else None
            support_signals: dict[str, object] = {
                "support_size": mean_confidence(support_sizes) if support_sizes else 0.0,
                "depth_scale": mean_confidence(depth_scales) if depth_scales else 1.0,
                "geometry_support": mean_confidence(geometry_supports) if geometry_supports else 0.0,
                "continuity_key": continuity_keys[0] if continuity_keys else "",
                "appearance_key": appearance_keys[0] if appearance_keys else representative.descriptor,
                "repair_edge_count": max(len(items) - 1, 0),
                "repair_reasons": tuple(repair_reasons),
            }
            if top_history is not None:
                support_signals.update(
                    {
                        "history_object_id": top_history.object_id,
                        "history_affinity": top_history.affinity,
                        "history_margin": top_history.margin,
                        "history_spatial_score": top_history.spatial_score,
                        "history_visual_score": top_history.visual_score,
                        "history_semantic_score": top_history.semantic_score,
                    }
                )
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
                    support_signals=support_signals,
                    history_candidates=history_candidates,
                    object_payload=self._merge_payloads(items),
                )
            )
        return hypotheses
