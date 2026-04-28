from __future__ import annotations

from dataclasses import dataclass


MEMORY_EXPORT_SOURCE = "duograph3d_online_object_memory"
MEMORY_DENSE_EXPORT_SOURCE = "duograph3d_online_memory_dense_geometry"
GEOMETRY_EXPORT_SOURCE = "duograph3d_geometry_key_coverage"
VALID_EXPORT_SOURCE_STRATEGIES = {"auto", "geometry", "memory", "memory-dense", "memory_dense"}


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
