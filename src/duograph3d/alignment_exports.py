from __future__ import annotations

import gzip
import json
import math
import pickle
import struct
import zipfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterable, Sequence

from .io_utils import write_json


@dataclass(frozen=True)
class AlignmentObject:
    object_id: str
    track_hint: str
    score: float
    class_id: int
    class_name: str
    point_indices: tuple[int, ...] = ()
    clip_ft: tuple[float, ...] = ()
    text_ft: tuple[float, ...] = ()
    has_explicit_class: bool = False
    has_explicit_features: bool = False


@dataclass(frozen=True)
class DenseObjectAssignment:
    object_id: str
    point_indices: tuple[int, ...]
    track_hint: str = ""
    score: float | None = None
    class_id: int | None = None
    class_name: str = ""
    clip_ft: tuple[float, ...] = ()
    text_ft: tuple[float, ...] = ()


@dataclass(frozen=True)
class DenseAlignmentGeometry:
    points: tuple[tuple[float, float, float], ...]
    colors: tuple[tuple[float, float, float], ...] = ()
    objects: dict[str, DenseObjectAssignment] = field(default_factory=dict)
    source: str = ""
    coordinate_frame: str = ""
    gt_aligned: bool = False


def load_report(path: str | Path) -> dict[str, object]:
    return json.loads(Path(path).read_text())


def _as_bool(value: object) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        return value.strip().lower() in {"1", "true", "yes", "y", "on"}
    return bool(value)


def _as_int(value: object) -> int | None:
    if value is None:
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _as_float(value: object) -> float | None:
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _float_tuple(values: object) -> tuple[float, ...]:
    if not isinstance(values, (list, tuple)):
        return ()
    parsed: list[float] = []
    for value in values:
        parsed_value = _as_float(value)
        if parsed_value is None:
            return ()
        parsed.append(parsed_value)
    return tuple(parsed)


def _point3(value: object) -> tuple[float, float, float] | None:
    parsed = _float_tuple(value)
    if len(parsed) < 3:
        return None
    return parsed[0], parsed[1], parsed[2]


def _color3(value: object) -> tuple[float, float, float] | None:
    parsed = _float_tuple(value)
    if len(parsed) < 3:
        return None
    color = parsed[0], parsed[1], parsed[2]
    if max(color) > 1.0:
        return tuple(max(0.0, min(channel / 255.0, 1.0)) for channel in color)  # type: ignore[return-value]
    return tuple(max(0.0, min(channel, 1.0)) for channel in color)  # type: ignore[return-value]


def _point_indices(value: object, *, point_count: int) -> tuple[int, ...]:
    if not isinstance(value, (list, tuple)):
        return ()
    indices: set[int] = set()
    for item in value:
        parsed = _as_int(item)
        if parsed is None:
            continue
        if 0 <= parsed < point_count:
            indices.add(parsed)
    return tuple(sorted(indices))


def read_ascii_ply_points(path: str | Path) -> tuple[tuple[tuple[float, float, float], ...], tuple[tuple[float, float, float], ...]]:
    """Read x/y/z and optional RGB colors from a simple ASCII PLY point cloud.

    This intentionally supports only the evaluator-facing interchange surface
    needed by the alignment layer. Binary PLY and mesh faces are out of scope
    for this dependency-free bridge; callers should pre-convert them before
    using this exporter.
    """
    path = Path(path)
    with path.open("r", encoding="ascii", errors="ignore") as handle:
        first = handle.readline().strip()
        if first != "ply":
            raise ValueError(f"not a PLY file: {path}")
        vertex_count = 0
        in_vertex = False
        vertex_properties: list[str] = []
        for raw_line in handle:
            line = raw_line.strip()
            if line == "format ascii 1.0":
                continue
            if line.startswith("format ") and line != "format ascii 1.0":
                raise ValueError(f"only ASCII PLY is supported by the alignment exporter: {path}")
            if line.startswith("element vertex "):
                vertex_count = int(line.split()[-1])
                in_vertex = True
                continue
            if line.startswith("element ") and not line.startswith("element vertex "):
                in_vertex = False
                continue
            if in_vertex and line.startswith("property "):
                vertex_properties.append(line.split()[-1])
                continue
            if line == "end_header":
                break
        required = {"x", "y", "z"}
        if not required.issubset(vertex_properties):
            raise ValueError(f"PLY file lacks x/y/z vertex properties: {path}")
        x_index = vertex_properties.index("x")
        y_index = vertex_properties.index("y")
        z_index = vertex_properties.index("z")
        color_names = [
            ("red", "green", "blue"),
            ("r", "g", "b"),
        ]
        color_indices: tuple[int, int, int] | None = None
        for red_name, green_name, blue_name in color_names:
            if {red_name, green_name, blue_name}.issubset(vertex_properties):
                color_indices = (
                    vertex_properties.index(red_name),
                    vertex_properties.index(green_name),
                    vertex_properties.index(blue_name),
                )
                break
        points: list[tuple[float, float, float]] = []
        colors: list[tuple[float, float, float]] = []
        for _ in range(vertex_count):
            values = handle.readline().split()
            if len(values) < len(vertex_properties):
                break
            points.append((float(values[x_index]), float(values[y_index]), float(values[z_index])))
            if color_indices is not None:
                raw_color = [float(values[index]) for index in color_indices]
                if max(raw_color) > 1.0:
                    colors.append(tuple(max(0.0, min(channel / 255.0, 1.0)) for channel in raw_color))  # type: ignore[arg-type]
                else:
                    colors.append(tuple(max(0.0, min(channel, 1.0)) for channel in raw_color))  # type: ignore[arg-type]
    return tuple(points), tuple(colors)


def _resolve_payload_path(value: object, *, base_dir: Path | None) -> Path | None:
    if value is None:
        return None
    path = Path(str(value))
    if not path.is_absolute() and base_dir is not None:
        path = base_dir / path
    return path


def load_dense_geometry(value: str | Path | dict[str, object], *, base_dir: str | Path | None = None) -> DenseAlignmentGeometry:
    """Load optional dense point/mask assignments for evaluator-format export.

    Supported JSON schema is intentionally permissive so that outputs from
    OnlineAnySeg-style or ConceptGraphs-style preprocessing can be bridged
    without adding a new dependency:

    ```json
    {
      "points": [[x, y, z], ...],
      "colors": [[r, g, b], ...],
      "gt_aligned": true,
      "objects": [
        {"object_id": "obj-1", "point_indices": [0, 1], "class_id": 5}
      ]
    }
    ```

    `point_cloud_path` / `point_cloud_ply` may be used instead of inline
    `points` when the referenced PLY is ASCII.
    """
    payload_base = Path(base_dir) if base_dir is not None else None
    if isinstance(value, dict):
        payload = value
        source = "embedded_alignment_geometry"
    else:
        payload_path = Path(value)
        payload_base = payload_path.parent
        payload = json.loads(payload_path.read_text())
        source = str(payload_path)
    if not isinstance(payload, dict):
        raise TypeError("dense geometry payload must be a JSON object")

    points: tuple[tuple[float, float, float], ...] = ()
    colors: tuple[tuple[float, float, float], ...] = ()
    inline_points = payload.get("points")
    if isinstance(inline_points, list):
        parsed_points = [_point3(item) for item in inline_points]
        points = tuple(point for point in parsed_points if point is not None)
    else:
        point_cloud_path = (
            _resolve_payload_path(payload.get("point_cloud_path"), base_dir=payload_base)
            or _resolve_payload_path(payload.get("point_cloud_ply"), base_dir=payload_base)
        )
        if point_cloud_path is not None:
            points, colors = read_ascii_ply_points(point_cloud_path)

    inline_colors = payload.get("colors")
    if isinstance(inline_colors, list):
        parsed_colors = [_color3(item) for item in inline_colors]
        colors = tuple(color for color in parsed_colors if color is not None)
    if len(colors) != len(points):
        colors = ()

    point_count = len(points)
    objects: dict[str, DenseObjectAssignment] = {}
    object_entries: list[object] = []
    raw_objects = payload.get("objects", [])
    if isinstance(raw_objects, list):
        object_entries.extend(raw_objects)
    raw_assignments = payload.get("object_assignments", payload.get("assignments", {}))
    if isinstance(raw_assignments, dict):
        for object_id, indices in raw_assignments.items():
            object_entries.append({"object_id": object_id, "point_indices": indices})
    for entry in object_entries:
        if not isinstance(entry, dict):
            continue
        object_id = str(entry.get("object_id") or entry.get("id") or "")
        if not object_id:
            continue
        indices = _point_indices(
            entry.get("point_indices", entry.get("mask_indices", entry.get("point_ids", ()))),
            point_count=point_count,
        )
        score = _as_float(entry.get("score", entry.get("confidence")))
        class_id = _as_int(entry.get("class_id", entry.get("category_id")))
        class_name = str(entry.get("class_name") or entry.get("category_name") or entry.get("label") or "")
        objects[object_id] = DenseObjectAssignment(
            object_id=object_id,
            point_indices=indices,
            track_hint=str(entry.get("track_hint") or entry.get("track_id") or entry.get("repair_group_id") or ""),
            score=score,
            class_id=class_id,
            class_name=class_name,
            clip_ft=_float_tuple(entry.get("clip_ft", entry.get("clip_feature", ()))),
            text_ft=_float_tuple(entry.get("text_ft", entry.get("text_feature", ()))),
        )
    return DenseAlignmentGeometry(
        points=points,
        colors=colors,
        objects=objects,
        source=str(payload.get("source") or source),
        coordinate_frame=str(payload.get("coordinate_frame") or payload.get("frame") or ""),
        gt_aligned=_as_bool(payload.get("gt_aligned") or payload.get("evaluation_geometry_ready") or payload.get("official_geometry_ready")),
    )


def _safe_scene_name(report: dict[str, object]) -> str:
    return str(report.get("scene") or report.get("sequence_id") or "unknown_scene")


def _branch_summary(report: dict[str, object], branch_id: str) -> dict[str, object]:
    branches = report.get("branches", {})
    if not isinstance(branches, dict) or branch_id not in branches:
        raise KeyError(f"missing branch `{branch_id}` in report")
    summary = branches[branch_id]
    if not isinstance(summary, dict):
        raise TypeError(f"branch `{branch_id}` summary is not a dict")
    return summary


def build_alignment_objects(
    report: dict[str, object],
    *,
    branch_id: str = "duograph3d_full",
    default_class_id: int = 1,
    default_class_name: str = "object",
    dense_geometry: DenseAlignmentGeometry | None = None,
) -> list[AlignmentObject]:
    """Build an object-level export list from a DuoGraph3D bounded-slice report.

    The bounded-slice report remains the source of object identity. Optional
    dense geometry adds evaluator-facing point assignments, semantic ids, and
    features when an upstream segmentation/mapping step has produced them.
    """
    summary = _branch_summary(report, branch_id)
    track_assignments = summary.get("track_assignments", {})
    objects: dict[str, str] = {}
    if isinstance(track_assignments, dict):
        for track_hint, object_ids in sorted(track_assignments.items()):
            if not isinstance(object_ids, list):
                continue
            for object_id in object_ids:
                object_key = str(object_id)
                if object_key:
                    objects.setdefault(object_key, str(track_hint))
    if not objects:
        count = int(summary.get("memory_node_count", 0) or 0)
        for index in range(count):
            objects[f"obj-{index + 1}"] = ""
    if dense_geometry is not None:
        for object_id, assignment in sorted(dense_geometry.objects.items()):
            if assignment.point_indices:
                objects.setdefault(object_id, assignment.track_hint)
    if not objects:
        return []
    raw_score = float(summary.get("avg_geometry_support", 0.5) or 0.5)
    score = max(0.05, min(0.99, raw_score if raw_score > 0 else 0.5))
    alignment_objects: list[AlignmentObject] = []
    for object_id, track_hint in sorted(objects.items()):
        assignment = dense_geometry.objects.get(object_id) if dense_geometry is not None else None
        object_score = max(0.0, min(1.0, assignment.score)) if assignment and assignment.score is not None else score
        class_id = assignment.class_id if assignment and assignment.class_id is not None else default_class_id
        class_name = assignment.class_name if assignment and assignment.class_name else default_class_name
        alignment_objects.append(
            AlignmentObject(
                object_id=object_id,
                track_hint=track_hint or (assignment.track_hint if assignment is not None else ""),
                score=object_score,
                class_id=class_id,
                class_name=class_name,
                point_indices=assignment.point_indices if assignment is not None else (),
                clip_ft=assignment.clip_ft if assignment is not None else (),
                text_ft=assignment.text_ft if assignment is not None else (),
                has_explicit_class=assignment.class_id is not None if assignment is not None else False,
                has_explicit_features=bool(assignment.clip_ft) if assignment is not None else False,
            )
        )
    return alignment_objects


def _cluster_points(objects: Sequence[AlignmentObject], points_per_object: int) -> tuple[list[tuple[float, float, float]], list[list[bool]]]:
    point_count = max(len(objects) * points_per_object, 0)
    points: list[tuple[float, float, float]] = []
    masks = [[False for _ in objects] for _ in range(point_count)]
    for object_index, _obj in enumerate(objects):
        base = object_index * points_per_object
        side = max(1, int(math.sqrt(points_per_object)))
        for offset in range(points_per_object):
            row = offset // side
            col = offset % side
            x = float(object_index * 2.0 + col * 0.02)
            y = float(row * 0.02)
            z = float((offset % 5) * 0.01)
            points.append((x, y, z))
            masks[base + offset][object_index] = True
    return points, masks


def _dense_masks(
    point_count: int,
    objects: Sequence[AlignmentObject],
) -> list[list[bool]]:
    masks = [[False for _ in objects] for _ in range(point_count)]
    for object_index, obj in enumerate(objects):
        for point_index in obj.point_indices:
            if 0 <= point_index < point_count:
                masks[point_index][object_index] = True
    return masks


def _export_points_and_masks(
    objects: Sequence[AlignmentObject],
    *,
    dense_geometry: DenseAlignmentGeometry | None,
    points_per_object: int,
) -> tuple[list[tuple[float, float, float]], list[list[bool]], list[tuple[float, float, float]], bool]:
    if dense_geometry is not None and dense_geometry.points and any(obj.point_indices for obj in objects):
        points = list(dense_geometry.points)
        colors = list(dense_geometry.colors) if dense_geometry.colors else []
        return points, _dense_masks(len(points), objects), colors, True
    points, masks = _cluster_points(objects, points_per_object)
    return points, masks, [], False


def write_ascii_ply(
    points: Iterable[tuple[float, float, float]],
    path: str | Path,
    *,
    colors: Sequence[tuple[float, float, float]] | None = None,
) -> Path:
    rows = list(points)
    color_rows = list(colors or ())
    include_color = len(color_rows) == len(rows) and bool(rows)
    lines = [
        "ply",
        "format ascii 1.0",
        f"element vertex {len(rows)}",
        "property float x",
        "property float y",
        "property float z",
    ]
    if include_color:
        lines.extend(["property uchar red", "property uchar green", "property uchar blue"])
    lines.append("end_header")
    if include_color:
        for (x, y, z), (red, green, blue) in zip(rows, color_rows):
            r = int(max(0.0, min(red, 1.0)) * 255)
            g = int(max(0.0, min(green, 1.0)) * 255)
            b = int(max(0.0, min(blue, 1.0)) * 255)
            lines.append(f"{x:.6f} {y:.6f} {z:.6f} {r} {g} {b}")
    else:
        lines.extend(f"{x:.6f} {y:.6f} {z:.6f}" for x, y, z in rows)
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n")
    return path


def _npy_header(dtype_descr: str, shape: tuple[int, ...]) -> bytes:
    shape_text = "(" + ", ".join(str(value) for value in shape) + ("," if len(shape) == 1 else "") + ")"
    header = f"{{'descr': '{dtype_descr}', 'fortran_order': False, 'shape': {shape_text}, }}"
    header_bytes = header.encode("latin1")
    padding = (16 - ((10 + len(header_bytes) + 1) % 16)) % 16
    header_bytes = header_bytes + b" " * padding + b"\n"
    return b"\x93NUMPY" + bytes([1, 0]) + struct.pack("<H", len(header_bytes)) + header_bytes


def _flatten_2d_bool(values: Sequence[Sequence[bool]]) -> bytes:
    return bytes(1 if item else 0 for row in values for item in row)


def _pack_i8(values: Sequence[int]) -> bytes:
    return b"".join(struct.pack("<q", int(value)) for value in values)


def _pack_f4(values: Sequence[float]) -> bytes:
    return b"".join(struct.pack("<f", float(value)) for value in values)


def write_onlineanyseg_npz(
    path: str | Path,
    *,
    pred_masks: Sequence[Sequence[bool]],
    pred_classes: Sequence[int],
    pred_score: Sequence[float],
) -> Path:
    """Write the minimal `ckpt_final.npz` keys read by OnlineAnySeg.

    The OnlineAnySeg evaluator reads `pred_masks` as shape `(num_points,
    num_instances)`, `pred_classes` as one integer per instance, and
    `pred_score` as one confidence per instance.
    """
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    point_count = len(pred_masks)
    instance_count = len(pred_classes)
    if len(pred_score) != instance_count:
        raise ValueError("pred_score length must match pred_classes length")
    if any(len(row) != instance_count for row in pred_masks):
        raise ValueError("each pred_masks row must have one value per instance")
    with zipfile.ZipFile(path, "w", compression=zipfile.ZIP_STORED) as archive:
        archive.writestr(
            "pred_masks.npy",
            _npy_header("|b1", (point_count, instance_count)) + _flatten_2d_bool(pred_masks),
        )
        archive.writestr(
            "pred_classes.npy",
            _npy_header("<i8", (instance_count,)) + _pack_i8(pred_classes),
        )
        archive.writestr(
            "pred_score.npy",
            _npy_header("<f4", (instance_count,)) + _pack_f4(pred_score),
        )
    return path


def _resolve_dense_geometry_for_report(
    report: dict[str, object],
    *,
    report_path: str | Path,
    geometry_path: str | Path | None,
) -> DenseAlignmentGeometry | None:
    if geometry_path is not None:
        return load_dense_geometry(geometry_path)
    embedded = report.get("alignment_geometry", report.get("dense_alignment_geometry"))
    if isinstance(embedded, dict):
        return load_dense_geometry(embedded, base_dir=Path(report_path).parent)
    return None


def _readiness_flags(
    objects: Sequence[AlignmentObject],
    *,
    dense_geometry: DenseAlignmentGeometry | None,
    dense_mode: bool,
) -> dict[str, object]:
    return {
        "dense_point_assignments": dense_mode,
        "all_exported_objects_have_points": bool(objects) and all(bool(obj.point_indices) for obj in objects),
        "gt_aligned_geometry_declared": bool(dense_geometry and dense_geometry.gt_aligned),
        "explicit_class_ids": bool(objects) and all(obj.has_explicit_class for obj in objects),
        "explicit_object_features": bool(objects) and all(obj.has_explicit_features for obj in objects),
    }


def _onlineanyseg_official_ready(flags: dict[str, object]) -> bool:
    return bool(
        flags["dense_point_assignments"]
        and flags["all_exported_objects_have_points"]
        and flags["gt_aligned_geometry_declared"]
        and flags["explicit_class_ids"]
    )


def _conceptgraphs_official_ready(flags: dict[str, object]) -> bool:
    return bool(
        flags["dense_point_assignments"]
        and flags["all_exported_objects_have_points"]
        and flags["gt_aligned_geometry_declared"]
        and flags["explicit_object_features"]
    )


def _status_and_reason(*, adapter: str, dense_mode: bool, official_ready: bool) -> tuple[str, str]:
    if not dense_mode:
        return (
            "format_aligned_proxy_geometry",
            "DuoGraph3D reports expose object identities but not dense point/mask assignments; exported masks are geometry placeholders for evaluator-format bring-up.",
        )
    if official_ready:
        return (
            "format_aligned_official_ready",
            f"Dense point assignments and the required {adapter} metadata were supplied; the export is evaluator-ready, subject to running the external benchmark script against the matching GT roots.",
        )
    return (
        "format_aligned_dense_geometry",
        f"Dense point assignments were supplied, but at least one official {adapter} prerequisite is still undeclared (GT-aligned coordinates, adapter semantic ids, or object features).",
    )


def _object_manifest(obj: AlignmentObject) -> dict[str, object]:
    return {
        "object_id": obj.object_id,
        "track_hint": obj.track_hint,
        "score": obj.score,
        "class_id": obj.class_id,
        "class_name": obj.class_name,
        "point_count": len(obj.point_indices),
        "has_explicit_class": obj.has_explicit_class,
        "has_explicit_features": obj.has_explicit_features,
    }


def export_onlineanyseg_alignment(
    report_path: str | Path,
    output_root: str | Path,
    *,
    branch_id: str = "duograph3d_full",
    default_class_id: int = 1,
    default_class_name: str = "object",
    points_per_object: int = 128,
    geometry_path: str | Path | None = None,
) -> dict[str, object]:
    report = load_report(report_path)
    scene = _safe_scene_name(report)
    dataset = str(report.get("dataset", "unknown"))
    dense_geometry = _resolve_dense_geometry_for_report(report, report_path=report_path, geometry_path=geometry_path)
    objects = build_alignment_objects(
        report,
        branch_id=branch_id,
        default_class_id=default_class_id,
        default_class_name=default_class_name,
        dense_geometry=dense_geometry,
    )
    scene_dir = Path(output_root) / scene
    points, masks, colors, dense_mode = _export_points_and_masks(
        objects,
        dense_geometry=dense_geometry,
        points_per_object=points_per_object,
    )
    final_ply = write_ascii_ply(points, scene_dir / "final.ply", colors=colors)
    npz_path = write_onlineanyseg_npz(
        scene_dir / "ckpt_final.npz",
        pred_masks=masks,
        pred_classes=[obj.class_id for obj in objects],
        pred_score=[obj.score for obj in objects],
    )
    readiness = _readiness_flags(objects, dense_geometry=dense_geometry, dense_mode=dense_mode)
    official_ready = _onlineanyseg_official_ready(readiness)
    status, reason = _status_and_reason(adapter="OnlineAnySeg", dense_mode=dense_mode, official_ready=official_ready)
    manifest = {
        "adapter": "onlineanyseg",
        "status": status,
        "official_evaluation_ready": official_ready,
        "reason": reason,
        "dataset": dataset,
        "scene": scene,
        "branch_id": branch_id,
        "object_count": len(objects),
        "point_count": len(points),
        "alignment_mode": "dense_geometry" if dense_mode else "proxy_geometry",
        "geometry_source": dense_geometry.source if dense_geometry is not None else "",
        "coordinate_frame": dense_geometry.coordinate_frame if dense_geometry is not None else "",
        "readiness": readiness,
        "files": {
            "final_ply": str(final_ply),
            "ckpt_final_npz": str(npz_path),
        },
        "evaluator_contract": {
            "expected_scene_dir": "<result_dir>/<scene>",
            "expected_files": ["final.ply", "ckpt_final.npz"],
            "npz_keys": ["pred_masks", "pred_classes", "pred_score"],
            "command_template": "python eval/evaluate_seqs.py --result_dir <result_dir> --seq_name <scene> --gt_dir <gt_dir> --gt_pc_pattern %s/%s_vh_clean_2.ply --gt_seg_dir <gt_seg_dir> --gt_seg_pattern %s.txt",
        },
        "objects": [_object_manifest(obj) for obj in objects],
    }
    write_json(manifest, scene_dir / "duograph3d_onlineanyseg_alignment_manifest.json")
    return manifest


def _bbox_from_points(points: Sequence[tuple[float, float, float]]) -> list[tuple[float, float, float]]:
    if not points:
        return [(0.0, 0.0, 0.0)] * 8
    xs = [p[0] for p in points]
    ys = [p[1] for p in points]
    zs = [p[2] for p in points]
    xmin, xmax = min(xs), max(xs)
    ymin, ymax = min(ys), max(ys)
    zmin, zmax = min(zs), max(zs)
    return [
        (xmin, ymin, zmin), (xmin, ymin, zmax), (xmin, ymax, zmin), (xmin, ymax, zmax),
        (xmax, ymin, zmin), (xmax, ymin, zmax), (xmax, ymax, zmin), (xmax, ymax, zmax),
    ]


def export_conceptgraphs_alignment(
    report_path: str | Path,
    output_root: str | Path,
    *,
    branch_id: str = "duograph3d_full",
    pred_exp_name: str = "duograph3d_alignment",
    default_class_id: int = 1,
    default_class_name: str = "object",
    feature_dim: int = 512,
    points_per_object: int = 128,
    geometry_path: str | Path | None = None,
) -> dict[str, object]:
    report = load_report(report_path)
    scene = _safe_scene_name(report)
    dataset = str(report.get("dataset", "unknown"))
    dense_geometry = _resolve_dense_geometry_for_report(report, report_path=report_path, geometry_path=geometry_path)
    objects = build_alignment_objects(
        report,
        branch_id=branch_id,
        default_class_id=default_class_id,
        default_class_name=default_class_name,
        dense_geometry=dense_geometry,
    )
    points, masks, colors, dense_mode = _export_points_and_masks(
        objects,
        dense_geometry=dense_geometry,
        points_per_object=points_per_object,
    )
    pcd_saves = Path(output_root) / scene / "pcd_saves"
    pcd_saves.mkdir(parents=True, exist_ok=True)
    serializable_objects: list[dict[str, object]] = []
    for object_index, obj in enumerate(objects):
        point_color_pairs = [
            (point, colors[point_index] if point_index < len(colors) else None)
            for point_index, (point, mask_row) in enumerate(zip(points, masks))
            if mask_row[object_index]
        ]
        object_points = [point for point, _color in point_color_pairs]
        fallback_color = [
            ((object_index * 53) % 255) / 255.0,
            ((object_index * 97) % 255) / 255.0,
            ((object_index * 151) % 255) / 255.0,
        ]
        object_colors = [list(color or fallback_color) for _point, color in point_color_pairs]
        feature = list(obj.clip_ft)
        if not feature:
            feature = [0.0] * feature_dim
            if feature_dim > 0:
                feature[object_index % feature_dim] = 1.0
        text_feature = list(obj.text_ft) if obj.text_ft else list(feature)
        serializable_objects.append(
            {
                "object_id": obj.object_id,
                "track_hint": obj.track_hint,
                "class_name": [obj.class_name],
                "class_id": [obj.class_id],
                "conf": [obj.score],
                "clip_ft": feature,
                "text_ft": text_feature,
                "pcd_np": object_points,
                "pcd_color_np": object_colors,
                "bbox_np": _bbox_from_points(object_points),
                "num_detections": 1,
            }
        )
    payload = {"objects": serializable_objects, "bg_objects": None}
    result_path = pcd_saves / f"full_pcd_{pred_exp_name}.pkl.gz"
    with gzip.open(result_path, "wb") as handle:
        pickle.dump(payload, handle)
    semantic_proxy = {
        "scene": scene,
        "dataset": dataset,
        "objects": [
            {
                "object_id": obj.object_id,
                "track_hint": obj.track_hint,
                "class_name": obj.class_name,
                "class_id": obj.class_id,
                "score": obj.score,
                "point_count": len(obj.point_indices) if dense_mode else sum(1 for row in masks if row[object_index]),
                "has_explicit_features": obj.has_explicit_features,
            }
            for object_index, obj in enumerate(objects)
        ],
    }
    write_json(semantic_proxy, pcd_saves / f"{pred_exp_name}_semantic_proxy.json")
    readiness = _readiness_flags(objects, dense_geometry=dense_geometry, dense_mode=dense_mode)
    official_ready = _conceptgraphs_official_ready(readiness)
    status, reason = _status_and_reason(adapter="ConceptGraphs", dense_mode=dense_mode, official_ready=official_ready)
    manifest = {
        "adapter": "conceptgraphs",
        "status": status,
        "official_evaluation_ready": official_ready,
        "reason": reason,
        "dataset": dataset,
        "scene": scene,
        "branch_id": branch_id,
        "pred_exp_name": pred_exp_name,
        "object_count": len(objects),
        "feature_dim": feature_dim,
        "alignment_mode": "dense_geometry" if dense_mode else "proxy_geometry",
        "geometry_source": dense_geometry.source if dense_geometry is not None else "",
        "coordinate_frame": dense_geometry.coordinate_frame if dense_geometry is not None else "",
        "readiness": readiness,
        "files": {
            "conceptgraphs_pkl_gz": str(result_path),
            "semantic_proxy_json": str(pcd_saves / f"{pred_exp_name}_semantic_proxy.json"),
        },
        "evaluator_contract": {
            "expected_glob": f"<replica_root>/<scene>/pcd_saves/full_pcd_{pred_exp_name}*.pkl.gz",
            "command_template": f"python scripts/eval_replica_semseg.py --replica_root <replica_root> --replica_semantic_root <replica_semantic_root> --pred_exp_name {pred_exp_name}",
            "payload_keys": ["objects", "bg_objects"],
            "object_keys": ["clip_ft", "text_ft", "pcd_np", "pcd_color_np", "bbox_np", "class_name", "class_id"],
        },
        "objects": [_object_manifest(obj) for obj in objects],
    }
    write_json(manifest, pcd_saves / "duograph3d_conceptgraphs_alignment_manifest.json")
    return manifest
