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


class FragmentStatus(str, Enum):
    TENTATIVE = "tentative"
    CONFIRMED = "confirmed"
    RETIRED = "retired"


@dataclass
class TentativeFragment:
    """Phase 丙: unconfirmed object fragment awaiting promotion.

    An unmatched hypothesis spawns a tentative fragment instead of directly
    creating a confirmed MemoryObjectNode.  After accumulating enough evidence
    (hits, self-consistency, geometry-consistency, low conflict rate), the
    fragment is promoted to a confirmed node.

    Tentative fragments participate in candidate retrieval at lower priority
    so they can absorb subsequent observations while awaiting promotion.
    """
    fragment_id: str
    birth_step: int
    hits: int = 1
    last_seen_step: int = 0
    miss_count: int = 0
    # Promotion signals
    self_consistency: float = 0.0
    geometry_consistency: float = 0.0
    conflict_count: int = 0
    # Accumulated fusion state (mirrors MemoryObjectNode but lightweight)
    descriptor: str = ""
    geometry_key: str = ""
    detection_count: int = 0
    confidence_sum: float = 0.0
    mask_area_sum: float = 0.0
    class_counts: dict[str, int] = field(default_factory=dict)
    clip_feature: tuple[float, ...] = ()
    text_feature: tuple[float, ...] = ()
    bbox_min: tuple[float, ...] = ()
    bbox_max: tuple[float, ...] = ()
    centroid: tuple[float, ...] = ()
    continuity_key_recent: str = ""
    appearance_key_recent: str = ""
    avg_support_size: float = 0.0
    avg_depth_scale: float = 1.0
    avg_geometry_support: float = 0.0
    # Rejection metadata
    rejection_reason: str = ""
    absorbed_into_id: str = ""


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
    # Phase 乙: label distribution and per-label point buckets (from signed Layer1)
    label_distribution: dict[str, float] = field(default_factory=dict)
    label_buckets: dict[str, tuple[tuple[float, float, float], ...]] = field(default_factory=dict)
    # Phase 乙: negative edges that were suppressed during repair
    neg_edge_ids: tuple[str, ...] = ()
    # Phase 乙: merge decision metadata
    merge_reasons: tuple[str, ...] = ()
    merge_score: float = 0.0


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
    merge_target_id: str = ""
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
    # Phase 丙: stable memory prototypes (EMA-updated, high-confidence only)
    stable_clip_feature: tuple[float, ...] = ()
    stable_text_feature: tuple[float, ...] = ()
    stable_write_count: int = 0
    last_stable_write_margin: float = 0.0

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
    candidate_retrieval_budget: int = 12
    candidate_retrieval_channel_budget: int = 5
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
    # Phase 乙: signed Layer1 — negative edges
    l1_neg_edge_enable: bool = False
    l1_pos_threshold: float = 0.75
    l1_neg_threshold: float = 0.60
    l1_sep3d_thresh: float = 0.18
    l1_jsd_neg_thresh: float = 0.45
    l1_preserve_label_distribution: bool = False
    # Phase 乙: candidate retrieval v2
    cand_include_adj_key: bool = False
    cand_include_ann: bool = False
    cand_adj_radius: int = 1
    cand_ann_top_k: int = 8
    # Phase 乙: per-candidate source tracking for monitoring
    cand_track_sources: bool = False
    # Phase 丙: tentative fragment + promotion gate
    enable_tentative_fragments: bool = False
    promotion_min_hits: int = 3
    promotion_min_sc: float = 0.70
    promotion_min_gc: float = 0.60
    promotion_max_conflict_rate: float = 0.10
    promotion_max_label_entropy: float = 1.0
    promotion_min_top_label_share: float = 0.60
    tentative_candidate_priority_boost: float = 0.15
    # Phase 丙: working / stable memory
    enable_stable_memory: bool = False
    stable_write_margin: float = 0.25
    stable_ema_alpha: float = 0.05
    working_memory_len: int = 8
    # Phase 丁: equivalence partition (UF + conflict pruning)
    entity_graph_enable: bool = False
    edge_pos_thresh: float = 0.95
    edge_neg_thresh: float = 0.05
    pair_topk: int = 10
    pair_max_dt: int = 120
    exact_component_max: int = 20
    # Phase 丁: carrier selection
    carrier_selection_enable: bool = False
    carrier_w_cov: float = 0.30
    carrier_w_purity: float = 0.25
    carrier_w_sem: float = 0.20
    carrier_w_geo: float = 0.15
    carrier_w_dup: float = 0.10
    layer2_history_identity_threshold: float = 0.7
    history_point_overlap_distance: float = 0.12
    history_overlap_max_points: int = 48
    history_point_overlap_affinity_weight: float = 0.25
    history_point_overlap_min_semantic_score: float = 0.45
    history_point_overlap_min_spatial_score: float = 0.3
    history_point_overlap_requires_spatial_evidence: bool = True
    layer2_enable_residual_absorption: bool = True
    layer2_absorption_threshold: float = 1.75
    layer2_absorption_min_point_overlap: float = 0.4
    layer2_absorption_min_semantic_score: float = 0.55
    layer2_require_strong_identity: bool = True
    layer2_history_min_spatial_score: float = 0.45
    layer2_history_min_semantic_score: float = 0.55
    layer2_history_min_point_overlap: float = 0.15
    layer2_point_overlap_weight: float = 0.45
    layer2_point_overlap_score_threshold: float = 0.15
    layer2_point_overlap_identity_threshold: float = 0.35
    layer2_point_overlap_identity_min_spatial: float = 0.35
    layer2_point_overlap_identity_min_semantic: float = 0.55
    layer2_point_overlap_identity_min_visual: float = 0.7
    layer2_point_overlap_identity_requires_spatial_evidence: bool = True
    layer2_relation_bonus_weight: float = 0.25
    layer2_relation_bonus_cap: float = 0.35
    layer2_relation_bonus_min_semantic_score: float = 0.55
    layer2_relation_bonus_requires_identity: bool = True
    layer2_visual_similarity_weight: float = 0.35
    layer2_descriptor_match_weight: float = 0.55
    layer2_appearance_match_weight: float = 0.3
    memory_max_points_per_object: int = 512
    enable_object_consolidation: bool = True
    object_merge_interval: int = 20
    object_merge_threshold: float = 0.88
    object_merge_spatial_threshold: float = 0.15
    object_merge_point_overlap_weight: float = 0.12
    object_merge_point_overlap_min_semantic_score: float = 0.55
    object_merge_semantic_conflict_guard: bool = True
    object_merge_semantic_conflict_min_score: float = 0.45
    object_merge_semantic_conflict_visual_override: float = 0.88
    object_merge_max_merged_label_entropy: float = 1.15
    object_merge_min_merged_top_label_share: float = 0.55
    object_merge_protect_small_label_share: float = 0.05
    object_merge_protect_small_label_confidence: float = 0.65
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
