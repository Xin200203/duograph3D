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


@dataclass
class Observation:
    observation_id: str
    descriptor: str
    geometry_key: str
    confidence: float = 1.0
    repair_group_id: str | None = None
    support_tokens: tuple[str, ...] = ()
    support: ObservationSupport | None = None


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
    association_threshold: float = 1.2
    occluded_after_misses: int = 1
    dormant_after_misses: int = 2
    retire_after_misses: int = 4
    propagation_keepalive_misses: int = 2


@dataclass
class SequenceRunResult:
    branch_id: str
    sequence_id: str
    memory_nodes: dict[str, MemoryObjectNode]
    event_count: int
    decisions: list[AssociationDecision]


def mean_confidence(items: Iterable[float]) -> float:
    values = list(items)
    return sum(values) / len(values) if values else 0.0
