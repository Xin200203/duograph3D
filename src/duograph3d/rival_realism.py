from __future__ import annotations

import json
from pathlib import Path
from statistics import mean


def _load_json(path: Path) -> dict[str, object] | list[object]:
    return json.loads(path.read_text())


def summarize_rival_realism(suite_dirs: list[str | Path]) -> dict[str, object]:
    unique_reports: dict[tuple[str, str], tuple[Path, dict[str, object]]] = {}
    for suite_dir in suite_dirs:
        suite_path = Path(suite_dir)
        for report_path in sorted(suite_path.glob('bounded_slice_*.json')):
            report = _load_json(report_path)
            key = (str(report['dataset']), str(report['scene']))
            unique_reports.setdefault(key, (suite_path, report))

    dense_keepalive_counts = []
    dense_retire_counts = []
    dense_update_counts = []
    dense_gap_values = []
    dense_nonzero_keepalive = 0
    strongest_scene = None
    strongest_value = -1.0
    representative_event_excerpt: list[dict[str, object]] = []

    for (_dataset, _scene), (suite_path, report) in unique_reports.items():
        dense_gap = report['rows']['dense_authority_gap_proxy']['value'] if 'rows' in report else None
        # report may be bounded slice or g2 summary; bounded slice contains branches/event files
        if 'branches' not in report:
            continue
        dense_gap_values.append(float(report['rows']['dense_authority_gap_proxy']['value']) if 'rows' in report else 0.0)
        dense_events_path = Path(report['branch_event_files']['dense_authority_export_rival'])
        if not dense_events_path.is_absolute():
            dense_events_path = suite_path / dense_events_path.name
        events = list(_load_json(dense_events_path))
        keepalive = sum(1 for event in events if event.get('event_type') == 'dense_keepalive')
        retire = sum(1 for event in events if event.get('event_type') == 'dense_retire')
        update = sum(1 for event in events if event.get('event_type') == 'dense_authority_update')
        dense_keepalive_counts.append(keepalive)
        dense_retire_counts.append(retire)
        dense_update_counts.append(update)
        if keepalive > 0:
            dense_nonzero_keepalive += 1
        if keepalive > strongest_value:
            strongest_value = keepalive
            strongest_scene = {'dataset': report['dataset'], 'scene': report['scene'], 'keepalive_events': keepalive, 'retire_events': retire, 'dense_gap_value': dense_gap}
            representative_event_excerpt = [event for event in events if event.get('event_type') in {'dense_keepalive', 'dense_retire', 'dense_authority_update'}][:8]

    scene_count = len(dense_keepalive_counts)
    return {
        'scene_count': scene_count,
        'avg_dense_keepalive_events': mean(dense_keepalive_counts) if dense_keepalive_counts else 0.0,
        'avg_dense_retire_events': mean(dense_retire_counts) if dense_retire_counts else 0.0,
        'avg_dense_update_events': mean(dense_update_counts) if dense_update_counts else 0.0,
        'avg_dense_gap_value': mean(dense_gap_values) if dense_gap_values else 0.0,
        'dense_nonzero_keepalive_scenes': dense_nonzero_keepalive,
        'strongest_dense_keepalive_scene': strongest_scene,
        'representative_event_excerpt': representative_event_excerpt,
    }


def render_rival_realism_markdown(summary: dict[str, object]) -> str:
    lines = [
        '# Rival Realism Summary — DuoGraph3D v1',
        '',
        f"- Scene coverage: {summary['scene_count']}",
        f"- Avg dense keepalive events: {summary['avg_dense_keepalive_events']:.2f}",
        f"- Avg dense retire events: {summary['avg_dense_retire_events']:.2f}",
        f"- Avg dense authority update events: {summary['avg_dense_update_events']:.2f}",
        f"- Avg dense-authority gap value: {summary['avg_dense_gap_value']:.2f}",
        f"- Scenes with nonzero dense keepalive: {summary['dense_nonzero_keepalive_scenes']}/{summary['scene_count']}",
        '',
        '## Strongest dense-keepalive scene',
        '',
    ]
    scene = summary.get('strongest_dense_keepalive_scene')
    if scene:
        lines.extend([
            f"- Scene: `{scene['dataset']}/{scene['scene']}`",
            f"- Keepalive events: {scene['keepalive_events']}",
            f"- Retire events: {scene['retire_events']}",
            f"- Dense gap value: {scene['dense_gap_value']}",
            '',
            '## Representative dense-rival event excerpt',
            '',
        ])
        for event in summary.get('representative_event_excerpt', []):
            lines.append(f"- `{event['event_type']}` step={event['step_id']} payload={event['payload']}")
    else:
        lines.append('- No representative scene found')
    lines.append('')
    return '\n'.join(lines)
