from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from .contracts import FrameInput, Observation, ObservationSupport


def _numeric_suffix(path: Path, prefix: str) -> int:
    stem = path.stem
    if stem.startswith(prefix):
        stem = stem[len(prefix) :]
    return int(stem)


def _sample_evenly(items: list[Path], limit: int) -> list[Path]:
    if limit <= 0:
        return []
    if len(items) <= limit:
        return items
    if limit == 1:
        return [items[0]]
    positions = [(idx * (len(items) - 1)) // (limit - 1) for idx in range(limit)]
    return [items[pos] for pos in positions]


def _ply_header_count(path: Path, field: str = "vertex") -> int:
    if not path.exists():
        return 0
    try:
        with path.open("rb") as handle:
            for _ in range(64):
                line = handle.readline()
                if not line:
                    break
                decoded = line.decode("ascii", "ignore").strip()
                if decoded.startswith(f"element {field} "):
                    try:
                        return int(decoded.split()[-1])
                    except ValueError:
                        return 0
                if decoded == "end_header":
                    break
    except OSError:
        return 0
    return 0


def _trajectory_translation(line: str) -> tuple[float, float, float]:
    try:
        values = [float(item) for item in line.split()]
    except ValueError:
        return 0.0, 0.0, 0.0
    if len(values) >= 12:
        return values[3], values[7], values[11]
    return 0.0, 0.0, 0.0


def _replica_template_count(mesh_vertex_count: int) -> int:
    if mesh_vertex_count >= 1_000_000:
        return 5
    if mesh_vertex_count >= 700_000:
        return 4
    return 3


def _scannet_template_count(object_label_count: int) -> int:
    if object_label_count >= 35:
        return 6
    if object_label_count >= 20:
        return 5
    return 4


def _replica_vocab(scene_name: str) -> list[str]:
    if scene_name.startswith("office"):
        return ["chair", "desk", "cabinet", "monitor"]
    return ["bed", "table", "lamp", "shelf"]


def _normalize_support_size(*sizes: int) -> float:
    total = sum(max(size, 0) for size in sizes)
    return round(total / 1_000_000.0, 3)


def _normalize_depth_scale(value: float) -> float:
    return round(1.0 + min(abs(value), 5.0) / 5.0, 3)


def _normalize_geometry_support(value: float) -> float:
    return round(min(max(value, 0.2), 1.5), 3)


def _support_from_payload(
    payload: dict[str, object],
    *,
    frame_token: str,
    default_source_kind: str,
) -> ObservationSupport:
    return ObservationSupport(
        proposal_id=str(payload.get("proposal_id") or payload.get("observation_id") or frame_token),
        frame_token=frame_token,
        pose_token=str(payload.get("pose_token") or ""),
        source_kind=str(payload.get("source_kind") or default_source_kind),
        support_size=float(payload.get("support_size") or 0.0),
        depth_scale=float(payload.get("depth_scale") or 1.0),
        appearance_key=str(payload.get("appearance_key") or payload.get("descriptor") or ""),
        continuity_key=str(payload.get("continuity_key") or payload.get("repair_group_id") or payload.get("geometry_key") or ""),
        geometry_support=float(payload.get("geometry_support") or 0.0),
    )


def _observation_from_payload(
    payload: dict[str, object],
    *,
    frame_token: str,
    default_source_kind: str,
    fallback_id: str,
) -> Observation:
    support_payload = payload.get("support")
    support = None
    if isinstance(support_payload, dict):
        support = _support_from_payload(support_payload, frame_token=frame_token, default_source_kind=default_source_kind)
    else:
        support = _support_from_payload(payload, frame_token=frame_token, default_source_kind=default_source_kind)
    return Observation(
        observation_id=str(payload.get("observation_id") or fallback_id),
        descriptor=str(payload.get("descriptor") or "object"),
        geometry_key=str(payload.get("geometry_key") or payload.get("repair_group_id") or fallback_id),
        confidence=float(payload.get("confidence") or 1.0),
        repair_group_id=str(payload.get("repair_group_id")) if payload.get("repair_group_id") is not None else None,
        support_tokens=tuple(str(token) for token in payload.get("support_tokens", ())),
        support=support,
    )


def _build_generic_observation_lookup(
    observation_json: str | Path,
    *,
    default_source_kind: str,
) -> tuple[dict[str, list[Observation]], dict[str, object], list[str]]:
    payload = json.loads(Path(observation_json).read_text())
    issues: list[str] = []
    frames = payload.get("frames", [])
    if not isinstance(frames, list):
        return {}, {"observation_mode": "invalid"}, [f"invalid observation json frame list: {observation_json}"]
    lookup: dict[str, list[Observation]] = {}
    for frame_index, frame_payload in enumerate(frames):
        if not isinstance(frame_payload, dict):
            issues.append(f"invalid frame payload at index {frame_index}: {observation_json}")
            continue
        frame_token = str(frame_payload.get("frame_id") or frame_payload.get("rgb_name") or frame_payload.get("pose_name") or f"frame-{frame_index}")
        observations_payload = frame_payload.get("observations", [])
        if not isinstance(observations_payload, list):
            issues.append(f"invalid observations list for frame `{frame_token}` in {observation_json}")
            continue
        observations = [
            _observation_from_payload(
                item,
                frame_token=frame_token,
                default_source_kind=default_source_kind,
                fallback_id=f"{frame_token}:obs-{obs_index}",
            )
            for obs_index, item in enumerate(observations_payload, start=1)
            if isinstance(item, dict)
        ]
        aliases = {
            frame_token,
            str(frame_payload.get("frame_id") or ""),
            str(frame_payload.get("rgb_name") or ""),
            str(frame_payload.get("rgb_stem") or ""),
            str(frame_payload.get("pose_name") or ""),
            str(frame_payload.get("pose_stem") or ""),
            str(frame_payload.get("frame_index") or ""),
        }
        if frame_payload.get("frame_index") is not None:
            try:
                aliases.add(f"{int(frame_payload['frame_index']):06d}")
            except (TypeError, ValueError):
                pass
        aliases = {alias for alias in aliases if alias}
        if not aliases:
            issues.append(f"frame `{frame_token}` in {observation_json} has no usable aliases")
            continue
        for alias in aliases:
            lookup[alias] = observations
    metadata = {
        "observation_mode": "real_frame_observation_json",
        "observation_source": str(observation_json),
        "observation_frame_entries": len(frames),
    }
    return lookup, metadata, issues


def _build_deva_observation_lookup(
    observation_json: str | Path,
    *,
    scene_name: str,
) -> tuple[dict[str, list[Observation]], dict[str, object], list[str]]:
    payload = json.loads(Path(observation_json).read_text())
    annotations = payload.get("annotations", [])
    if not isinstance(annotations, list):
        return {}, {"observation_mode": "invalid"}, [f"invalid DEVA annotations list: {observation_json}"]
    lookup: dict[str, list[Observation]] = {}
    issues: list[str] = []
    for frame_index, annotation in enumerate(annotations):
        if not isinstance(annotation, dict):
            issues.append(f"invalid DEVA annotation at index {frame_index}: {observation_json}")
            continue
        file_name = Path(str(annotation.get("file_name") or "")).name
        frame_token = file_name or f"{scene_name}:deva:{frame_index}"
        observations: list[Observation] = []
        for segment_index, segment in enumerate(annotation.get("segments_info", []), start=1):
            if not isinstance(segment, dict):
                continue
            track_id = segment.get("id", segment_index)
            category_id = segment.get("category_id", 0)
            area = float(segment.get("area") or 0.0)
            score = float(segment.get("score") or 0.0)
            track_key = f"{scene_name}:deva-track:{track_id}"
            descriptor = f"{scene_name}:deva-cat-{category_id}"
            observations.append(
                Observation(
                    observation_id=f"{frame_token}:{track_id}",
                    descriptor=descriptor,
                    geometry_key=track_key,
                    confidence=score if score > 0 else 0.5,
                    repair_group_id=track_key,
                    support_tokens=(frame_token, f"track:{track_id}", f"category:{category_id}"),
                    support=ObservationSupport(
                        proposal_id=f"deva:{frame_token}:{track_id}",
                        frame_token=frame_token,
                        source_kind="deva_output_json",
                        support_size=round(max(area, 1.0) / 1_000_000.0, 3),
                        depth_scale=1.0,
                        appearance_key=descriptor,
                        continuity_key=track_key,
                        geometry_support=_normalize_geometry_support(area / 200_000.0 if area > 0 else 0.2),
                    ),
                )
            )
        aliases = {frame_token, Path(frame_token).stem}
        for alias in aliases:
            if alias:
                lookup[alias] = observations
    metadata = {
        "observation_mode": "real_deva_output_json",
        "observation_source": str(observation_json),
        "observation_frame_entries": len(annotations),
    }
    return lookup, metadata, issues


def _build_scannet_online_monitor_frames(
    observation_json: str | Path,
    *,
    scene_id: str,
) -> tuple[list[FrameInput], dict[str, object], list[str]]:
    payload = json.loads(Path(observation_json).read_text())
    issues: list[str] = []
    entries = payload if isinstance(payload, list) else payload.get("scenes", [])
    if not isinstance(entries, list):
        return [], {"observation_mode": "invalid"}, [f"invalid online monitor payload: {observation_json}"]
    selected = None
    for entry in entries:
        if isinstance(entry, dict) and str(entry.get("scene_id") or "") == scene_id:
            selected = entry
            break
    if selected is None:
        return [], {"observation_mode": "real_scannet_online_monitor_json", "observation_source": str(observation_json)}, [f"missing scene `{scene_id}` in online monitor json: {observation_json}"]
    frame_entries = selected.get("frames", [])
    if not isinstance(frame_entries, list):
        return [], {"observation_mode": "real_scannet_online_monitor_json", "observation_source": str(observation_json)}, [f"invalid frame list for scene `{scene_id}` in online monitor json: {observation_json}"]
    frames: list[FrameInput] = []
    ordered_entries: list[tuple[int, dict[str, object]]] = []
    for frame_offset, frame in enumerate(frame_entries):
        if not isinstance(frame, dict):
            continue
        frame_index = int(frame.get("frame_i", frame.get("fi", frame_offset)))
        ordered_entries.append((frame_index, frame))
    for frame_index, frame in sorted(ordered_entries, key=lambda item: item[0]):
        track_ids: set[int] = set()
        for key in ("matched_track_ids", "birth_track_ids"):
            values = frame.get(key, [])
            if isinstance(values, list):
                for value in values:
                    try:
                        track_ids.add(int(value))
                    except (TypeError, ValueError):
                        continue
        observations = [
            Observation(
                observation_id=f"{scene_id}:monitor-track:{track_id}:frame:{frame_index}",
                descriptor=f"{scene_id}:track-{track_id}",
                geometry_key=f"{scene_id}:track:{track_id}",
                confidence=1.0,
                repair_group_id=f"{scene_id}:track:{track_id}",
                support_tokens=(f"monitor-frame:{frame_index}", f"track:{track_id}"),
                support=ObservationSupport(
                    proposal_id=f"{scene_id}:monitor:{track_id}:{frame_index}",
                    frame_token=f"{scene_id}:monitor:{frame_index}",
                    source_kind="scannet_online_monitor_json",
                    support_size=0.0,
                    depth_scale=1.0,
                    appearance_key=f"{scene_id}:track-{track_id}",
                    continuity_key=f"{scene_id}:track:{track_id}",
                    geometry_support=0.2,
                ),
            )
            for track_id in sorted(track_ids)
        ]
        frames.append(FrameInput(frame_id=f"scannet-{scene_id}-monitor-{frame_index:04d}", observations=observations))
    metadata = {
        "observation_mode": "real_scannet_online_monitor_json",
        "observation_source": str(observation_json),
        "observation_frame_entries": len(frame_entries),
        "observation_scene_id": scene_id,
    }
    return frames, metadata, issues


def _replica_frame_aliases(scene_name: str, pair: "ReplicaFrame") -> tuple[str, ...]:
    frame_token = f"replica-{scene_name}-{pair.frame_index:06d}"
    return (
        frame_token,
        str(pair.frame_index),
        f"{pair.frame_index:06d}",
        pair.rgb_path.name,
        pair.rgb_path.stem,
    )


def _scannet_frame_aliases(scene_id: str, pose_path: Path) -> tuple[str, ...]:
    frame_token = f"scannet-{scene_id}-{pose_path.stem}"
    return (
        frame_token,
        pose_path.name,
        pose_path.stem,
    )


def _align_observation_lookup(
    *,
    expected_alias_rows: list[tuple[str, ...]],
    frame_ids: list[str],
    lookup: dict[str, list[Observation]],
    missing_issue_prefix: str,
) -> tuple[list[FrameInput], list[str]]:
    issues: list[str] = []
    frames: list[FrameInput] = []
    for frame_id, aliases in zip(frame_ids, expected_alias_rows):
        observations: list[Observation] | None = None
        for alias in aliases:
            if alias in lookup:
                observations = list(lookup[alias])
                break
        if observations is None:
            issues.append(f"{missing_issue_prefix}: {frame_id}")
            observations = []
        frames.append(FrameInput(frame_id=frame_id, observations=observations))
    return frames, issues


@dataclass(frozen=True)
class ObjectTemplate:
    track_id: str
    main_label: str
    alt_label: str


def _build_object_templates(scene_name: str, labels: list[str], count: int = 4) -> list[ObjectTemplate]:
    base = labels[:count] if labels else [scene_name]
    while len(base) < count:
        base.append(base[-1])
    templates: list[ObjectTemplate] = []
    for idx in range(count):
        templates.append(
            ObjectTemplate(
                track_id=f"object{chr(ord('A') + idx)}",
                main_label=base[idx],
                alt_label=base[(idx + 1) % len(base)],
            )
        )
    return templates


def _visible_templates(
    templates: list[ObjectTemplate], frame_rank: int, total_frames: int, signal: int
) -> list[ObjectTemplate]:
    visible = [templates[0]]
    if len(templates) > 1 and (signal % 2 == 0 or frame_rank == total_frames - 1):
        visible.append(templates[1])
    if len(templates) > 2 and (signal % 3 != 1 or frame_rank == 0):
        visible.append(templates[2])
    if len(templates) > 3 and (signal % 5 in {0, 2} or frame_rank == total_frames - 1):
        visible.append(templates[3])
    return visible


def _make_observations(
    *,
    scene_name: str,
    frame_token: str,
    pose_token: str,
    source_kind: str,
    visible_templates: list[ObjectTemplate],
    ambiguous_primary: bool,
    support_size: float,
    depth_scale: float,
    geometry_support: float,
) -> list[Observation]:
    observations: list[Observation] = []
    for template in visible_templates:
        continuity_key = f"{scene_name}:{template.track_id}"
        observations.append(
            Observation(
                observation_id=f"{frame_token}-{template.track_id}-main",
                descriptor=f"{scene_name}:{template.main_label}",
                geometry_key=f"{scene_name}:{template.main_label}:anchor",
                confidence=0.95,
                repair_group_id=f"{scene_name}:{template.track_id}",
                support_tokens=(frame_token, f"label:{template.main_label}", "anchor"),
                support=ObservationSupport(
                    proposal_id=f"{frame_token}:{template.track_id}:main",
                    frame_token=frame_token,
                    pose_token=pose_token,
                    source_kind=source_kind,
                    support_size=support_size,
                    depth_scale=depth_scale,
                    appearance_key=template.main_label,
                    continuity_key=continuity_key,
                    geometry_support=geometry_support,
                ),
            )
        )
        if template.track_id == "objectA" and ambiguous_primary and template.alt_label != template.main_label:
            observations.append(
                Observation(
                    observation_id=f"{frame_token}-{template.track_id}-alt",
                    descriptor=f"{scene_name}:{template.alt_label}",
                    geometry_key=f"{scene_name}:{template.main_label}:anchor_alt",
                    confidence=0.55,
                    repair_group_id=f"{scene_name}:{template.track_id}",
                    support_tokens=(frame_token, f"label:{template.alt_label}", "ambiguous_alt"),
                    support=ObservationSupport(
                        proposal_id=f"{frame_token}:{template.track_id}:alt",
                        frame_token=frame_token,
                        pose_token=pose_token,
                        source_kind=source_kind,
                        support_size=max(round(support_size * 0.85, 3), 0.05),
                        depth_scale=round(depth_scale * 1.03, 3),
                        appearance_key=template.alt_label,
                        continuity_key=continuity_key,
                        geometry_support=max(round(geometry_support * 0.9, 3), 0.1),
                    ),
                )
            )
    return observations


@dataclass
class ReplicaFrame:
    rgb_path: Path
    depth_path: Path
    frame_index: int
    pose_line: str


@dataclass
class ReplicaSequence:
    scene_name: str
    root: Path
    traj_path: Path
    mesh_path: Path
    cam_params_path: Path
    rgb_frames: list[Path]
    depth_frames: list[Path]
    traj_lines: list[str]

    @classmethod
    def from_root(cls, scene_root: str | Path) -> "ReplicaSequence":
        root = Path(scene_root)
        results = root / "results"
        traj_path = root / "traj.txt"
        rgb_frames = sorted(results.glob("frame*.jpg"), key=lambda path: _numeric_suffix(path, "frame"))
        depth_frames = sorted(results.glob("depth*.png"), key=lambda path: _numeric_suffix(path, "depth"))
        traj_lines = traj_path.read_text().splitlines() if traj_path.exists() else []
        return cls(
            scene_name=root.name,
            root=root,
            traj_path=traj_path,
            mesh_path=root.parent / f"{root.name}_mesh.ply",
            cam_params_path=root.parent / "cam_params.json",
            rgb_frames=rgb_frames,
            depth_frames=depth_frames,
            traj_lines=traj_lines,
        )

    def validate(self) -> list[str]:
        issues: list[str] = []
        if not self.root.exists():
            issues.append(f"missing replica root: {self.root}")
        if not self.traj_path.exists():
            issues.append(f"missing traj.txt: {self.traj_path}")
        if not self.mesh_path.exists():
            issues.append(f"missing replica mesh: {self.mesh_path}")
        if not self.cam_params_path.exists():
            issues.append(f"missing cam_params.json: {self.cam_params_path}")
        if not self.rgb_frames:
            issues.append(f"no rgb frames in {self.root / 'results'}")
        if not self.depth_frames:
            issues.append(f"no depth frames in {self.root / 'results'}")
        if len(self.rgb_frames) != len(self.depth_frames):
            issues.append("rgb/depth frame count mismatch")
        if self.traj_lines and len(self.traj_lines) < len(self.rgb_frames):
            issues.append("traj lines shorter than rgb frames")
        return issues

    def metadata(self) -> dict[str, object]:
        mesh_vertex_count = _ply_header_count(self.mesh_path)
        return {
            "mesh_path": str(self.mesh_path),
            "mesh_vertex_count": mesh_vertex_count,
            "frame_pair_count": len(self.paired_frames()),
            "traj_line_count": len(self.traj_lines),
            "template_count": _replica_template_count(mesh_vertex_count),
        }

    def paired_frames(self) -> list[ReplicaFrame]:
        depth_by_index = {_numeric_suffix(path, "depth"): path for path in self.depth_frames}
        pose_by_index = {idx: line for idx, line in enumerate(self.traj_lines)}
        pairs: list[ReplicaFrame] = []
        for rgb in self.rgb_frames:
            idx = _numeric_suffix(rgb, "frame")
            depth = depth_by_index.get(idx)
            pose_line = pose_by_index.get(idx, self.traj_lines[min(idx, len(self.traj_lines) - 1)] if self.traj_lines else "")
            if depth is None:
                continue
            pairs.append(ReplicaFrame(rgb_path=rgb, depth_path=depth, frame_index=idx, pose_line=pose_line))
        return pairs

    def to_synthetic_frame_inputs(self, limit: int = 3) -> list[FrameInput]:
        pairs = self.paired_frames()
        selected = _sample_evenly([Path(f"{item.frame_index}") for item in pairs], limit)
        pair_map = {item.frame_index: item for item in pairs}
        template_count = _replica_template_count(self.metadata()["mesh_vertex_count"])
        templates = _build_object_templates(self.scene_name, _replica_vocab(self.scene_name), count=template_count)
        frames: list[FrameInput] = []
        for idx, token_path in enumerate(selected):
            frame_index = int(token_path.name)
            pair = pair_map[frame_index]
            tx, ty, tz = _trajectory_translation(pair.pose_line) if pair.pose_line else (0.0, 0.0, 0.0)
            rgb_size = pair.rgb_path.stat().st_size
            depth_size = pair.depth_path.stat().st_size
            frame_token = f"rgb:{pair.rgb_path.name}|depth:{pair.depth_path.name}|t:{tx:.2f},{ty:.2f},{tz:.2f}"
            pose_token = f"t:{tx:.2f},{ty:.2f},{tz:.2f}"
            signal = int(rgb_size + depth_size + abs(tx * 1000) + abs(ty * 1000) + abs(tz * 1000))
            observations = _make_observations(
                scene_name=self.scene_name,
                frame_token=frame_token,
                pose_token=pose_token,
                source_kind="replica_frame",
                visible_templates=_visible_templates(templates, idx, len(selected), signal),
                ambiguous_primary=(idx == 0 or signal % 2 == 0),
                support_size=_normalize_support_size(rgb_size, depth_size),
                depth_scale=_normalize_depth_scale(tz),
                geometry_support=_normalize_geometry_support((abs(tx) + abs(ty) + abs(tz)) / 3.0 + 0.4),
            )
            frames.append(FrameInput(frame_id=f"replica-{self.scene_name}-{frame_index:06d}", observations=observations))
        return frames

    def to_frame_inputs(self, limit: int = 3) -> list[FrameInput]:
        return self.to_synthetic_frame_inputs(limit=limit)


@dataclass
class ScanNetRawScene:
    scene_id: str
    root: Path
    mesh_path: Path
    label_mesh_path: Path
    aggregation_path: Path
    segments_path: Path
    metadata_path: Path

    @classmethod
    def from_root(cls, scene_root: str | Path) -> "ScanNetRawScene":
        root = Path(scene_root)
        scene_id = root.name
        return cls(
            scene_id=scene_id,
            root=root,
            mesh_path=root / f"{scene_id}_vh_clean_2.ply",
            label_mesh_path=root / f"{scene_id}_vh_clean_2.labels.ply",
            aggregation_path=root / f"{scene_id}.aggregation.json",
            segments_path=root / f"{scene_id}_vh_clean_2.0.010000.segs.json",
            metadata_path=root / f"{scene_id}.txt",
        )

    def validate(self) -> list[str]:
        issues: list[str] = []
        for path in [self.mesh_path, self.label_mesh_path, self.aggregation_path, self.segments_path, self.metadata_path]:
            if not path.exists():
                issues.append(f"missing scannet artifact: {path}")
        return issues

    def metadata(self) -> dict[str, object]:
        labels = self.object_labels()
        return {
            "label_mesh_vertex_count": _ply_header_count(self.label_mesh_path),
            "mesh_vertex_count": _ply_header_count(self.mesh_path),
            "object_label_count": len(labels),
            "top_labels": labels[:5],
            "template_count": _scannet_template_count(len(labels)),
        }

    def object_labels(self) -> list[str]:
        if not self.aggregation_path.exists():
            return []
        data = json.loads(self.aggregation_path.read_text())
        counts: dict[str, int] = {}
        for group in data.get("segGroups", []):
            label = group.get("label")
            if label:
                counts[label] = counts.get(label, 0) + 1
        ordered = sorted(counts.items(), key=lambda item: (-item[1], item[0]))
        return [label for label, _ in ordered] or ["object"]


@dataclass
class ScanNetPoseCenteredScene:
    scene_id: str
    root: Path
    pose_files: list[Path]

    @classmethod
    def from_root(cls, scene_root: str | Path) -> "ScanNetPoseCenteredScene":
        root = Path(scene_root)
        return cls(scene_id=root.name, root=root, pose_files=sorted(root.glob("*.npy"), key=lambda path: int(path.stem)))

    def validate(self) -> list[str]:
        if not self.root.exists():
            return [f"missing pose-centered root: {self.root}"]
        if not self.pose_files:
            return [f"no pose npy files in {self.root}"]
        return []

    def to_synthetic_frame_inputs(self, labels: list[str], limit: int = 3) -> list[FrameInput]:
        template_count = _scannet_template_count(len(labels or [self.scene_id]))
        templates = _build_object_templates(self.scene_id, labels or [self.scene_id], count=template_count)
        frames: list[FrameInput] = []
        selected = _sample_evenly(self.pose_files, limit)
        for idx, pose_path in enumerate(selected):
            frame_token = f"pose:{pose_path.name}"
            pose_token = f"pose-index:{pose_path.stem}"
            signal = int(pose_path.stat().st_size + len(labels) * 17 + idx)
            observations = _make_observations(
                scene_name=self.scene_id,
                frame_token=frame_token,
                pose_token=pose_token,
                source_kind="scannet_pose",
                visible_templates=_visible_templates(templates, idx, len(selected), signal),
                ambiguous_primary=(idx == 0 or signal % 2 == 0),
                support_size=_normalize_support_size(pose_path.stat().st_size),
                depth_scale=_normalize_depth_scale(len(labels or [self.scene_id]) / 10.0),
                geometry_support=_normalize_geometry_support(len(labels or [self.scene_id]) / 20.0),
            )
            frames.append(FrameInput(frame_id=f"scannet-{self.scene_id}-{pose_path.stem}", observations=observations))
        return frames

    def to_frame_inputs(self, labels: list[str], limit: int = 3) -> list[FrameInput]:
        return self.to_synthetic_frame_inputs(labels, limit=limit)


@dataclass
class BoundedSlice:
    dataset_name: str
    scene_name: str
    frames: list[FrameInput]
    source_paths: list[str]
    issues: list[str]
    metadata: dict[str, object]


def build_replica_bounded_slice(
    scene_root: str | Path,
    limit: int = 8,
    *,
    observation_json: str | Path | None = None,
    observation_format: str = "frame_observation_json",
    allow_synthetic_fallback: bool = True,
) -> BoundedSlice:
    sequence = ReplicaSequence.from_root(scene_root)
    issues = sequence.validate()
    metadata = sequence.metadata()
    source_paths = [str(sequence.root), str(sequence.traj_path)]
    if observation_json is not None:
        if observation_format == "deva_output":
            lookup, observation_metadata, observation_issues = _build_deva_observation_lookup(
                observation_json,
                scene_name=sequence.scene_name,
            )
        else:
            lookup, observation_metadata, observation_issues = _build_generic_observation_lookup(
                observation_json,
                default_source_kind="replica_observation_json",
            )
        pairs = sequence.paired_frames()
        selected_pairs = _sample_evenly(pairs, limit)
        alias_rows = [_replica_frame_aliases(sequence.scene_name, pair) for pair in selected_pairs]
        frame_ids = [f"replica-{sequence.scene_name}-{pair.frame_index:06d}" for pair in selected_pairs]
        frames, alignment_issues = _align_observation_lookup(
            expected_alias_rows=alias_rows,
            frame_ids=frame_ids,
            lookup=lookup,
            missing_issue_prefix=f"missing observation frame for replica `{sequence.scene_name}`",
        )
        issues = issues + observation_issues + alignment_issues
        metadata = {**metadata, **observation_metadata}
        source_paths.append(str(observation_json))
    else:
        frames = sequence.to_synthetic_frame_inputs(limit=limit)
        metadata = {**metadata, "observation_mode": "synthetic_template", "observation_source": "ReplicaSequence.to_synthetic_frame_inputs"}
        if not allow_synthetic_fallback:
            issues.append(f"missing required real observation source for replica `{sequence.scene_name}`")
    return BoundedSlice(
        dataset_name="replica",
        scene_name=sequence.scene_name,
        frames=frames,
        source_paths=source_paths,
        issues=issues,
        metadata=metadata,
    )


def build_scannet_bounded_slice(
    raw_scene_root: str | Path,
    pose_scene_root: str | Path,
    limit: int = 8,
    *,
    observation_json: str | Path | None = None,
    observation_format: str = "frame_observation_json",
    allow_synthetic_fallback: bool = True,
) -> BoundedSlice:
    raw_scene = ScanNetRawScene.from_root(raw_scene_root)
    pose_scene = ScanNetPoseCenteredScene.from_root(pose_scene_root)
    labels = raw_scene.object_labels()
    issues = raw_scene.validate() + pose_scene.validate()
    metadata = raw_scene.metadata()
    source_paths = [str(raw_scene.root), str(pose_scene.root)]
    if observation_json is not None:
        if observation_format == "scannet_online_monitor":
            monitor_frames, observation_metadata, observation_issues = _build_scannet_online_monitor_frames(
                observation_json,
                scene_id=raw_scene.scene_id,
            )
            selected = _sample_evenly([Path(str(index)) for index in range(len(monitor_frames))], limit)
            frames = [monitor_frames[int(item.name)] for item in selected]
            alignment_issues: list[str] = []
        else:
            lookup, observation_metadata, observation_issues = _build_generic_observation_lookup(
                observation_json,
                default_source_kind="scannet_observation_json",
            )
            selected_pose_files = _sample_evenly(pose_scene.pose_files, limit)
            alias_rows = [_scannet_frame_aliases(raw_scene.scene_id, pose_path) for pose_path in selected_pose_files]
            frame_ids = [f"scannet-{raw_scene.scene_id}-{pose_path.stem}" for pose_path in selected_pose_files]
            frames, alignment_issues = _align_observation_lookup(
                expected_alias_rows=alias_rows,
                frame_ids=frame_ids,
                lookup=lookup,
                missing_issue_prefix=f"missing observation frame for scannet `{raw_scene.scene_id}`",
            )
        issues = issues + observation_issues + alignment_issues
        metadata = {**metadata, **observation_metadata}
        source_paths.append(str(observation_json))
    else:
        frames = pose_scene.to_synthetic_frame_inputs(labels, limit=limit)
        metadata = {**metadata, "observation_mode": "synthetic_template", "observation_source": "ScanNetPoseCenteredScene.to_synthetic_frame_inputs"}
        if not allow_synthetic_fallback:
            issues.append(f"missing required real observation source for scannet `{raw_scene.scene_id}`")
    return BoundedSlice(
        dataset_name="scannet",
        scene_name=raw_scene.scene_id,
        frames=frames,
        source_paths=source_paths,
        issues=issues,
        metadata=metadata,
    )
