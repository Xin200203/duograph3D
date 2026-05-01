from __future__ import annotations

from dataclasses import replace
import math

from .contracts import (
    CurrentObjectHypothesis,
    EvidenceItem,
    FragmentStatus,
    HistoryCandidate,
    MemoryObjectNode,
    MemoryRelationEdge,
    ObjectObservationPayload,
    ObjectStatus,
    PipelineConfig,
    TentativeFragment,
)


class ObjectGraphMemory:
    def __init__(self, config: PipelineConfig | None = None) -> None:
        self.config = config or PipelineConfig()
        self.nodes: dict[str, MemoryObjectNode] = {}
        self.relation_edges: dict[tuple[str, str], MemoryRelationEdge] = {}
        self._next_id = 1
        # Phase 乙: geometry-key → node-id index for adj-key retrieval
        self._geometry_index: dict[str, list[str]] = {}
        # Phase 丙: tentative fragments pending promotion
        self.tentative_fragments: dict[str, TentativeFragment] = {}
        self._next_tentative_id = 1

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
        # Phase 乙: maintain geometry index
        if geometry_key:
            self._geometry_index.setdefault(geometry_key, []).append(object_id)
        return node

    # ---- Phase 丙: tentative fragment + promotion gate ----

    def _next_fragment_id(self) -> str:
        fid = f"tent-{self._next_tentative_id}"
        self._next_tentative_id += 1
        return fid

    def create_tentative_fragment(
        self, *, descriptor: str, geometry_key: str, step_id: int,
        hypothesis: CurrentObjectHypothesis | None = None,
    ) -> TentativeFragment:
        fid = self._next_fragment_id()
        fragment = TentativeFragment(
            fragment_id=fid,
            birth_step=step_id,
            last_seen_step=step_id,
            hits=1,
            descriptor=descriptor,
            geometry_key=geometry_key,
        )
        if hypothesis is not None:
            payload = hypothesis.object_payload
            if payload is not None:
                fragment.detection_count = max(payload.detection_count, 1)
                fragment.confidence_sum = hypothesis.confidence * fragment.detection_count
                fragment.mask_area_sum = float(payload.mask_area or 0.0)
                fragment.clip_feature = self._as_float_tuple(payload.clip_feature)
                fragment.text_feature = self._as_float_tuple(payload.text_feature)
                bbox_min, bbox_max = self._payload_bbox(payload)
                fragment.bbox_min = bbox_min
                fragment.bbox_max = bbox_max
                fragment.centroid = self._payload_centroid(payload)
                if payload.label:
                    fragment.class_counts[payload.label] = fragment.class_counts.get(payload.label, 0) + fragment.detection_count
            continuity_key = str(hypothesis.support_signals.get("continuity_key", ""))
            appearance_key = str(hypothesis.support_signals.get("appearance_key", ""))
            if continuity_key:
                fragment.continuity_key_recent = continuity_key
            if appearance_key:
                fragment.appearance_key_recent = appearance_key
            fragment.avg_support_size = float(hypothesis.support_signals.get("support_size", 0.0) or 0.0)
            fragment.avg_depth_scale = float(hypothesis.support_signals.get("depth_scale", 1.0) or 1.0)
            fragment.avg_geometry_support = float(hypothesis.support_signals.get("geometry_support", 0.0) or 0.0)
        self.tentative_fragments[fid] = fragment
        return fragment

    def promote_to_confirmed(self, fragment: TentativeFragment, step_id: int) -> MemoryObjectNode:
        node = self.create_node(
            descriptor=fragment.descriptor,
            geometry_key=fragment.geometry_key,
            step_id=step_id,
        )
        # Transfer accumulated state
        node.birth_step = fragment.birth_step
        node.last_seen_step = step_id
        node.detection_count = max(fragment.detection_count, 1)
        node.confidence_sum = fragment.confidence_sum
        node.mask_area_sum = fragment.mask_area_sum
        node.class_counts = dict(fragment.class_counts)
        if fragment.clip_feature:
            node.clip_feature = self._normalize_feature(fragment.clip_feature)
        if fragment.text_feature:
            node.text_feature = self._normalize_feature(fragment.text_feature)
        node.bbox_min = fragment.bbox_min
        node.bbox_max = fragment.bbox_max
        node.centroid = fragment.centroid
        node.continuity_key_recent = fragment.continuity_key_recent
        node.appearance_key_recent = fragment.appearance_key_recent
        node.avg_support_size = fragment.avg_support_size
        node.avg_depth_scale = fragment.avg_depth_scale
        node.avg_geometry_support = fragment.avg_geometry_support
        node.point_count = len(fragment.clip_feature)  # approximate
        # Mark fragment as promoted
        fragment.absorbed_into_id = node.object_id
        return node

    def promotion_gate(self, fragment: TentativeFragment) -> tuple[bool, str]:
        """Check if a tentative fragment is ready to be promoted to confirmed.

        Returns (should_promote, reason).
        """
        config = self.config
        if fragment.hits < config.promotion_min_hits:
            return False, "insufficient_hits"
        if config.promotion_min_sc > 0 and fragment.self_consistency < config.promotion_min_sc:
            return False, "low_self_consistency"
        if config.promotion_min_gc > 0 and fragment.geometry_consistency < config.promotion_min_gc:
            return False, "low_geometry_consistency"
        # Check label entropy
        if fragment.class_counts:
            total = sum(fragment.class_counts.values())
            if total > 0:
                top_label, top_count = max(fragment.class_counts.items(), key=lambda x: x[1])
                top_share = top_count / total
                entropy = 0.0
                for count in fragment.class_counts.values():
                    p = count / total
                    if p > 0:
                        entropy -= p * math.log(p, 2)
                if entropy > config.promotion_max_label_entropy and top_share < config.promotion_min_top_label_share:
                    return False, "high_label_entropy"
        # Check conflict rate
        total_events = max(fragment.hits, 1)
        conflict_rate = fragment.conflict_count / total_events
        if conflict_rate > config.promotion_max_conflict_rate:
            return False, "high_conflict_rate"
        return True, ""

    def retire_tentative_fragment(self, fragment: TentativeFragment, reason: str) -> None:
        fragment.rejection_reason = reason

    # ---- Phase 丙: working / stable memory ----

    def stable_write_gate(
        self,
        *,
        margin: float,
        conflict_count: int,
        has_identity: bool,
    ) -> tuple[bool, str]:
        """Gate for stable prototype updates.

        Returns (should_write_stable, reason).
        """
        config = self.config
        if not has_identity:
            return False, "no_strong_identity"
        if margin < config.stable_write_margin:
            return False, "low_margin"
        if conflict_count > 0:
            return False, "has_conflicts"
        return True, ""

    def _update_stable_prototype(self, node: MemoryObjectNode, feature: tuple[float, ...], *, key: str) -> None:
        """EMA-update stable prototype with low learning rate."""
        alpha = self.config.stable_ema_alpha
        if key == "clip":
            current_stable = node.stable_clip_feature
            if not current_stable:
                node.stable_clip_feature = self._normalize_feature(feature)
            elif len(current_stable) == len(feature):
                node.stable_clip_feature = self._normalize_feature(
                    tuple(
                        round((1 - alpha) * sv + alpha * cv, 6)
                        for sv, cv in zip(current_stable, feature)
                    )
                )
            node.stable_write_count += 1
        elif key == "text":
            current_stable = node.stable_text_feature
            if not current_stable:
                node.stable_text_feature = self._normalize_feature(feature)
            elif len(current_stable) == len(feature):
                node.stable_text_feature = self._normalize_feature(
                    tuple(
                        round((1 - alpha) * sv + alpha * cv, 6)
                        for sv, cv in zip(current_stable, feature)
                    )
                )

    def candidate_nodes(
        self,
        geometry_key: str,
        candidate_budget: int,
        *,
        history_object_ids: tuple[str, ...] = (),
        hypothesis: CurrentObjectHypothesis | None = None,
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
        if hypothesis is None:
            eligible.sort(key=lambda node: (node.object_id not in history_set, node.status != ObjectStatus.ACTIVE, node.miss_count, -node.last_seen_step, node.object_id))
            return eligible[: max(candidate_budget, 1)]

        channel_budget = max(self.config.candidate_retrieval_channel_budget, 1)
        final_budget = max(candidate_budget, self.config.candidate_retrieval_budget, 1)
        selected: dict[str, MemoryObjectNode] = {}

        def add(node: MemoryObjectNode) -> None:
            if node.status is not ObjectStatus.RETIRED:
                selected.setdefault(node.object_id, node)

        for object_id in history_object_ids:
            node = self.nodes.get(object_id)
            if node is not None:
                add(node)

        exact_geometry = [node for node in eligible if geometry_key and node.geometry_key == geometry_key]
        exact_geometry.sort(key=lambda node: (node.status != ObjectStatus.ACTIVE, node.miss_count, -node.last_seen_step, node.object_id))
        for node in exact_geometry[:channel_budget]:
            add(node)

        recent = sorted(
            eligible,
            key=lambda node: (node.status != ObjectStatus.ACTIVE, node.miss_count, -node.last_seen_step, node.object_id),
        )
        for node in recent[:channel_budget]:
            add(node)

        # Phase 乙: adj-key channel — nodes in adjacent voxel cells
        if self.config.cand_include_adj_key and geometry_key:
            adj_keys = self._adjacent_geometry_keys(geometry_key, radius=self.config.cand_adj_radius)
            adj_candidates: list[MemoryObjectNode] = []
            for adj_key in adj_keys:
                for object_id in self._geometry_index.get(adj_key, []):
                    node = self.nodes.get(object_id)
                    if node is not None and node.status is not ObjectStatus.RETIRED and node.object_id not in selected:
                        adj_candidates.append(node)
            adj_candidates.sort(key=lambda node: (node.status != ObjectStatus.ACTIVE, node.miss_count, -node.last_seen_step, node.object_id))
            for node in adj_candidates[:channel_budget]:
                add(node)

        # Phase 乙: ANN channel — nearest-neighbour over clip features
        if self.config.cand_include_ann and hypothesis is not None and hypothesis.object_payload is not None:
            query_feature = self._as_float_tuple(hypothesis.object_payload.clip_feature)
            if query_feature:
                ann_nodes = self._ann_search(query_feature, top_k=self.config.cand_ann_top_k)
                for node in ann_nodes:
                    if node.object_id not in selected:
                        add(node)

        cheap_scores: list[tuple[float, float, float, float, float, float, MemoryObjectNode]] = []
        for node in eligible:
            spatial_score = self.hypothesis_spatial_score(hypothesis, node)
            point_overlap_score = self.hypothesis_point_overlap_score(hypothesis, node)
            visual_score = self.hypothesis_visual_score(hypothesis, node)
            semantic_score = self.hypothesis_semantic_score(hypothesis, node)
            recency_score = self._node_recency_score(node)
            retrieval_score = round(
                0.42 * spatial_score
                + 0.18 * visual_score
                + 0.17 * semantic_score
                + 0.13 * recency_score
                + 0.10 * point_overlap_score,
                4,
            )
            cheap_scores.append((retrieval_score, spatial_score, point_overlap_score, visual_score, semantic_score, recency_score, node))

        for bucket_index in (0, 1, 2, 3, 4):
            ranked = sorted(cheap_scores, key=lambda item: (item[bucket_index], item[-1].object_id), reverse=True)
            for *_, node in ranked[:channel_budget]:
                add(node)

        _id_key = self._object_id_sort_key

        def final_rank(node: MemoryObjectNode) -> tuple[float, ...]:
            spatial_score = self.hypothesis_spatial_score(hypothesis, node)
            point_overlap_score = self.hypothesis_point_overlap_score(hypothesis, node)
            visual_score = self.hypothesis_visual_score(hypothesis, node)
            semantic_score = self.hypothesis_semantic_score(hypothesis, node)
            recency_score = self._node_recency_score(node)
            return (
                1.0 if node.object_id in history_set else 0.0,
                1.0 if geometry_key and node.geometry_key == geometry_key else 0.0,
                point_overlap_score,
                spatial_score,
                visual_score,
                semantic_score,
                recency_score,
                1.0 if node.status is ObjectStatus.ACTIVE else 0.0,
                -float(node.miss_count),
                float(node.last_seen_step),
                _id_key(node.object_id),
            )

        candidates = list(selected.values())
        if not candidates:
            candidates = recent[:final_budget]
        candidates.sort(key=final_rank, reverse=True)
        return candidates[:final_budget]

    @staticmethod
    def _parse_geometry_key(geometry_key: str) -> tuple[str, int, int, int] | None:
        """Parse a geometry key of the form ``scene:gsa:item:qx:qy:qz``.

        Returns ``(scene, qx, qy, qz)`` or None if the key doesn't match the
        expected pattern.
        """
        if not geometry_key:
            return None
        parts = geometry_key.rsplit(":", 3)
        if len(parts) != 4:
            return None
        try:
            qx, qy, qz = int(parts[1]), int(parts[2]), int(parts[3])
        except (ValueError, TypeError):
            return None
        return parts[0], qx, qy, qz

    @classmethod
    def _adjacent_geometry_keys(cls, geometry_key: str, radius: int = 1) -> list[str]:
        """Generate geometry keys for adjacent quantized cells.

        For a 0.2m voxel, radius=1 generates 26 neighbor cells (3×3×3 − 1).
        """
        parsed = cls._parse_geometry_key(geometry_key)
        if parsed is None:
            return []
        prefix, qx, qy, qz = parsed
        keys: list[str] = []
        for dx in range(-radius, radius + 1):
            for dy in range(-radius, radius + 1):
                for dz in range(-radius, radius + 1):
                    if dx == 0 and dy == 0 and dz == 0:
                        continue
                    keys.append(f"{prefix}:{qx + dx}:{qy + dy}:{qz + dz}")
        return keys

    def _ann_search(
        self,
        query_feature: tuple[float, ...],
        *,
        top_k: int = 8,
    ) -> list[MemoryObjectNode]:
        """Brute-force ANN over CLIP features of non-retired nodes.

        Uses cosine similarity via the existing ``_cosine`` + ``_similarity_from_cosine``
        pipeline.  Returns nodes sorted by similarity (descending).
        """
        if not query_feature:
            return []
        scored: list[tuple[float, MemoryObjectNode]] = []
        for node in self.nodes.values():
            if node.status is ObjectStatus.RETIRED:
                continue
            if not node.clip_feature or len(node.clip_feature) != len(query_feature):
                continue
            sim = self._similarity_from_cosine(self._cosine(query_feature, node.clip_feature))
            if sim > 0:
                scored.append((sim, node))
        scored.sort(key=lambda item: (item[0], item[1].object_id), reverse=True)
        return [node for _, node in scored[:top_k]]

    @staticmethod
    def _object_id_sort_key(object_id: str) -> int:
        """Extract the numeric suffix from ``obj-{N}`` for deterministic tie-breaking."""
        if object_id.startswith("obj-"):
            try:
                return int(object_id[4:])
            except ValueError:
                pass
        return hash(object_id)  # fallback, rare

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
    def _positive_cosine_similarity(value: float) -> float:
        return max(0.0, min(value, 1.0))

    @staticmethod
    def _normalize_feature(feature: tuple[float, ...]) -> tuple[float, ...]:
        if not feature:
            return ()
        norm = math.sqrt(sum(value * value for value in feature))
        if norm <= 0:
            return ()
        return tuple(round(value / norm, 6) for value in feature)

    @staticmethod
    def _label_from_descriptor(descriptor: str) -> str:
        if not descriptor:
            return ""
        return descriptor.rsplit(":", 1)[-1]

    @classmethod
    def _descriptor_with_label(cls, descriptor: str, label: str) -> str:
        label = cls._label_from_descriptor(label)
        if not label:
            return descriptor
        if ":" not in descriptor:
            return label
        prefix = descriptor.rsplit(":", 1)[0]
        return f"{prefix}:{label}"

    @classmethod
    def dominant_semantic_label(cls, node: MemoryObjectNode) -> str:
        """Return the stable object-level semantic label without changing identity.

        `descriptor_fused` is an identity descriptor used by Layer2 matching.  In
        the ConceptGraphs-style class-agnostic setting it is intentionally a
        token such as `room0:item`, while the object's semantic state lives in
        `class_counts` / CLIP features.  Keeping this helper separate prevents
        one noisy SAM/GSA label from rewriting the identity channel.
        """

        if node.class_counts:
            max_count = max(node.class_counts.values())
            tied_labels = {label for label, count in node.class_counts.items() if count == max_count}
            fused_label = cls._label_from_descriptor(node.descriptor_fused)
            if fused_label in tied_labels:
                return fused_label
            recent_label = cls._label_from_descriptor(node.descriptor_recent)
            if recent_label in tied_labels:
                return recent_label
            return sorted(tied_labels)[0]
        return cls._label_from_descriptor(node.appearance_key_recent or node.descriptor_recent or node.descriptor_fused)

    @classmethod
    def _semantic_vote_score(cls, label: str, descriptor: str, node: MemoryObjectNode) -> float:
        if label:
            candidates = {value for value in (label, cls._label_from_descriptor(label)) if value}
        else:
            candidates = {value for value in (cls._label_from_descriptor(descriptor), descriptor) if value}
        if node.class_counts:
            total = sum(node.class_counts.values())
            if total > 0:
                return max((node.class_counts.get(candidate, 0) / total for candidate in candidates), default=0.0)
        node_labels = {
            node.appearance_key_recent,
            node.descriptor_recent,
            node.descriptor_fused,
            cls._label_from_descriptor(node.descriptor_recent),
            cls._label_from_descriptor(node.descriptor_fused),
        }
        if candidates.intersection(item for item in node_labels if item):
            return 1.0
        return 0.0

    @classmethod
    def _refresh_fused_descriptor(cls, node: MemoryObjectNode, fallback_descriptor: str = "") -> None:
        # Do not rewrite `descriptor_fused` with a semantic class label.  Layer2
        # uses this field as an identity descriptor; class-agnostic experiments
        # rely on it staying at values such as `room0:item` while semantics are
        # maintained separately in class_counts/feature embeddings.
        if fallback_descriptor and not node.descriptor_fused:
            node.descriptor_fused = fallback_descriptor

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

    def _payload_points(self, payload: ObjectObservationPayload | None) -> tuple[tuple[float, float, float], ...]:
        if payload is None:
            return ()
        return self._as_point_tuple(payload.points_sample)

    @staticmethod
    def _sample_points_evenly(
        points: tuple[tuple[float, float, float], ...],
        limit: int,
    ) -> tuple[tuple[float, float, float], ...]:
        if limit <= 0 or len(points) <= limit:
            return points
        if limit == 1:
            return (points[0],)
        keep_indices = [round(index * (len(points) - 1) / (limit - 1)) for index in range(limit)]
        return tuple(points[index] for index in keep_indices)

    @classmethod
    def _point_overlap_fraction(
        cls,
        query_points: tuple[tuple[float, float, float], ...],
        reference_points: tuple[tuple[float, float, float], ...],
        *,
        max_distance: float,
        max_points: int,
    ) -> float:
        """Fraction of query points that land close to any reference point.

        BBox and centroid gates are cheap but too coarse for SAM fragments:
        two fragments from the same physical object can have different small
        boxes, while their sampled 3D points still sit on the same surface.
        This bounded nearest-neighbour check gives history/object matching a
        direct object-overlap signal without adding a dependency.
        """

        if not query_points or not reference_points or max_distance <= 0:
            return 0.0
        query = cls._sample_points_evenly(query_points, max_points)
        reference = cls._sample_points_evenly(reference_points, max_points)
        if not query or not reference:
            return 0.0
        threshold_sq = max_distance * max_distance
        matched = 0
        for qx, qy, qz in query:
            for rx, ry, rz in reference:
                distance_sq = (qx - rx) * (qx - rx) + (qy - ry) * (qy - ry) + (qz - rz) * (qz - rz)
                if distance_sq <= threshold_sq:
                    matched += 1
                    break
        return round(matched / max(len(query), 1), 4)

    def payload_point_overlap_score(
        self,
        payload: ObjectObservationPayload | None,
        node: MemoryObjectNode,
    ) -> float:
        return self._point_overlap_fraction(
            self._payload_points(payload),
            node.sampled_points,
            max_distance=self.config.history_point_overlap_distance,
            max_points=self.config.history_overlap_max_points,
        )

    def hypothesis_point_overlap_score(self, hypothesis: CurrentObjectHypothesis, node: MemoryObjectNode) -> float:
        return self.payload_point_overlap_score(hypothesis.object_payload, node)

    def hypothesis_spatial_score(self, hypothesis: CurrentObjectHypothesis, node: MemoryObjectNode) -> float:
        score = 0.0
        if hypothesis.geometry_key and hypothesis.geometry_key == node.geometry_key:
            score = max(score, 1.0)
        continuity_key = str(hypothesis.support_signals.get("continuity_key") or "")
        if continuity_key and continuity_key == node.continuity_key_recent:
            score = max(score, 0.9)
        payload_min, payload_max = self._payload_bbox(hypothesis.object_payload)
        bbox_score = self._bbox_overlap_score(payload_min, payload_max, node.bbox_min, node.bbox_max)
        score = max(score, bbox_score)
        centroid_score = self._centroid_distance_score(self._payload_centroid(hypothesis.object_payload), node.centroid)
        score = max(score, centroid_score * 0.75)
        return round(score, 4)

    def hypothesis_visual_score(self, hypothesis: CurrentObjectHypothesis, node: MemoryObjectNode) -> float:
        if hypothesis.object_payload is None:
            return 0.0
        feature = self._as_float_tuple(hypothesis.object_payload.clip_feature)
        if not feature or not node.clip_feature:
            return 0.0
        return round(self._similarity_from_cosine(self._cosine(feature, node.clip_feature)), 4)

    def hypothesis_semantic_score(self, hypothesis: CurrentObjectHypothesis, node: MemoryObjectNode) -> float:
        label = ""
        text_feature: tuple[float, ...] = ()
        if hypothesis.object_payload is not None:
            label = hypothesis.object_payload.label
            text_feature = self._as_float_tuple(hypothesis.object_payload.text_feature)
        if not label:
            label = str(hypothesis.support_signals.get("appearance_key") or "")
        return self._semantic_score(label, hypothesis.descriptor, node, text_feature=text_feature)

    def _semantic_score(
        self,
        label: str,
        descriptor: str,
        node: MemoryObjectNode,
        *,
        text_feature: tuple[float, ...] = (),
    ) -> float:
        vote_score = self._semantic_vote_score(label, descriptor, node)
        text_score: float | None = None
        if text_feature and node.text_feature and len(text_feature) == len(node.text_feature):
            text_score = self._positive_cosine_similarity(self._cosine(text_feature, node.text_feature))
        if text_score is not None:
            # ConceptGraphs keeps object-level CLIP/text embeddings and lets the
            # accumulated feature be the semantic authority.  The top-1 class
            # vote is only a weak tie-breaker when feature evidence exists, so
            # one noisy SAM/GSA label cannot overwrite an otherwise stable
            # object semantic state.
            return round(max(text_score, 0.75 * text_score + 0.25 * vote_score), 4)
        if not label and not descriptor:
            return 0.0
        return round(vote_score, 4)

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

    def _item_semantic_score(self, item: EvidenceItem, node: MemoryObjectNode) -> float:
        label = item.object_payload.label if item.object_payload is not None else self._support_str(item, "appearance_key")
        text_feature = self._as_float_tuple(item.object_payload.text_feature) if item.object_payload is not None else ()
        return self._semantic_score(label, item.descriptor, node, text_feature=text_feature)

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
        for node in self.nodes.values():
            if node.status is ObjectStatus.RETIRED:
                continue
            spatial_score = self._node_spatial_score(item, node)
            point_overlap_score = self.payload_point_overlap_score(item.object_payload, node)
            visual_score = self._node_visual_score(item, node)
            semantic_score = self._item_semantic_score(item, node)
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
            if self.config.history_point_overlap_affinity_weight > 0:
                semantic_ok = semantic_score >= self.config.history_point_overlap_min_semantic_score
                spatial_ok = spatial_score >= self.config.history_point_overlap_min_spatial_score
                visual_ok = visual_score >= self.config.layer2_point_overlap_identity_min_visual
                gated_overlap = (
                    point_overlap_score
                    if (
                        point_overlap_score >= self.config.layer2_history_min_point_overlap
                        and (semantic_ok or visual_ok)
                        and (
                            spatial_ok
                            or (
                                point_overlap_score >= self.config.layer2_point_overlap_identity_threshold
                                and not self.config.history_point_overlap_requires_spatial_evidence
                            )
                        )
                    )
                    else 0.0
                )
                affinity = round(
                    min(affinity + self.config.history_point_overlap_affinity_weight * gated_overlap, 1.0),
                    4,
                )
            if affinity >= min_affinity:
                raw_candidates.append(
                    (
                        affinity,
                        node.object_id,
                        {
                            "spatial_score": spatial_score,
                            "point_overlap_score": point_overlap_score,
                            "visual_score": visual_score,
                            "semantic_score": semantic_score,
                            "recency_score": recency_score,
                            "size_score": size_score,
                        },
                    )
                )
        raw_candidates.sort(key=lambda item_score: (item_score[0], item_score[1]), reverse=True)
        candidates: list[HistoryCandidate] = []
        for index, (affinity, object_id, components) in enumerate(raw_candidates[:top_k]):
            next_affinity = raw_candidates[index + 1][0] if index + 1 < len(raw_candidates) else 0.0
            margin = round(affinity - next_affinity, 4)
            candidates.append(
                HistoryCandidate(
                    object_id=object_id,
                    affinity=affinity,
                    spatial_score=components["spatial_score"],
                    point_overlap_score=components["point_overlap_score"],
                    visual_score=components["visual_score"],
                    semantic_score=components["semantic_score"],
                    recency_score=components["recency_score"],
                    size_score=components["size_score"],
                    margin=margin,
                    strong=affinity >= min_affinity and margin >= self.config.history_candidate_margin_threshold,
                )
            )
        return tuple(candidates)

    def _blend_feature(
        self,
        previous: tuple[float, ...],
        current: tuple[float, ...],
        previous_weight: int,
        current_weight: int,
        *,
        normalize: bool = False,
    ) -> tuple[float, ...]:
        if not current:
            return previous
        if normalize:
            current = self._normalize_feature(current)
            previous = self._normalize_feature(previous)
            if not current:
                return previous
        if not previous or len(previous) != len(current):
            return current
        total = max(previous_weight + current_weight, 1)
        blended = tuple(round((pv * previous_weight + cv * current_weight) / total, 6) for pv, cv in zip(previous, current))
        return self._normalize_feature(blended) if normalize else blended

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
        previous_descriptor_fused = node.descriptor_fused
        node.descriptor_recent = hypothesis.descriptor
        if not node.descriptor_fused:
            node.descriptor_fused = hypothesis.descriptor
        node.last_seen_step = step_id
        node.detection_count = previous_count + current_count
        node.confidence_sum += hypothesis.confidence * current_count
        if payload is not None:
            label = payload.label or str(hypothesis.support_signals.get("appearance_key") or hypothesis.descriptor)
            label = self._label_from_descriptor(label)
            if label:
                node.class_counts[label] = node.class_counts.get(label, 0) + current_count
            node.mask_area_sum += float(payload.mask_area or 0.0)
            current_clip = self._as_float_tuple(payload.clip_feature)
            current_text = self._as_float_tuple(payload.text_feature)
            node.clip_feature = self._blend_feature(node.clip_feature, current_clip, previous_count, current_count, normalize=True)
            node.text_feature = self._blend_feature(node.text_feature, current_text, previous_count, current_count, normalize=True)
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
            label = self._label_from_descriptor(label)
            if label:
                node.class_counts[label] = node.class_counts.get(label, 0) + current_count
        self._refresh_fused_descriptor(node, previous_descriptor_fused or hypothesis.descriptor)

    def _object_semantic_score(self, left: MemoryObjectNode, right: MemoryObjectNode) -> float:
        text_score: float | None = None
        if left.text_feature and right.text_feature and len(left.text_feature) == len(right.text_feature):
            text_score = self._positive_cosine_similarity(self._cosine(left.text_feature, right.text_feature))
        vote_score = 0.0
        if not left.class_counts or not right.class_counts:
            if left.appearance_key_recent and left.appearance_key_recent == right.appearance_key_recent:
                vote_score = 1.0
        else:
            common = set(left.class_counts).intersection(right.class_counts)
            if common:
                overlap = sum(min(left.class_counts[label], right.class_counts[label]) for label in common)
                denominator = max(min(sum(left.class_counts.values()), sum(right.class_counts.values())), 1)
                vote_score = overlap / denominator
        if text_score is None:
            return round(vote_score, 4)
        return round(max(text_score, 0.75 * text_score + 0.25 * vote_score), 4)

    @staticmethod
    def _class_distribution_summary(counts: dict[str, int]) -> dict[str, float | str | int]:
        total = sum(max(int(count), 0) for count in counts.values())
        if total <= 0:
            return {"total": 0, "top_label": "", "top_share": 0.0, "entropy": 0.0}
        top_label, top_count = max(counts.items(), key=lambda item: (int(item[1]), str(item[0])))
        entropy = 0.0
        for count in counts.values():
            p = max(int(count), 0) / total
            if p > 0:
                entropy -= p * math.log(p, 2)
        return {
            "total": total,
            "top_label": str(top_label),
            "top_share": round(top_count / total, 4),
            "entropy": round(entropy, 4),
        }

    def _object_semantic_conflict(
        self,
        left: MemoryObjectNode,
        right: MemoryObjectNode,
        *,
        semantic_score: float,
        visual_score: float,
    ) -> tuple[bool, dict[str, float | str | int | bool]]:
        if not self.config.object_merge_semantic_conflict_guard:
            return False, {"semantic_conflict": False}
        if not left.class_counts or not right.class_counts:
            return False, {"semantic_conflict": False}
        if visual_score >= self.config.object_merge_semantic_conflict_visual_override and semantic_score >= self.config.object_merge_semantic_conflict_min_score:
            return False, {"semantic_conflict": False, "semantic_conflict_visual_override": True}

        left_summary = self._class_distribution_summary(left.class_counts)
        right_summary = self._class_distribution_summary(right.class_counts)
        merged_counts: dict[str, int] = dict(left.class_counts)
        for label, count in right.class_counts.items():
            merged_counts[label] = merged_counts.get(label, 0) + count
        merged_summary = self._class_distribution_summary(merged_counts)
        left_top = str(left_summary.get("top_label", ""))
        right_top = str(right_summary.get("top_label", ""))
        left_total = int(left_summary.get("total", 0) or 0)
        right_total = int(right_summary.get("total", 0) or 0)
        merged_total = max(int(merged_summary.get("total", 0) or 0), 1)
        common_labels = set(left.class_counts).intersection(right.class_counts)
        common_overlap = sum(min(left.class_counts[label], right.class_counts[label]) for label in common_labels)
        common_share = common_overlap / max(min(left_total, right_total), 1)
        smaller_top_share = float(right_summary.get("top_share", 0.0) if right_total <= left_total else left_summary.get("top_share", 0.0))
        smaller_total_share = min(left_total, right_total) / merged_total
        dominant_label_conflict = (
            bool(left_top and right_top and left_top != right_top)
            and semantic_score < self.config.object_merge_semantic_conflict_min_score
        )
        mixed_root_conflict = (
            float(merged_summary.get("entropy", 0.0) or 0.0) > self.config.object_merge_max_merged_label_entropy
            and float(merged_summary.get("top_share", 0.0) or 0.0) < self.config.object_merge_min_merged_top_label_share
            and common_share < 0.5
        )
        protected_small_label_conflict = (
            bool(left_top and right_top and left_top != right_top)
            and smaller_total_share >= self.config.object_merge_protect_small_label_share
            and smaller_top_share >= self.config.object_merge_protect_small_label_confidence
            and semantic_score < self.config.object_merge_semantic_conflict_min_score
        )
        conflict = dominant_label_conflict or mixed_root_conflict or protected_small_label_conflict
        return conflict, {
            "semantic_conflict": conflict,
            "left_top_label": left_top,
            "right_top_label": right_top,
            "merged_top_label": str(merged_summary.get("top_label", "")),
            "left_top_share": float(left_summary.get("top_share", 0.0) or 0.0),
            "right_top_share": float(right_summary.get("top_share", 0.0) or 0.0),
            "merged_top_share": float(merged_summary.get("top_share", 0.0) or 0.0),
            "merged_label_entropy": float(merged_summary.get("entropy", 0.0) or 0.0),
            "semantic_common_share": round(common_share, 4),
            "smaller_label_share": round(smaller_total_share, 4),
            "semantic_conflict_dominant_label": dominant_label_conflict,
            "semantic_conflict_mixed_root": mixed_root_conflict,
            "semantic_conflict_protected_small_label": protected_small_label_conflict,
        }

    def object_affinity(self, left: MemoryObjectNode, right: MemoryObjectNode) -> tuple[float, dict[str, object]]:
        semantic_score = self._object_semantic_score(left, right)
        spatial_score = self._bbox_overlap_score(left.bbox_min, left.bbox_max, right.bbox_min, right.bbox_max)
        spatial_score = max(spatial_score, self._centroid_distance_score(left.centroid, right.centroid) * 0.75)
        point_overlap_score = max(
            self._point_overlap_fraction(
                left.sampled_points,
                right.sampled_points,
                max_distance=self.config.history_point_overlap_distance,
                max_points=self.config.history_overlap_max_points,
            ),
            self._point_overlap_fraction(
                right.sampled_points,
                left.sampled_points,
                max_distance=self.config.history_point_overlap_distance,
                max_points=self.config.history_overlap_max_points,
            ),
        )
        if semantic_score >= self.config.object_merge_point_overlap_min_semantic_score:
            spatial_score = max(spatial_score, point_overlap_score)
        if left.geometry_key and left.geometry_key == right.geometry_key:
            spatial_score = max(spatial_score, 1.0)
        if left.continuity_key_recent and left.continuity_key_recent == right.continuity_key_recent:
            spatial_score = max(spatial_score, 0.9)
        visual_score = self._similarity_from_cosine(self._cosine(left.clip_feature, right.clip_feature))
        semantic_conflict, semantic_conflict_components = self._object_semantic_conflict(
            left,
            right,
            semantic_score=semantic_score,
            visual_score=visual_score,
        )
        size_score = round(
            (
                self._compatibility(left.avg_support_size, right.avg_support_size, max_delta=0.2)
                + self._compatibility(left.avg_depth_scale, right.avg_depth_scale, max_delta=0.3)
                + self._compatibility(left.avg_geometry_support, right.avg_geometry_support, max_delta=0.25)
            )
            / 3.0,
            4,
        )
        point_overlap_weight = max(self.config.object_merge_point_overlap_weight, 0.0)
        base_score = round(0.50 * spatial_score + 0.25 * visual_score + 0.20 * semantic_score + 0.05 * size_score, 4)
        score = round(
            min(base_score + point_overlap_weight * point_overlap_score, 1.0),
            4,
        )
        components = {
            "spatial": round(spatial_score, 4),
            "point_overlap": round(point_overlap_score, 4),
            "visual": round(visual_score, 4),
            "semantic": round(semantic_score, 4),
            "size": round(size_score, 4),
        }
        components.update(semantic_conflict_components)  # type: ignore[arg-type]
        if semantic_conflict:
            score = min(score, round(max(self.config.object_merge_threshold - 0.01, 0.0), 4))
        return score, components

    def merge_nodes(self, target: MemoryObjectNode, source: MemoryObjectNode) -> None:
        previous_count = max(target.detection_count, 0)
        source_count = max(source.detection_count, 1)
        target.detection_count = previous_count + source_count
        target.confidence_sum += source.confidence_sum
        target.mask_area_sum += source.mask_area_sum
        target.point_count += source.point_count
        for label, count in source.class_counts.items():
            target.class_counts[label] = target.class_counts.get(label, 0) + count
        target.clip_feature = self._blend_feature(target.clip_feature, source.clip_feature, previous_count, source_count, normalize=True)
        target.text_feature = self._blend_feature(target.text_feature, source.text_feature, previous_count, source_count, normalize=True)
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
        self._refresh_fused_descriptor(target, target.descriptor_fused or source.descriptor_fused)
        self._redirect_relation_edges(source.object_id, target.object_id)
        source.status = ObjectStatus.RETIRED
        source.merge_target_id = target.object_id
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
                if components.get("semantic_conflict"):
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

    @staticmethod
    def export_skip_reason(
        node: MemoryObjectNode,
        *,
        min_points: int = 4,
        min_detections: int = 1,
    ) -> str:
        if "merged_into_duplicate_object" in node.failure_tags:
            return "merged_into_duplicate_object"
        if "filtered_low_detection_object" in node.failure_tags:
            return "filtered_low_detection_object"
        if max(int(node.detection_count), 0) < max(int(min_detections), 1):
            return "too_few_detections"
        if max(int(node.point_count), len(node.sampled_points)) < max(int(min_points), 0):
            return "too_few_points"
        return ""

    @classmethod
    def is_exportable_node(
        cls,
        node: MemoryObjectNode,
        *,
        min_points: int = 4,
        min_detections: int = 1,
    ) -> bool:
        return cls.export_skip_reason(node, min_points=min_points, min_detections=min_detections) == ""

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

    # ---- Phase 丁: equivalence partition (UF + conflict pruning) ----

    def _generate_merge_candidate_pairs(
        self, active_nodes: list[MemoryObjectNode], step_id: int
    ) -> list[tuple[int, int, float, dict[str, object]]]:
        """Generate scored candidate pairs for equivalence partition.

        Returns list of (idx_a, idx_b, score, components) sorted by score desc.
        """
        edges: list[tuple[int, int, float, dict[str, object]]] = []
        max_dt = self.config.pair_max_dt
        topk = self.config.pair_topk

        for i, left in enumerate(active_nodes):
            # Only consider nodes within birth_step window
            candidates = []
            for j, right in enumerate(active_nodes):
                if j <= i:
                    continue
                if abs(left.birth_step - right.birth_step) > max_dt:
                    continue
                score, components = self.object_affinity(left, right)
                if score >= self.config.edge_neg_thresh:
                    candidates.append((j, score, components))
            # Keep top-k per node for efficiency
            candidates.sort(key=lambda x: x[1], reverse=True)
            for j, score, components in candidates[:topk]:
                edges.append((i, j, score, components))

        edges.sort(key=lambda x: x[2], reverse=True)
        return edges

    def _union_find_with_conflicts(
        self,
        n: int,
        pos_edges: list[tuple[int, int, float]],
        neg_edges: set[tuple[int, int]],
    ) -> dict[int, int]:
        """Union-find respecting cannot-link constraints.

        Returns mapping from node index to component root.
        """
        parent = list(range(n))

        def find(x: int) -> int:
            while parent[x] != x:
                parent[x] = parent[parent[x]]
                x = parent[x]
            return x

        def union(a: int, b: int) -> bool:
            ra, rb = find(a), find(b)
            if ra == rb:
                return False
            parent[ra] = rb
            return True

        def component_members(root: int) -> set[int]:
            return {i for i in range(n) if find(i) == root}

        for i, j, _score in pos_edges:
            ri, rj = find(i), find(j)
            if ri == rj:
                continue
            # Check: is there any negative edge between the two components?
            members_i = component_members(ri)
            members_j = component_members(rj)
            conflict = False
            for mi in members_i:
                for mj in members_j:
                    if (mi, mj) in neg_edges or (mj, mi) in neg_edges:
                        conflict = True
                        break
                if conflict:
                    break
            if not conflict:
                union(i, j)

        # Return component assignments
        return {i: find(i) for i in range(n)}

    def merge_duplicate_objects_v2(self, step_id: int = 0) -> list[dict[str, object]]:
        """Equivalence partition via scored edges + UF with conflict pruning.

        Replaces pairwise greedy merge with global signed-graph partition.
        """
        merges: list[dict[str, object]] = []
        active_nodes = [node for node in self.nodes.values() if node.status is not ObjectStatus.RETIRED]
        if len(active_nodes) < 2:
            return merges

        # Index nodes for the partition
        node_indices = {node.object_id: i for i, node in enumerate(active_nodes)}
        n = len(active_nodes)

        # Generate scored edges
        edges = self._generate_merge_candidate_pairs(active_nodes, step_id)

        # Build signed graphs
        pos_thresh = self.config.edge_pos_thresh
        neg_thresh = self.config.edge_neg_thresh
        pos_edges: list[tuple[int, int, float]] = []
        neg_edges: set[tuple[int, int]] = set()

        for i, j, score, components in edges:
            if score >= pos_thresh and not components.get("semantic_conflict"):
                pos_edges.append((i, j, score))
            elif score <= neg_thresh:
                neg_edges.add((i, j))

        # Union-find with conflict pruning
        partition = self._union_find_with_conflicts(n, pos_edges, neg_edges)

        # Execute merges: all nodes in same component merge to the first node
        component_roots: dict[int, list[int]] = {}
        for idx, root in partition.items():
            component_roots.setdefault(root, []).append(idx)

        merge_log: list[dict[str, object]] = []
        for root_idx, member_indices in component_roots.items():
            if len(member_indices) < 2:
                continue
            # Merge all into the first (oldest birth_step) node
            sorted_members = sorted(member_indices, key=lambda idx: (active_nodes[idx].birth_step, active_nodes[idx].object_id))
            target_node = active_nodes[sorted_members[0]]
            for member_idx in sorted_members[1:]:
                source_node = active_nodes[member_idx]
                if source_node.status is ObjectStatus.RETIRED or target_node.status is ObjectStatus.RETIRED:
                    continue
                # Recompute affinity for the merge log
                score, components = self.object_affinity(target_node, source_node)
                if components.get("semantic_conflict"):
                    continue
                self.merge_nodes(target_node, source_node)
                merge_log.append({
                    "target_object_id": target_node.object_id,
                    "source_object_id": source_node.object_id,
                    "score": score,
                    "components": components,
                    "partition_method": "uf_conflict_pruning",
                    "component_size": len(member_indices),
                })

        return merge_log

    def consolidate_objects(self) -> dict[str, object]:
        denoise_summary = self.denoise_objects()
        if self.config.enable_object_consolidation:
            if self.config.entity_graph_enable:
                merges = self.merge_duplicate_objects_v2()
            else:
                merges = self.merge_duplicate_objects()
        else:
            merges = []
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

    def _redirect_relation_edges(self, source_object_id: str, target_object_id: str) -> None:
        """Move co-visibility evidence from a merged source node to its target."""

        if not source_object_id or not target_object_id or source_object_id == target_object_id:
            return
        rewritten: dict[tuple[str, str], MemoryRelationEdge] = {}
        for _old_key, edge in self.relation_edges.items():
            left = target_object_id if edge.source_object_id == source_object_id else edge.source_object_id
            right = target_object_id if edge.target_object_id == source_object_id else edge.target_object_id
            if left == right:
                continue
            key = self._relation_key(left, right)
            existing = rewritten.get(key)
            if existing is None:
                rewritten[key] = MemoryRelationEdge(
                    source_object_id=key[0],
                    target_object_id=key[1],
                    relation_type=edge.relation_type,
                    co_visibility_count=edge.co_visibility_count,
                    last_seen_step=edge.last_seen_step,
                    strength=edge.strength,
                )
            else:
                existing.co_visibility_count += edge.co_visibility_count
                existing.last_seen_step = max(existing.last_seen_step, edge.last_seen_step)
                existing.strength = round(min(existing.co_visibility_count / 5.0, 1.0), 3)
        self.relation_edges = rewritten

    def relation_bonus(self, source_object_id: str, target_object_id: str) -> float:
        edge = self.relation_edges.get(self._relation_key(source_object_id, target_object_id))
        return edge.strength if edge is not None else 0.0
