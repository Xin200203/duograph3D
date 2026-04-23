from __future__ import annotations

import json
from pathlib import Path
from statistics import mean


def _load_report(path: Path) -> dict[str, object]:
    return json.loads(path.read_text())


def summarize_metadata_grounding(suite_dirs: list[str | Path]) -> dict[str, object]:
    unique_scenes: dict[tuple[str, str], dict[str, object]] = {}
    for suite_dir in suite_dirs:
        for report_path in sorted(Path(suite_dir).glob('bounded_slice_*.json')):
            report = _load_report(report_path)
            key = (str(report['dataset']), str(report['scene']))
            unique_scenes.setdefault(key, report)

    replica_reports = [report for (dataset, _scene), report in unique_scenes.items() if dataset == 'replica']
    scannet_reports = [report for (dataset, _scene), report in unique_scenes.items() if dataset == 'scannet']

    replica_mesh_vertices = [report['scene_metadata'].get('mesh_vertex_count', 0) for report in replica_reports]
    scannet_mesh_vertices = [report['scene_metadata'].get('mesh_vertex_count', 0) for report in scannet_reports]
    scannet_label_counts = [report['scene_metadata'].get('object_label_count', 0) for report in scannet_reports]
    template_counts = [report['scene_metadata'].get('template_count', 0) for report in unique_scenes.values()]

    best_scannet = max(
        scannet_reports,
        key=lambda report: (report['scene_metadata'].get('object_label_count', 0), str(report['scene'])),
    ) if scannet_reports else None
    best_replica = max(
        replica_reports,
        key=lambda report: (report['scene_metadata'].get('mesh_vertex_count', 0), str(report['scene'])),
    ) if replica_reports else None

    return {
        'unique_scene_count': len(unique_scenes),
        'replica_scene_count': len(replica_reports),
        'scannet_scene_count': len(scannet_reports),
        'replica_mesh_coverage': sum(1 for value in replica_mesh_vertices if value > 0),
        'scannet_label_mesh_coverage': sum(1 for value in scannet_mesh_vertices if value > 0),
        'avg_replica_mesh_vertices': mean(replica_mesh_vertices) if replica_mesh_vertices else 0.0,
        'avg_scannet_mesh_vertices': mean(scannet_mesh_vertices) if scannet_mesh_vertices else 0.0,
        'avg_scannet_object_label_count': mean(scannet_label_counts) if scannet_label_counts else 0.0,
        'avg_template_count': mean(template_counts) if template_counts else 0.0,
        'max_replica_mesh_scene': {
            'scene': best_replica['scene'],
            'mesh_vertex_count': best_replica['scene_metadata'].get('mesh_vertex_count', 0),
        } if best_replica else None,
        'max_scannet_label_scene': {
            'scene': best_scannet['scene'],
            'object_label_count': best_scannet['scene_metadata'].get('object_label_count', 0),
            'top_labels': best_scannet['scene_metadata'].get('top_labels', []),
        } if best_scannet else None,
    }


def render_metadata_grounding_markdown(summary: dict[str, object]) -> str:
    return '\n'.join([
        '# Metadata Grounding Summary — DuoGraph3D v1',
        '',
        f"- Unique scenes: {summary['unique_scene_count']}",
        f"- Replica scenes: {summary['replica_scene_count']}",
        f"- ScanNet scenes: {summary['scannet_scene_count']}",
        f"- Replica mesh coverage: {summary['replica_mesh_coverage']}/{summary['replica_scene_count']}",
        f"- ScanNet label-mesh coverage: {summary['scannet_label_mesh_coverage']}/{summary['scannet_scene_count']}",
        f"- Avg replica mesh vertices: {summary['avg_replica_mesh_vertices']:.2f}",
        f"- Avg ScanNet mesh vertices: {summary['avg_scannet_mesh_vertices']:.2f}",
        f"- Avg ScanNet object-label count: {summary['avg_scannet_object_label_count']:.2f}",
        f"- Avg object-template count: {summary['avg_template_count']:.2f}",
        '',
        '## Representative metadata-rich scenes',
        '',
        f"- Replica max mesh scene: `{summary['max_replica_mesh_scene']['scene']}` with {summary['max_replica_mesh_scene']['mesh_vertex_count']} vertices" if summary['max_replica_mesh_scene'] else '- Replica max mesh scene: n/a',
        f"- ScanNet max label scene: `{summary['max_scannet_label_scene']['scene']}` with {summary['max_scannet_label_scene']['object_label_count']} labels; top labels: {summary['max_scannet_label_scene']['top_labels']}" if summary['max_scannet_label_scene'] else '- ScanNet max label scene: n/a',
        '',
    ])
