from __future__ import annotations

from dataclasses import dataclass, field


MEMORY_EXPORT_SOURCE = "duograph3d_online_object_memory"
MEMORY_DENSE_EXPORT_SOURCE = "duograph3d_online_memory_dense_geometry"
GEOMETRY_EXPORT_SOURCE = "duograph3d_geometry_key_coverage"
LABEL_BUCKET_EXPORT_SOURCE = "duograph3d_label_bucket_split"
VALID_EXPORT_SOURCE_STRATEGIES = {"auto", "geometry", "memory", "memory-dense", "memory_dense", "carrier_v2"}
VALID_CARRIER_TYPES = {"memory", "memory-dense", "label-bucket", "geometry-fallback"}


@dataclass(frozen=True)
class CarrierCandidate:
    """Phase 丁: a candidate export carrier for one entity."""
    carrier_id: str
    carrier_type: str  # "memory" | "memory-dense" | "label-bucket" | "geometry-fallback"
    entity_id: str
    label: str = ""
    coverage_score: float = 0.0
    purity_score: float = 0.0
    semantic_confidence: float = 0.0
    geometry_quality: float = 0.0
    duplicate_risk: float = 0.0
    point_count: int = 0


@dataclass(frozen=True)
class ExportCoveragePolicy:
    """Coverage gate for choosing what to feed into official semantic mIoU.

    Official ConceptGraphs Replica evaluation resamples every SLAM point from the
    exported object point clouds.  A tiny set of clean online-memory objects can
    be useful for duplicate diagnostics, but it is not a valid dense semantic map
    unless it covers a meaningful fraction of the geometry-key staging map.
    """

    min_memory_objects: int = 100
    min_memory_key_ratio: float = 0.10
    min_memory_point_ratio: float = 0.05


def _ratio(numerator: int | float, denominator: int | float) -> float:
    denominator = float(denominator)
    if denominator <= 0:
        return 0.0
    return round(float(numerator) / denominator, 6)


def choose_export_source(
    *,
    strategy: str,
    memory_object_count: int,
    key_object_count: int,
    memory_point_count: int,
    key_point_budget: int,
    policy: ExportCoveragePolicy | None = None,
) -> dict[str, object]:
    """Choose memory vs geometry export with explicit coverage diagnostics."""

    policy = policy or ExportCoveragePolicy()
    strategy = str(strategy or "auto").lower().replace("_", "-")
    if strategy not in VALID_EXPORT_SOURCE_STRATEGIES:
        raise ValueError(f"unsupported export source strategy: {strategy}")

    memory_key_ratio = _ratio(memory_object_count, key_object_count)
    memory_point_ratio = _ratio(memory_point_count, key_point_budget)
    diagnostics: dict[str, object] = {
        "requested_source": strategy,
        "memory_object_count": int(memory_object_count),
        "key_object_count": int(key_object_count),
        "memory_point_count": int(memory_point_count),
        "key_point_budget": int(key_point_budget),
        "memory_key_ratio": memory_key_ratio,
        "memory_point_ratio": memory_point_ratio,
        "min_memory_objects": int(policy.min_memory_objects),
        "min_memory_key_ratio": float(policy.min_memory_key_ratio),
        "min_memory_point_ratio": float(policy.min_memory_point_ratio),
    }

    if strategy == "geometry":
        diagnostics.update({"selected_source": GEOMETRY_EXPORT_SOURCE, "fallback_reason": "forced_geometry"})
        return diagnostics
    if strategy == "memory":
        diagnostics.update({"selected_source": MEMORY_EXPORT_SOURCE, "fallback_reason": "forced_memory"})
        return diagnostics
    if strategy == "memory-dense":
        diagnostics.update({"selected_source": MEMORY_DENSE_EXPORT_SOURCE, "fallback_reason": "forced_memory_dense"})
        return diagnostics

    if memory_object_count <= 0:
        reason = "memory_empty"
    elif memory_object_count < policy.min_memory_objects:
        reason = "memory_object_count_below_coverage_floor"
    elif memory_key_ratio < policy.min_memory_key_ratio:
        reason = "memory_key_ratio_below_coverage_floor"
    elif memory_point_ratio < policy.min_memory_point_ratio:
        reason = "memory_point_ratio_below_coverage_floor"
    else:
        diagnostics.update({"selected_source": MEMORY_EXPORT_SOURCE, "fallback_reason": "memory_coverage_pass"})
        return diagnostics

    diagnostics.update({"selected_source": GEOMETRY_EXPORT_SOURCE, "fallback_reason": reason})
    return diagnostics


# ---- Phase 丁: carrier selection v2 ----


def score_carrier(
    candidate: CarrierCandidate,
    *,
    w_cov: float = 0.30,
    w_purity: float = 0.25,
    w_sem: float = 0.20,
    w_geo: float = 0.15,
    w_dup: float = 0.10,
) -> float:
    """Score a carrier candidate across five dimensions.

    Higher is better.  All weights should sum to 1.0.
    """
    return round(
        w_cov * candidate.coverage_score
        + w_purity * candidate.purity_score
        + w_sem * candidate.semantic_confidence
        + w_geo * candidate.geometry_quality
        - w_dup * candidate.duplicate_risk,
        4,
    )


def build_carrier_candidates(
    *,
    entity_id: str,
    label: str = "",
    point_count: int = 0,
    semantic_confidence: float = 0.0,
    has_memory_node: bool = False,
    has_dense_geometry: bool = False,
    duplicate_risk: float = 0.0,
) -> list[CarrierCandidate]:
    """Build all valid carrier candidates for one entity.

    Returns at most one candidate per carrier type.
    """
    candidates: list[CarrierCandidate] = []

    # Memory carrier
    if has_memory_node:
        candidates.append(CarrierCandidate(
            carrier_id=f"{entity_id}:memory",
            carrier_type="memory",
            entity_id=entity_id,
            label=label,
            coverage_score=0.6,
            purity_score=0.9,
            semantic_confidence=semantic_confidence,
            geometry_quality=0.6,
            duplicate_risk=duplicate_risk,
            point_count=point_count,
        ))

    # Memory-dense carrier
    if has_memory_node and has_dense_geometry:
        candidates.append(CarrierCandidate(
            carrier_id=f"{entity_id}:memory-dense",
            carrier_type="memory-dense",
            entity_id=entity_id,
            label=label,
            coverage_score=0.85,
            purity_score=0.75,
            semantic_confidence=semantic_confidence,
            geometry_quality=0.85,
            duplicate_risk=duplicate_risk * 0.8,
            point_count=point_count,
        ))

    # Label-bucket split carrier
    if label:
        candidates.append(CarrierCandidate(
            carrier_id=f"{entity_id}:label-{label}",
            carrier_type="label-bucket",
            entity_id=entity_id,
            label=label,
            coverage_score=0.5,
            purity_score=0.95,
            semantic_confidence=0.95,
            geometry_quality=0.5,
            duplicate_risk=0.05,
            point_count=point_count,
        ))

    # Geometry-fallback carrier (always available)
    candidates.append(CarrierCandidate(
        carrier_id=f"{entity_id}:geometry",
        carrier_type="geometry-fallback",
        entity_id=entity_id,
        label=label,
        coverage_score=1.0,
        purity_score=0.3,
        semantic_confidence=0.1,
        geometry_quality=1.0,
        duplicate_risk=0.0,
        point_count=point_count,
    ))

    return candidates


def select_primary_carrier(
    candidates: list[CarrierCandidate],
    *,
    w_cov: float = 0.30,
    w_purity: float = 0.25,
    w_sem: float = 0.20,
    w_geo: float = 0.15,
    w_dup: float = 0.10,
) -> CarrierCandidate | None:
    """Select the best carrier from a list of candidates."""
    if not candidates:
        return None
    scored = [
        (score_carrier(c, w_cov=w_cov, w_purity=w_purity, w_sem=w_sem, w_geo=w_geo, w_dup=w_dup), c)
        for c in candidates
    ]
    scored.sort(key=lambda x: (x[0], x[1].carrier_id), reverse=True)
    return scored[0][1] if scored else None


def estimate_oracle_gap(
    chosen: CarrierCandidate,
    candidates: list[CarrierCandidate],
    *,
    w_cov: float = 0.30,
    w_purity: float = 0.25,
    w_sem: float = 0.20,
    w_geo: float = 0.15,
    w_dup: float = 0.10,
) -> float:
    """Compute the quality gap between the chosen carrier and the oracle (best possible)."""
    if not candidates:
        return 0.0
    chosen_score = score_carrier(chosen, w_cov=w_cov, w_purity=w_purity, w_sem=w_sem, w_geo=w_geo, w_dup=w_dup)
    oracle_score = max(
        score_carrier(c, w_cov=w_cov, w_purity=w_purity, w_sem=w_sem, w_geo=w_geo, w_dup=w_dup)
        for c in candidates
    )
    return round(max(oracle_score - chosen_score, 0.0), 4)
