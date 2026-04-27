from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Iterable


class TemporalVariant(str, Enum):
    NONE = "temporal_none"
    NAIVE_FRAMEWISE = "temporal_naive_framewise"
    DEVA_STYLE = "temporal_deva_style"


class EvidenceProvenance(str, Enum):
    CURRENT = "current"
    PROPAGATED = "propagated"


class ObjectStatus(str, Enum):
    ACTIVE = "active"
    OCCLUDED = "occluded"
    DORMANT = "dormant"
    RETIRED = "retired"


@dataclass
class ObservationSupport:
    proposal_id: str
    frame_token: str
    pose_token: str = ""
    source_kind: str = "synthetic"
    support_size: float = 0.0
    depth_scale: float = 1.0
    appearance_key: str = ""
    continuity_key: str = ""
    geometry_support: float = 0.0


@dataclass(frozen=True)
class ObjectObservationPayload:
    """Object-level evidence carried by one 2D/3D observation.

    The core package keeps this representation dependency-free so runners can
    pass sampled points/features as plain tuples or lists.  Memory code is
    responsible for normalizing these values before fusion.
    """

    label: str = ""
    points_sample: tuple[tuple[float, float, float], ...] = ()
    colors_sample: tuple[tuple[float, float, float], ...] = ()
    bbox_min: tuple[float, ...] = ()
    bbox_max: tuple[float, ...] = ()
    centroid: tuple[float, ...] = ()
    clip_feature: tuple[float, ...] = ()
    text_feature: tuple[float, ...] = ()
    mask_area: float = 0.0
    detection_count: int = 1


@dataclass(frozen=True)
class HistoryCandidate:
    object_id: str
    affinity: float
    spatial_score: float = 0.0
    point_overlap_score: float = 0.0
    visual_score: float = 0.0
    semantic_score: float = 0.0
    recency_score: float = 0.0
    size_score: float = 0.0
    margin: float = 0.0
    source: str = "memory"
    strong: bool = False


@dataclass
class Observation:
    observation_id: str
    descriptor: str
    geometry_key: str
    confidence: float = 1.0
    repair_group_id: str | None = None
    support_tokens: tuple[str, ...] = ()
    support: ObservationSupport | None = None
    object_payload: ObjectObservationPayload | None = None


@dataclass
class FrameInput:
    frame_id: str
    observations: list[Observation]


@dataclass
class EvidenceItem:
    evidence_id: str
    descriptor: str
    geometry_key: str
    confidence: float
    provenance: EvidenceProvenance
    source_observation_ids: tuple[str, ...] = ()
    support_tokens: tuple[str, ...] = ()
    repair_group_id: str | None = None
    memory_hint_id: str | None = None
    support: ObservationSupport | None = None
    history_candidates: tuple[HistoryCandidate, ...] = ()
    object_payload: ObjectObservationPayload | None = None


@dataclass
class CurrentObjectHypothesis:
    hypothesis_id: str
    descriptor: str
    geometry_key: str
    confidence: float
    evidence_ids: tuple[str, ...]
    track_hint: str
    ambiguity_flags: tuple[str, ...] = ()
    provenance_counts: dict[str, int] = field(default_factory=dict)
    support_signals: dict[str, object] = field(default_factory=dict)
    history_candidates: tuple[HistoryCandidate, ...] = ()
    object_payload: ObjectObservationPayload | None = None


@dataclass
class MemoryRelationEdge:
    source_object_id: str
    target_object_id: str
    relation_type: str = "co_visibility"
    co_visibility_count: int = 0
    last_seen_step: int = 0
    strength: float = 0.0


@dataclass
class MemoryObjectNode:
    object_id: str
    descriptor_fused: str
    descriptor_recent: str
    geometry_key: str
    status: ObjectStatus = ObjectStatus.ACTIVE
    birth_step: int = 0
    last_seen_step: int = 0
    miss_count: int = 0
    reentry_count: int = 0
    lifecycle_confidence: float = 1.0
    temporal_support_history: list[str] = field(default_factory=list)
    propagation_support_ratio: float = 0.0
    refresh_support_ratio: float = 1.0
    evidence_provenance_tail: list[str] = field(default_factory=list)
    ambiguity_flags: set[str] = field(default_factory=set)
    failure_tags: set[str] = field(default_factory=set)
    continuity_key_recent: str = ""
    appearance_key_recent: str = ""
    avg_support_size: float = 0.0
    avg_depth_scale: float = 1.0
    avg_geometry_support: float = 0.0
    detection_count: int = 0
    confidence_sum: float = 0.0
    mask_area_sum: float = 0.0
    point_count: int = 0
    sampled_points: tuple[tuple[float, float, float], ...] = ()
    sampled_colors: tuple[tuple[float, float, float], ...] = ()
    bbox_min: tuple[float, ...] = ()
    bbox_max: tuple[float, ...] = ()
    centroid: tuple[float, ...] = ()
    clip_feature: tuple[float, ...] = ()
    text_feature: tuple[float, ...] = ()
    class_counts: dict[str, int] = field(default_factory=dict)

    def register_support(self, provenance: EvidenceProvenance) -> None:
        self.evidence_provenance_tail.append(provenance.value)
        self.temporal_support_history.append(provenance.value)
        tail = self.temporal_support_history[-10:]
        propagated = sum(1 for item in tail if item == EvidenceProvenance.PROPAGATED.value)
        refreshed = sum(1 for item in tail if item == EvidenceProvenance.CURRENT.value)
        total = max(len(tail), 1)
        self.propagation_support_ratio = propagated / total
        self.refresh_support_ratio = refreshed / total


@dataclass
class AssociationDecision:
    hypothesis_id: str
    action: str
    object_id: str
    score: float
    reason: str
    track_hint: str = ""


@dataclass
class PipelineConfig:
    candidate_budget: int = 5
    association_threshold: float = 1.7
    occluded_after_misses: int = 1
    dormant_after_misses: int = 2
    retire_after_misses: int = 4
    propagation_keepalive_misses: int = 2
    emit_association_diagnostics: bool = False
    association_diagnostics_top_k: int = 3
    enable_history_candidates: bool = True
    history_candidate_top_k: int = 5
    history_candidate_affinity_threshold: float = 0.7
    history_candidate_margin_threshold: float = 0.15
    layer1_merge_threshold: float = 0.9
    layer1_history_shared_boost: float = 0.45
    layer1_history_min_spatial_score: float = 0.45
    layer1_history_min_semantic_score: float = 0.55
    layer1_history_min_visual_score: float = 0.0
    layer1_history_min_size_score: float = 0.0
    layer2_history_identity_threshold: float = 0.7
    history_point_overlap_distance: float = 0.12
    history_overlap_max_points: int = 48
    history_point_overlap_affinity_weight: float = 0.0
    layer2_enable_residual_absorption: bool = False
    layer2_absorption_threshold: float = 1.68
    layer2_absorption_min_point_overlap: float = 1.0
    layer2_absorption_min_semantic_score: float = 1.0
    memory_max_points_per_object: int = 512
    enable_object_consolidation: bool = True
    object_merge_interval: int = 20
    object_merge_threshold: float = 0.88
    object_merge_spatial_threshold: float = 0.15
    object_filter_min_detections: int = 1


@dataclass
class SequenceRunResult:
    branch_id: str
    sequence_id: str
    memory_nodes: dict[str, MemoryObjectNode]
    event_count: int
    decisions: list[AssociationDecision]
    relation_edges: dict[tuple[str, str], MemoryRelationEdge] = field(default_factory=dict)


def mean_confidence(items: Iterable[float]) -> float:
    values = list(items)
    return sum(values) / len(values) if values else 0.0
