from __future__ import annotations

import argparse
import json
from pathlib import Path


SVG_HEADER = """<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" viewBox="0 0 {w} {h}">
<style>
    .title {{ font: 700 26px sans-serif; fill: #111; }}
    .subtitle {{ font: 500 18px sans-serif; fill: #222; }}
    .body {{ font: 400 16px sans-serif; fill: #222; }}
    .small {{ font: 400 14px sans-serif; fill: #333; }}
    .box {{ fill: #f7f9fc; stroke: #2c3e50; stroke-width: 2; rx: 12; ry: 12; }}
    .accent {{ fill: #eaf2ff; stroke: #356ae6; stroke-width: 2; rx: 12; ry: 12; }}
    .danger {{ fill: #fff0f0; stroke: #c0392b; stroke-width: 2; rx: 12; ry: 12; }}
    .arrow {{ stroke: #34495e; stroke-width: 3; fill: none; marker-end: url(#arrow); }}
</style>
<defs>
  <marker id="arrow" markerWidth="10" markerHeight="10" refX="9" refY="3" orient="auto" markerUnits="strokeWidth">
    <path d="M0,0 L0,6 L9,3 z" fill="#34495e"/>
  </marker>
</defs>
"""


def _wrap_text(text: str, width: int = 50) -> list[str]:
    words = text.split()
    lines: list[str] = []
    current = ""
    for word in words:
        candidate = f"{current} {word}".strip()
        if len(candidate) <= width:
            current = candidate
        else:
            if current:
                lines.append(current)
            current = word
    if current:
        lines.append(current)
    return lines


def _text_block(x: int, y: int, lines: list[str], klass: str = "body", line_height: int = 22) -> str:
    chunks = []
    for idx, line in enumerate(lines):
        chunks.append(f'<text class="{klass}" x="{x}" y="{y + idx * line_height}">{line}</text>')
    return "\n".join(chunks)


def _box(x: int, y: int, w: int, h: int, label: str, lines: list[str], klass: str = "box") -> str:
    return (
        f'<rect class="{klass}" x="{x}" y="{y}" width="{w}" height="{h}"/>'
        + f'\n<text class="subtitle" x="{x + 18}" y="{y + 30}">{label}</text>\n'
        + _text_block(x + 18, y + 60, lines, "small", 20)
    )


def render_pipeline_overview(output_path: Path) -> None:
    w, h = 1400, 720
    blocks = [
        _box(40, 140, 220, 160, "Real observations", [
            "Replica: DEVA JSON",
            "ScanNet: ESAM monitor",
            "Synthetic path isolated",
        ], "accent"),
        _box(320, 140, 220, 160, "Evidence builder", [
            "Current + propagated evidence",
            "Support signals preserved",
            "Temporal variants available",
        ]),
        _box(600, 110, 260, 220, "Layer-1 repair", [
            "Compatibility graph",
            "Continuity / appearance /",
            "geometry-profile consistency",
            "Connected-component repair",
        ], "accent"),
        _box(920, 110, 260, 220, "Layer-2 association", [
            "Temporal identity cues",
            "Geometry-profile check",
            "Dual-consistency gate",
            "Relation-aware bonus",
        ], "accent"),
        _box(1240, 110, 120, 220, "Graph memory", [
            "node state",
            "lifecycle",
            "relation edges",
            "co-visibility",
        ], "accent"),
        _box(600, 420, 300, 180, "Phase 4 package", [
            "main table candidate",
            "ablation table candidate",
            "worst/best analysis",
            "failure + representative casebooks",
        ]),
        _box(960, 420, 320, 180, "Phase 5 manuscript assets", [
            "paper draft",
            "reviewer defense",
            "figure specs / caption bank",
            "supplementary outline",
        ]),
    ]
    arrows = [
        '<path class="arrow" d="M260 220 L320 220"/>',
        '<path class="arrow" d="M540 220 L600 220"/>',
        '<path class="arrow" d="M860 220 L920 220"/>',
        '<path class="arrow" d="M1180 220 L1240 220"/>',
        '<path class="arrow" d="M860 300 L860 420"/>',
        '<path class="arrow" d="M1060 300 L1060 420"/>',
        '<path class="arrow" d="M900 510 L960 510"/>',
    ]
    svg = SVG_HEADER.format(w=w, h=h)
    svg += '<text class="title" x="40" y="60">Figure 1. DuoGraph3D overall pipeline</text>\n'
    svg += '<text class="body" x="40" y="95">Real observations flow through evidence repair, association, graph-memory updates, and manuscript-facing analysis assets.</text>\n'
    svg += "\n".join(blocks + arrows) + "\n</svg>\n"
    output_path.write_text(svg)


def render_layer1(output_path: Path) -> None:
    w, h = 1200, 700
    svg = SVG_HEADER.format(w=w, h=h)
    svg += '<text class="title" x="40" y="60">Figure 2. Layer-1 current-evidence repair</text>\n'
    svg += '<text class="body" x="40" y="95">Evidence items are linked by continuity, appearance, and geometry-profile consistency before component collapse.</text>\n'
    svg += _box(60, 150, 240, 180, "Evidence items", [
        "proposal id",
        "descriptor / geometry key",
        "support size / depth scale",
        "continuity / appearance keys",
    ], "accent")
    svg += "\n" + _box(360, 110, 320, 260, "Compatibility graph", [
        "repair-group overlap",
        "continuity match",
        "appearance match",
        "geometry-profile consistency",
        "edge reasons retained",
    ], "accent")
    svg += "\n" + _box(740, 150, 360, 180, "Connected components -> hypotheses", [
        "one component = one repaired hypothesis",
        "ambiguity flags preserved",
        "repair reasons propagated",
    ], "box")
    svg += '\n<path class="arrow" d="M300 240 L360 240"/>\n'
    svg += '<path class="arrow" d="M680 240 L740 240"/>\n'
    svg += _box(360, 430, 520, 170, "Why it matters", [
        "Makes current-evidence graph operational rather than diagrammatic.",
        "Separates local evidence repair from long-term memory association.",
    ], "box")
    svg += "</svg>\n"
    output_path.write_text(svg)


def render_layer2(output_path: Path) -> None:
    w, h = 1300, 760
    svg = SVG_HEADER.format(w=w, h=h)
    svg += '<text class="title" x="40" y="60">Figure 3. Layer-2 current-to-memory association</text>\n'
    svg += '<text class="body" x="40" y="95">Temporal identity cues and geometry-profile consistency jointly constrain identity updates, with graph-memory relation bonuses.</text>\n'
    svg += _box(60, 150, 240, 180, "Current hypotheses", [
        "descriptor",
        "track hint",
        "support signals",
        "repair reasons",
    ], "accent")
    svg += "\n" + _box(360, 110, 320, 260, "Association score", [
        "descriptor / appearance",
        "continuity key",
        "geometry-profile consistency",
        "relation bonus",
    ], "accent")
    svg += "\n" + _box(740, 110, 240, 260, "Dual-consistency gate", [
        "continuity alone is",
        "insufficient when",
        "geometry collapses",
    ], "danger")
    svg += "\n" + _box(1040, 150, 220, 180, "Memory update", [
        "birth / associate / reentry",
        "status update",
        "relation-edge update",
    ], "accent")
    svg += '\n<path class="arrow" d="M300 240 L360 240"/>\n'
    svg += '<path class="arrow" d="M680 240 L740 240"/>\n'
    svg += '<path class="arrow" d="M980 240 L1040 240"/>\n'
    svg += _box(360, 430, 520, 180, "Why it matters", [
        "Prevents temporal continuity from carrying identity alone.",
        "Lets relation edges influence later association decisions.",
    ])
    svg += "</svg>\n"
    output_path.write_text(svg)


def render_graph_memory(output_path: Path) -> None:
    w, h = 1200, 760
    svg = SVG_HEADER.format(w=w, h=h)
    svg += '<text class="title" x="40" y="60">Figure 4. Graph-memory structure</text>\n'
    svg += '<text class="body" x="40" y="95">Object graph memory stores node state, lifecycle status, and explicit relation edges updated online.</text>\n'
    svg += _box(90, 150, 260, 210, "Memory node A", [
        "descriptor fused / recent",
        "lifecycle state",
        "support history",
        "continuity / appearance",
    ], "accent")
    svg += "\n" + _box(470, 150, 260, 210, "Memory node B", [
        "descriptor fused / recent",
        "lifecycle state",
        "support history",
        "continuity / appearance",
    ], "accent")
    svg += "\n" + _box(850, 150, 260, 210, "Relation edge", [
        "co-visibility count",
        "last seen step",
        "edge strength",
        "feeds association bonus",
    ], "danger")
    svg += '\n<path class="arrow" d="M350 255 L470 255"/>\n'
    svg += '<path class="arrow" d="M730 255 L850 255"/>\n'
    svg += _box(280, 450, 640, 180, "Decision-bearing memory", [
        "Graph memory is not only a post-hoc export: relation edges are updated online",
        "and can influence future current-to-memory association decisions.",
    ])
    svg += "</svg>\n"
    output_path.write_text(svg)


def render_case_panel(output_path: Path, *, title: str, subtitle: str, bullet_lines: list[str], event_lines: list[str], danger: bool = False) -> None:
    w, h = 1200, 760
    svg = SVG_HEADER.format(w=w, h=h)
    svg += f'<text class="title" x="40" y="60">{title}</text>\n'
    svg += f'<text class="body" x="40" y="95">{subtitle}</text>\n'
    svg += _box(60, 150, 380, 250, "Scene summary", bullet_lines, "danger" if danger else "accent")
    svg += "\n" + _box(500, 150, 620, 460, "Event excerpt", event_lines, "box")
    svg += "</svg>\n"
    output_path.write_text(svg)


def main() -> None:
    parser = argparse.ArgumentParser(description="Render Phase 5 figure assets")
    parser.add_argument("--output-dir", default="docs/manuscript/figures")
    parser.add_argument("--manifest", default="docs/manuscript/phase5_figure_asset_manifest.md")
    args = parser.parse_args()

    root = Path(args.output_dir)
    root.mkdir(parents=True, exist_ok=True)

    casebook = json.loads(Path("docs/baselines/generated/phase4_broad_analysis/phase4_casebook.json").read_text())
    failure = json.loads(Path("docs/baselines/generated/phase4_broad_analysis/phase4_failure_casebook.json").read_text())

    render_pipeline_overview(root / "figure1_pipeline_overview.svg")
    render_layer1(root / "figure2_layer1_evidence_graph.svg")
    render_layer2(root / "figure3_layer2_association.svg")
    render_graph_memory(root / "figure4_graph_memory.svg")

    best_case = casebook["cases"][0]
    best_events = [
        f"{item['event_type']} @ step {item['step_id']}"
        for item in best_case["event_excerpt"][:8]
    ]
    render_case_panel(
        root / "figure5_replica_deva_case.svg",
        title="Figure 5. Representative Replica / DEVA case",
        subtitle="Best identity-stability case from the broad Phase 4 package.",
        bullet_lines=[
            f"Scene: {best_case['dataset']}/{best_case['scene']}",
            f"Metric: {best_case['metric']} = {best_case['value']}",
            f"Observation mode: {best_case['observation_mode']}",
        ],
        event_lines=best_events,
    )

    worst_case = failure["rows"][0]
    render_case_panel(
        root / "figure6_scannet_failure_case.svg",
        title="Figure 6. Worst fragmentation ScanNet case",
        subtitle="Highest-severity fragmentation case from the broad Phase 4 package.",
        bullet_lines=[
            f"Scene: {worst_case['dataset']}/{worst_case['scene']}",
            f"Severity: {worst_case['severity']}",
            f"Fragmentation: {worst_case['identity_fragmentation_count']}",
            f"Track consistency: {worst_case['track_consistency_rate']}",
            f"Observation frame rate: {worst_case['real_observation_frame_rate']}",
            f"Geometry support: {worst_case['geometry_support_mean']}",
        ],
        event_lines=[
            "High fragmentation under dense turnover",
            "Low consistency despite strong observation coverage",
            "Current stress frontier for DuoGraph3D",
        ],
        danger=True,
    )

    rep_lines = []
    for item in casebook["cases"]:
        rep_lines.append(f"{item['label']}: {item['dataset']}/{item['scene']}")
        rep_lines.append(f"{item['metric']} = {item['value']}")
    render_case_panel(
        root / "figure7_representative_casebook_panel.svg",
        title="Figure 7. Representative casebook panel",
        subtitle="Current best/worst qualitative anchors used for Phase 5 figure selection.",
        bullet_lines=rep_lines[:10],
        event_lines=[
            "best_identity_stability",
            "best_track_consistency",
            "worst_fragmentation",
            "weakest_geometry_support",
        ],
    )

    manifest = Path(args.manifest)
    manifest.parent.mkdir(parents=True, exist_ok=True)
    manifest.write_text(
        "# Phase 5 Figure Asset Manifest\n\n"
        + f"- `{root / 'figure1_pipeline_overview.svg'}`\n"
        + f"- `{root / 'figure2_layer1_evidence_graph.svg'}`\n"
        + f"- `{root / 'figure3_layer2_association.svg'}`\n"
        + f"- `{root / 'figure4_graph_memory.svg'}`\n"
        + f"- `{root / 'figure5_replica_deva_case.svg'}`\n"
        + f"- `{root / 'figure6_scannet_failure_case.svg'}`\n"
        + f"- `{root / 'figure7_representative_casebook_panel.svg'}`\n"
    )
    print(manifest)


if __name__ == "__main__":
    main()
