from __future__ import annotations

import argparse
import csv
import gzip
import json
import math
import pickle
import sys
import time
from collections import Counter, defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

import h5py
import numpy as np
from PIL import Image
import torch
import open_clip
from chamferdist.chamfer import knn_points

sys.path.insert(0, "/home/nebula/xxy/DuoGraph3D/src")
sys.path.insert(0, "/home/nebula/xxy/concept-graphs-main")

from duograph3d.contracts import FrameInput, ObjectObservationPayload, Observation, ObservationSupport, PipelineConfig, TemporalVariant
from duograph3d.events import BRANCH_DUOGRAPH3D, EventLogger
from duograph3d.evidence import EvidenceBuilder
from duograph3d.layer1 import CurrentEvidenceGraphLayer
from duograph3d.layer2 import CurrentToMemoryAssociationLayer
from duograph3d.memory import ObjectGraphMemory
from duograph3d.io_utils import write_json
from duograph3d.metrics import summarize_run
from duograph3d.contracts import SequenceRunResult
from duograph3d.supervised_diagnosis import summarize_stage_coverage
from conceptgraph.dataset.replica_constants import REPLICA_CLASSES, REPLICA_EXISTING_CLASSES, REPLICA_SCENE_IDS, REPLICA_SCENE_IDS_
from conceptgraph.utils.ious import mask_subtract_contained

ROOT = Path("/home/nebula/xxy/duograph3d_artifacts/duograph3d_conceptgraphs_gt_layer_monitor_20260426")
ENGINEERED_ROOT = Path("/home/nebula/xxy/duograph3d_artifacts/duograph3d_conceptgraphs_engineered_gt_analysis_20260426")
REPLICA_ROOT = Path("/home/nebula/xxy/dataset/Replica")
REPLICA_SEMANTIC_ROOT = Path("/home/nebula/xxy/dataset/Replica-semantic")
BASELINE_CSV = Path("/home/nebula/xxy/duograph3d_artifacts/conceptgraphs_replica_official_20260423/replica_ex6_results.csv")
BASELINE_PRED_EXP_NAME = "none_overlap_maskconf0.95_simsum1.2_dbscan.1_merge20_masksub"
DUOGRAPH_PRED_EXP_NAME = "duograph3d_gt_layer_monitor"
PROFILE = "legacy"
FX = 600.0
FY = 600.0
CX = 599.5
CY = 339.5
DEPTH_SCALE = 6553.5
VOXEL_SIZE = 0.75
GT_TARGET_VOXEL_SIZE = 1.0
MIN_MASK_PIXELS = 300
MIN_VALID_DEPTH_POINTS = 1
MAX_POINTS_PER_OBS = 48
MAX_POINTS_PER_OBJECT = 4096
KNN_CHUNK_POINTS = 120_000
LOW_CLIP_MARGIN = 0.03
MASK_CONF_THRESHOLD: float | None = None
MAX_BBOX_AREA_RATIO: float | None = None
APPLY_MASK_SUBTRACT_CONTAINED = False
CLASS_AGNOSTIC_IDENTITY = False
CLASS_AGNOSTIC_TOKEN = "item"
EXPORT_MIN_DETECTIONS = 1
PIPELINE_GATE_OVERRIDES: dict[str, float] = {}


def object_payload_from_arrays(
    *,
    label: str,
    points: np.ndarray,
    centroid: np.ndarray,
    clip_feature: np.ndarray,
    text_feature: np.ndarray | None = None,
    mask_area: int,
) -> ObjectObservationPayload:
    points_np = np.asarray(points, dtype=np.float32)
    text_feature_np = np.asarray(text_feature, dtype=np.float32).reshape(-1) if text_feature is not None else np.asarray((), dtype=np.float32)
    return ObjectObservationPayload(
        label=label,
        points_sample=tuple(tuple(float(value) for value in row[:3]) for row in points_np),
        bbox_min=tuple(float(value) for value in points_np.min(axis=0)[:3]),
        bbox_max=tuple(float(value) for value in points_np.max(axis=0)[:3]),
        centroid=tuple(float(value) for value in np.asarray(centroid, dtype=np.float32)[:3]),
        clip_feature=tuple(float(value) for value in np.asarray(clip_feature, dtype=np.float32).reshape(-1)),
        text_feature=tuple(float(value) for value in text_feature_np),
        mask_area=float(mask_area),
        detection_count=1,
    )


@dataclass
class ObservationMeta:
    evidence_id: str
    frame_id: str
    observation_id: str
    label: str
    pred_class_index: int
    geometry_key: str
    points: np.ndarray
    centroid: np.ndarray
    confidence: float
    mask_pixels: int
    clip_margin: float
    clip_ft: np.ndarray
    clip_top1_probability: float
    clip_entropy: float


@dataclass
class GTAssignment:
    valid: bool
    eval_keep: bool
    target_id: str
    gt_class_index: int
    gt_class_name: str
    purity: float
    semantic_correct: bool
    point_count: int


def normalize_np(arr: np.ndarray) -> np.ndarray:
    arr = np.asarray(arr, dtype=np.float32)
    norm = np.linalg.norm(arr, axis=-1, keepdims=True)
    norm[norm == 0] = 1.0
    return arr / norm


def sample_indices(count: int, limit: int) -> np.ndarray:
    if count <= limit:
        return np.arange(count, dtype=np.int64)
    return np.linspace(0, count - 1, num=limit, dtype=np.int64)


def quantile(values: Iterable[float], q: float) -> float:
    data = sorted(float(v) for v in values if v is not None and not math.isnan(float(v)))
    if not data:
        return 0.0
    if len(data) == 1:
        return round(data[0], 6)
    pos = (len(data) - 1) * q
    lo = int(math.floor(pos))
    hi = int(math.ceil(pos))
    if lo == hi:
        return round(data[lo], 6)
    frac = pos - lo
    return round(data[lo] * (1.0 - frac) + data[hi] * frac, 6)


def numeric_summary(values: Iterable[float]) -> dict[str, object]:
    data = [float(v) for v in values if v is not None and not math.isnan(float(v))]
    if not data:
        return {"count": 0}
    return {
        "count": len(data),
        "min": round(min(data), 6),
        "mean": round(sum(data) / len(data), 6),
        "p10": quantile(data, 0.10),
        "p50": quantile(data, 0.50),
        "p90": quantile(data, 0.90),
        "p99": quantile(data, 0.99),
        "max": round(max(data), 6),
    }


def to_builtin(value):
    if isinstance(value, dict):
        return {str(k): to_builtin(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [to_builtin(v) for v in value]
    if isinstance(value, Counter):
        return {str(k): int(v) for k, v in value.items()}
    if isinstance(value, np.ndarray):
        return value.tolist()
    if isinstance(value, (np.integer,)):
        return int(value)
    if isinstance(value, (np.floating,)):
        return float(value)
    if isinstance(value, (np.bool_,)):
        return bool(value)
    return value


def softmax(values: np.ndarray) -> np.ndarray:
    x = values.astype(np.float64)
    x = x - np.max(x)
    ex = np.exp(x)
    total = ex.sum()
    return ex / total if total > 0 else np.ones_like(ex) / max(len(ex), 1)


def entropy(probs: np.ndarray) -> float:
    probs = probs[probs > 0]
    return float(-(probs * np.log2(probs)).sum()) if probs.size else 0.0


def read_h5(path: Path, name: str) -> np.ndarray:
    with h5py.File(path, "r") as handle:
        return handle[name][:]


def load_gt_scene(scene_id_: str, class_all2existing: torch.Tensor, device: str):
    gt_pc_path = REPLICA_SEMANTIC_ROOT / scene_id_ / "Sequence_1" / "saved-maps-gt" / "pointclouds"
    gt_pose_path = REPLICA_SEMANTIC_ROOT / scene_id_ / "Sequence_1" / "traj_w_c.txt"
    points = read_h5(gt_pc_path / "pc_points.h5", "pc_points").astype(np.float32)
    embeddings = read_h5(gt_pc_path / "pc_embeddings.h5", "pc_embeddings")
    gt_full_class = torch.from_numpy(embeddings.argmax(axis=1)).long()
    gt_class = class_all2existing[gt_full_class].numpy().astype(np.int64)
    poses = np.loadtxt(gt_pose_path, dtype=np.float32).reshape(-1, 4, 4)
    points = (points @ poses[0, :3, :3].T + poses[0, :3, 3]).astype(np.float32)
    return torch.from_numpy(points).to(device), torch.from_numpy(gt_class).long().to(device)


def gt_target_id(class_name: str, centroid: np.ndarray) -> str:
    q = np.floor(centroid / GT_TARGET_VOXEL_SIZE).astype(int)
    return f"{class_name}:{q[0]}:{q[1]}:{q[2]}"


def assign_points_to_gt(
    points_list: list[np.ndarray],
    pred_class_indices: list[int],
    gt_xyz: torch.Tensor,
    gt_class: torch.Tensor,
    class_names: list[str],
    keep_indices: set[int],
    *,
    device: str,
) -> list[GTAssignment]:
    if not points_list:
        return []
    lengths = [len(points) for points in points_list]
    flat = np.concatenate(points_list, axis=0).astype(np.float32) if sum(lengths) else np.zeros((0, 3), dtype=np.float32)
    if len(flat) == 0:
        return [GTAssignment(False, False, "", -1, "", 0.0, False, 0) for _ in points_list]
    nearest_indices = []
    with torch.no_grad():
        for start in range(0, len(flat), KNN_CHUNK_POINTS):
            chunk = torch.from_numpy(flat[start:start + KNN_CHUNK_POINTS]).to(device).float()
            nn = knn_points(
                chunk.unsqueeze(0).contiguous(),
                gt_xyz.unsqueeze(0).contiguous().float(),
                lengths1=None,
                lengths2=None,
                return_nn=False,
                return_sorted=True,
                K=1,
            )
            nearest_indices.append(nn.idx.squeeze(0).squeeze(-1).detach().cpu())
    nearest = torch.cat(nearest_indices, dim=0).long()
    gt_class_cpu = gt_class.detach().cpu()
    gt_xyz_cpu = gt_xyz.detach().cpu().numpy()
    assignments: list[GTAssignment] = []
    offset = 0
    for points, pred_class, length in zip(points_list, pred_class_indices, lengths):
        idx = nearest[offset:offset + length]
        offset += length
        if length == 0:
            assignments.append(GTAssignment(False, False, "", -1, "", 0.0, False, 0))
            continue
        classes = gt_class_cpu[idx].numpy().astype(np.int64)
        counts = Counter(int(c) for c in classes if int(c) >= 0)
        if not counts:
            assignments.append(GTAssignment(False, False, "", -1, "", 0.0, False, length))
            continue
        gt_idx, majority_count = counts.most_common(1)[0]
        class_name = class_names[gt_idx]
        majority_mask = classes == gt_idx
        gt_centroid = gt_xyz_cpu[idx.numpy()[majority_mask]].mean(axis=0) if majority_mask.any() else points.mean(axis=0)
        assignments.append(
            GTAssignment(
                valid=True,
                eval_keep=gt_idx in keep_indices,
                target_id=gt_target_id(class_name, gt_centroid),
                gt_class_index=gt_idx,
                gt_class_name=class_name,
                purity=round(majority_count / max(length, 1), 6),
                semantic_correct=pred_class == gt_idx,
                point_count=length,
            )
        )
    return assignments


def clip_margin(row: np.ndarray) -> float:
    if row.size < 2:
        return 0.0
    top2 = np.partition(row, -2)[-2:]
    top2.sort()
    return float(top2[-1] - top2[-2])


def quant_key(scene: str, label: str, centroid: np.ndarray) -> str:
    q = np.floor(centroid / VOXEL_SIZE).astype(int)
    if CLASS_AGNOSTIC_IDENTITY:
        return f"{scene}:gsa:{CLASS_AGNOSTIC_TOKEN}:{q[0]}:{q[1]}:{q[2]}"
    return f"{scene}:gsa:{label}:{q[0]}:{q[1]}:{q[2]}"


def world_points_from_mask_arrays(mask: np.ndarray, depth: np.ndarray, pose: np.ndarray):
    valid = mask & (depth > 1e-6)
    ys, xs = np.nonzero(valid)
    if len(xs) < MIN_VALID_DEPTH_POINTS:
        return None, None
    keep = sample_indices(len(xs), MAX_POINTS_PER_OBS)
    xs = xs[keep]
    ys = ys[keep]
    z = depth[ys, xs]
    x = (xs.astype(np.float32) - CX) / FX * z
    y = (ys.astype(np.float32) - CY) / FY * z
    cam = np.stack([x, y, z], axis=1).astype(np.float32)
    world = (cam @ pose[:3, :3].T + pose[:3, 3]).astype(np.float32)
    return world, world.mean(axis=0)


def prepare_scene(scene: str, class_names: list[str], class_feats_np: np.ndarray, *, logit_scale: float):
    t0 = time.time()
    gsa_dir = REPLICA_ROOT / scene / "gsa_detections_none"
    poses = np.loadtxt(REPLICA_ROOT / scene / "traj.txt", dtype=np.float32).reshape(-1, 4, 4)
    frames: list[FrameInput] = []
    obs_meta: list[ObservationMeta] = []
    raw_count = 0
    too_small = 0
    zero_depth = 0
    too_few_valid_points = 0
    low_confidence = 0
    large_bbox = 0
    mask_pixels_subtracted = 0
    post_subtract_empty = 0
    post_subtract_tiny = 0
    pre_subtract_kept_mask_pixels: list[int] = []
    post_subtract_candidate_mask_pixels: list[int] = []
    for det_path in sorted(gsa_dir.glob("frame*.pkl.gz")):
        frame_stem = det_path.name.split(".")[0]
        frame_idx = int(frame_stem[len("frame"):])
        frame_id = f"replica-{scene}-{frame_idx:06d}"
        observations: list[Observation] = []
        depth = np.asarray(Image.open(REPLICA_ROOT / scene / "results" / f"depth{frame_idx:06d}.png"), dtype=np.float32) / DEPTH_SCALE
        pose = poses[frame_idx]
        with gzip.open(det_path, "rb") as handle:
            det = pickle.load(handle)
        image_feats = normalize_np(det["image_feats"].astype(np.float32))
        sims = image_feats @ class_feats_np.T
        label_idx = sims.argmax(axis=1)
        masks = np.asarray(det["mask"]).astype(bool)
        xyxy = np.asarray(det.get("xyxy", np.zeros((len(masks), 4), dtype=np.float32)))
        confidences = det.get("confidence", np.ones(len(masks), dtype=np.float32))
        raw_count += int(len(masks))
        pre_keep_indices = []
        for det_i in range(len(masks)):
            raw_area = int(masks[det_i].sum())
            if raw_area < MIN_MASK_PIXELS:
                too_small += 1
                continue
            raw_conf = float(confidences[det_i])
            if MASK_CONF_THRESHOLD is not None and raw_conf < MASK_CONF_THRESHOLD:
                low_confidence += 1
                continue
            if MAX_BBOX_AREA_RATIO is not None and len(xyxy) == len(masks):
                x1, y1, x2, y2 = [float(value) for value in xyxy[det_i]]
                bbox_area = max(x2 - x1, 0.0) * max(y2 - y1, 0.0)
                if bbox_area > MAX_BBOX_AREA_RATIO * float(depth.shape[0] * depth.shape[1]):
                    large_bbox += 1
                    continue
            pre_keep_indices.append(det_i)

        if pre_keep_indices:
            frame_masks = masks[pre_keep_indices]
            pre_subtract_kept_mask_pixels.extend(int(mask.sum()) for mask in frame_masks)
            if APPLY_MASK_SUBTRACT_CONTAINED and len(xyxy) == len(masks):
                before_pixels = int(frame_masks.sum())
                frame_masks = mask_subtract_contained(xyxy[pre_keep_indices], frame_masks).astype(bool)
                mask_pixels_subtracted += max(before_pixels - int(frame_masks.sum()), 0)
            else:
                frame_masks = frame_masks.astype(bool)
        else:
            frame_masks = np.zeros((0,) + masks.shape[1:], dtype=bool) if masks.ndim == 3 else np.zeros((0, 0, 0), dtype=bool)

        for local_i, det_i in enumerate(pre_keep_indices):
            class_i = int(label_idx[det_i])
            mask = frame_masks[local_i]
            area = int(mask.sum())
            post_subtract_candidate_mask_pixels.append(area)
            if area == 0:
                post_subtract_empty += 1
            elif area < MIN_MASK_PIXELS:
                post_subtract_tiny += 1
            world, centroid = world_points_from_mask_arrays(mask, depth, pose)
            if world is None:
                valid_pixels = int((mask & (depth > 1e-6)).sum())
                if valid_pixels == 0:
                    zero_depth += 1
                else:
                    too_few_valid_points += 1
                continue
            label = class_names[int(class_i)]
            key = quant_key(scene, label, centroid)
            raw_conf = float(confidences[det_i])
            conf = float(np.clip(raw_conf, 0.0, 1.0))
            probs = softmax(sims[det_i] * logit_scale)
            obs_id = f"{frame_stem}:gsa-{det_i:03d}"
            support_size = round(area / 1_000_000.0, 4)
            depth_scale = round(float(np.linalg.norm(centroid)), 4)
            geometry_support = round(min(max(area / 200000.0, 0.2), 1.5), 4)
            observations.append(
                Observation(
                    observation_id=obs_id,
                    descriptor=f"{scene}:{CLASS_AGNOSTIC_TOKEN if CLASS_AGNOSTIC_IDENTITY else label}",
                    geometry_key=key,
                    confidence=conf,
                    repair_group_id=key,
                    support_tokens=(frame_stem, label, key),
                    support=ObservationSupport(
                        proposal_id=obs_id,
                        frame_token=frame_stem,
                        source_kind=f"conceptgraphs_gsa_none_{PROFILE}",
                        support_size=support_size,
                        depth_scale=depth_scale,
                        appearance_key=label,
                        continuity_key=key,
                        geometry_support=geometry_support,
                    ),
                    object_payload=object_payload_from_arrays(
                        label=label,
                        points=world,
                        centroid=centroid,
                        clip_feature=image_feats[det_i],
                        # In the class-agnostic identity setting, a generic
                        # `item` text embedding would make every object
                        # semantically identical inside DuoGraph3D's gates.  Keep
                        # online matching semantics in accumulated class votes
                        # and object-level visual CLIP instead.
                        text_feature=None if CLASS_AGNOSTIC_IDENTITY else class_feats_np[int(class_i)],
                        mask_area=area,
                    ),
                )
            )
            obs_meta.append(
                ObservationMeta(
                    evidence_id=f"{frame_id}:{obs_id}",
                    frame_id=frame_id,
                    observation_id=obs_id,
                    label=label,
                    pred_class_index=int(class_i),
                    geometry_key=key,
                    points=world,
                    centroid=centroid,
                    confidence=conf,
                    mask_pixels=area,
                    clip_margin=clip_margin(sims[det_i]),
                    clip_ft=image_feats[det_i].astype(np.float32),
                    clip_top1_probability=float(probs[int(class_i)]),
                    clip_entropy=entropy(probs),
                )
            )
        frames.append(FrameInput(frame_id=frame_id, observations=observations))
    prep = {
        "scene": scene,
        "frame_count": len(frames),
        "frames_with_observations": sum(1 for f in frames if f.observations),
        "raw_detection_count": raw_count,
        "kept_observation_count": len(obs_meta),
        "too_small_mask_count": too_small,
        "low_confidence_mask_count": low_confidence,
        "large_bbox_mask_count": large_bbox,
        "too_few_valid_points_count": too_few_valid_points,
        "zero_valid_depth_count": zero_depth,
        "mask_pixels_subtracted": mask_pixels_subtracted,
        "post_subtract_empty_mask_count": post_subtract_empty,
        "post_subtract_tiny_mask_count": post_subtract_tiny,
        "pre_subtract_kept_mask_pixels": numeric_summary(pre_subtract_kept_mask_pixels),
        "post_subtract_candidate_mask_pixels": numeric_summary(post_subtract_candidate_mask_pixels),
        "parameters": {
            "profile": PROFILE,
            "voxel_size": VOXEL_SIZE,
            "min_mask_pixels": MIN_MASK_PIXELS,
            "mask_conf_threshold": MASK_CONF_THRESHOLD,
            "max_bbox_area_ratio": MAX_BBOX_AREA_RATIO,
            "min_valid_depth_points": MIN_VALID_DEPTH_POINTS,
            "max_points_per_obs": MAX_POINTS_PER_OBS,
            "class_agnostic_identity": CLASS_AGNOSTIC_IDENTITY,
            "mask_subtract_order": "conceptgraphs_filter_then_subtract",
        },
        "seconds": round(time.time() - t0, 3),
    }
    return frames, obs_meta, prep


def duplicate_stats(target_ids: list[str]) -> dict[str, object]:
    ids = [target for target in target_ids if target]
    total = len(ids)
    unique = len(set(ids))
    duplicates = max(total - unique, 0)
    counts = Counter(ids)
    return {
        "total": total,
        "unique_targets": unique,
        "duplicate_count": duplicates,
        "duplicate_rate": round(duplicates / max(total, 1), 6),
        "overseg_factor": round(total / max(unique, 1), 6),
        "targets_with_duplicates": sum(1 for c in counts.values() if c > 1),
        "max_items_per_target": max(counts.values()) if counts else 0,
    }


def class_from_target_id(target_id: str) -> str:
    if not target_id:
        return ""
    parts = target_id.rsplit(":", 3)
    return parts[0] if parts else target_id


def resolve_object_root(object_id: str, nodes: dict[str, object]) -> str:
    """Map a raw online object id to its final object-merge root."""

    current = object_id
    seen: set[str] = set()
    while current and current not in seen:
        seen.add(current)
        node = nodes.get(current)
        merge_target = str(getattr(node, "merge_target_id", "") or "") if node is not None else ""
        if not merge_target:
            break
        current = merge_target
    return current or object_id


def classify_raw_switch_cause(previous_object: str, decision, candidate_diag: dict[str, object]) -> str:
    """Classify the online cause before final object-merge canonicalization."""

    top_candidates = candidate_diag.get("top_candidates") or []
    previous_candidate = None
    if isinstance(top_candidates, list):
        for candidate in top_candidates:
            if isinstance(candidate, dict) and str(candidate.get("object_id", "")) == previous_object:
                previous_candidate = candidate
                break
    if decision.action == "birth":
        if not top_candidates:
            return "duplicate_birth_no_candidate_diagnostic"
        if previous_candidate is None:
            return "duplicate_birth_candidate_missing_previous"
        if not bool(previous_candidate.get("has_strong_identity", False)):
            return "duplicate_birth_previous_candidate_no_strong_identity"
        try:
            previous_score = float(previous_candidate.get("score", 0.0) or 0.0)
        except (TypeError, ValueError):
            previous_score = 0.0
        if previous_score < float(candidate_diag.get("threshold", 0.0) or 0.0):
            return "duplicate_birth_previous_candidate_below_threshold"
        return "duplicate_birth_other"
    if previous_candidate is None:
        return "false_association_candidate_missing_previous"
    return "false_association_wrong_object"


def confusion_records(counter: Counter[tuple[str, str]], limit: int = 12) -> list[dict[str, object]]:
    return [
        {"pred": pred, "gt": gt, "count": int(count)}
        for (pred, gt), count in counter.most_common(limit)
    ]


def per_class_accuracy_records(total: Counter[str], correct: Counter[str]) -> list[dict[str, object]]:
    rows = []
    for gt_class, count in total.most_common():
        rows.append(
            {
                "gt_class": gt_class,
                "count": int(count),
                "correct": int(correct.get(gt_class, 0)),
                "accuracy": round(correct.get(gt_class, 0) / max(count, 1), 6),
            }
        )
    return rows


def summarize_geometry_keys(obs_meta: list[ObservationMeta], obs_gt: dict[str, GTAssignment]) -> dict[str, dict[str, object]]:
    buckets: dict[str, list[ObservationMeta]] = defaultdict(list)
    for obs in obs_meta:
        buckets[obs.geometry_key].append(obs)
    summaries: dict[str, dict[str, object]] = {}
    for key, items in buckets.items():
        valid = [obs for obs in items if obs_gt[obs.evidence_id].eval_keep]
        pred_counts = Counter(obs.label for obs in items)
        gt_counts = Counter(obs_gt[obs.evidence_id].gt_class_name for obs in valid)
        target_counts = Counter(obs_gt[obs.evidence_id].target_id for obs in valid)
        dominant_pred, _ = majority(list(pred_counts.elements()))
        dominant_gt, _ = majority(list(gt_counts.elements()))
        correct = sum(1 for obs in valid if obs_gt[obs.evidence_id].semantic_correct)
        summaries[key] = {
            "observation_count": len(items),
            "eval_keep_observation_count": len(valid),
            "dominant_pred_label": dominant_pred,
            "dominant_gt_class": dominant_gt,
            "semantic_accuracy": round(correct / max(len(valid), 1), 6),
            "unique_gt_target_count": len(target_counts),
            "dominant_target_id": target_counts.most_common(1)[0][0] if target_counts else "",
            "gt_purity": numeric_summary(obs_gt[obs.evidence_id].purity for obs in valid),
            "clip_margin": numeric_summary(obs.clip_margin for obs in items),
            "pred_label_counts": dict(pred_counts.most_common(8)),
            "gt_class_counts": dict(gt_counts.most_common(8)),
            "target_counts": dict(target_counts.most_common(8)),
        }
    return summaries


def aggregate_object_monitor(scene_summaries: list[dict[str, object]], key: str) -> dict[str, object]:
    monitors = [item.get(key, {}) for item in scene_summaries if item.get(key, {}).get("available")]
    object_count = sum(int(monitor.get("object_count", 0)) for monitor in monitors)
    valid_count = sum(int(monitor.get("valid_eval_object_count", 0)) for monitor in monitors)
    duplicate_count = sum(int((monitor.get("semantic_cell_duplicates") or {}).get("duplicate_count", 0)) for monitor in monitors)
    total_duplicate_items = sum(int((monitor.get("semantic_cell_duplicates") or {}).get("total", 0)) for monitor in monitors)
    semantic_correct_weighted = sum(
        float(monitor.get("semantic_accuracy", 0.0)) * int(monitor.get("valid_eval_object_count", 0))
        for monitor in monitors
    )
    return {
        "available_scene_count": len(monitors),
        "object_count": object_count,
        "valid_eval_object_count": valid_count,
        "semantic_accuracy_weighted": round(semantic_correct_weighted / max(valid_count, 1), 6),
        "semantic_cell_duplicate_count": duplicate_count,
        "semantic_cell_duplicate_rate_micro": round(duplicate_count / max(total_duplicate_items, 1), 6),
    }


def aggregate_counter(scene_summaries: list[dict[str, object]], path: tuple[str, str]) -> dict[str, int]:
    result: Counter[str] = Counter()
    section, key = path
    for item in scene_summaries:
        values = (item.get(section, {}) or {}).get(key, {})  # type: ignore[union-attr]
        if isinstance(values, dict):
            for name, count in values.items():
                result[str(name)] += int(count)
    return dict(result)


def summarize_init(obs_meta: list[ObservationMeta], obs_gt: dict[str, GTAssignment]) -> dict[str, object]:
    valid = [obs for obs in obs_meta if obs_gt[obs.evidence_id].eval_keep]
    semantic_correct = [obs_gt[obs.evidence_id].semantic_correct for obs in valid]
    frame_targets: dict[str, list[str]] = defaultdict(list)
    for obs in valid:
        frame_targets[obs.frame_id].append(obs_gt[obs.evidence_id].target_id)
    frame_dup_rates = [duplicate_stats(targets)["duplicate_rate"] for targets in frame_targets.values()]
    frame_overseg = [duplicate_stats(targets)["overseg_factor"] for targets in frame_targets.values()]
    all_dup = duplicate_stats([obs_gt[obs.evidence_id].target_id for obs in valid])
    gt_class_counts = Counter(obs_gt[obs.evidence_id].gt_class_name for obs in valid)
    gt_class_correct = Counter(obs_gt[obs.evidence_id].gt_class_name for obs in valid if obs_gt[obs.evidence_id].semantic_correct)
    pred_label_counts = Counter(obs.label for obs in valid)
    semantic_confusions = Counter(
        (obs.label, obs_gt[obs.evidence_id].gt_class_name)
        for obs in valid
        if not obs_gt[obs.evidence_id].semantic_correct
    )
    return {
        "valid_eval_observations": len(valid),
        "unique_gt_target_count": all_dup["unique_targets"],
        "semantic_accuracy": round(sum(semantic_correct) / max(len(semantic_correct), 1), 6),
        "top_semantic_confusions": confusion_records(semantic_confusions),
        "per_class_semantic_accuracy": per_class_accuracy_records(gt_class_counts, gt_class_correct),
        "gt_class_counts": dict(gt_class_counts.most_common(20)),
        "pred_label_counts": dict(pred_label_counts.most_common(20)),
        "gt_purity": numeric_summary(obs_gt[obs.evidence_id].purity for obs in valid),
        "clip_margin": numeric_summary(obs.clip_margin for obs in valid),
        "clip_top1_probability": numeric_summary(obs.clip_top1_probability for obs in valid),
        "clip_entropy": numeric_summary(obs.clip_entropy for obs in valid),
        "low_clip_margin_rate": round(sum(1 for obs in valid if obs.clip_margin < LOW_CLIP_MARGIN) / max(len(valid), 1), 6),
        "per_frame_duplicate_rate": numeric_summary(frame_dup_rates),
        "per_frame_overseg_factor": numeric_summary(frame_overseg),
        "global_semantic_cell_duplicates": all_dup,
    }


def majority(items: list[str]) -> tuple[str, int]:
    if not items:
        return "", 0
    return Counter(items).most_common(1)[0]


def hypothesis_semantic_label(hypothesis) -> str:
    payload = getattr(hypothesis, "object_payload", None)
    label = getattr(payload, "label", "") if payload is not None else ""
    if label:
        return str(label)
    descriptor = str(getattr(hypothesis, "descriptor", ""))
    return descriptor.split(":")[-1] if descriptor else ""


def build_pipeline_config() -> PipelineConfig:
    config = PipelineConfig(emit_association_diagnostics=True, association_diagnostics_top_k=2)
    for key, value in PIPELINE_GATE_OVERRIDES.items():
        setattr(config, key, value)
    return config


def run_layer_monitors(scene: str, frames: list[FrameInput], obs_gt: dict[str, GTAssignment]):
    config = build_pipeline_config()
    memory = ObjectGraphMemory(config)
    logger = EventLogger()
    builder = EvidenceBuilder(config)
    layer1 = CurrentEvidenceGraphLayer(config)
    layer2 = CurrentToMemoryAssociationLayer(config)
    all_decisions = []

    init_eval_targets = {item.target_id for item in obs_gt.values() if item.eval_keep}
    layer1_hyp_targets_by_frame: dict[str, list[str]] = defaultdict(list)
    layer1_purities = []
    layer1_semantic_correct = []
    layer1_gt_class_counts: Counter[str] = Counter()
    layer1_gt_class_correct: Counter[str] = Counter()
    layer1_pred_label_counts: Counter[str] = Counter()
    layer1_semantic_confusions: Counter[tuple[str, str]] = Counter()
    false_merge_hypotheses = 0
    multi_class_hypotheses = 0
    merged_pair_total = 0
    merged_pair_correct = 0
    merged_pair_wrong = 0
    hyp_records = []

    target_objects: dict[str, set[str]] = defaultdict(set)
    target_object_history: dict[str, list[str]] = defaultdict(list)
    target_last_object: dict[str, str] = {}
    object_targets: dict[str, set[str]] = defaultdict(set)
    l2 = Counter()
    l2_valid_decisions = 0
    l2_semantic_correct = 0
    l2_gt_class_counts: Counter[str] = Counter()
    l2_gt_class_correct: Counter[str] = Counter()
    l2_pred_label_counts: Counter[str] = Counter()
    l2_semantic_confusions: Counter[tuple[str, str]] = Counter()
    l2_id_switch_events = 0
    l2_target_revisits = 0
    raw_id_switch_records = []
    l2_decision_samples = []
    duplicate_birth_reason_counts = Counter()
    duplicate_birth_failure_family_counts = Counter()
    duplicate_birth_top_scores = []
    duplicate_birth_top_overlaps = []
    duplicate_birth_top_semantics = []
    duplicate_birth_records = []

    for step_id, frame in enumerate(frames, start=1):
        logger.log(sequence_id=f"replica-{scene}-gt-layer-monitor", step_id=step_id, branch_id=BRANCH_DUOGRAPH3D, event_type="comparison_slice_start", owner_component="pipeline", frame_id=frame.frame_id, temporal_variant=TemporalVariant.NAIVE_FRAMEWISE.value)
        evidence = builder.build(frame, memory=memory, temporal_variant=TemporalVariant.NAIVE_FRAMEWISE)
        hypotheses = layer1.repair(evidence)
        for hyp in hypotheses:
            gt_items = [obs_gt[eid] for eid in hyp.evidence_ids if eid in obs_gt and obs_gt[eid].eval_keep]
            if not gt_items:
                hyp_records.append({"step_id": step_id, "hypothesis_id": hyp.hypothesis_id, "valid": False, "target_id": ""})
                continue
            target_list = [item.target_id for item in gt_items]
            class_list = [item.gt_class_name for item in gt_items]
            target_id, target_count = majority(target_list)
            gt_class_name, _ = majority(class_list)
            purity = target_count / max(len(gt_items), 1)
            pred_label = hypothesis_semantic_label(hyp)
            semantic_ok = pred_label == gt_class_name
            layer1_gt_class_counts[gt_class_name] += 1
            layer1_pred_label_counts[pred_label] += 1
            if semantic_ok:
                layer1_gt_class_correct[gt_class_name] += 1
            else:
                layer1_semantic_confusions[(pred_label, gt_class_name)] += 1
            unique_targets = set(target_list)
            unique_classes = set(class_list)
            false_merge = len(unique_targets) > 1
            multi_class = len(unique_classes) > 1
            false_merge_hypotheses += int(false_merge)
            multi_class_hypotheses += int(multi_class)
            layer1_purities.append(purity)
            layer1_semantic_correct.append(semantic_ok)
            layer1_hyp_targets_by_frame[frame.frame_id].append(target_id)
            for i in range(len(target_list)):
                for j in range(i + 1, len(target_list)):
                    merged_pair_total += 1
                    if target_list[i] == target_list[j]:
                        merged_pair_correct += 1
                    else:
                        merged_pair_wrong += 1
            hyp_records.append({
                "step_id": step_id,
                "hypothesis_id": hyp.hypothesis_id,
                "valid": True,
                "target_id": target_id,
                "gt_class_name": gt_class_name,
                "pred_label": pred_label,
                "purity": round(purity, 6),
                "semantic_correct": semantic_ok,
                "false_merge": false_merge,
                "multi_class": multi_class,
                "evidence_count": len(hyp.evidence_ids),
            })
        decisions = layer2.update(sequence_id=f"replica-{scene}-gt-layer-monitor", step_id=step_id, branch_id=BRANCH_DUOGRAPH3D, hypotheses=hypotheses, memory=memory, logger=logger)
        all_decisions.extend(decisions)
        birth_diagnostics = {
            (record.step_id, str(record.payload.get("hypothesis_id", ""))): record.payload
            for record in logger.records
            if record.event_type == "association_birth_diagnostic" and record.step_id == step_id
        }
        candidate_diagnostics = {
            (record.step_id, str(record.payload.get("hypothesis_id", ""))): record.payload
            for record in logger.records
            if record.event_type == "association_candidate_diagnostic" and record.step_id == step_id
        }
        for hyp, decision, hyp_info in zip(hypotheses, decisions, hyp_records[-len(hypotheses):]):
            if not hyp_info.get("valid"):
                continue
            l2_valid_decisions += 1
            target_id = str(hyp_info["target_id"])
            gt_class_name = str(hyp_info.get("gt_class_name", ""))
            pred_label = str(hyp_info.get("pred_label", ""))
            semantic_ok = bool(hyp_info.get("semantic_correct", False))
            l2_gt_class_counts[gt_class_name] += 1
            l2_pred_label_counts[pred_label] += 1
            l2_semantic_correct += int(semantic_ok)
            if semantic_ok:
                l2_gt_class_correct[gt_class_name] += 1
            else:
                l2_semantic_confusions[(pred_label, gt_class_name)] += 1
            object_id = decision.object_id
            prev_last = target_last_object.get(target_id)
            prev_objects = target_objects[target_id]
            if prev_last is not None:
                l2_target_revisits += 1
            if decision.action == "birth":
                if not prev_objects:
                    l2["correct_birth"] += 1
                    correct = True
                else:
                    l2["duplicate_birth"] += 1
                    correct = False
                    diag = birth_diagnostics.get((step_id, hyp.hypothesis_id), {})
                    failure_family = str(diag.get("failure_family") or "missing_diagnostic")
                    duplicate_birth_reason_counts[decision.reason] += 1
                    duplicate_birth_failure_family_counts[failure_family] += 1
                    top_candidates = diag.get("top_candidates") or []
                    if top_candidates:
                        top = top_candidates[0]
                        duplicate_birth_top_scores.append(float(top.get("score", 0.0) or 0.0))
                        duplicate_birth_top_overlaps.append(float(top.get("point_overlap_score", 0.0) or 0.0))
                        duplicate_birth_top_semantics.append(float(top.get("semantic_score", 0.0) or 0.0))
                    duplicate_birth_records.append(
                        {
                            "step_id": step_id,
                            "hypothesis_id": hyp.hypothesis_id,
                            "object_id": object_id,
                            "target_id": target_id,
                            "previous_object": prev_last or "",
                            "reason": decision.reason,
                            "failure_family": failure_family,
                            "best_object_id": str(diag.get("best_object_id", "")),
                            "best_score": diag.get("best_score"),
                            "best_has_strong_identity": diag.get("best_has_strong_identity"),
                        }
                    )
            else:
                known_targets = object_targets.get(object_id, set())
                if target_id in known_targets:
                    l2["correct_association"] += 1
                    correct = True
                elif not prev_objects:
                    l2["false_association_before_birth"] += 1
                    correct = False
                else:
                    l2["false_association_wrong_object"] += 1
                    correct = False
            if decision.action == "absorb":
                l2["residual_absorption"] += 1
                if correct:
                    l2["correct_residual_absorption"] += 1
                else:
                    l2["false_residual_absorption"] += 1
            if prev_last is not None and object_id != prev_last:
                l2_id_switch_events += 1
                raw_switch_cause = classify_raw_switch_cause(
                    prev_last,
                    decision,
                    candidate_diagnostics.get((step_id, hyp.hypothesis_id), {}),
                )
                raw_id_switch_records.append(
                    {
                        "step_id": step_id,
                        "hypothesis_id": hyp.hypothesis_id,
                        "target_id": target_id,
                        "previous_object": prev_last,
                        "object_id": object_id,
                        "action": decision.action,
                        "reason": decision.reason,
                        "raw_cause": raw_switch_cause,
                    }
                )
            target_objects[target_id].add(object_id)
            target_object_history[target_id].append(object_id)
            target_last_object[target_id] = object_id
            object_targets[object_id].add(target_id)
            if len(l2_decision_samples) < 50 and not correct:
                l2_decision_samples.append({
                    "step_id": step_id,
                    "hypothesis_id": hyp.hypothesis_id,
                    "action": decision.action,
                    "reason": decision.reason,
                    "object_id": object_id,
                    "target_id": target_id,
                    "previous_object": prev_last or "",
                    "object_known_targets": sorted(known_targets) if decision.action != "birth" else [],
                })
        logger.log(sequence_id=f"replica-{scene}-gt-layer-monitor", step_id=step_id, branch_id=BRANCH_DUOGRAPH3D, event_type="comparison_slice_end", owner_component="pipeline", frame_id=frame.frame_id)

    result = SequenceRunResult(
        branch_id=BRANCH_DUOGRAPH3D,
        sequence_id=f"replica-{scene}-gt-layer-monitor",
        memory_nodes=memory.snapshot(),
        event_count=len(logger.records),
        decisions=all_decisions,
        relation_edges=memory.relation_snapshot(),
    )
    summary = summarize_run(result, logger)
    canonical_target_objects: dict[str, set[str]] = defaultdict(set)
    canonical_object_targets: dict[str, set[str]] = defaultdict(set)
    canonical_id_switch_events = 0
    canonical_target_revisits = 0
    for target_id, object_history in target_object_history.items():
        previous_root = None
        for object_id in object_history:
            root_id = resolve_object_root(object_id, result.memory_nodes)
            canonical_target_objects[target_id].add(root_id)
            canonical_object_targets[root_id].add(target_id)
            if previous_root is not None:
                canonical_target_revisits += 1
                if root_id != previous_root:
                    canonical_id_switch_events += 1
            previous_root = root_id
    raw_id_switch_cause_counts = Counter(str(record["raw_cause"]) for record in raw_id_switch_records)
    canonical_id_switch_cause_counts: Counter[str] = Counter()
    for record in raw_id_switch_records:
        previous_root = resolve_object_root(str(record["previous_object"]), result.memory_nodes)
        current_root = resolve_object_root(str(record["object_id"]), result.memory_nodes)
        if previous_root == current_root:
            canonical_id_switch_cause_counts["merge_repaired_raw_id_change"] += 1
        else:
            canonical_id_switch_cause_counts[str(record["raw_cause"])] += 1
    duplicate_birth_repaired = 0
    duplicate_birth_unrepaired = 0
    for record in duplicate_birth_records:
        node = result.memory_nodes.get(str(record["object_id"]))
        if node is not None and "merged_into_duplicate_object" in node.failure_tags:
            duplicate_birth_repaired += 1
        else:
            duplicate_birth_unrepaired += 1
    frame_dup_rates = [duplicate_stats(targets)["duplicate_rate"] for targets in layer1_hyp_targets_by_frame.values()]
    frame_overseg = [duplicate_stats(targets)["overseg_factor"] for targets in layer1_hyp_targets_by_frame.values()]
    layer1_targets = {target for targets in layer1_hyp_targets_by_frame.values() for target in targets}
    layer1_summary = {
        "hypothesis_count_eval_keep": sum(len(v) for v in layer1_hyp_targets_by_frame.values()),
        "unique_gt_target_count": len(layer1_targets),
        "coverage_vs_init": round(len(layer1_targets) / max(len(init_eval_targets), 1), 6),
        "semantic_accuracy": round(sum(layer1_semantic_correct) / max(len(layer1_semantic_correct), 1), 6),
        "top_semantic_confusions": confusion_records(layer1_semantic_confusions),
        "per_class_semantic_accuracy": per_class_accuracy_records(layer1_gt_class_counts, layer1_gt_class_correct),
        "gt_class_counts": dict(layer1_gt_class_counts.most_common(20)),
        "pred_label_counts": dict(layer1_pred_label_counts.most_common(20)),
        "hypothesis_target_purity": numeric_summary(layer1_purities),
        "false_merge_hypothesis_count": false_merge_hypotheses,
        "false_merge_hypothesis_rate": round(false_merge_hypotheses / max(len(layer1_purities), 1), 6),
        "multi_class_hypothesis_count": multi_class_hypotheses,
        "multi_class_hypothesis_rate": round(multi_class_hypotheses / max(len(layer1_purities), 1), 6),
        "merged_pair_total": merged_pair_total,
        "merge_pair_precision": round(merged_pair_correct / max(merged_pair_total, 1), 6),
        "merge_pair_error_rate": round(merged_pair_wrong / max(merged_pair_total, 1), 6),
        "per_frame_duplicate_rate": numeric_summary(frame_dup_rates),
        "per_frame_overseg_factor": numeric_summary(frame_overseg),
        "global_semantic_cell_duplicates": duplicate_stats([target for targets in layer1_hyp_targets_by_frame.values() for target in targets]),
    }
    correct_total = l2["correct_birth"] + l2["correct_association"]
    assoc_total = l2["correct_association"] + l2["false_association_before_birth"] + l2["false_association_wrong_object"]
    birth_total = l2["correct_birth"] + l2["duplicate_birth"]
    multi_target_objects = sum(1 for targets in object_targets.values() if len(targets) > 1)
    canonical_multi_target_objects = sum(1 for targets in canonical_object_targets.values() if len(targets) > 1)
    layer2_targets = set(target_objects)
    stage_coverage = summarize_stage_coverage(
        init_unique_targets=len(init_eval_targets),
        layer1_unique_targets=len(layer1_targets),
        layer2_unique_targets=len(layer2_targets),
    )
    layer2_summary = {
        "valid_decision_count": l2_valid_decisions,
        "decision_accuracy": round(correct_total / max(l2_valid_decisions, 1), 6),
        "decision_accuracy_after_object_merge": round((correct_total + duplicate_birth_repaired) / max(l2_valid_decisions, 1), 6),
        "decision_error_rate": round(1.0 - correct_total / max(l2_valid_decisions, 1), 6),
        "decision_semantic_accuracy": round(l2_semantic_correct / max(l2_valid_decisions, 1), 6),
        "top_semantic_confusions": confusion_records(l2_semantic_confusions),
        "per_class_semantic_accuracy": per_class_accuracy_records(l2_gt_class_counts, l2_gt_class_correct),
        "gt_class_counts": dict(l2_gt_class_counts.most_common(20)),
        "pred_label_counts": dict(l2_pred_label_counts.most_common(20)),
        "unique_gt_target_count": len(layer2_targets),
        "coverage_vs_init": stage_coverage["layer2_coverage_vs_init"],
        "coverage_vs_layer1": stage_coverage["layer2_coverage_vs_layer1"],
        "birth_count_eval_keep": birth_total,
        "correct_birth": l2["correct_birth"],
        "duplicate_birth": l2["duplicate_birth"],
        "duplicate_birth_rate": round(l2["duplicate_birth"] / max(birth_total, 1), 6),
        "duplicate_birth_reason_counts": dict(duplicate_birth_reason_counts),
        "duplicate_birth_failure_family_counts": dict(duplicate_birth_failure_family_counts),
        "duplicate_birth_top_candidate_score": numeric_summary(duplicate_birth_top_scores),
        "duplicate_birth_top_candidate_point_overlap": numeric_summary(duplicate_birth_top_overlaps),
        "duplicate_birth_top_candidate_semantic": numeric_summary(duplicate_birth_top_semantics),
        "duplicate_birth_repaired_by_object_merge": duplicate_birth_repaired,
        "duplicate_birth_unrepaired_after_object_merge": duplicate_birth_unrepaired,
        "duplicate_birth_repair_rate": round(duplicate_birth_repaired / max(len(duplicate_birth_records), 1), 6),
        "association_count_eval_keep": assoc_total,
        "correct_association": l2["correct_association"],
        "false_association_before_birth": l2["false_association_before_birth"],
        "false_association_wrong_object": l2["false_association_wrong_object"],
        "association_accuracy": round(l2["correct_association"] / max(assoc_total, 1), 6),
        "residual_absorption_count": l2["residual_absorption"],
        "correct_residual_absorption": l2["correct_residual_absorption"],
        "false_residual_absorption": l2["false_residual_absorption"],
        "residual_absorption_accuracy": round(l2["correct_residual_absorption"] / max(l2["residual_absorption"], 1), 6),
        "id_switch_events": l2_id_switch_events,
        "id_switch_rate_per_revisit": round(l2_id_switch_events / max(l2_target_revisits, 1), 6),
        "raw_id_switch_events": l2_id_switch_events,
        "raw_id_switch_rate_per_revisit": round(l2_id_switch_events / max(l2_target_revisits, 1), 6),
        "raw_id_switch_cause_counts": dict(raw_id_switch_cause_counts),
        "canonical_id_switch_events_after_object_merge": canonical_id_switch_events,
        "canonical_id_switch_rate_per_revisit_after_object_merge": round(canonical_id_switch_events / max(canonical_target_revisits, 1), 6),
        "canonical_id_switch_cause_counts_after_object_merge": dict(canonical_id_switch_cause_counts),
        "fragmented_gt_target_count": sum(1 for objects in target_objects.values() if len(objects) > 1),
        "fragmented_gt_target_rate": round(sum(1 for objects in target_objects.values() if len(objects) > 1) / max(len(target_objects), 1), 6),
        "gt_target_fragmentation": sum(max(len(objects) - 1, 0) for objects in target_objects.values()),
        "canonical_fragmented_gt_target_count_after_object_merge": sum(1 for objects in canonical_target_objects.values() if len(objects) > 1),
        "canonical_fragmented_gt_target_rate_after_object_merge": round(sum(1 for objects in canonical_target_objects.values() if len(objects) > 1) / max(len(canonical_target_objects), 1), 6),
        "canonical_gt_target_fragmentation_after_object_merge": sum(max(len(objects) - 1, 0) for objects in canonical_target_objects.values()),
        "multi_target_memory_object_count": multi_target_objects,
        "multi_target_memory_object_rate": round(multi_target_objects / max(len(object_targets), 1), 6),
        "canonical_multi_target_memory_object_count_after_object_merge": canonical_multi_target_objects,
        "canonical_multi_target_memory_object_rate_after_object_merge": round(canonical_multi_target_objects / max(len(canonical_object_targets), 1), 6),
        "error_samples": l2_decision_samples,
        "raw_id_switch_samples": raw_id_switch_records[:50],
        "duplicate_birth_samples": duplicate_birth_records[:50],
        "reason_counts": dict(Counter(decision.reason for decision in all_decisions)),
    }
    return result, logger, summary, layer1_summary, layer2_summary


def object_probability_monitor(
    scene: str,
    pred_exp_name: str,
    class_feats_np: np.ndarray,
    class_names: list[str],
    keep_indices: set[int],
    gt_xyz: torch.Tensor,
    gt_class: torch.Tensor,
    *,
    device: str,
    logit_scale: float,
    object_path: Path | None = None,
) -> dict[str, object]:
    if object_path is not None and object_path.exists():
        paths = [object_path]
    else:
        exact = REPLICA_ROOT / scene / "pcd_saves" / f"full_pcd_{pred_exp_name}.pkl.gz"
        if exact.exists():
            paths = [exact]
        else:
            paths = sorted((REPLICA_ROOT / scene / "pcd_saves").glob(f"full_pcd_{pred_exp_name}*.pkl.gz"), key=lambda p: p.stat().st_mtime)
    if not paths:
        return {"available": False, "pred_exp_name": pred_exp_name}
    with gzip.open(paths[-1], "rb") as handle:
        payload = pickle.load(handle)
    objects = payload.get("objects") or []
    points_list = []
    pred_indices = []
    top_probs = []
    margins = []
    entropies = []
    top_sims = []
    labels = []
    for obj in objects:
        points = np.asarray(obj.get("pcd_np", np.zeros((0, 3))), dtype=np.float32)
        if len(points) > MAX_POINTS_PER_OBJECT:
            points = points[sample_indices(len(points), MAX_POINTS_PER_OBJECT)]
        clip_ft = normalize_np(np.asarray(obj.get("clip_ft"), dtype=np.float32).reshape(1, -1))[0]
        sims = clip_ft @ class_feats_np.T
        masked = sims.copy()
        ignored = [i for i in range(len(class_names)) if i not in keep_indices]
        masked[ignored] = -1e9
        pred_idx = int(masked.argmax())
        kept_sims = masked[list(sorted(keep_indices))]
        probs = softmax(kept_sims * logit_scale)
        sorted_sims = np.sort(kept_sims)
        margins.append(float(sorted_sims[-1] - sorted_sims[-2]) if len(sorted_sims) > 1 else 0.0)
        top_probs.append(float(probs.max()))
        entropies.append(entropy(probs))
        top_sims.append(float(masked[pred_idx]))
        labels.append(class_names[pred_idx])
        points_list.append(points)
        pred_indices.append(pred_idx)
    assignments = assign_points_to_gt(points_list, pred_indices, gt_xyz, gt_class, class_names, keep_indices, device=device)
    valid_indices = [i for i, item in enumerate(assignments) if item.eval_keep]
    semantic_correct = [assignments[i].semantic_correct for i in valid_indices]
    target_ids = [assignments[i].target_id for i in valid_indices]
    false_labels = Counter()
    for i in valid_indices:
        if not assignments[i].semantic_correct:
            false_labels[(labels[i], assignments[i].gt_class_name)] += 1
    return {
        "available": True,
        "pred_exp_name": pred_exp_name,
        "probability_logit_scale": round(float(logit_scale), 6),
        "path": str(paths[-1]),
        "object_count": len(objects),
        "valid_eval_object_count": len(valid_indices),
        "semantic_accuracy": round(sum(semantic_correct) / max(len(semantic_correct), 1), 6),
        "gt_purity": numeric_summary(assignments[i].purity for i in valid_indices),
        "top1_probability": numeric_summary(top_probs[i] for i in valid_indices),
        "top1_similarity": numeric_summary(top_sims[i] for i in valid_indices),
        "class_margin": numeric_summary(margins[i] for i in valid_indices),
        "class_entropy": numeric_summary(entropies[i] for i in valid_indices),
        "semantic_cell_duplicates": duplicate_stats(target_ids),
        "top_pred_to_gt_errors": [
            {"pred": key[0], "gt": key[1], "count": value}
            for key, value in false_labels.most_common(12)
        ],
    }


def write_duograph_payload(scene: str, result, logger, obs_meta: list[ObservationMeta], obs_gt: dict[str, GTAssignment], class_feats_np: np.ndarray):
    # Minimal object export for object-level probability parity. Prefer the
    # online object memory; fall back to geometry-key aggregation for legacy
    # runs that do not carry object payloads.
    t0 = time.time()
    obs_by_eid = {obs.evidence_id: obs for obs in obs_meta}
    label_to_index = {obs.label: int(obs.pred_class_index) for obs in obs_meta}
    objects = []
    skip_counts: Counter[str] = Counter()
    for object_id, node in sorted(result.memory_nodes.items()):
        skip_reason = ObjectGraphMemory.export_skip_reason(
            node,
            min_points=4,
            min_detections=EXPORT_MIN_DETECTIONS,
        )
        if skip_reason:
            skip_counts[skip_reason] += 1
            continue
        points = np.asarray(node.sampled_points, dtype=np.float32)
        if len(points) > MAX_POINTS_PER_OBJECT:
            points = points[sample_indices(len(points), MAX_POINTS_PER_OBJECT)]
        label = ObjectGraphMemory.dominant_semantic_label(node)
        if not label:
            label = node.appearance_key_recent or node.descriptor_recent
        label_index = int(label_to_index.get(label, 0))
        clip_ft = np.asarray(node.clip_feature, dtype=np.float32)
        if clip_ft.shape != class_feats_np[0].shape:
            clip_ft = class_feats_np[label_index].astype(np.float32)
        text_ft = np.asarray(node.text_feature, dtype=np.float32)
        if text_ft.shape != class_feats_np[0].shape:
            text_ft = class_feats_np[label_index].astype(np.float32)
        objects.append({
            "object_id": object_id,
            "track_hint": object_id,
            "class_name": [label],
            "class_id": [1],
            "conf": [float(node.confidence_sum / max(node.detection_count, 1)) if node.detection_count else 0.0],
            "clip_ft": normalize_np(clip_ft.reshape(1, -1))[0].astype(np.float32),
            "text_ft": normalize_np(text_ft.reshape(1, -1))[0].astype(np.float32),
            "pcd_np": points,
            "pcd_color_np": np.asarray(node.sampled_colors, dtype=np.float32) if len(node.sampled_colors) == len(points) else np.zeros_like(points),
            "bbox_np": np.zeros((8, 3), dtype=np.float32),
            "num_detections": max(int(node.detection_count), 1),
        })
    object_source = "online_memory_node"
    has_memory_payload_nodes = any(node.sampled_points for node in result.memory_nodes.values())
    if not objects and not has_memory_payload_nodes:
        by_key: dict[str, dict[str, object]] = {}
        object_source = "geometry_key_fallback"
        for record in logger.records:
            if record.event_type not in {"birth_commit", "association_commit", "reentry_commit"}:
                continue
            track_hint = str(record.payload.get("track_hint", ""))
            object_id = str(record.payload.get("object_id", ""))
            if not track_hint or not object_id:
                continue
            bucket = by_key.setdefault(track_hint, {"object_ids": [], "evidence_ids": []})
            bucket["object_ids"].append(object_id)
        # The monitor's layer keys equal observation geometry keys; aggregate all observations with the same key.
        for obs in obs_meta:
            bucket = by_key.setdefault(obs.geometry_key, {"object_ids": [obs.geometry_key], "evidence_ids": []})
            bucket["evidence_ids"].append(obs.evidence_id)
        for key, bucket in sorted(by_key.items()):
            eids = [eid for eid in bucket.get("evidence_ids", []) if eid in obs_by_eid]
            if not eids:
                continue
            points = np.concatenate([obs_by_eid[eid].points for eid in eids], axis=0).astype(np.float32)
            keep = sample_indices(len(points), MAX_POINTS_PER_OBJECT)
            points = points[keep]
            labels = [obs_by_eid[eid].label for eid in eids]
            label = Counter(labels).most_common(1)[0][0]
            clip_ft = normalize_np(np.mean([obs_by_eid[eid].clip_ft for eid in eids], axis=0, dtype=np.float64).reshape(1, -1))[0].astype(np.float32)
            label_index = int(obs_by_eid[eids[0]].pred_class_index)
            text_ft = class_feats_np[label_index].astype(np.float32)
            objects.append({
                "object_id": str((bucket.get("object_ids") or [key])[0]),
                "track_hint": key,
                "class_name": [label],
                "class_id": [1],
                "conf": [float(np.mean([obs_by_eid[eid].confidence for eid in eids]))],
                "clip_ft": clip_ft,
                "text_ft": text_ft,
                "pcd_np": points,
                "pcd_color_np": np.zeros_like(points),
                "bbox_np": np.zeros((8, 3), dtype=np.float32),
                "num_detections": len(eids),
            })
    pcd_dir = REPLICA_ROOT / scene / "pcd_saves"
    pcd_dir.mkdir(parents=True, exist_ok=True)
    path = pcd_dir / f"full_pcd_{DUOGRAPH_PRED_EXP_NAME}_gt_monitor.pkl.gz"
    with gzip.open(path, "wb") as handle:
        pickle.dump({"objects": objects, "bg_objects": None}, handle)
    return {
        "path": str(path),
        "object_count": len(objects),
        "object_source": object_source,
        "export_min_detections": EXPORT_MIN_DETECTIONS,
        "skipped_object_counts": dict(skip_counts),
        "seconds": round(time.time() - t0, 3),
    }


def load_baseline_rows() -> dict[str, dict[str, str]]:
    if not BASELINE_CSV.exists():
        return {}
    with BASELINE_CSV.open() as handle:
        return {row["scene_id"]: row for row in csv.DictReader(handle)}


def configure_profile(args) -> None:
    global ROOT, BASELINE_PRED_EXP_NAME, DUOGRAPH_PRED_EXP_NAME, PROFILE, PIPELINE_GATE_OVERRIDES
    global VOXEL_SIZE, MIN_VALID_DEPTH_POINTS, MAX_POINTS_PER_OBS
    global MASK_CONF_THRESHOLD, MAX_BBOX_AREA_RATIO, APPLY_MASK_SUBTRACT_CONTAINED, CLASS_AGNOSTIC_IDENTITY
    global EXPORT_MIN_DETECTIONS

    PROFILE = args.profile
    if PROFILE == "engineered":
        ROOT = args.root or ENGINEERED_ROOT
        VOXEL_SIZE = 0.20
        MIN_VALID_DEPTH_POINTS = 16
        MAX_POINTS_PER_OBS = 160
        MASK_CONF_THRESHOLD = 0.95
        MAX_BBOX_AREA_RATIO = 0.50
        APPLY_MASK_SUBTRACT_CONTAINED = True
        CLASS_AGNOSTIC_IDENTITY = True
        EXPORT_MIN_DETECTIONS = 2
        DUOGRAPH_PRED_EXP_NAME = "duograph3d_gsa_engineered_monitor"
    else:
        ROOT = args.root or ROOT
        VOXEL_SIZE = 0.75
        MIN_VALID_DEPTH_POINTS = 1
        MAX_POINTS_PER_OBS = 48
        MASK_CONF_THRESHOLD = None
        MAX_BBOX_AREA_RATIO = None
        APPLY_MASK_SUBTRACT_CONTAINED = False
        CLASS_AGNOSTIC_IDENTITY = False
        EXPORT_MIN_DETECTIONS = 1
        DUOGRAPH_PRED_EXP_NAME = "duograph3d_gt_layer_monitor"

    if args.duograph_pred_exp_name:
        DUOGRAPH_PRED_EXP_NAME = args.duograph_pred_exp_name
    if args.baseline_pred_exp_name:
        BASELINE_PRED_EXP_NAME = args.baseline_pred_exp_name
    if args.export_min_detections is not None:
        EXPORT_MIN_DETECTIONS = max(int(args.export_min_detections), 1)
    gate_args = {
        "association_threshold": args.association_threshold,
        "candidate_retrieval_budget": args.candidate_retrieval_budget,
        "candidate_retrieval_channel_budget": args.candidate_retrieval_channel_budget,
        "history_candidate_affinity_threshold": args.history_affinity_threshold,
        "history_candidate_margin_threshold": args.history_margin_threshold,
        "layer1_merge_threshold": args.layer1_merge_threshold,
        "layer1_history_shared_boost": args.layer1_history_boost,
        "layer1_history_min_spatial_score": args.layer1_history_min_spatial,
        "layer1_history_min_semantic_score": args.layer1_history_min_semantic,
        "layer1_history_min_visual_score": args.layer1_history_min_visual,
        "layer1_history_min_size_score": args.layer1_history_min_size,
        "layer2_history_identity_threshold": args.layer2_history_identity_threshold,
        "history_point_overlap_distance": args.history_point_overlap_distance,
        "history_overlap_max_points": args.history_overlap_max_points,
        "history_point_overlap_affinity_weight": args.history_point_overlap_affinity_weight,
        "history_point_overlap_min_semantic_score": args.history_point_overlap_min_semantic_score,
        "history_point_overlap_min_spatial_score": args.history_point_overlap_min_spatial_score,
        "history_point_overlap_requires_spatial_evidence": args.history_point_overlap_requires_spatial_evidence,
        "layer2_absorption_threshold": args.layer2_absorption_threshold,
        "layer2_absorption_min_point_overlap": args.layer2_absorption_min_point_overlap,
        "layer2_absorption_min_semantic_score": args.layer2_absorption_min_semantic_score,
        "layer2_point_overlap_weight": args.layer2_point_overlap_weight,
        "layer2_point_overlap_score_threshold": args.layer2_point_overlap_score_threshold,
        "layer2_point_overlap_identity_threshold": args.layer2_point_overlap_identity_threshold,
        "layer2_point_overlap_identity_min_spatial": args.layer2_point_overlap_identity_min_spatial,
        "layer2_point_overlap_identity_min_semantic": args.layer2_point_overlap_identity_min_semantic,
        "layer2_point_overlap_identity_min_visual": args.layer2_point_overlap_identity_min_visual,
        "layer2_point_overlap_identity_requires_spatial_evidence": args.layer2_point_overlap_identity_requires_spatial_evidence,
        "layer2_relation_bonus_cap": args.layer2_relation_bonus_cap,
        "layer2_relation_bonus_requires_identity": args.layer2_relation_bonus_requires_identity,
        "layer2_visual_similarity_weight": args.layer2_visual_similarity_weight,
        "layer2_descriptor_match_weight": args.layer2_descriptor_match_weight,
        "layer2_appearance_match_weight": args.layer2_appearance_match_weight,
        "object_merge_threshold": args.object_merge_threshold,
        "object_merge_spatial_threshold": args.object_merge_spatial_threshold,
        "object_merge_point_overlap_weight": args.object_merge_point_overlap_weight,
        "object_merge_point_overlap_min_semantic_score": args.object_merge_point_overlap_min_semantic_score,
        "object_merge_semantic_conflict_guard": args.object_merge_semantic_conflict_guard,
        "object_merge_semantic_conflict_min_score": args.object_merge_semantic_conflict_min_score,
        "object_merge_semantic_conflict_visual_override": args.object_merge_semantic_conflict_visual_override,
        "object_merge_max_merged_label_entropy": args.object_merge_max_merged_label_entropy,
        "object_merge_min_merged_top_label_share": args.object_merge_min_merged_top_label_share,
        "object_merge_protect_small_label_share": args.object_merge_protect_small_label_share,
        "object_merge_protect_small_label_confidence": args.object_merge_protect_small_label_confidence,
    }
    if args.layer2_enable_residual_absorption is not None:
        gate_args["layer2_enable_residual_absorption"] = bool(args.layer2_enable_residual_absorption)
    if args.layer2_relation_bonus_requires_identity is not None:
        gate_args["layer2_relation_bonus_requires_identity"] = bool(args.layer2_relation_bonus_requires_identity)
    if args.history_point_overlap_requires_spatial_evidence is not None:
        gate_args["history_point_overlap_requires_spatial_evidence"] = bool(args.history_point_overlap_requires_spatial_evidence)
    if args.layer2_point_overlap_identity_requires_spatial_evidence is not None:
        gate_args["layer2_point_overlap_identity_requires_spatial_evidence"] = bool(args.layer2_point_overlap_identity_requires_spatial_evidence)
    if args.object_merge_semantic_conflict_guard is not None:
        gate_args["object_merge_semantic_conflict_guard"] = bool(args.object_merge_semantic_conflict_guard)
    PIPELINE_GATE_OVERRIDES = {key: value for key, value in gate_args.items() if value is not None}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--profile", choices=["legacy", "engineered"], default="legacy")
    parser.add_argument("--root", type=Path, default=None)
    parser.add_argument("--scenes", nargs="*", default=list(REPLICA_SCENE_IDS))
    parser.add_argument("--skip-object-export", action="store_true")
    parser.add_argument("--duograph-pred-exp-name", default=None)
    parser.add_argument("--baseline-pred-exp-name", default=None)
    parser.add_argument("--export-min-detections", type=int, default=None)
    parser.add_argument("--association-threshold", type=float, default=None)
    parser.add_argument("--candidate-retrieval-budget", type=int, default=None)
    parser.add_argument("--candidate-retrieval-channel-budget", type=int, default=None)
    parser.add_argument("--history-affinity-threshold", type=float, default=None)
    parser.add_argument("--history-margin-threshold", type=float, default=None)
    parser.add_argument("--layer1-merge-threshold", type=float, default=None)
    parser.add_argument("--layer1-history-boost", type=float, default=None)
    parser.add_argument("--layer1-history-min-spatial", type=float, default=None)
    parser.add_argument("--layer1-history-min-semantic", type=float, default=None)
    parser.add_argument("--layer1-history-min-visual", type=float, default=None)
    parser.add_argument("--layer1-history-min-size", type=float, default=None)
    parser.add_argument("--layer2-history-identity-threshold", type=float, default=None)
    parser.add_argument("--history-point-overlap-distance", type=float, default=None)
    parser.add_argument("--history-overlap-max-points", type=int, default=None)
    parser.add_argument("--history-point-overlap-affinity-weight", type=float, default=None)
    parser.add_argument("--history-point-overlap-min-semantic-score", type=float, default=None)
    parser.add_argument("--history-point-overlap-min-spatial-score", type=float, default=None)
    parser.add_argument("--history-point-overlap-requires-spatial-evidence", type=int, choices=[0, 1], default=None)
    parser.add_argument("--layer2-absorption-threshold", type=float, default=None)
    parser.add_argument("--layer2-absorption-min-point-overlap", type=float, default=None)
    parser.add_argument("--layer2-absorption-min-semantic-score", type=float, default=None)
    parser.add_argument("--layer2-point-overlap-weight", type=float, default=None)
    parser.add_argument("--layer2-point-overlap-score-threshold", type=float, default=None)
    parser.add_argument("--layer2-point-overlap-identity-threshold", type=float, default=None)
    parser.add_argument("--layer2-point-overlap-identity-min-spatial", type=float, default=None)
    parser.add_argument("--layer2-point-overlap-identity-min-semantic", type=float, default=None)
    parser.add_argument("--layer2-point-overlap-identity-min-visual", type=float, default=None)
    parser.add_argument("--layer2-point-overlap-identity-requires-spatial-evidence", type=int, choices=[0, 1], default=None)
    parser.add_argument("--layer2-relation-bonus-cap", type=float, default=None)
    parser.add_argument("--layer2-relation-bonus-requires-identity", type=int, choices=[0, 1], default=None)
    parser.add_argument("--layer2-visual-similarity-weight", type=float, default=None)
    parser.add_argument("--layer2-descriptor-match-weight", type=float, default=None)
    parser.add_argument("--layer2-appearance-match-weight", type=float, default=None)
    parser.add_argument("--layer2-enable-residual-absorption", type=int, choices=[0, 1], default=None)
    parser.add_argument("--object-merge-threshold", type=float, default=None)
    parser.add_argument("--object-merge-spatial-threshold", type=float, default=None)
    parser.add_argument("--object-merge-point-overlap-weight", type=float, default=None)
    parser.add_argument("--object-merge-point-overlap-min-semantic-score", type=float, default=None)
    parser.add_argument("--object-merge-semantic-conflict-guard", type=int, choices=[0, 1], default=None)
    parser.add_argument("--object-merge-semantic-conflict-min-score", type=float, default=None)
    parser.add_argument("--object-merge-semantic-conflict-visual-override", type=float, default=None)
    parser.add_argument("--object-merge-max-merged-label-entropy", type=float, default=None)
    parser.add_argument("--object-merge-min-merged-top-label-share", type=float, default=None)
    parser.add_argument("--object-merge-protect-small-label-share", type=float, default=None)
    parser.add_argument("--object-merge-protect-small-label-confidence", type=float, default=None)
    args = parser.parse_args()
    configure_profile(args)
    ROOT.mkdir(parents=True, exist_ok=True)
    device = "cuda:0" if torch.cuda.is_available() else "cpu"
    torch.set_num_threads(4)

    class_all2existing = torch.ones(len(REPLICA_CLASSES)).long() * -1
    for i, c in enumerate(REPLICA_EXISTING_CLASSES):
        class_all2existing[c] = i
    class_names = [REPLICA_CLASSES[i] for i in REPLICA_EXISTING_CLASSES]
    exclude_names = {"other", "floor", "wall", "ceiling", "door", "window"}
    keep_indices = {i for i, name in enumerate(class_names) if name not in exclude_names}

    print("Loading CLIP text encoder", flush=True)
    clip_model, _, _ = open_clip.create_model_and_transforms("ViT-H-14", "laion2b_s32b_b79k")
    clip_model = clip_model.to(device)
    tokenizer = open_clip.get_tokenizer("ViT-H-14")
    text = tokenizer([f"an image of {c}" for c in class_names]).to(device)
    with torch.no_grad():
        class_feats = clip_model.encode_text(text)
        class_feats = class_feats / class_feats.norm(dim=-1, keepdim=True)
    logit_scale = float(clip_model.logit_scale.exp().detach().cpu()) if hasattr(clip_model, "logit_scale") else 100.0
    class_feats_np = class_feats.detach().cpu().numpy().astype(np.float32)
    scene_id_map = {scene_id: scene_id_ for scene_id, scene_id_ in zip(REPLICA_SCENE_IDS, REPLICA_SCENE_IDS_)}
    baseline_rows = load_baseline_rows()

    scene_summaries = []
    for scene in args.scenes:
        scene_t0 = time.time()
        print(f"=== {scene}: prepare detections ===", flush=True)
        frames, obs_meta, prep = prepare_scene(scene, class_names, class_feats_np, logit_scale=logit_scale)
        print(json.dumps(prep), flush=True)
        print(f"=== {scene}: load GT and assign observations ===", flush=True)
        gt_xyz, gt_class = load_gt_scene(scene_id_map[scene], class_all2existing, device)
        assignments = assign_points_to_gt(
            [obs.points for obs in obs_meta],
            [obs.pred_class_index for obs in obs_meta],
            gt_xyz,
            gt_class,
            class_names,
            keep_indices,
            device=device,
        )
        obs_gt = {obs.evidence_id: assignment for obs, assignment in zip(obs_meta, assignments)}
        init_summary = summarize_init(obs_meta, obs_gt)
        geometry_key_gt_monitor = summarize_geometry_keys(obs_meta, obs_gt)
        print(json.dumps({"scene": scene, "init": init_summary}, ensure_ascii=False), flush=True)
        print(f"=== {scene}: run DuoGraph3D with layer monitors ===", flush=True)
        result, logger, run_summary, layer1_summary, layer2_summary = run_layer_monitors(scene, frames, obs_gt)
        export_summary = {}
        if not args.skip_object_export:
            export_summary = write_duograph_payload(scene, result, logger, obs_meta, obs_gt, class_feats_np)
        duograph_object_path = Path(str(export_summary.get("path", ""))) if export_summary.get("path") else None
        duograph_object_monitor = object_probability_monitor(scene, DUOGRAPH_PRED_EXP_NAME, class_feats_np, class_names, keep_indices, gt_xyz, gt_class, device=device, logit_scale=logit_scale, object_path=duograph_object_path)
        baseline_object_monitor = object_probability_monitor(scene, BASELINE_PRED_EXP_NAME, class_feats_np, class_names, keep_indices, gt_xyz, gt_class, device=device, logit_scale=logit_scale)
        scene_summary = {
            "scene": scene,
            "prep": prep,
            "init": init_summary,
            "layer1": layer1_summary,
            "layer2": layer2_summary,
            "stage_coverage": summarize_stage_coverage(
                init_unique_targets=int(init_summary["unique_gt_target_count"]),
                layer1_unique_targets=int(layer1_summary["unique_gt_target_count"]),
                layer2_unique_targets=int(layer2_summary["unique_gt_target_count"]),
            ),
            "geometry_key_gt_monitor": geometry_key_gt_monitor,
            "duograph_run_summary": run_summary,
            "duograph_object_export": export_summary,
            "duograph_object_monitor": duograph_object_monitor,
            "conceptgraphs_baseline_object_monitor": baseline_object_monitor,
            "conceptgraphs_baseline_metrics": baseline_rows.get(scene),
            "pipeline_gate_overrides": PIPELINE_GATE_OVERRIDES,
            "seconds_total": round(time.time() - scene_t0, 3),
        }
        scene_summaries.append(scene_summary)
        write_json(to_builtin({"scenes": scene_summaries}), ROOT / "progress_gt_layer_monitor.json")
        print(json.dumps({
            "scene": scene,
            "layer1_dup_p50": layer1_summary["per_frame_duplicate_rate"].get("p50"),
            "layer2_acc": layer2_summary["decision_accuracy"],
            "layer2_id_switch_rate": layer2_summary["id_switch_rate_per_revisit"],
            "baseline_obj_acc": baseline_object_monitor.get("semantic_accuracy"),
        }), flush=True)

    rollup = {
        "valid_eval_observations": sum(item["init"]["valid_eval_observations"] for item in scene_summaries),
        "layer1_eval_hypotheses": sum(item["layer1"]["hypothesis_count_eval_keep"] for item in scene_summaries),
        "layer2_valid_decisions": sum(item["layer2"]["valid_decision_count"] for item in scene_summaries),
        "layer2_correct_birth": sum(item["layer2"]["correct_birth"] for item in scene_summaries),
        "layer2_correct_association": sum(item["layer2"]["correct_association"] for item in scene_summaries),
        "layer2_duplicate_birth": sum(item["layer2"]["duplicate_birth"] for item in scene_summaries),
        "layer2_id_switch_events": sum(item["layer2"]["id_switch_events"] for item in scene_summaries),
        "layer2_raw_id_switch_events": sum(item["layer2"]["raw_id_switch_events"] for item in scene_summaries),
        "layer2_canonical_id_switch_events_after_object_merge": sum(item["layer2"]["canonical_id_switch_events_after_object_merge"] for item in scene_summaries),
        "layer2_gt_target_fragmentation": sum(item["layer2"]["gt_target_fragmentation"] for item in scene_summaries),
        "layer2_canonical_gt_target_fragmentation_after_object_merge": sum(item["layer2"]["canonical_gt_target_fragmentation_after_object_merge"] for item in scene_summaries),
        "layer2_residual_absorption_count": sum(item["layer2"]["residual_absorption_count"] for item in scene_summaries),
        "layer2_correct_residual_absorption": sum(item["layer2"]["correct_residual_absorption"] for item in scene_summaries),
        "layer2_false_residual_absorption": sum(item["layer2"]["false_residual_absorption"] for item in scene_summaries),
        "layer2_duplicate_birth_repaired_by_object_merge": sum(item["layer2"]["duplicate_birth_repaired_by_object_merge"] for item in scene_summaries),
    }
    rollup["layer2_decision_accuracy"] = round((rollup["layer2_correct_birth"] + rollup["layer2_correct_association"]) / max(rollup["layer2_valid_decisions"], 1), 6)
    rollup["init_unique_gt_targets"] = sum(item["init"]["unique_gt_target_count"] for item in scene_summaries)
    rollup["layer1_unique_gt_targets"] = sum(item["layer1"]["unique_gt_target_count"] for item in scene_summaries)
    rollup["layer2_unique_gt_targets"] = sum(item["layer2"]["unique_gt_target_count"] for item in scene_summaries)
    rollup["layer1_coverage_vs_init_micro"] = round(rollup["layer1_unique_gt_targets"] / max(rollup["init_unique_gt_targets"], 1), 6)
    rollup["layer2_coverage_vs_init_micro"] = round(rollup["layer2_unique_gt_targets"] / max(rollup["init_unique_gt_targets"], 1), 6)
    rollup["layer2_coverage_vs_layer1_micro"] = round(rollup["layer2_unique_gt_targets"] / max(rollup["layer1_unique_gt_targets"], 1), 6)
    rollup["layer2_duplicate_birth_rate"] = round(rollup["layer2_duplicate_birth"] / max(rollup["layer2_correct_birth"] + rollup["layer2_duplicate_birth"], 1), 6)
    rollup["layer2_residual_absorption_accuracy"] = round(rollup["layer2_correct_residual_absorption"] / max(rollup["layer2_residual_absorption_count"], 1), 6)
    rollup["layer2_duplicate_birth_failure_family_counts"] = aggregate_counter(scene_summaries, ("layer2", "duplicate_birth_failure_family_counts"))
    rollup["layer2_duplicate_birth_reason_counts"] = aggregate_counter(scene_summaries, ("layer2", "duplicate_birth_reason_counts"))
    rollup["layer2_raw_id_switch_cause_counts"] = aggregate_counter(scene_summaries, ("layer2", "raw_id_switch_cause_counts"))
    rollup["layer2_canonical_id_switch_cause_counts_after_object_merge"] = aggregate_counter(scene_summaries, ("layer2", "canonical_id_switch_cause_counts_after_object_merge"))
    rollup["duograph_object_monitor"] = aggregate_object_monitor(scene_summaries, "duograph_object_monitor")
    rollup["conceptgraphs_baseline_object_monitor"] = aggregate_object_monitor(scene_summaries, "conceptgraphs_baseline_object_monitor")

    summary = {
        "protocol": "GT-aware layer monitor for DuoGraph3D over ConceptGraphs GSA detections; GT target is semantic class + 1m GT cell proxy, not true instance id.",
        "parameters": {
            "profile": PROFILE,
            "voxel_size": VOXEL_SIZE,
            "gt_target_voxel_size": GT_TARGET_VOXEL_SIZE,
            "min_mask_pixels": MIN_MASK_PIXELS,
            "mask_conf_threshold": MASK_CONF_THRESHOLD,
            "max_bbox_area_ratio": MAX_BBOX_AREA_RATIO,
            "min_valid_depth_points": MIN_VALID_DEPTH_POINTS,
            "max_points_per_obs": MAX_POINTS_PER_OBS,
            "apply_mask_subtract_contained": APPLY_MASK_SUBTRACT_CONTAINED,
            "class_agnostic_identity": CLASS_AGNOSTIC_IDENTITY,
            "export_min_detections": EXPORT_MIN_DETECTIONS,
            "baseline_pred_exp_name": BASELINE_PRED_EXP_NAME,
            "duograph_pred_exp_name": DUOGRAPH_PRED_EXP_NAME,
            "clip_probability_logit_scale": round(logit_scale, 6),
            "excluded_eval_classes": sorted(exclude_names),
            "pipeline_gate_overrides": PIPELINE_GATE_OVERRIDES,
        },
        "rollup": rollup,
        "scenes": scene_summaries,
    }
    write_json(to_builtin(summary), ROOT / "gt_layer_monitor_summary.json")
    lines = [
        "# GT-aware layer monitor",
        "",
        "GT target = semantic class + 1m GT cell proxy. It separates SAM/init duplication, Layer1 post-repair duplication, and Layer2 ID behavior; it is not a true instance-ID metric because the available Replica semantic map is semantic-label based.",
        "",
        "## Rollup",
        "",
        f"- valid eval observations: {rollup['valid_eval_observations']}",
        f"- Layer1 eval hypotheses: {rollup['layer1_eval_hypotheses']}",
        f"- Layer2 decision accuracy: {rollup['layer2_decision_accuracy']}",
        f"- Stage target coverage (micro): init {rollup['init_unique_gt_targets']} -> L1 {rollup['layer1_unique_gt_targets']} ({rollup['layer1_coverage_vs_init_micro']}) -> L2 {rollup['layer2_unique_gt_targets']} ({rollup['layer2_coverage_vs_init_micro']})",
        f"- Layer2 duplicate birth rate: {rollup['layer2_duplicate_birth_rate']}",
        f"- Layer2 duplicate birth failure families: {rollup['layer2_duplicate_birth_failure_family_counts']}",
        f"- Layer2 residual absorption: {rollup['layer2_residual_absorption_count']} (accuracy {rollup['layer2_residual_absorption_accuracy']})",
        f"- Layer2 ID switch events: {rollup['layer2_id_switch_events']}",
        f"- DuoGraph3D object monitor: {rollup['duograph_object_monitor']}",
        f"- ConceptGraphs object monitor: {rollup['conceptgraphs_baseline_object_monitor']}",
        "",
        "## Per scene",
        "",
        "| scene | init targets | L1 cov | L2 cov | init dup p50 | layer1 dup p50 | layer1 false merge | layer2 acc | duplicate birth rate | id switch rate | Duo obj count | Duo obj acc | Duo obj dup | CG obj count | CG obj acc | CG obj dup |",
        "| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    for item in scene_summaries:
        duo_obj = item.get("duograph_object_monitor", {})
        cg_obj = item.get("conceptgraphs_baseline_object_monitor", {})
        lines.append(
            f"| {item['scene']} | {int(item['init']['unique_gt_target_count'])} | "
            f"{item['stage_coverage']['layer1_coverage_vs_init']:.3f} | {item['stage_coverage']['layer2_coverage_vs_init']:.3f} | "
            f"{item['init']['per_frame_duplicate_rate'].get('p50', 0):.3f} | "
            f"{item['layer1']['per_frame_duplicate_rate'].get('p50', 0):.3f} | {item['layer1']['false_merge_hypothesis_rate']:.3f} | "
            f"{item['layer2']['decision_accuracy']:.3f} | {item['layer2']['duplicate_birth_rate']:.3f} | "
            f"{item['layer2']['id_switch_rate_per_revisit']:.3f} | "
            f"{int(duo_obj.get('object_count', 0))} | {duo_obj.get('semantic_accuracy', 0):.3f} | "
            f"{duo_obj.get('semantic_cell_duplicates', {}).get('duplicate_rate', 0):.3f} | "
            f"{int(cg_obj.get('object_count', 0))} | {cg_obj.get('semantic_accuracy', 0):.3f} | "
            f"{cg_obj.get('semantic_cell_duplicates', {}).get('duplicate_rate', 0):.3f} |"
        )
    (ROOT / "gt_layer_monitor_report.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(ROOT / "gt_layer_monitor_summary.json", flush=True)
    print(ROOT / "gt_layer_monitor_report.md", flush=True)


if __name__ == "__main__":
    main()
