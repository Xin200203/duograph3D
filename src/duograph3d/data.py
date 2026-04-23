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

    def to_frame_inputs(self, limit: int = 3) -> list[FrameInput]:
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

    def to_frame_inputs(self, labels: list[str], limit: int = 3) -> list[FrameInput]:
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


@dataclass
class BoundedSlice:
    dataset_name: str
    scene_name: str
    frames: list[FrameInput]
    source_paths: list[str]
    issues: list[str]
    metadata: dict[str, object]


def build_replica_bounded_slice(scene_root: str | Path, limit: int = 8) -> BoundedSlice:
    sequence = ReplicaSequence.from_root(scene_root)
    return BoundedSlice(
        dataset_name="replica",
        scene_name=sequence.scene_name,
        frames=sequence.to_frame_inputs(limit=limit),
        source_paths=[str(sequence.root), str(sequence.traj_path)],
        issues=sequence.validate(),
        metadata=sequence.metadata(),
    )


def build_scannet_bounded_slice(raw_scene_root: str | Path, pose_scene_root: str | Path, limit: int = 8) -> BoundedSlice:
    raw_scene = ScanNetRawScene.from_root(raw_scene_root)
    pose_scene = ScanNetPoseCenteredScene.from_root(pose_scene_root)
    labels = raw_scene.object_labels()
    return BoundedSlice(
        dataset_name="scannet",
        scene_name=raw_scene.scene_id,
        frames=pose_scene.to_frame_inputs(labels, limit=limit),
        source_paths=[str(raw_scene.root), str(pose_scene.root)],
        issues=raw_scene.validate() + pose_scene.validate(),
        metadata=raw_scene.metadata(),
    )
