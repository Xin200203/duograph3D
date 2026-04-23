from __future__ import annotations


def render_paper_outline(mega: dict[str, object], readiness: dict[str, object]) -> str:
    scene_count = mega['scene_count']
    regime_count = readiness['regime_count']
    return "\n".join([
        "# Paper Outline — DuoGraph3D v1",
        "",
        "Date: 2026-04-22",
        "",
        "1. Introduction — motivate the missing unified online object-memory structure and summarize the 5 core signals.",
        "2. Related Work — organize by structural rivals (single-layer, dense-authority export, temporal-only, stitching baselines).",
        "3. Problem Formulation and Claim Boundary — define the scoped necessity claim and non-goals.",
        "4. Method — two-layer evidence repair + current-to-memory association + object-memory authority.",
        "5. Experimental Protocol — fairness contract, dataset splits, and regime definitions.",
        f"6. Main Results — summarize {scene_count} scene-level evidence points across {regime_count} regimes.",
        "7. Ablations — temporal family, burst/random stress, holdout splits, and counterfactual strength.",
        "8. Representative Cases — use casebook excerpts to explain identity fragmentation vs memory-authority behavior.",
        "9. Limitations and Deferred Extensions — distinguish prototype-backed evidence from paper-grade next steps.",
        "",
    ])


def render_intro_claim_stack(mega: dict[str, object], readiness: dict[str, object]) -> str:
    return "\n".join([
        "# Intro Claim Stack — DuoGraph3D v1",
        "",
        "Date: 2026-04-22",
        "",
        "## Claim order",
        "1. Existing work covers ingredients, but not a unified online object-memory framework with explicit state authority.",
        "2. DuoGraph3D separates current evidence repair from current-to-memory association under one shared temporal/geometric evidence contract.",
        "3. Object graph memory is the sole long-term decision state; dense support remains auxiliary.",
        f"4. Across {mega['scene_count']} scene-level evidence points and {readiness['regime_count']} regimes, fair rivals fail to match the same behavior.",
        "5. Therefore the current prototype-backed evidence supports the necessity claim inside the scoped v1 boundary.",
        "",
    ])


def render_camera_ready_risk_list(readiness: dict[str, object]) -> str:
    return "\n".join([
        "# Camera-ready Risk List — DuoGraph3D v1",
        "",
        "Date: 2026-04-22",
        "",
        "- writing drifts into blocked “first-ever” novelty language",
        "- reviewer copy overclaims the evidence as paper-grade when readiness still says prototype-backed",
        "- figures emphasize complexity instead of the single necessity story",
        "- temporal family is compressed into an on/off story instead of the full regime family",
        "- dense-authority rival is described too weakly relative to the current stronger proxy implementation",
        "- representative cases are omitted, weakening the narrative bridge from table evidence to reviewer intuition",
        f"- readiness still lists remaining gaps: {', '.join(readiness['remaining_gap'])}",
        "",
    ])


def render_extension_backlog(mega: dict[str, object]) -> str:
    return "\n".join([
        "# Post-v1 Extension Backlog — DuoGraph3D",
        "",
        "Date: 2026-04-22",
        "",
        "## Deferred beyond current prototype-backed package",
        "- replace proxy object evidence with stronger object-level evidence derived from real observations",
        "- strengthen dense-authority and stitching rivals into more realistic implementations",
        "- add richer geometry-aware metrics beyond current proxy signals",
        "- test on broader benchmark families beyond the current 20-scene suite blocks",
        f"- convert the current {mega['scene_count']}-point evidence base into a paper-grade final experiment section",
        "- expand from conference-style evidence package to journal-grade analysis depth if needed",
        "",
    ])


def render_submission_readiness(readiness: dict[str, object], mega: dict[str, object]) -> str:
    return "\n".join([
        "# Submission Readiness Summary — DuoGraph3D v1",
        "",
        "Date: 2026-04-22",
        "",
        f"- Scene coverage: {mega['scene_count']}",
        f"- Regime coverage: {readiness['regime_count']}",
        f"- All scenes pass: {'Yes' if readiness['all_scenes_pass'] else 'No'}",
        f"- All regimes pass: {'Yes' if readiness['all_regimes_pass'] else 'No'}",
        f"- All core rows pass: {'Yes' if readiness['all_core_rows_pass'] else 'No'}",
        f"- Prototype-backed: {'Yes' if readiness['prototype_backed'] else 'No'}",
        f"- Paper-grade: {'Yes' if readiness['paper_grade'] else 'No'}",
        "",
        "## Interpretation",
        "The current package is strong enough to support internal review, planning handoff, and structured paper drafting, but it still self-identifies as prototype-backed rather than final paper-grade evidence.",
        "",
    ])
