from __future__ import annotations

from dataclasses import replace
import math

from .contracts import (
    CurrentObjectHypothesis,
    EvidenceItem,
    HistoryCandidate,
    MemoryObjectNode,
    MemoryRelationEdge,
    ObjectObservationPayload,
    ObjectStatus,
    PipelineConfig,
)


class ObjectGraphMemory:
    def __init__(self, config: PipelineConfig | None = None) -> None:
        self.config = config or PipelineConfig()
        self.nodes: dict[str, MemoryObjectNode] = {}
        self.relation_edges: dict[tuple[str, str], MemoryRelationEdge] = {}
        self._next_id = 1

    def snapshot(self) -> dict[str, MemoryObjectNode]:
        return {
            key: replace(
                value,
                temporal_support_history=list(value.temporal_support_history),
                evidence_provenance_tail=list(value.evidence_provenance_tail),
                ambiguity_flags=set(value.ambiguity_flags),
                failure_tags=set(value.failure_tags),
                class_counts=dict(value.class_counts),
            )
            for key, value in self.nodes.items()
        }

    def relation_snapshot(self) -> dict[tuple[str, str], MemoryRelationEdge]:
        return {key: replace(value) for key, value in self.relation_edges.items()}

    def next_object_id(self) -> str:
        object_id = f"obj-{self._next_id}"
        self._next_id += 1
        return object_id

    def create_node(self, *, descriptor: str, geometry_key: str, step_id: int) -> MemoryObjectNode:
        object_id = self.next_object_id()
        node = MemoryObjectNode(
            object_id=object_id,
            descriptor_fused=descriptor,
            descriptor_recent=descriptor,
            geometry_key=geometry_key,
            birth_step=step_id,
            last_seen_step=step_id,
        )
        self.nodes[object_id] = node
        return node

    def candidate_nodes(
        self,
        geometry_key: str,
        candidate_budget: int,
        *,
        history_object_ids: tuple[str, ...] = (),
    ) -> list[MemoryObjectNode]:
        history_set = set(history_object_ids)
        eligible = [
            node
            for node in self.nodes.values()
            if node.status != ObjectStatus.RETIRED
            and (
                node.object_id in history_set
                or node.geometry_key == geometry_key
                or node.status in {ObjectStatus.ACTIVE, ObjectStatus.OCCLUDED, ObjectStatus.DORMANT}
            )
        ]
        eligible.sort(key=lambda node: (node.object_id not in history_set, node.status != ObjectStatus.ACTIVE, node.miss_count, -node.last_seen_step))
        return eligible[:candidate_budget]

    @staticmethod
    def _as_float_tuple(values: object, *, limit: int | None = None) -> tuple[float, ...]:
        if values is None:
            return ()
        try:
            raw_values = list(values)  # type: ignore[arg-type]
        except TypeError:
            return ()
        if limit is not None:
            raw_values = raw_values[:limit]
        result: list[float] = []
        for value in raw_values:
            try:
                result.append(float(value))
            except (TypeError, ValueError):
                return ()
        return tuple(result)

    @classmethod
    def _as_point_tuple(cls, values: object, *, limit: int | None = None) -> tuple[tuple[float, float, float], ...]:
        if values is None:
            return ()
        try:
            raw_points = list(values)  # type: ignore[arg-type]
        except TypeError:
            return ()
        if limit is not None:
            raw_points = raw_points[:limit]
        points: list[tuple[float, float, float]] = []
        for point in raw_points:
            coords = cls._as_float_tuple(point, limit=3)
            if len(coords) == 3:
                points.append((coords[0], coords[1], coords[2]))
        return tuple(points)

    @staticmethod
    def _cosine(left: tuple[float, ...], right: tuple[float, ...]) -> float:
        if not left or not right or len(left) != len(right):
            return 0.0
        left_norm = math.sqrt(sum(value * value for value in left))
        right_norm = math.sqrt(sum(value * value for value in right))
        if left_norm <= 0 or right_norm <= 0:
            return 0.0
        return sum(lv * rv for lv, rv in zip(left, right)) / (left_norm * right_norm)

    @staticmethod
    def _similarity_from_cosine(value: float) -> float:
        return max(0.0, min((value + 1.0) / 2.0, 1.0))

    @staticmethod
    def _bbox_from_points(points: tuple[tuple[float, float, float], ...]) -> tuple[tuple[float, float, float], tuple[float, float, float]]:
        mins = tuple(min(point[index] for point in points) for index in range(3))
        maxs = tuple(max(point[index] for point in points) for index in range(3))
        return mins, maxs  # type: ignore[return-value]

    @staticmethod
    def _bbox_volume(bbox_min: tuple[float, ...], bbox_max: tuple[float, ...]) -> float:
        if len(bbox_min) != 3 or len(bbox_max) != 3:
            return 0.0
        volume = 1.0
        for min_value, max_value in zip(bbox_min, bbox_max):
            volume *= max(max_value - min_value, 0.0)
        return volume

    @classmethod
    def _bbox_overlap_score(
        cls,
        left_min: tuple[float, ...],
        left_max: tuple[float, ...],
        right_min: tuple[float, ...],
        right_max: tuple[float, ...],
    ) -> float:
        if len(left_min) != 3 or len(left_max) != 3 or len(right_min) != 3 or len(right_max) != 3:
            return 0.0
        intersection = 1.0
        for axis in range(3):
            low = max(left_min[axis], right_min[axis])
            high = min(left_max[axis], right_max[axis])
            intersection *= max(high - low, 0.0)
        if intersection <= 0:
            return 0.0
        left_volume = cls._bbox_volume(left_min, left_max)
        right_volume = cls._bbox_volume(right_min, right_max)
        denominator = max(min(left_volume, right_volume), 1e-9)
        return max(0.0, min(intersection / denominator, 1.0))

    @staticmethod
    def _centroid_from_points(points: tuple[tuple[float, float, float], ...]) -> tuple[float, float, float]:
        count = max(len(points), 1)
        return (
            sum(point[0] for point in points) / count,
            sum(point[1] for point in points) / count,
            sum(point[2] for point in points) / count,
        )

    @staticmethod
    def _centroid_distance_score(left: tuple[float, ...], right: tuple[float, ...], *, max_distance: float = 1.25) -> float:
        if len(left) != 3 or len(right) != 3:
            return 0.0
        distance = math.sqrt(sum((lv - rv) * (lv - rv) for lv, rv in zip(left, right)))
        if distance >= max_distance:
            return 0.0
        return round(1.0 - distance / max_distance, 4)

    @staticmethod
    def _compatibility(current: float, previous: float, *, max_delta: float) -> float:
        if current <= 0 or previous <= 0:
            return 0.0
        delta = abs(previous - current)
        if delta > max_delta:
            return 0.0
        return max(0.0, 1.0 - delta / max_delta)

    @staticmethod
    def _support_value(item: EvidenceItem, key: str, default: float = 0.0) -> float:
        if item.support is None:
            return default
        try:
            return float(getattr(item.support, key, default))
        except (TypeError, ValueError):
            return default

    @staticmethod
    def _support_str(item: EvidenceItem, key: str) -> str:
        if item.support is None:
            return ""
        value = getattr(item.support, key, "")
        return str(value) if value is not None else ""

    def _payload_bbox(self, payload: ObjectObservationPayload | None) -> tuple[tuple[float, ...], tuple[float, ...]]:
        if payload is None:
            return (), ()
        bbox_min = self._as_float_tuple(payload.bbox_min, limit=3)
        bbox_max = self._as_float_tuple(payload.bbox_max, limit=3)
        if len(bbox_min) == 3 and len(bbox_max) == 3:
            return bbox_min, bbox_max
        points = self._as_point_tuple(payload.points_sample)
        if points:
            return self._bbox_from_points(points)
        return (), ()

    def _payload_centroid(self, payload: ObjectObservationPayload | None) -> tuple[float, ...]:
        if payload is None:
            return ()
        centroid = self._as_float_tuple(payload.centroid, limit=3)
        if len(centroid) == 3:
            return centroid
        points = self._as_point_tuple(payload.points_sample)
        if points:
            return self._centroid_from_points(points)
        return ()

    def _semantic_score(self, label: str, descriptor: str, node: MemoryObjectNode) -> float:
        if not label:
            label = descriptor
        if not label:
            return 0.0
        if node.class_counts:
            total = sum(node.class_counts.values())
            if total > 0:
                return node.class_counts.get(label, 0) / total
        if label and label in {node.appearance_key_recent, node.descriptor_recent, node.descriptor_fused}:
            return 1.0
        return 0.0

    def _node_spatial_score(self, item: EvidenceItem, node: MemoryObjectNode) -> float:
        score = 0.0
        if item.geometry_key and item.geometry_key == node.geometry_key:
            score = max(score, 1.0)
        continuity_key = self._support_str(item, "continuity_key")
        if continuity_key and continuity_key == node.continuity_key_recent:
            score = max(score, 0.9)
        payload_min, payload_max = self._payload_bbox(item.object_payload)
        bbox_score = self._bbox_overlap_score(payload_min, payload_max, node.bbox_min, node.bbox_max)
        score = max(score, bbox_score)
        centroid_score = self._centroid_distance_score(self._payload_centroid(item.object_payload), node.centroid)
        score = max(score, centroid_score * 0.75)
        return round(score, 4)

    def _node_size_score(self, item: EvidenceItem, node: MemoryObjectNode) -> float:
        return round(
            (
                self._compatibility(self._support_value(item, "support_size"), node.avg_support_size, max_delta=0.2)
                + self._compatibility(self._support_value(item, "depth_scale", 1.0), node.avg_depth_scale, max_delta=0.3)
                + self._compatibility(self._support_value(item, "geometry_support"), node.avg_geometry_support, max_delta=0.25)
            )
            / 3.0,
            4,
        )

    def _node_visual_score(self, item: EvidenceItem, node: MemoryObjectNode) -> float:
        if item.object_payload is None:
            return 0.0
        feature = self._as_float_tuple(item.object_payload.clip_feature)
        if not feature or not node.clip_feature:
            return 0.0
        return round(self._similarity_from_cosine(self._cosine(feature, node.clip_feature)), 4)

    @staticmethod
    def _node_recency_score(node: MemoryObjectNode) -> float:
        if node.status is ObjectStatus.ACTIVE:
            base = 1.0
        elif node.status is ObjectStatus.OCCLUDED:
            base = 0.75
        elif node.status is ObjectStatus.DORMANT:
            base = 0.5
        else:
            base = 0.0
        return max(0.0, base - min(node.miss_count, 5) * 0.05)

    def history_candidates_for(
        self,
        item: EvidenceItem,
        *,
        top_k: int | None = None,
        min_affinity: float | None = None,
    ) -> tuple[HistoryCandidate, ...]:
        if not self.config.enable_history_candidates:
            return ()
        top_k = self.config.history_candidate_top_k if top_k is None else top_k
        min_affinity = self.config.history_candidate_affinity_threshold if min_affinity is None else min_affinity
        if top_k <= 0:
            return ()
        raw_candidates: list[tuple[float, str, dict[str, float]]] = []
        label = item.object_payload.label if item.object_payload is not None else self._support_str(item, "appearance_key")
        for node in self.nodes.values():
            if node.status is ObjectStatus.RETIRED:
                continue
            spatial_score = self._node_spatial_score(item, node)
            visual_score = self._node_visual_score(item, node)
            semantic_score = self._semantic_score(label, item.descriptor, node)
            recency_score = self._node_recency_score(node)
            size_score = self._node_size_score(item, node)
            affinity = round(
                0.42 * spatial_score
                + 0.23 * visual_score
                + 0.18 * semantic_score
                + 0.10 * recency_score
                + 0.07 * size_score,
                4,
            )
            if affinity >= min_affinity:
                raw_candidates.append(
                    (
                        affinity,
                        node.object_id,
                        {
                            "spatial_score": spatial_score,
                            "visual_score": visual_score,
                            "semantic_score": semantic_score,
                            "recency_score": recency_score,
                            "size_score": size_score,
                        },
                    )
                )
        raw_candidates.sort(key=lambda item_score: item_score[0], reverse=True)
        candidates: list[HistoryCandidate] = []
        for index, (affinity, object_id, components) in enumerate(raw_candidates[:top_k]):
            next_affinity = raw_candidates[index + 1][0] if index + 1 < len(raw_candidates) else 0.0
            margin = round(affinity - next_affinity, 4)
            candidates.append(
                HistoryCandidate(
                    object_id=object_id,
                    affinity=affinity,
                    spatial_score=components["spatial_score"],
                    visual_score=components["visual_score"],
                    semantic_score=components["semantic_score"],
                    recency_score=components["recency_score"],
                    size_score=components["size_score"],
                    margin=margin,
                    strong=affinity >= min_affinity and margin >= self.config.history_candidate_margin_threshold,
                )
            )
        return tuple(candidates)

    def _blend_feature(self, previous: tuple[float, ...], current: tuple[float, ...], previous_weight: int, current_weight: int) -> tuple[float, ...]:
        if not current:
            return previous
        if not previous or len(previous) != len(current):
            return current
        total = max(previous_weight + current_weight, 1)
        return tuple(round((pv * previous_weight + cv * current_weight) / total, 6) for pv, cv in zip(previous, current))

    @staticmethod
    def _merge_bbox(
        left_min: tuple[float, ...],
        left_max: tuple[float, ...],
        right_min: tuple[float, ...],
        right_max: tuple[float, ...],
    ) -> tuple[tuple[float, ...], tuple[float, ...]]:
        if len(left_min) != 3 or len(left_max) != 3:
            return right_min, right_max
        if len(right_min) != 3 or len(right_max) != 3:
            return left_min, left_max
        return (
            tuple(min(lv, rv) for lv, rv in zip(left_min, right_min)),
            tuple(max(lv, rv) for lv, rv in zip(left_max, right_max)),
        )

    def _cap_points(
        self,
        points: tuple[tuple[float, float, float], ...],
        colors: tuple[tuple[float, float, float], ...],
    ) -> tuple[tuple[tuple[float, float, float], ...], tuple[tuple[float, float, float], ...]]:
        limit = max(self.config.memory_max_points_per_object, 0)
        if limit <= 0 or len(points) <= limit:
            return points, colors
        if limit == 1:
            keep_indices = [0]
        else:
            keep_indices = [round(index * (len(points) - 1) / (limit - 1)) for index in range(limit)]
        capped_points = tuple(points[index] for index in keep_indices)
        capped_colors = tuple(colors[index] for index in keep_indices if index < len(colors))
        return capped_points, capped_colors

    def fuse_hypothesis(self, node: MemoryObjectNode, hypothesis: CurrentObjectHypothesis, *, step_id: int) -> None:
        previous_count = max(node.detection_count, 0)
        payload = hypothesis.object_payload
        current_count = max(payload.detection_count if payload is not None else 1, 1)
        node.descriptor_recent = hypothesis.descriptor
        node.descriptor_fused = hypothesis.descriptor
        node.last_seen_step = step_id
        node.detection_count = previous_count + current_count
        node.confidence_sum += hypothesis.confidence * current_count
        if payload is not None:
            label = payload.label or str(hypothesis.support_signals.get("appearance_key") or hypothesis.descriptor)
            if label:
                node.class_counts[label] = node.class_counts.get(label, 0) + current_count
            node.mask_area_sum += float(payload.mask_area or 0.0)
            current_clip = self._as_float_tuple(payload.clip_feature)
            current_text = self._as_float_tuple(payload.text_feature)
            node.clip_feature = self._blend_feature(node.clip_feature, current_clip, previous_count, current_count)
            node.text_feature = self._blend_feature(node.text_feature, current_text, previous_count, current_count)
            payload_min, payload_max = self._payload_bbox(payload)
            node.bbox_min, node.bbox_max = self._merge_bbox(node.bbox_min, node.bbox_max, payload_min, payload_max)
            current_centroid = self._payload_centroid(payload)
            if len(current_centroid) == 3:
                if len(node.centroid) != 3 or previous_count == 0:
                    node.centroid = current_centroid
                else:
                    total = max(previous_count + current_count, 1)
                    node.centroid = tuple(
                        round((node.centroid[index] * previous_count + current_centroid[index] * current_count) / total, 6)
                        for index in range(3)
                    )
            points = self._as_point_tuple(payload.points_sample)
            colors = self._as_point_tuple(payload.colors_sample)
            node.sampled_points, node.sampled_colors = self._cap_points(node.sampled_points + points, node.sampled_colors + colors)
            node.point_count = max(node.point_count + len(points), len(node.sampled_points))
        else:
            label = str(hypothesis.support_signals.get("appearance_key") or hypothesis.descriptor)
            if label:
                node.class_counts[label] = node.class_counts.get(label, 0) + current_count

    def _object_semantic_score(self, left: MemoryObjectNode, right: MemoryObjectNode) -> float:
        if not left.class_counts or not right.class_counts:
            if left.appearance_key_recent and left.appearance_key_recent == right.appearance_key_recent:
                return 1.0
            return 0.0
        common = set(left.class_counts).intersection(right.class_counts)
        if not common:
            return 0.0
        overlap = sum(min(left.class_counts[label], right.class_counts[label]) for label in common)
        denominator = max(min(sum(left.class_counts.values()), sum(right.class_counts.values())), 1)
        return overlap / denominator

    def object_affinity(self, left: MemoryObjectNode, right: MemoryObjectNode) -> tuple[float, dict[str, float]]:
        spatial_score = self._bbox_overlap_score(left.bbox_min, left.bbox_max, right.bbox_min, right.bbox_max)
        spatial_score = max(spatial_score, self._centroid_distance_score(left.centroid, right.centroid) * 0.75)
        if left.geometry_key and left.geometry_key == right.geometry_key:
            spatial_score = max(spatial_score, 1.0)
        if left.continuity_key_recent and left.continuity_key_recent == right.continuity_key_recent:
            spatial_score = max(spatial_score, 0.9)
        visual_score = self._similarity_from_cosine(self._cosine(left.clip_feature, right.clip_feature))
        semantic_score = self._object_semantic_score(left, right)
        size_score = round(
            (
                self._compatibility(left.avg_support_size, right.avg_support_size, max_delta=0.2)
                + self._compatibility(left.avg_depth_scale, right.avg_depth_scale, max_delta=0.3)
                + self._compatibility(left.avg_geometry_support, right.avg_geometry_support, max_delta=0.25)
            )
            / 3.0,
            4,
        )
        score = round(0.50 * spatial_score + 0.25 * visual_score + 0.20 * semantic_score + 0.05 * size_score, 4)
        return score, {
            "spatial": round(spatial_score, 4),
            "visual": round(visual_score, 4),
            "semantic": round(semantic_score, 4),
            "size": round(size_score, 4),
        }

    def merge_nodes(self, target: MemoryObjectNode, source: MemoryObjectNode) -> None:
        previous_count = max(target.detection_count, 0)
        source_count = max(source.detection_count, 1)
        target.detection_count = previous_count + source_count
        target.confidence_sum += source.confidence_sum
        target.mask_area_sum += source.mask_area_sum
        target.point_count += source.point_count
        for label, count in source.class_counts.items():
            target.class_counts[label] = target.class_counts.get(label, 0) + count
        target.clip_feature = self._blend_feature(target.clip_feature, source.clip_feature, previous_count, source_count)
        target.text_feature = self._blend_feature(target.text_feature, source.text_feature, previous_count, source_count)
        target.bbox_min, target.bbox_max = self._merge_bbox(target.bbox_min, target.bbox_max, source.bbox_min, source.bbox_max)
        if len(source.centroid) == 3:
            if len(target.centroid) != 3 or previous_count == 0:
                target.centroid = source.centroid
            else:
                total = max(previous_count + source_count, 1)
                target.centroid = tuple(
                    round((target.centroid[index] * previous_count + source.centroid[index] * source_count) / total, 6)
                    for index in range(3)
                )
        target.sampled_points, target.sampled_colors = self._cap_points(
            target.sampled_points + source.sampled_points,
            target.sampled_colors + source.sampled_colors,
        )
        target.last_seen_step = max(target.last_seen_step, source.last_seen_step)
        target.birth_step = min(target.birth_step, source.birth_step)
        target.reentry_count += source.reentry_count
        target.ambiguity_flags.update(source.ambiguity_flags)
        target.failure_tags.update(source.failure_tags)
        source.status = ObjectStatus.RETIRED
        source.failure_tags.add("merged_into_duplicate_object")

    def merge_duplicate_objects(self) -> list[dict[str, object]]:
        merges: list[dict[str, object]] = []
        active_nodes = [node for node in self.nodes.values() if node.status is not ObjectStatus.RETIRED]
        active_nodes.sort(key=lambda node: (node.birth_step, node.object_id))
        for left_index, left in enumerate(active_nodes):
            if left.status is ObjectStatus.RETIRED:
                continue
            for right in active_nodes[left_index + 1 :]:
                if right.status is ObjectStatus.RETIRED:
                    continue
                score, components = self.object_affinity(left, right)
                if score < self.config.object_merge_threshold:
                    continue
                if components["spatial"] < self.config.object_merge_spatial_threshold:
                    continue
                self.merge_nodes(left, right)
                merges.append(
                    {
                        "target_object_id": left.object_id,
                        "source_object_id": right.object_id,
                        "score": score,
                        "components": components,
                    }
                )
        return merges

    def filter_low_quality_objects(self) -> list[str]:
        min_detections = max(self.config.object_filter_min_detections, 1)
        retired: list[str] = []
        if min_detections <= 1:
            return retired
        for node in self.nodes.values():
            if node.status is ObjectStatus.RETIRED:
                continue
            if node.detection_count < min_detections:
                node.status = ObjectStatus.RETIRED
                node.failure_tags.add("filtered_low_detection_object")
                retired.append(node.object_id)
        return retired

    def denoise_objects(self) -> dict[str, int]:
        changed = 0
        for node in self.nodes.values():
            before = len(node.sampled_points)
            node.sampled_points, node.sampled_colors = self._cap_points(node.sampled_points, node.sampled_colors)
            if len(node.sampled_points) != before:
                changed += 1
            if node.sampled_points and (len(node.bbox_min) != 3 or len(node.bbox_max) != 3):
                node.bbox_min, node.bbox_max = self._bbox_from_points(node.sampled_points)
            if node.sampled_points and len(node.centroid) != 3:
                node.centroid = self._centroid_from_points(node.sampled_points)
        return {"objects_capped": changed}

    def consolidate_objects(self) -> dict[str, object]:
        denoise_summary = self.denoise_objects()
        merges = self.merge_duplicate_objects() if self.config.enable_object_consolidation else []
        filtered = self.filter_low_quality_objects() if self.config.enable_object_consolidation else []
        return {
            "denoise": denoise_summary,
            "merges": merges,
            "filtered_object_ids": filtered,
        }

    @staticmethod
    def _relation_key(source_object_id: str, target_object_id: str) -> tuple[str, str]:
        return tuple(sorted((source_object_id, target_object_id)))

    def register_co_visibility(self, object_ids: list[str], *, step_id: int) -> None:
        unique_ids = sorted(set(object_ids))
        for index, source_object_id in enumerate(unique_ids):
            for target_object_id in unique_ids[index + 1:]:
                relation_key = self._relation_key(source_object_id, target_object_id)
                edge = self.relation_edges.get(
                    relation_key,
                    MemoryRelationEdge(
                        source_object_id=relation_key[0],
                        target_object_id=relation_key[1],
                    ),
                )
                edge.co_visibility_count += 1
                edge.last_seen_step = step_id
                edge.strength = round(min(edge.co_visibility_count / 5.0, 1.0), 3)
                self.relation_edges[relation_key] = edge

    def relation_bonus(self, source_object_id: str, target_object_id: str) -> float:
        edge = self.relation_edges.get(self._relation_key(source_object_id, target_object_id))
        return edge.strength if edge is not None else 0.0
