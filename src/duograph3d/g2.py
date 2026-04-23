from __future__ import annotations

from dataclasses import dataclass


@dataclass
class FailureSignature:
    name: str
    triggered: bool
    detail: str


def detect_failure_signatures(report: dict[str, object]) -> list[FailureSignature]:
    branches = report["branches"]
    triplet = report["temporal_triplet"]
    full = branches["duograph3d_full"]
    single = branches["single_layer_rival"]
    dense = branches["dense_authority_export_rival"]
    counter = branches["full_fair_counterfactual"]
    none_branch = triplet["temporal_none"]
    naive_branch = triplet["temporal_naive_framewise"]
    deva_branch = triplet["temporal_deva_style"]

    signatures = [
        FailureSignature(
            name="single_layer_fragmentation",
            triggered=single["memory_node_count"] > full["memory_node_count"],
            detail=f"single_layer fragmentation={single.get('track_fragmentation', 0)} vs duo={full.get('track_fragmentation', 0)}",
        ),
        FailureSignature(
            name="dense_authority_fragmentation",
            triggered=(dense["memory_node_count"] > full["memory_node_count"]) or (full.get("memory_authority_events", 0) > dense.get("memory_authority_events", 0)),
            detail=f"dense_export memory nodes={dense['memory_node_count']} vs duo={full['memory_node_count']}; authority dense={dense.get('memory_authority_events', 0)} duo={full['memory_authority_events']}",
        ),
        FailureSignature(
            name="counterfactual_fragmentation",
            triggered=counter["memory_node_count"] > full["memory_node_count"],
            detail=f"counterfactual fragmentation={counter.get('track_fragmentation', 0)} vs duo={full.get('track_fragmentation', 0)}",
        ),
        FailureSignature(
            name="temporal_reentry_gap",
            triggered=(
                deva_branch["reentries"] < none_branch["reentries"]
                or deva_branch["reentries"] < naive_branch["reentries"]
                or deva_branch.get("track_fragmentation", 0) < none_branch.get("track_fragmentation", 0)
                or deva_branch.get("track_fragmentation", 0) < naive_branch.get("track_fragmentation", 0)
            ),
            detail=(
                f"reentries none={none_branch['reentries']} naive={naive_branch['reentries']} deva={deva_branch['reentries']}; "
                f"fragmentation none={none_branch.get('track_fragmentation', 0)} naive={naive_branch.get('track_fragmentation', 0)} deva={deva_branch.get('track_fragmentation', 0)}"
            ),
        ),
        FailureSignature(
            name="memory_authority_active",
            triggered=full.get("memory_authority_events", 0) > 0,
            detail=f"memory_authority_events={full['memory_authority_events']}",
        ),
    ]
    return signatures


def build_g2_summary(report: dict[str, object]) -> dict[str, object]:
    branches = report["branches"]
    triplet = report["temporal_triplet"]
    signatures = detect_failure_signatures(report)
    full = branches["duograph3d_full"]
    single = branches["single_layer_rival"]
    dense = branches["dense_authority_export_rival"]
    counter = branches["full_fair_counterfactual"]
    none_branch = triplet["temporal_none"]
    naive_branch = triplet["temporal_naive_framewise"]
    deva_branch = triplet["temporal_deva_style"]

    rows = {
        "identity_churn_proxy": {
            "observable": "track fragmentation proxy",
            "unit": "fragmented track assignments",
            "comparison_target": "duograph3d_full vs single_layer_rival",
            "value": single.get("track_fragmentation", 0) - full.get("track_fragmentation", 0),
            "pass": single.get("track_fragmentation", 0) > full.get("track_fragmentation", 0),
            "detail": f"single={single.get('track_fragmentation', 0)} duo={full.get('track_fragmentation', 0)}",
        },
        "reentry_recovery_proxy": {
            "observable": "reentry or fragmentation recovery gap",
            "unit": "reentries / fragmented track assignments",
            "comparison_target": "temporal_none/naive vs temporal_deva_style",
            "value": max(
                max(none_branch["reentries"], naive_branch["reentries"]) - deva_branch["reentries"],
                max(none_branch.get("track_fragmentation", 0), naive_branch.get("track_fragmentation", 0)) - deva_branch.get("track_fragmentation", 0),
            ),
            "pass": (
                deva_branch["reentries"] < none_branch["reentries"]
                or deva_branch["reentries"] < naive_branch["reentries"]
                or deva_branch.get("track_fragmentation", 0) < none_branch.get("track_fragmentation", 0)
                or deva_branch.get("track_fragmentation", 0) < naive_branch.get("track_fragmentation", 0)
            ),
            "detail": (
                f"reentries none={none_branch['reentries']} naive={naive_branch['reentries']} deva={deva_branch['reentries']}; "
                f"fragmentation none={none_branch.get('track_fragmentation', 0)} naive={naive_branch.get('track_fragmentation', 0)} deva={deva_branch.get('track_fragmentation', 0)}"
            ),
        },
        "memory_authority_usage": {
            "observable": "memory authority events",
            "unit": "count",
            "comparison_target": "duograph3d_full",
            "value": full.get("memory_authority_events", 0),
            "pass": full.get("memory_authority_events", 0) > 0,
            "detail": f"events={full['memory_authority_events']}",
        },
        "counterfactual_divergence_proxy": {
            "observable": "counterfactual fragmentation gap",
            "unit": "fragmented track assignments",
            "comparison_target": "duograph3d_full vs full_fair_counterfactual",
            "value": counter.get("track_fragmentation", 0) - full.get("track_fragmentation", 0),
            "pass": counter.get("track_fragmentation", 0) > full.get("track_fragmentation", 0),
            "detail": f"counter={counter.get('track_fragmentation', 0)} duo={full.get('track_fragmentation', 0)}",
        },
        "dense_authority_gap_proxy": {
            "observable": "dense-authority node or authority gap",
            "unit": "memory_node_count delta / authority event delta",
            "comparison_target": "duograph3d_full vs dense_authority_export_rival",
            "value": max(dense["memory_node_count"] - full["memory_node_count"], full.get("memory_authority_events", 0) - dense.get("memory_authority_events", 0)),
            "pass": (dense["memory_node_count"] > full["memory_node_count"]) or (full.get("memory_authority_events", 0) > dense.get("memory_authority_events", 0)),
            "detail": f"dense_nodes={dense['memory_node_count']} duo_nodes={full['memory_node_count']}; dense_authority={dense.get('memory_authority_events', 0)} duo_authority={full['memory_authority_events']}",
        },
    }
    return {
        "dataset": report["dataset"],
        "scene": report["scene"],
        "frame_count": report["frame_count"],
        "frames_with_observations": report["frames_with_observations"],
        "rows": rows,
        "failure_signatures": [signature.__dict__ for signature in signatures],
        "all_rows_pass": all(row["pass"] for row in rows.values()),
    }
