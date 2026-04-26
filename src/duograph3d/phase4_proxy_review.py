from __future__ import annotations

import json
from pathlib import Path
from statistics import mean


def _load_json(path: str | Path) -> dict[str, object] | list[object]:
    return json.loads(Path(path).read_text())


def build_phase4_proxy_review(report_paths: list[str]) -> dict[str, object]:
    rows = []
    zero_memory_authority = 0
    zero_ambiguity = 0
    for report_path in report_paths:
        report = _load_json(report_path)
        if not isinstance(report, dict):
            continue
        full = report["branches"]["duograph3d_full"]
        g2_identity_proxy = 0.0
        g2_memory_authority_proxy = 0.0
        g2_counterfactual_proxy = 0.0
        g2_path = Path(report_path).with_name(Path(report_path).name.replace("bounded_slice_", "g2_summary_"))
        if g2_path.exists():
            g2 = _load_json(g2_path)
            if isinstance(g2, dict):
                g2_identity_proxy = float(g2["rows"]["identity_churn_proxy"]["value"])
                g2_memory_authority_proxy = float(g2["rows"]["memory_authority_usage"]["value"])
                g2_counterfactual_proxy = float(g2["rows"]["counterfactual_divergence_proxy"]["value"])
        ambiguity = int(full.get("hypotheses_with_ambiguity", 0))
        authority = int(full.get("memory_authority_events", 0))
        fragmentation = float(full.get("track_fragmentation", 0))
        if authority == 0:
            zero_memory_authority += 1
        if ambiguity == 0:
            zero_ambiguity += 1
        rows.append(
            {
                "dataset": report["dataset"],
                "scene": report["scene"],
                "observation_mode": report.get("scene_metadata", {}).get("observation_mode"),
                "g2_identity_proxy": g2_identity_proxy,
                "g2_memory_authority_usage": g2_memory_authority_proxy,
                "g2_counterfactual_divergence_proxy": g2_counterfactual_proxy,
                "track_fragmentation": fragmentation,
                "memory_authority_events": authority,
                "hypotheses_with_ambiguity": ambiguity,
            }
        )
    report_coverage = len(rows)
    identity_proxy_positive = sum(1 for row in rows if row["g2_identity_proxy"] > 0)
    fragmentation_positive = sum(1 for row in rows if row["track_fragmentation"] > 0)
    return {
        "report_coverage": report_coverage,
        "zero_memory_authority_reports": zero_memory_authority,
        "zero_ambiguity_reports": zero_ambiguity,
        "identity_proxy_positive_reports": identity_proxy_positive,
        "fragmentation_positive_reports": fragmentation_positive,
        "mean_track_fragmentation": round(mean(row["track_fragmentation"] for row in rows), 3) if rows else 0.0,
        "rows": rows,
        "legacy_proxy_reference_only_candidate": (
            report_coverage > 0
            and zero_memory_authority == report_coverage
            and zero_ambiguity == report_coverage
            and fragmentation_positive > 0
        ),
    }


def render_phase4_proxy_review_markdown(review: dict[str, object]) -> str:
    lines = [
        "# Phase 4 Legacy Proxy Review",
        "",
        f"- Report coverage: {review['report_coverage']}",
        f"- Zero memory-authority reports: {review['zero_memory_authority_reports']}/{review['report_coverage']}",
        f"- Zero ambiguity reports: {review['zero_ambiguity_reports']}/{review['report_coverage']}",
        f"- Identity proxy positive reports: {review['identity_proxy_positive_reports']}",
        f"- Fragmentation-positive reports: {review['fragmentation_positive_reports']}",
        f"- Mean track fragmentation: {review['mean_track_fragmentation']:.3f}",
        f"- Legacy proxies are reference-only candidate: {'Yes' if review['legacy_proxy_reference_only_candidate'] else 'No'}",
        "",
        "| Scene | Observation mode | Identity proxy | Counterfactual proxy | Memory authority | Ambiguity hypotheses | Track fragmentation |",
        "| --- | --- | ---: | ---: | ---: | ---: | ---: |",
    ]
    for row in review["rows"]:
        lines.append(
            f"| `{row['dataset']}/{row['scene']}` | `{row['observation_mode']}` | {row['g2_identity_proxy']:.3f} | "
            f"{row['g2_counterfactual_divergence_proxy']:.3f} | {row['memory_authority_events']} | {row['hypotheses_with_ambiguity']} | {row['track_fragmentation']:.3f} |"
        )
    lines.append("")
    return "\n".join(lines)
