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
from pathlib import Path
from types import SimpleNamespace
from typing import Iterable

import numpy as np
from PIL import Image
import torch
import open_clip
import open3d as o3d

sys.path.insert(0, "/home/nebula/xxy/DuoGraph3D/src")
sys.path.insert(0, "/home/nebula/xxy/concept-graphs-main")

from duograph3d.contracts import FrameInput, ObjectObservationPayload, Observation, ObservationSupport, PipelineConfig, TemporalVariant
from duograph3d.events import BRANCH_DUOGRAPH3D
from duograph3d.export_policy import GEOMETRY_EXPORT_SOURCE, MEMORY_DENSE_EXPORT_SOURCE, ExportCoveragePolicy, choose_export_source
from duograph3d.io_utils import write_json
from duograph3d.memory import ObjectGraphMemory
from duograph3d.metrics import summarize_run
from duograph3d.pipeline import DuoGraph3DPipeline
from conceptgraph.dataset.replica_constants import REPLICA_CLASSES, REPLICA_EXISTING_CLASSES, REPLICA_SCENE_IDS, REPLICA_SCENE_IDS_
from conceptgraph.scripts.eval_replica_semseg import eval_replica
from conceptgraph.slam.slam_classes import MapObjectList
from conceptgraph.slam.utils import denoise_objects, filter_objects, get_bounding_box, merge_objects, process_pcd
from conceptgraph.utils.ious import mask_subtract_contained
from conceptgraph.utils.eval import compute_metrics

ROOT = Path("/home/nebula/xxy/duograph3d_artifacts/duograph3d_conceptgraphs_engineered_20260426")
REPLICA_ROOT = Path("/home/nebula/xxy/dataset/Replica")
REPLICA_SEMANTIC_ROOT = Path("/home/nebula/xxy/dataset/Replica-semantic")
BASELINE_CSV = Path("/home/nebula/xxy/duograph3d_artifacts/conceptgraphs_replica_official_20260423/replica_ex6_results.csv")
PRED_EXP_NAME = "duograph3d_gsa_engineered_monitor"
FX = 600.0
FY = 600.0
CX = 599.5
CY = 339.5
DEPTH_SCALE = 6553.5
# Class-agnostic identity keys cannot use the old 0.75m semantic-cell bucket:
# without the label dimension it over-groups nearby objects before overlap
# post-processing has a chance to reason over them.  Use a finer geometry cell
# as an online staging key, then let ConceptGraphs-style overlap merge recover
# duplicate fragments.
VOXEL_SIZE = 0.20
MIN_MASK_PIXELS = 300
MAX_POINTS_PER_OBS = 160
MAX_POINTS_PER_OBJECT = 4096
ASSOCIATION_DIAGNOSTICS_TOP_K = 2
SHADOW_UNDERMERGE_DISTANCE_M = 1.25
SHADOW_UNDERMERGE_CLIP_SIM = 0.80
LOW_CLIP_MARGIN = 0.03
LOW_VALID_DEPTH_RATIO = 0.25
MASK_CONF_THRESHOLD = 0.95
MAX_BBOX_AREA_RATIO = 0.50
MIN_VALID_DEPTH_POINTS = 16
MIN_OBJECT_DETECTIONS = 2
EXPORT_SOURCE_STRATEGY = "auto"
MIN_MEMORY_EXPORT_OBJECTS = 100
MIN_MEMORY_EXPORT_KEY_RATIO = 0.10
MIN_MEMORY_EXPORT_POINT_RATIO = 0.05
MEMORY_DENSE_MIN_ROOT_SHARE = 0.60
MEMORY_DENSE_GEOMETRY_FALLBACK = True
CLASS_AGNOSTIC_TOKEN = "item"
EXPORT_SPLIT_BY_LABEL = False
CG_DOWNSAMPLE_VOXEL_SIZE = 0.025
CG_DBSCAN_EPS = 0.1
CG_DBSCAN_MIN_POINTS = 10
CG_MERGE_OVERLAP_THRESH = 0.7
CG_MERGE_VISUAL_SIM_THRESH = 0.8
CG_MERGE_TEXT_SIM_THRESH = 0.8


def normalize_np(arr: np.ndarray) -> np.ndarray:
    arr = np.asarray(arr, dtype=np.float32)
    norm = np.linalg.norm(arr, axis=-1, keepdims=True)
    norm[norm == 0] = 1.0
    return arr / norm


def object_payload_from_arrays(
    *,
    label: str,
    points: np.ndarray,
    colors: np.ndarray,
    centroid: np.ndarray,
    clip_feature: np.ndarray,
    text_feature: np.ndarray,
    mask_area: int,
) -> ObjectObservationPayload:
    return ObjectObservationPayload(
        label=label,
        points_sample=tuple(tuple(float(value) for value in row[:3]) for row in np.asarray(points, dtype=np.float32)),
        colors_sample=tuple(tuple(float(value) for value in row[:3]) for row in np.asarray(colors, dtype=np.float32)),
        bbox_min=tuple(float(value) for value in np.asarray(points, dtype=np.float32).min(axis=0)[:3]),
        bbox_max=tuple(float(value) for value in np.asarray(points, dtype=np.float32).max(axis=0)[:3]),
        centroid=tuple(float(value) for value in np.asarray(centroid, dtype=np.float32)[:3]),
        clip_feature=tuple(float(value) for value in np.asarray(clip_feature, dtype=np.float32).reshape(-1)),
        text_feature=tuple(float(value) for value in np.asarray(text_feature, dtype=np.float32).reshape(-1)),
        mask_area=float(mask_area),
        detection_count=1,
    )


def to_builtin(value):
    if isinstance(value, dict):
        return {str(key): to_builtin(val) for key, val in value.items()}
    if isinstance(value, (list, tuple)):
        return [to_builtin(item) for item in value]
    if isinstance(value, Counter):
        return {str(key): int(val) for key, val in value.items()}
    if isinstance(value, np.ndarray):
        return value.tolist()
    if isinstance(value, (np.integer,)):
        return int(value)
    if isinstance(value, (np.floating,)):
        return float(value)
    if isinstance(value, (np.bool_,)):
        return bool(value)
    return value


def sample_indices(count: int, limit: int) -> np.ndarray:
    if count <= limit:
        return np.arange(count, dtype=np.int64)
    return np.linspace(0, count - 1, num=limit, dtype=np.int64)


def quantile(values: Iterable[float], q: float) -> float:
    data = sorted(float(value) for value in values if value is not None and not math.isnan(float(value)))
    if not data:
        return 0.0
    if len(data) == 1:
        return round(data[0], 6)
    pos = (len(data) - 1) * q
    lower = int(math.floor(pos))
    upper = int(math.ceil(pos))
    if lower == upper:
        return round(data[lower], 6)
    frac = pos - lower
    return round(data[lower] * (1.0 - frac) + data[upper] * frac, 6)


def numeric_summary(values: Iterable[float]) -> dict[str, object]:
    data = [float(value) for value in values if value is not None and not math.isnan(float(value))]
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


def label_entropy(counter: Counter) -> float:
    total = sum(counter.values())
    if total <= 0:
        return 0.0
    entropy = 0.0
    for count in counter.values():
        p = count / total
        entropy -= p * math.log(p + 1e-12, 2)
    return round(entropy, 6)


def bbox_from_points(points: np.ndarray) -> np.ndarray:
    if points.size == 0:
        return np.zeros((8, 3), dtype=np.float32)
    mins = points.min(axis=0)
    maxs = points.max(axis=0)
    return np.asarray([
        [mins[0], mins[1], mins[2]], [mins[0], mins[1], maxs[2]],
        [mins[0], maxs[1], mins[2]], [mins[0], maxs[1], maxs[2]],
        [maxs[0], mins[1], mins[2]], [maxs[0], mins[1], maxs[2]],
        [maxs[0], maxs[1], mins[2]], [maxs[0], maxs[1], maxs[2]],
    ], dtype=np.float32)


def quant_key(scene: str, label: str, centroid: np.ndarray) -> str:
    q = np.floor(centroid / VOXEL_SIZE).astype(int)
    # ConceptGraphs `gsa_variant=none` is effectively class-agnostic during
    # online mapping.  Keep semantics in object feature histograms, not in the
    # identity key, so low-margin CLIP label flips do not split tracks.
    del label
    return f"{scene}:gsa:{CLASS_AGNOSTIC_TOKEN}:{q[0]}:{q[1]}:{q[2]}"


def class_agnostic_text_anchor(dim: int) -> np.ndarray:
    """Stable text feature that mimics ConceptGraphs `none`/`item` detections.

    ConceptGraphs' `gsa_detections_none` stores one text feature for the generic
    `item` class.  Our runner derives Replica-class scores for monitoring, but
    post-merge text similarity should stay class-agnostic; otherwise top-1 CLIP
    label noise would block duplicate-object merges that ConceptGraphs allows.
    """

    anchor = np.zeros(dim, dtype=np.float32)
    anchor[0] = 1.0
    return anchor


def world_points_from_mask_arrays(mask: np.ndarray, depth: np.ndarray, rgb_image: np.ndarray, pose: np.ndarray):
    area = int(mask.sum())
    valid = mask & (depth > 1e-6)
    valid_count = int(valid.sum())
    ys, xs = np.nonzero(valid)
    if len(xs) < MIN_VALID_DEPTH_POINTS:
        return None, None, None, {
            "valid_depth_pixels": valid_count,
            "valid_depth_ratio": round(valid_count / max(area, 1), 6),
        }
    keep = sample_indices(len(xs), MAX_POINTS_PER_OBS)
    xs = xs[keep]
    ys = ys[keep]
    z = depth[ys, xs]
    x = (xs.astype(np.float32) - CX) / FX * z
    y = (ys.astype(np.float32) - CY) / FY * z
    cam = np.stack([x, y, z], axis=1).astype(np.float32)
    world = (cam @ pose[:3, :3].T + pose[:3, 3]).astype(np.float32)
    rgb = rgb_image[ys, xs].astype(np.float32)
    centroid = world.mean(axis=0)
    stats = {
        "valid_depth_pixels": valid_count,
        "valid_depth_ratio": round(valid_count / max(area, 1), 6),
    }
    return world, rgb, centroid, stats


def clip_margin(row: np.ndarray) -> float:
    if row.size < 2:
        return 0.0
    top2 = np.partition(row, -2)[-2:]
    top2.sort()
    return float(top2[-1] - top2[-2])


def prepare_scene(scene: str, class_names: list[str], class_feats_np: np.ndarray):
    t0 = time.time()
    gsa_dir = REPLICA_ROOT / scene / "gsa_detections_none"
    poses = np.loadtxt(REPLICA_ROOT / scene / "traj.txt", dtype=np.float32).reshape(-1, 4, 4)
    text_anchor = class_agnostic_text_anchor(class_feats_np.shape[1]).astype(np.float64)
    online_matching_text_feature = np.asarray((), dtype=np.float32)
    key_data: dict[str, dict[str, object]] = {}
    frames: list[FrameInput] = []
    frame_debug = []
    total_raw_dets = 0
    total_kept = 0
    monitor = {
        "raw_mask_pixels": [],
        "kept_mask_pixels": [],
        "confidence": [],
        "valid_depth_ratio": [],
        "clip_margin": [],
        "top1_similarity": [],
        "frame_observation_counts": [],
        "too_small_mask_count": 0,
        "low_confidence_mask_count": 0,
        "large_bbox_mask_count": 0,
        "too_few_valid_points_count": 0,
        "zero_valid_depth_count": 0,
        "low_clip_margin_count": 0,
        "low_valid_depth_count": 0,
        "mask_pixels_subtracted": 0,
        "label_counts": Counter(),
    }
    for det_path in sorted(gsa_dir.glob("frame*.pkl.gz")):
        frame_stem = det_path.name.split(".")[0]
        frame_idx = int(frame_stem[len("frame"):])
        observations: list[Observation] = []
        depth = np.asarray(Image.open(REPLICA_ROOT / scene / "results" / f"depth{frame_idx:06d}.png"), dtype=np.float32) / DEPTH_SCALE
        rgb_image = np.asarray(Image.open(REPLICA_ROOT / scene / "results" / f"frame{frame_idx:06d}.jpg").convert("RGB"), dtype=np.float32) / 255.0
        pose = poses[frame_idx]
        with gzip.open(det_path, "rb") as handle:
            det = pickle.load(handle)
        image_feats = normalize_np(det["image_feats"].astype(np.float32))
        sims = image_feats @ class_feats_np.T
        label_idx = sims.argmax(axis=1)
        masks = np.asarray(det["mask"]).astype(bool)
        xyxy = np.asarray(det.get("xyxy", np.zeros((len(masks), 4), dtype=np.float32)))
        if len(masks) and len(xyxy) == len(masks):
            before_pixels = int(masks.sum())
            masks = mask_subtract_contained(xyxy, masks).astype(bool)
            monitor["mask_pixels_subtracted"] += max(before_pixels - int(masks.sum()), 0)
        confidences = det.get("confidence", np.ones(len(masks), dtype=np.float32))
        total_raw_dets += int(len(masks))
        for det_i, class_i in enumerate(label_idx):
            mask = masks[det_i]
            area = int(mask.sum())
            monitor["raw_mask_pixels"].append(area)
            if area < MIN_MASK_PIXELS:
                monitor["too_small_mask_count"] += 1
                continue
            raw_conf = float(confidences[det_i])
            if raw_conf < MASK_CONF_THRESHOLD:
                monitor["low_confidence_mask_count"] += 1
                continue
            if len(xyxy) == len(masks):
                x1, y1, x2, y2 = [float(value) for value in xyxy[det_i]]
                bbox_area = max(x2 - x1, 0.0) * max(y2 - y1, 0.0)
                if bbox_area > MAX_BBOX_AREA_RATIO * float(rgb_image.shape[0] * rgb_image.shape[1]):
                    monitor["large_bbox_mask_count"] += 1
                    continue
            world, colors, centroid, projection_stats = world_points_from_mask_arrays(mask, depth, rgb_image, pose)
            if world is None:
                if int(projection_stats.get("valid_depth_pixels", 0)) == 0:
                    monitor["zero_valid_depth_count"] += 1
                else:
                    monitor["too_few_valid_points_count"] += 1
                continue
            valid_ratio = float(projection_stats["valid_depth_ratio"])
            margin = clip_margin(sims[det_i])
            top1 = float(sims[det_i, int(class_i)])
            if margin < LOW_CLIP_MARGIN:
                monitor["low_clip_margin_count"] += 1
            if valid_ratio < LOW_VALID_DEPTH_RATIO:
                monitor["low_valid_depth_count"] += 1
            label = class_names[int(class_i)]
            key = quant_key(scene, label, centroid)
            conf = float(np.clip(raw_conf, 0.0, 1.0))
            support_size = round(area / 1_000_000.0, 4)
            depth_scale = round(float(np.linalg.norm(centroid)), 4)
            geometry_support = round(min(max(area / 200000.0, 0.2), 1.5), 4)
            obs_id = f"{frame_stem}:gsa-{det_i:03d}"
            observations.append(Observation(
                observation_id=obs_id,
                descriptor=f"{scene}:{CLASS_AGNOSTIC_TOKEN}",
                geometry_key=key,
                confidence=conf,
                repair_group_id=key,
                support_tokens=(frame_stem, label, key),
                    support=ObservationSupport(
                        proposal_id=obs_id,
                        frame_token=frame_stem,
                        source_kind="conceptgraphs_gsa_none_engineered",
                    support_size=support_size,
                    depth_scale=depth_scale,
                    appearance_key=label,
                        continuity_key=key,
                        geometry_support=geometry_support,
                    ),
                    object_payload=object_payload_from_arrays(
                        label=label,
                        points=world,
                        colors=colors,
                        centroid=centroid,
                        clip_feature=image_feats[det_i],
                        text_feature=online_matching_text_feature,
                        mask_area=area,
                    ),
                ))
            bucket = key_data.setdefault(key, {
                "label_counts": Counter(),
                "clip_sum": np.zeros_like(class_feats_np[0], dtype=np.float64),
                "text_sum": np.zeros_like(class_feats_np[0], dtype=np.float64),
                "feature_count": 0,
                "points": [],
                "colors": [],
                "mask_pixels": 0,
                "confidence_sum": 0.0,
                "centroid_sum": np.zeros(3, dtype=np.float64),
                "valid_depth_ratio_sum": 0.0,
                "clip_margin_sum": 0.0,
                "label_buckets": {},
            })
            bucket["label_counts"][label] += 1
            bucket["clip_sum"] += image_feats[det_i].astype(np.float64)
            bucket["text_sum"] += text_anchor
            bucket["feature_count"] += 1
            bucket["points"].append(world)
            bucket["colors"].append(colors)
            bucket["mask_pixels"] += area
            bucket["confidence_sum"] += conf
            bucket["centroid_sum"] += centroid.astype(np.float64)
            bucket["valid_depth_ratio_sum"] += valid_ratio
            bucket["clip_margin_sum"] += margin
            label_bucket = bucket["label_buckets"].setdefault(label, {
                "label_counts": Counter(),
                "clip_sum": np.zeros_like(class_feats_np[0], dtype=np.float64),
                "text_sum": np.zeros_like(class_feats_np[0], dtype=np.float64),
                "feature_count": 0,
                "points": [],
                "colors": [],
                "mask_pixels": 0,
                "confidence_sum": 0.0,
                "centroid_sum": np.zeros(3, dtype=np.float64),
                "valid_depth_ratio_sum": 0.0,
                "clip_margin_sum": 0.0,
            })
            label_bucket["label_counts"][label] += 1
            label_bucket["clip_sum"] += image_feats[det_i].astype(np.float64)
            label_bucket["text_sum"] += text_anchor
            label_bucket["feature_count"] += 1
            label_bucket["points"].append(world)
            label_bucket["colors"].append(colors)
            label_bucket["mask_pixels"] += area
            label_bucket["confidence_sum"] += conf
            label_bucket["centroid_sum"] += centroid.astype(np.float64)
            label_bucket["valid_depth_ratio_sum"] += valid_ratio
            label_bucket["clip_margin_sum"] += margin
            monitor["kept_mask_pixels"].append(area)
            monitor["confidence"].append(conf)
            monitor["valid_depth_ratio"].append(valid_ratio)
            monitor["clip_margin"].append(margin)
            monitor["top1_similarity"].append(top1)
            monitor["label_counts"][label] += 1
            total_kept += 1
        frames.append(FrameInput(frame_id=f"replica-{scene}-{frame_idx:06d}", observations=observations))
        monitor["frame_observation_counts"].append(len(observations))
        frame_debug.append({"frame": frame_stem, "observations": len(observations)})
    obs_per_key = [int(data["feature_count"]) for data in key_data.values()]
    entropy_by_key = [label_entropy(data["label_counts"]) for data in key_data.values()]
    prep_monitor = {
        "mask_pixels_raw": numeric_summary(monitor["raw_mask_pixels"]),
        "mask_pixels_kept": numeric_summary(monitor["kept_mask_pixels"]),
        "confidence": numeric_summary(monitor["confidence"]),
        "valid_depth_ratio": numeric_summary(monitor["valid_depth_ratio"]),
        "clip_margin": numeric_summary(monitor["clip_margin"]),
        "top1_similarity": numeric_summary(monitor["top1_similarity"]),
        "observations_per_frame": numeric_summary(monitor["frame_observation_counts"]),
        "observations_per_key": numeric_summary(obs_per_key),
        "label_entropy_per_key": numeric_summary(entropy_by_key),
        "too_small_mask_count": int(monitor["too_small_mask_count"]),
        "low_confidence_mask_count": int(monitor["low_confidence_mask_count"]),
        "large_bbox_mask_count": int(monitor["large_bbox_mask_count"]),
        "too_few_valid_points_count": int(monitor["too_few_valid_points_count"]),
        "zero_valid_depth_count": int(monitor["zero_valid_depth_count"]),
        "low_clip_margin_count": int(monitor["low_clip_margin_count"]),
        "low_clip_margin_rate": round(int(monitor["low_clip_margin_count"]) / max(total_kept, 1), 6),
        "low_valid_depth_count": int(monitor["low_valid_depth_count"]),
        "low_valid_depth_rate": round(int(monitor["low_valid_depth_count"]) / max(total_kept, 1), 6),
        "mask_pixels_subtracted": int(monitor["mask_pixels_subtracted"]),
        "singleton_key_count": sum(1 for value in obs_per_key if value == 1),
        "singleton_key_rate": round(sum(1 for value in obs_per_key if value == 1) / max(len(obs_per_key), 1), 6),
        "top_labels": monitor["label_counts"].most_common(15),
    }
    prep = {
        "scene": scene,
        "frame_count": len(frames),
        "frames_with_observations": sum(1 for frame in frames if frame.observations),
        "raw_detection_count": total_raw_dets,
        "kept_observation_count": total_kept,
        "key_count": len(key_data),
        "seconds": round(time.time() - t0, 3),
        "parameters": {
            "voxel_size": VOXEL_SIZE,
            "min_mask_pixels": MIN_MASK_PIXELS,
            "mask_conf_threshold": MASK_CONF_THRESHOLD,
            "max_bbox_area_ratio": MAX_BBOX_AREA_RATIO,
            "min_valid_depth_points": MIN_VALID_DEPTH_POINTS,
            "class_agnostic_identity_token": CLASS_AGNOSTIC_TOKEN,
            "max_points_per_obs": MAX_POINTS_PER_OBS,
            "max_points_per_object": MAX_POINTS_PER_OBJECT,
            "temporal_variant": TemporalVariant.NAIVE_FRAMEWISE.value,
        },
        "monitor": prep_monitor,
    }
    return frames, key_data, prep, frame_debug


def summarize_association_diagnostics(logger) -> dict[str, object]:
    candidate_records = logger.filter(event_type="association_candidate_diagnostic")
    birth_records = logger.filter(event_type="association_birth_diagnostic")
    best_scores = []
    margins = []
    candidate_counts = []
    best_relation_bonuses = []
    component_values: dict[str, list[float]] = defaultdict(list)
    no_candidate_count = 0
    no_strong_identity_best_count = 0
    below_threshold_best_count = 0
    for record in candidate_records:
        payload = record.payload
        candidate_count = int(payload.get("candidate_count") or 0)
        candidate_counts.append(candidate_count)
        if candidate_count == 0:
            no_candidate_count += 1
        if payload.get("best_score") is not None:
            best_score = float(payload["best_score"])
            best_scores.append(best_score)
            if not bool(payload.get("best_has_strong_identity")):
                no_strong_identity_best_count += 1
            elif best_score < float(payload.get("threshold") or 0.0):
                below_threshold_best_count += 1
        if payload.get("score_margin") is not None:
            margins.append(float(payload["score_margin"]))
        top_candidates = payload.get("top_candidates") or []
        if top_candidates:
            best_candidate = top_candidates[0]
            best_relation_bonuses.append(float(best_candidate.get("relation_bonus") or 0.0))
            for key, value in (best_candidate.get("components") or {}).items():
                component_values[str(key)].append(float(value or 0.0))
    birth_reason_counts = Counter(str(record.payload.get("reason", "unknown")) for record in birth_records)
    return {
        "candidate_event_count": len(candidate_records),
        "birth_diagnostic_event_count": len(birth_records),
        "candidate_count": numeric_summary(candidate_counts),
        "candidate_events_without_candidate": no_candidate_count,
        "candidate_events_without_strong_identity_best": no_strong_identity_best_count,
        "candidate_events_below_threshold_best": below_threshold_best_count,
        "best_score": numeric_summary(best_scores),
        "score_margin": numeric_summary(margins),
        "best_relation_bonus": numeric_summary(best_relation_bonuses),
        "best_candidate_component_means": {
            key: round(sum(values) / len(values), 6)
            for key, values in sorted(component_values.items())
            if values
        },
        "birth_reasons": dict(birth_reason_counts),
    }


def run_duograph(scene: str, frames: list[FrameInput]):
    t0 = time.time()
    config = PipelineConfig(
        emit_association_diagnostics=True,
        association_diagnostics_top_k=ASSOCIATION_DIAGNOSTICS_TOP_K,
    )
    result, logger = DuoGraph3DPipeline(config).run_sequence(
        sequence_id=f"replica-{scene}-conceptgraphs-gsa-monitor",
        frames=frames,
        temporal_variant=TemporalVariant.NAIVE_FRAMEWISE,
        branch_id=BRANCH_DUOGRAPH3D,
    )
    summary = summarize_run(result, logger)
    summary["temporal_variant"] = TemporalVariant.NAIVE_FRAMEWISE.value
    summary["seconds"] = round(time.time() - t0, 3)
    summary["association_diagnostics"] = summarize_association_diagnostics(logger)
    return result, logger, summary


def write_report(scene: str, prep: dict, branch_summary: dict, logger) -> Path:
    outdir = ROOT / "reports" / scene
    outdir.mkdir(parents=True, exist_ok=True)
    diagnostic_sample = []
    for record in logger.records:
        if record.event_type in {"association_candidate_diagnostic", "association_birth_diagnostic", "memory_relation_update", "memory_object_consolidation"}:
            diagnostic_sample.append({
                "sequence_id": record.sequence_id,
                "step_id": record.step_id,
                "branch_id": record.branch_id,
                "event_type": record.event_type,
                "owner_component": record.owner_component,
                "payload": record.payload,
            })
        if len(diagnostic_sample) >= 200:
            break
    event_path = outdir / f"diagnostic_event_sample_replica_{scene}_duograph3d_full.json"
    write_json(to_builtin(diagnostic_sample), event_path)
    report = {
        "dataset": "replica",
        "scene": scene,
        "frame_count": prep["frame_count"],
        "frames_with_observations": prep["frames_with_observations"],
        "drop_mode": "none",
        "source_paths": [str(REPLICA_ROOT / scene), str(REPLICA_ROOT / scene / "gsa_detections_none")],
        "issues": [],
        "scene_metadata": {
            "observation_mode": "conceptgraphs_official_gsa_detections_none",
            "voxel_size": VOXEL_SIZE,
            "min_mask_pixels": MIN_MASK_PIXELS,
            "mask_conf_threshold": MASK_CONF_THRESHOLD,
            "max_bbox_area_ratio": MAX_BBOX_AREA_RATIO,
            "min_valid_depth_points": MIN_VALID_DEPTH_POINTS,
            "class_agnostic_identity_token": CLASS_AGNOSTIC_TOKEN,
            "max_points_per_obs": MAX_POINTS_PER_OBS,
            "max_points_per_object": MAX_POINTS_PER_OBJECT,
            "temporal_variant": TemporalVariant.NAIVE_FRAMEWISE.value,
            "association_diagnostics_top_k": ASSOCIATION_DIAGNOSTICS_TOP_K,
        },
        "preparation_monitor": prep.get("monitor", {}),
        "branches": {BRANCH_DUOGRAPH3D: branch_summary},
        "branch_event_files": {BRANCH_DUOGRAPH3D: str(event_path)},
    }
    path = outdir / f"bounded_slice_replica_{scene}.json"
    write_json(to_builtin(report), path)
    return path


def average_feature(data: dict[str, object], key: str) -> np.ndarray:
    count = max(int(data["feature_count"]), 1)
    return normalize_np((data[key] / count).reshape(1, -1))[0].astype(np.float32)


def centroid_of_key(data: dict[str, object]) -> np.ndarray:
    count = max(int(data["feature_count"]), 1)
    return (data["centroid_sum"] / count).astype(np.float32)


def conceptgraphs_postprocess_cfg():
    return SimpleNamespace(
        spatial_sim_type="overlap",
        downsample_voxel_size=CG_DOWNSAMPLE_VOXEL_SIZE,
        dbscan_remove_noise=True,
        dbscan_eps=CG_DBSCAN_EPS,
        dbscan_min_points=CG_DBSCAN_MIN_POINTS,
        obj_min_points=0,
        obj_min_detections=MIN_OBJECT_DETECTIONS,
        merge_overlap_thresh=CG_MERGE_OVERLAP_THRESH,
        merge_visual_sim_thresh=CG_MERGE_VISUAL_SIM_THRESH,
        merge_text_sim_thresh=CG_MERGE_TEXT_SIM_THRESH,
        device="cuda" if torch.cuda.is_available() else "cpu",
    )


def make_open3d_pcd(points: np.ndarray, colors: np.ndarray) -> o3d.geometry.PointCloud:
    pcd = o3d.geometry.PointCloud()
    pcd.points = o3d.utility.Vector3dVector(np.asarray(points, dtype=np.float64))
    pcd.colors = o3d.utility.Vector3dVector(np.asarray(colors, dtype=np.float64))
    return pcd


def cap_object_points(objects: MapObjectList, cfg) -> None:
    for obj in objects:
        pts = np.asarray(obj["pcd"].points)
        cols = np.asarray(obj["pcd"].colors)
        if len(pts) <= MAX_POINTS_PER_OBJECT:
            continue
        keep = sample_indices(len(pts), MAX_POINTS_PER_OBJECT)
        obj["pcd"] = make_open3d_pcd(pts[keep], cols[keep])
        obj["bbox"] = get_bounding_box(cfg, obj["pcd"])


def iter_key_export_items(
    key_data: dict[str, dict[str, object]],
) -> list[tuple[str, str, dict[str, object], str]]:
    export_items: list[tuple[str, str, dict[str, object], str]] = []
    for key, data in sorted(key_data.items()):
        label_buckets = data.get("label_buckets") or {}
        if EXPORT_SPLIT_BY_LABEL and label_buckets:
            for label, label_data in sorted(label_buckets.items()):
                export_items.append((key, f"{key}:label:{label}", label_data, str(label)))
        else:
            label = str(data["label_counts"].most_common(1)[0][0])
            export_items.append((key, key, data, label))
    return export_items


def estimate_key_point_budget(key_data: dict[str, dict[str, object]]) -> int:
    """Estimate dense geometry points available before ConceptGraphs postprocess."""

    total = 0
    for _base_key, _export_key, data, _label in iter_key_export_items(key_data):
        point_count = sum(len(chunk) for chunk in data.get("points", []))
        if point_count < 4:
            continue
        total += min(point_count, MAX_POINTS_PER_OBJECT * 2)
    return int(total)


def build_initial_map_objects(
    key_data: dict[str, dict[str, object]],
    track_assignments: dict[str, list[str]],
    label_to_index: dict[str, int],
) -> tuple[MapObjectList, list[dict[str, object]], list[str]]:
    cfg = conceptgraphs_postprocess_cfg()
    objects = MapObjectList()
    export_debug = []
    skipped_keys = []
    export_items = iter_key_export_items(key_data)

    for base_key, export_key, data, label in export_items:
        pts_chunks = data["points"]
        col_chunks = data["colors"]
        if not pts_chunks:
            skipped_keys.append(export_key)
            continue
        pts = np.concatenate(pts_chunks, axis=0).astype(np.float32)
        cols = np.concatenate(col_chunks, axis=0).astype(np.float32)
        if len(pts) < 4:
            skipped_keys.append(export_key)
            continue
        # Keep more geometry than the old runner for overlap matching, but cap
        # before Open3D post-processing so final merge stays tractable.
        pre_keep = sample_indices(len(pts), MAX_POINTS_PER_OBJECT * 2)
        pts = pts[pre_keep]
        cols = cols[pre_keep]
        pcd_original = make_open3d_pcd(pts, cols)
        pcd = process_pcd(pcd_original, cfg, run_dbscan=True)
        if len(pcd.points) < 4:
            pcd = pcd_original
        if len(pcd.points) < 4:
            skipped_keys.append(export_key)
            continue
        count = max(int(data["feature_count"]), 1)
        clip_ft = average_feature(data, "clip_sum")
        text_ft = average_feature(data, "text_sum")
        conf = float(data["confidence_sum"] / count)
        object_ids = track_assignments.get(base_key, [])
        obj = {
            "image_idx": [],
            "mask_idx": [],
            "color_path": [],
            "class_name": [label],
            "class_id": [int(label_to_index.get(label, -1))],
            "num_detections": count,
            "conf": [conf],
            "n_points": [len(pcd.points)],
            "pixel_area": [int(data["mask_pixels"])],
            "contain_number": [None],
            "source_key": [export_key],
            "base_geometry_key": [base_key],
            "source_object_id": list(object_ids),
            "inst_color": np.random.rand(3),
            "is_background": [False],
            "pcd": pcd,
            "bbox": get_bounding_box(cfg, pcd),
            "clip_ft": torch.from_numpy(clip_ft.astype(np.float32)),
            "text_ft": torch.from_numpy(text_ft.astype(np.float32)),
        }
        objects.append(obj)
        export_debug.append({
            "track_hint": export_key,
            "base_geometry_key": base_key,
            "object_ids": list(object_ids),
            "label": label,
            "num_detections": count,
            "point_count_before_postprocess": int(len(pts)),
            "point_count_after_key_denoise": int(len(pcd.points)),
            "fragment_object_count": len(object_ids),
            "mask_pixels": int(data["mask_pixels"]),
            "avg_valid_depth_ratio": round(float(data["valid_depth_ratio_sum"] / count), 6),
            "avg_clip_margin": round(float(data["clip_margin_sum"] / count), 6),
        })
    return objects, export_debug, skipped_keys


def build_memory_map_objects(result, label_to_index: dict[str, int], class_feats_np: np.ndarray):
    cfg = conceptgraphs_postprocess_cfg()
    objects = MapObjectList()
    export_debug = []
    skipped = []
    for object_id, node in sorted(result.memory_nodes.items()):
        skip_reason = ObjectGraphMemory.export_skip_reason(
            node,
            min_points=4,
            min_detections=MIN_OBJECT_DETECTIONS,
        )
        if skip_reason:
            skipped.append(f"{object_id}:{skip_reason}")
            continue
        points = np.asarray(node.sampled_points, dtype=np.float32)
        colors = np.asarray(node.sampled_colors, dtype=np.float32)
        if colors.shape != points.shape:
            colors = np.zeros_like(points)
        if len(points) > MAX_POINTS_PER_OBJECT:
            keep = sample_indices(len(points), MAX_POINTS_PER_OBJECT)
            points = points[keep]
            colors = colors[keep]
        label = ObjectGraphMemory.dominant_semantic_label(node) or node.appearance_key_recent or node.descriptor_recent
        label_index = int(label_to_index.get(label, -1))
        text_ft = np.asarray(node.text_feature, dtype=np.float32)
        if text_ft.shape != class_feats_np[0].shape:
            if label_index >= 0:
                text_ft = class_feats_np[label_index].astype(np.float32)
            else:
                text_ft = np.zeros_like(class_feats_np[0], dtype=np.float32)
        clip_ft = np.asarray(node.clip_feature, dtype=np.float32)
        if clip_ft.shape != text_ft.shape:
            clip_ft = text_ft
        clip_ft = normalize_np(clip_ft.reshape(1, -1))[0].astype(np.float32)
        text_ft = normalize_np(text_ft.reshape(1, -1))[0].astype(np.float32)
        pcd_original = make_open3d_pcd(points, colors)
        pcd = process_pcd(pcd_original, cfg, run_dbscan=True)
        if len(pcd.points) < 4:
            pcd = pcd_original
        obj = {
            "image_idx": [],
            "mask_idx": [],
            "color_path": [],
            "class_name": [label],
            "class_id": [label_index],
            "num_detections": max(int(node.detection_count), 1),
            "conf": [float(node.confidence_sum / max(node.detection_count, 1)) if node.detection_count else 0.0],
            "n_points": [len(pcd.points)],
            "pixel_area": [int(node.mask_area_sum)],
            "contain_number": [None],
            "source_key": [object_id],
            "base_geometry_key": [node.geometry_key],
            "source_object_id": [object_id],
            "inst_color": np.random.rand(3),
            "is_background": [False],
            "pcd": pcd,
            "bbox": get_bounding_box(cfg, pcd),
            "clip_ft": torch.from_numpy(clip_ft),
            "text_ft": torch.from_numpy(text_ft),
        }
        objects.append(obj)
        export_debug.append({
            "track_hint": object_id,
            "base_geometry_key": node.geometry_key,
            "object_ids": [object_id],
            "label": label,
            "num_detections": max(int(node.detection_count), 1),
            "point_count_before_postprocess": int(len(points)),
            "point_count_after_key_denoise": int(len(pcd.points)),
            "fragment_object_count": 1,
            "mask_pixels": int(node.mask_area_sum),
            "source": "online_memory_node",
        })
    return objects, export_debug, skipped


def resolve_memory_root(object_id: str, memory_nodes: dict[str, object]) -> str:
    """Follow merge aliases so retired duplicate nodes still export through root."""

    current = str(object_id or "")
    seen: set[str] = set()
    while current and current in memory_nodes and current not in seen:
        seen.add(current)
        target = str(getattr(memory_nodes[current], "merge_target_id", "") or "")
        if not target:
            return current
        current = target
    return current if current in memory_nodes else ""


def dominant_memory_root_for_key(
    base_key: str,
    track_assignments: dict[str, object],
    memory_nodes: dict[str, object],
) -> tuple[str, dict[str, object]]:
    raw_assignment = track_assignments.get(base_key) or {}
    if isinstance(raw_assignment, dict):
        raw_counts = Counter({str(object_id): int(count) for object_id, count in raw_assignment.items() if str(object_id)})
    else:
        raw_counts = Counter(str(object_id) for object_id in raw_assignment if str(object_id))
    root_counts: Counter[str] = Counter()
    for object_id, count in raw_counts.items():
        root_id = resolve_memory_root(object_id, memory_nodes)
        if root_id:
            root_counts[root_id] += max(int(count), 1)
    if not root_counts:
        return "", {
            "base_geometry_key": base_key,
            "assigned_object_counts": dict(raw_counts),
            "resolved_root_counts": {},
            "assignment_status": "no_memory_assignment",
        }
    ranked_roots = sorted(
        root_counts,
        key=lambda root_id: (
            -root_counts[root_id],
            -int(getattr(memory_nodes[root_id], "detection_count", 0) or 0),
            -int(getattr(memory_nodes[root_id], "last_seen_step", 0) or 0),
            str(root_id),
        ),
    )
    root_id = ranked_roots[0]
    root_total = max(sum(root_counts.values()), 1)
    return root_id, {
        "base_geometry_key": base_key,
        "assigned_object_counts": dict(raw_counts),
        "resolved_root_counts": dict(root_counts),
        "selected_root_id": root_id,
        "selected_root_share": round(root_counts[root_id] / root_total, 6),
        "assignment_status": "ambiguous_memory_assignment" if len(root_counts) > 1 else "single_memory_assignment",
    }


def build_memory_dense_map_objects(
    result,
    key_data: dict[str, dict[str, object]],
    track_assignments: dict[str, object],
    label_to_index: dict[str, int],
) -> tuple[MapObjectList, list[dict[str, object]], list[str], dict[str, object]]:
    """Export online memory IDs with dense ConceptGraphs-style geometry.

    The online memory node is the object authority, but its `sampled_points` are
    intentionally capped for matching speed.  For official mIoU, reuse the dense
    per-geometry-key points staged from GSA masks and group those keys by the
    memory root selected by Layer2/merge aliases.
    """

    cfg = conceptgraphs_postprocess_cfg()
    root_buckets: dict[str, dict[str, object]] = {}
    skipped: list[str] = []
    assignment_status_counts: Counter[str] = Counter()
    raw_assignment_status_counts: Counter[str] = Counter()
    root_share_values = []
    ambiguous_examples = []
    export_items = iter_key_export_items(key_data)
    for base_key, export_key, data, label in export_items:
        root_id, assignment_debug = dominant_memory_root_for_key(base_key, track_assignments, result.memory_nodes)
        status = str(assignment_debug["assignment_status"])
        selected_root_share = float(assignment_debug.get("selected_root_share", 0.0) or 0.0)
        if selected_root_share > 0.0:
            root_share_values.append(selected_root_share)
        raw_assignment_status_counts[status] += 1
        if status == "ambiguous_memory_assignment" and len(ambiguous_examples) < 20:
            ambiguous_examples.append(assignment_debug)
        use_geometry_fallback = False
        if MEMORY_DENSE_GEOMETRY_FALLBACK and not root_id:
            use_geometry_fallback = True
            status = "unassigned_geometry_fallback"
        elif (
            MEMORY_DENSE_GEOMETRY_FALLBACK
            and status == "ambiguous_memory_assignment"
            and selected_root_share < MEMORY_DENSE_MIN_ROOT_SHARE
        ):
            use_geometry_fallback = True
            status = "ambiguous_geometry_fallback"
        assignment_status_counts[status] += 1
        if not root_id and not use_geometry_fallback:
            skipped.append(f"{export_key}:no_memory_assignment")
            continue
        node = result.memory_nodes.get(root_id) if root_id else None
        if not use_geometry_fallback:
            if node is None:
                skipped.append(f"{export_key}:missing_memory_root")
                continue
            skip_reason = ObjectGraphMemory.export_skip_reason(
                node,
                min_points=0,
                min_detections=MIN_OBJECT_DETECTIONS,
            )
            if skip_reason:
                skipped.append(f"{export_key}:{skip_reason}")
                continue
        bucket_id = f"geometry:{export_key}" if use_geometry_fallback else root_id
        bucket = root_buckets.setdefault(
            bucket_id,
            {
                "label_counts": Counter(),
                "clip_sum": np.zeros_like(np.asarray(data["clip_sum"], dtype=np.float64), dtype=np.float64),
                "text_sum": np.zeros_like(np.asarray(data["text_sum"], dtype=np.float64), dtype=np.float64),
                "feature_count": 0,
                "points": [],
                "colors": [],
                "mask_pixels": 0,
                "confidence_sum": 0.0,
                "valid_depth_ratio_sum": 0.0,
                "clip_margin_sum": 0.0,
                "geometry_keys": set(),
                "export_keys": [],
                "memory_root_ids": set(),
                "source_types": Counter(),
                "assignment_status_counts": Counter(),
            },
        )
        bucket["label_counts"].update(data["label_counts"])
        bucket["clip_sum"] += np.asarray(data["clip_sum"], dtype=np.float64)
        bucket["text_sum"] += np.asarray(data["text_sum"], dtype=np.float64)
        bucket["feature_count"] += int(data["feature_count"])
        bucket["points"].extend(data["points"])
        bucket["colors"].extend(data["colors"])
        bucket["mask_pixels"] += int(data["mask_pixels"])
        bucket["confidence_sum"] += float(data["confidence_sum"])
        bucket["valid_depth_ratio_sum"] += float(data["valid_depth_ratio_sum"])
        bucket["clip_margin_sum"] += float(data["clip_margin_sum"])
        bucket["geometry_keys"].add(base_key)
        bucket["export_keys"].append(export_key)
        if root_id:
            bucket["memory_root_ids"].add(root_id)
        bucket["source_types"]["geometry_fallback" if use_geometry_fallback else "memory_root"] += 1
        bucket["assignment_status_counts"][status] += 1

    objects = MapObjectList()
    export_debug = []
    for bucket_id, data in sorted(root_buckets.items()):
        pts_chunks = data["points"]
        col_chunks = data["colors"]
        if not pts_chunks:
            skipped.append(f"{bucket_id}:no_dense_points")
            continue
        pts = np.concatenate(pts_chunks, axis=0).astype(np.float32)
        cols = np.concatenate(col_chunks, axis=0).astype(np.float32)
        if len(pts) < 4:
            skipped.append(f"{bucket_id}:too_few_dense_points")
            continue
        pre_keep = sample_indices(len(pts), MAX_POINTS_PER_OBJECT * 2)
        pts = pts[pre_keep]
        cols = cols[pre_keep]
        pcd_original = make_open3d_pcd(pts, cols)
        pcd = process_pcd(pcd_original, cfg, run_dbscan=True)
        if len(pcd.points) < 4:
            pcd = pcd_original
        if len(pcd.points) < 4:
            skipped.append(f"{bucket_id}:too_few_postprocess_points")
            continue
        memory_root_ids = sorted(data["memory_root_ids"])
        primary_root_id = memory_root_ids[0] if memory_root_ids else ""
        node = result.memory_nodes.get(primary_root_id) if primary_root_id else None
        label_counts = data["label_counts"]
        label = str(label_counts.most_common(1)[0][0]) if label_counts else (ObjectGraphMemory.dominant_semantic_label(node) if node else "")
        label_index = int(label_to_index.get(label, -1))
        count = max(int(data["feature_count"]), 1)
        clip_ft = normalize_np((data["clip_sum"] / count).reshape(1, -1))[0].astype(np.float32)
        text_ft = normalize_np((data["text_sum"] / count).reshape(1, -1))[0].astype(np.float32)
        geometry_keys = sorted(data["geometry_keys"])
        export_keys = sorted(data["export_keys"])
        conf = float(data["confidence_sum"] / count)
        obj = {
            "image_idx": [],
            "mask_idx": [],
            "color_path": [],
            "class_name": [label],
            "class_id": [label_index],
            "num_detections": count,
            "conf": [conf],
            "n_points": [len(pcd.points)],
            "pixel_area": [int(data["mask_pixels"])],
            "contain_number": [None],
            "source_key": [f"memory:{bucket_id}" if primary_root_id else f"geometry-fallback:{bucket_id}"],
            "base_geometry_key": geometry_keys,
            "source_object_id": memory_root_ids,
            "inst_color": np.random.rand(3),
            "is_background": [False],
            "pcd": pcd,
            "bbox": get_bounding_box(cfg, pcd),
            "clip_ft": torch.from_numpy(clip_ft),
            "text_ft": torch.from_numpy(text_ft),
        }
        objects.append(obj)
        export_debug.append({
            "track_hint": f"memory:{bucket_id}" if primary_root_id else f"geometry-fallback:{bucket_id}",
            "base_geometry_key": geometry_keys,
            "export_keys": export_keys,
            "object_ids": memory_root_ids,
            "label": label,
            "num_detections": count,
            "point_count_before_postprocess": int(len(pts)),
            "point_count_after_key_denoise": int(len(pcd.points)),
            "fragment_object_count": len(geometry_keys),
            "mask_pixels": int(data["mask_pixels"]),
            "avg_valid_depth_ratio": round(float(data["valid_depth_ratio_sum"] / count), 6),
            "avg_clip_margin": round(float(data["clip_margin_sum"] / count), 6),
            "source": "online_memory_dense_geometry",
            "source_types": dict(data["source_types"]),
            "assignment_status_counts": dict(data["assignment_status_counts"]),
            "memory_detection_count": int(getattr(node, "detection_count", 0) or 0) if node else 0,
            "memory_status": str(getattr(getattr(node, "status", ""), "value", getattr(node, "status", ""))) if node else "",
        })
    diagnostics = {
        "candidate_key_object_count": len(export_items),
        "assigned_key_count": sum(1 for item in export_debug for _key in item.get("base_geometry_key", [])),
        "initial_object_count": len(objects),
        "skipped_key_count": len(skipped),
        "assignment_status_counts": dict(assignment_status_counts),
        "raw_assignment_status_counts": dict(raw_assignment_status_counts),
        "selected_root_share": numeric_summary(root_share_values),
        "memory_dense_min_root_share": MEMORY_DENSE_MIN_ROOT_SHARE,
        "memory_dense_geometry_fallback": MEMORY_DENSE_GEOMETRY_FALLBACK,
        "ambiguous_assignment_examples": ambiguous_examples,
    }
    return objects, export_debug, skipped, diagnostics


def point_count_from_export_debug(export_debug: list[dict[str, object]]) -> int:
    return int(sum(int(item.get("point_count_before_postprocess", 0) or 0) for item in export_debug))


def compute_shadow_undermerge(scene: str, key_data: dict[str, dict[str, object]], track_assignments: dict[str, list[str]]) -> dict[str, object]:
    groups: dict[str, list[dict[str, object]]] = defaultdict(list)
    for key, data in key_data.items():
        if int(data["feature_count"]) <= 0:
            continue
        label = str(data["label_counts"].most_common(1)[0][0])
        groups[label].append({
            "key": key,
            "label": label,
            "centroid": centroid_of_key(data),
            "clip": average_feature(data, "clip_sum"),
            "obs_count": int(data["feature_count"]),
            "object_ids": set(track_assignments.get(key, [])),
        })
    pair_count = 0
    by_label = Counter()
    examples = []
    distance_values = []
    clip_values = []
    for label, items in groups.items():
        for left_index in range(len(items)):
            left = items[left_index]
            for right_index in range(left_index + 1, len(items)):
                right = items[right_index]
                if left["object_ids"] and right["object_ids"] and left["object_ids"].intersection(right["object_ids"]):
                    continue
                distance = float(np.linalg.norm(left["centroid"] - right["centroid"]))
                if distance > SHADOW_UNDERMERGE_DISTANCE_M:
                    continue
                clip_sim = float(np.dot(left["clip"], right["clip"]))
                if clip_sim < SHADOW_UNDERMERGE_CLIP_SIM:
                    continue
                pair_count += 1
                by_label[label] += 1
                distance_values.append(distance)
                clip_values.append(clip_sim)
                if len(examples) < 30:
                    examples.append({
                        "left_key": left["key"],
                        "right_key": right["key"],
                        "label": label,
                        "distance_m": round(distance, 4),
                        "clip_sim": round(clip_sim, 4),
                        "left_obs": left["obs_count"],
                        "right_obs": right["obs_count"],
                    })
    return {
        "scene": scene,
        "distance_threshold_m": SHADOW_UNDERMERGE_DISTANCE_M,
        "clip_similarity_threshold": SHADOW_UNDERMERGE_CLIP_SIM,
        "candidate_pair_count": pair_count,
        "candidate_pairs_per_key": round(pair_count / max(len(key_data), 1), 6),
        "distance_m": numeric_summary(distance_values),
        "clip_similarity": numeric_summary(clip_values),
        "top_labels": by_label.most_common(12),
        "examples": examples,
    }


def write_conceptgraphs_payload(
    scene: str,
    result,
    key_data: dict[str, dict[str, object]],
    track_assignments: dict[str, list[str]],
    branch_summary: dict,
    label_to_index: dict[str, int],
    class_feats_np: np.ndarray,
):
    t0 = time.time()
    pcd_dir = REPLICA_ROOT / scene / "pcd_saves"
    pcd_dir.mkdir(parents=True, exist_ok=True)
    cfg = conceptgraphs_postprocess_cfg()

    memory_objects, memory_export_debug, memory_skipped_keys = build_memory_map_objects(result, label_to_index, class_feats_np)
    (
        memory_dense_objects,
        memory_dense_export_debug,
        memory_dense_skipped_keys,
        memory_dense_diagnostics,
    ) = build_memory_dense_map_objects(result, key_data, track_assignments, label_to_index)
    requested_source = str(EXPORT_SOURCE_STRATEGY or "auto").lower().replace("_", "-")
    selection_objects = memory_dense_objects if requested_source == "memory-dense" else memory_objects
    selection_debug = memory_dense_export_debug if requested_source == "memory-dense" else memory_export_debug
    export_policy = ExportCoveragePolicy(
        min_memory_objects=MIN_MEMORY_EXPORT_OBJECTS,
        min_memory_key_ratio=MIN_MEMORY_EXPORT_KEY_RATIO,
        min_memory_point_ratio=MIN_MEMORY_EXPORT_POINT_RATIO,
    )
    export_selection = choose_export_source(
        strategy=EXPORT_SOURCE_STRATEGY,
        memory_object_count=len(selection_objects),
        key_object_count=len(iter_key_export_items(key_data)),
        memory_point_count=point_count_from_export_debug(selection_debug),
        key_point_budget=estimate_key_point_budget(key_data),
        policy=export_policy,
    )
    export_source = str(export_selection["selected_source"])
    if export_source == GEOMETRY_EXPORT_SOURCE:
        initial_objects, export_debug, skipped_keys = build_initial_map_objects(key_data, track_assignments, label_to_index)
    elif export_source == MEMORY_DENSE_EXPORT_SOURCE:
        initial_objects, export_debug, skipped_keys = memory_dense_objects, memory_dense_export_debug, memory_dense_skipped_keys
    else:
        initial_objects, export_debug, skipped_keys = memory_objects, memory_export_debug, memory_skipped_keys
    pre_postprocess_count = len(initial_objects)
    print(
        f"ConceptGraphs-style postprocess before denoise/filter/merge: {pre_postprocess_count} "
        f"(source={export_source}, reason={export_selection['fallback_reason']})",
        flush=True,
    )
    objects = denoise_objects(cfg, initial_objects)
    post_denoise_count = len(objects)
    objects = filter_objects(cfg, objects)
    post_filter_count = len(objects)
    objects = merge_objects(cfg, objects)
    post_merge_count = len(objects)
    cap_object_points(objects, cfg)
    serializable_objects = objects.to_serializable()
    payload = {"objects": serializable_objects, "bg_objects": None}
    result_path = pcd_dir / f"full_pcd_{PRED_EXP_NAME}.pkl.gz"
    with gzip.open(result_path, "wb") as handle:
        pickle.dump(payload, handle)
    point_counts = [int(len(obj["pcd_np"])) for obj in serializable_objects]
    detection_counts = [int(item["num_detections"]) for item in export_debug]
    fragment_counts = [int(item["fragment_object_count"]) for item in export_debug]
    export_monitor = {
        "export_selection": export_selection,
        "memory_export_probe": {
            "initial_object_count": len(memory_objects),
            "skipped_object_count": len(memory_skipped_keys),
            "point_count_before_postprocess": point_count_from_export_debug(memory_export_debug),
            "sample": memory_export_debug[:10],
        },
        "memory_dense_export_probe": {
            **memory_dense_diagnostics,
            "point_count_before_postprocess": point_count_from_export_debug(memory_dense_export_debug),
            "sample": memory_dense_export_debug[:10],
        },
        "geometry_export_probe": {
            "candidate_key_object_count": len(iter_key_export_items(key_data)),
            "estimated_point_budget": estimate_key_point_budget(key_data),
        },
        "initial_key_object_count": pre_postprocess_count,
        "post_denoise_object_count": post_denoise_count,
        "post_filter_object_count": post_filter_count,
        "post_merge_object_count": post_merge_count,
        "skipped_key_count": len(skipped_keys),
        "objects_per_track_key": numeric_summary(fragment_counts),
        "detections_per_exported_object": numeric_summary(detection_counts),
        "points_per_exported_object": numeric_summary(point_counts),
        "fragmented_export_key_count": sum(1 for value in fragment_counts if value > 1),
        "fragmented_export_key_rate": round(sum(1 for value in fragment_counts if value > 1) / max(len(fragment_counts), 1), 6),
        "sample": export_debug[:20],
    }
    proxy = {
        "scene": scene,
        "pred_exp_name": PRED_EXP_NAME,
        "object_count": len(serializable_objects),
        "point_count": int(sum(len(obj["pcd_np"]) for obj in serializable_objects)),
        "source": "duograph3d_over_conceptgraphs_gsa_detections_none_engineered",
        "object_source": export_source,
        "temporal_variant": TemporalVariant.NAIVE_FRAMEWISE.value,
        "readiness": {
            "same_replica_scene_list_as_conceptgraphs": True,
            "same_gsa_detections_as_conceptgraphs": True,
            "same_eval_replica_semseg": True,
            "n_exclude": 6,
        },
    }
    write_json(to_builtin(proxy), pcd_dir / f"{PRED_EXP_NAME}_semantic_proxy.json")
    manifest = {
        "adapter": "conceptgraphs",
        "status": "format_aligned_official_evaluated_monitored",
        "dataset": "replica",
        "scene": scene,
        "branch_id": BRANCH_DUOGRAPH3D,
        "pred_exp_name": PRED_EXP_NAME,
        "object_count": len(serializable_objects),
        "point_count": proxy["point_count"],
        "feature_dim": int(serializable_objects[0]["clip_ft"].shape[0]) if serializable_objects else 0,
        "files": {
            "conceptgraphs_pkl_gz": str(result_path),
            "semantic_proxy_json": str(pcd_dir / f"{PRED_EXP_NAME}_semantic_proxy.json"),
        },
        "export_parameters": {
            "voxel_size": VOXEL_SIZE,
            "min_mask_pixels": MIN_MASK_PIXELS,
            "mask_conf_threshold": MASK_CONF_THRESHOLD,
            "max_bbox_area_ratio": MAX_BBOX_AREA_RATIO,
            "min_valid_depth_points": MIN_VALID_DEPTH_POINTS,
            "min_object_detections": MIN_OBJECT_DETECTIONS,
            "export_source_strategy": EXPORT_SOURCE_STRATEGY,
            "memory_coverage_gate": {
                "min_memory_objects": MIN_MEMORY_EXPORT_OBJECTS,
                "min_memory_key_ratio": MIN_MEMORY_EXPORT_KEY_RATIO,
                "min_memory_point_ratio": MIN_MEMORY_EXPORT_POINT_RATIO,
                "memory_dense_min_root_share": MEMORY_DENSE_MIN_ROOT_SHARE,
                "memory_dense_geometry_fallback": MEMORY_DENSE_GEOMETRY_FALLBACK,
            },
            "max_points_per_obs": MAX_POINTS_PER_OBS,
            "max_points_per_object": MAX_POINTS_PER_OBJECT,
            "export_split_by_label": EXPORT_SPLIT_BY_LABEL,
            "temporal_variant": TemporalVariant.NAIVE_FRAMEWISE.value,
            "fragmentation_policy": (
                "coverage-preserving export: auto uses online memory only when it passes object/key/point coverage gates; "
                "otherwise class-agnostic geometry-key objects are denoised, support-filtered, and overlap-merged "
                "with ConceptGraphs-style post-processing before official mIoU export; memory-dense keeps online memory root IDs "
                "but exports dense key geometry assigned to each root"
            ),
            "conceptgraphs_engineering": {
                "class_agnostic_identity_token": CLASS_AGNOSTIC_TOKEN,
                "export_split_by_label": EXPORT_SPLIT_BY_LABEL,
                "mask_subtract_contained": True,
                "downsample_voxel_size": CG_DOWNSAMPLE_VOXEL_SIZE,
                "dbscan_remove_noise": True,
                "dbscan_eps": CG_DBSCAN_EPS,
                "dbscan_min_points": CG_DBSCAN_MIN_POINTS,
                "merge_overlap_thresh": CG_MERGE_OVERLAP_THRESH,
                "merge_visual_sim_thresh": CG_MERGE_VISUAL_SIM_THRESH,
                "merge_text_sim_thresh": CG_MERGE_TEXT_SIM_THRESH,
            },
        },
        "branch_summary_excerpt": {
            "memory_node_count": branch_summary.get("memory_node_count"),
            "track_fragmentation": branch_summary.get("track_fragmentation"),
            "memory_relation_edge_count": branch_summary.get("memory_relation_edge_count"),
        },
        "export_monitor": export_monitor,
        "object_source": export_source,
        "seconds": round(time.time() - t0, 3),
    }
    write_json(to_builtin(manifest), pcd_dir / f"{PRED_EXP_NAME}_manifest.json")
    return manifest, export_debug, skipped_keys


def metrics_row(scene_id: str, conf_matrix: torch.Tensor, keep_index, class_names: list[str]) -> dict[str, object]:
    cm = conf_matrix[keep_index, :][:, keep_index]
    keep_names = [class_names[int(i)] for i in keep_index]
    md = compute_metrics(cm, keep_names)
    return {
        "scene_id": scene_id,
        "miou": float(md["miou"] * 100.0),
        "mrecall": float(np.mean(md["recall"]) * 100.0),
        "mprecision": float(np.mean(md["precision"]) * 100.0),
        "mf1score": float(np.mean(md["f1score"]) * 100.0),
        "fmiou": float(md["fmiou"] * 100.0),
    }


def load_baseline_rows() -> dict[str, dict[str, str]]:
    with BASELINE_CSV.open() as handle:
        return {row["scene_id"]: row for row in csv.DictReader(handle)}


def add_gap_rows(duograph_rows: list[dict[str, object]], baseline_rows: dict[str, dict[str, str]]) -> list[dict[str, object]]:
    rows = []
    for row in duograph_rows:
        scene_id = str(row["scene_id"])
        baseline = baseline_rows.get(scene_id)
        if not baseline:
            continue
        gap = {"scene_id": scene_id}
        for metric in ["miou", "mrecall", "mprecision", "mf1score", "fmiou"]:
            duograph_value = float(row[metric])
            baseline_value = float(baseline[metric])
            gap[f"duograph_{metric}"] = duograph_value
            gap[f"conceptgraphs_{metric}"] = baseline_value
            gap[f"gap_{metric}"] = duograph_value - baseline_value
        rows.append(gap)
    return rows


def monitor_rollup(scene_debug: list[dict[str, object]], gap_rows: list[dict[str, object]]) -> dict[str, object]:
    prep = [item["prep"] for item in scene_debug]
    branch = [item["duograph_summary"] for item in scene_debug]
    shadows = [item["shadow_undermerge"] for item in scene_debug]
    export_sources = Counter(str(item.get("manifest", {}).get("object_source", "")) for item in scene_debug)
    fallback_reasons = Counter(
        str(item.get("export_monitor", {}).get("export_selection", {}).get("fallback_reason", ""))
        for item in scene_debug
    )
    return {
        "raw_detection_count": sum(int(item["raw_detection_count"]) for item in prep),
        "kept_observation_count": sum(int(item["kept_observation_count"]) for item in prep),
        "key_count": sum(int(item["key_count"]) for item in prep),
        "export_object_count": sum(int(item.get("export_object_count", 0)) for item in scene_debug),
        "export_sources": dict(export_sources),
        "export_fallback_reasons": dict(fallback_reasons),
        "memory_node_count": sum(int(item["memory_node_count"]) for item in branch),
        "track_fragmentation": sum(int(item["track_fragmentation"]) for item in branch),
        "shadow_undermerge_candidate_pairs": sum(int(item["candidate_pair_count"]) for item in shadows),
        "low_clip_margin_count": sum(int(item["monitor"]["low_clip_margin_count"]) for item in prep),
        "low_valid_depth_count": sum(int(item["monitor"]["low_valid_depth_count"]) for item in prep),
        "low_confidence_mask_count": sum(int(item["monitor"].get("low_confidence_mask_count", 0)) for item in prep),
        "large_bbox_mask_count": sum(int(item["monitor"].get("large_bbox_mask_count", 0)) for item in prep),
        "mask_pixels_subtracted": sum(int(item["monitor"].get("mask_pixels_subtracted", 0)) for item in prep),
        "birth_reasons": dict(sum((Counter(item["duograph_summary"]["association_diagnostics"].get("birth_reasons", {})) for item in scene_debug), Counter())),
        "all_gap": next((row for row in gap_rows if row["scene_id"] == "all"), None),
    }


def write_markdown_report(summary: dict[str, object], path: Path) -> None:
    gap_rows = summary.get("gap_rows") or []
    scene_debug = summary.get("scene_debug") or []
    rollup = summary.get("monitor_rollup") or {}
    lines = [
        "# DuoGraph3D × ConceptGraphs engineered parity run",
        "",
        f"- Protocol: {summary['protocol']}",
        f"- Pred exp name: `{summary['pred_exp_name']}`",
        f"- Scenes: {', '.join(summary['scenes'])}",
        f"- Association diagnostics: enabled, top-k={ASSOCIATION_DIAGNOSTICS_TOP_K}",
        "",
        "## Aggregate metrics vs ConceptGraphs",
        "",
        "| scene | ΔmIoU | DuoGraph3D mIoU | ConceptGraphs mIoU | ΔmRecall | ΔmPrecision | ΔF-mIoU |",
        "| --- | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    for row in gap_rows:
        lines.append(
            f"| {row['scene_id']} | {row['gap_miou']:.3f} | {row['duograph_miou']:.3f} | "
            f"{row['conceptgraphs_miou']:.3f} | {row['gap_mrecall']:.3f} | {row['gap_mprecision']:.3f} | {row['gap_fmiou']:.3f} |"
        )
    lines.extend([
        "",
        "## Monitor rollup",
        "",
        f"- raw detections / kept observations / track keys: {rollup.get('raw_detection_count')} / {rollup.get('kept_observation_count')} / {rollup.get('key_count')}",
        f"- memory nodes / track fragmentation: {rollup.get('memory_node_count')} / {rollup.get('track_fragmentation')}",
        f"- exported objects after ConceptGraphs-style postprocess: {rollup.get('export_object_count')}",
        f"- export sources: `{rollup.get('export_sources')}`; fallback reasons: `{rollup.get('export_fallback_reasons')}`",
        f"- shadow under-merge candidate pairs: {rollup.get('shadow_undermerge_candidate_pairs')}",
        f"- low CLIP-margin observations: {rollup.get('low_clip_margin_count')}; low valid-depth observations: {rollup.get('low_valid_depth_count')}",
        f"- birth reasons: `{rollup.get('birth_reasons')}`",
        f"- engineering filters: low-confidence masks={rollup.get('low_confidence_mask_count')}; large-bbox masks={rollup.get('large_bbox_mask_count')}; mask pixels subtracted={rollup.get('mask_pixels_subtracted')}",
        "",
        "## Per-scene merge monitors",
        "",
        "| scene | source | fallback | keys | export objs | memory nodes | fragmentation | singleton-key rate | shadow pairs | no-candidate births | weak-identity births | p50 best score | eval mIoU | ΔmIoU |",
        "| --- | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
    ])
    gap_by_scene = {row["scene_id"]: row for row in gap_rows}
    for item in scene_debug:
        scene = item["scene"]
        prep = item["prep"]
        diag = item["duograph_summary"]["association_diagnostics"]
        reasons = Counter(diag.get("birth_reasons", {}))
        eval_row = item.get("eval_row") or {}
        gap = gap_by_scene.get(scene, {})
        export_selection = item.get("export_monitor", {}).get("export_selection", {})
        lines.append(
            f"| {scene} | {item.get('manifest', {}).get('object_source', '')} | {export_selection.get('fallback_reason', '')} | "
            f"{prep['key_count']} | {item.get('export_object_count', 0)} | {item['duograph_summary']['memory_node_count']} | "
            f"{item['duograph_summary']['track_fragmentation']} | {prep['monitor']['singleton_key_rate']:.3f} | "
            f"{item['shadow_undermerge']['candidate_pair_count']} | {reasons.get('no_candidate', 0)} | "
            f"{reasons.get('best_candidate_without_strong_identity', 0)} | "
            f"{diag['best_score'].get('p50', 0.0):.3f} | {float(eval_row.get('miou', 0.0)):.3f} | {float(gap.get('gap_miou', 0.0)):.3f} |"
        )
    lines.extend([
        "",
        "## Preliminary attribution",
        "",
        "1. If `shadow pairs`, `singleton-key rate`, and `no_candidate` births are high while valid-depth failures are low, the gap is primarily an online merge/key-fragmentation issue rather than an input projection failure.",
        "2. If low CLIP-margin counts concentrate in the worst-gap scenes, semantic ambiguity contributes to wrong object labels even under the same GSA detections.",
        "3. If precision is above ConceptGraphs but recall/F-mIoU lag, DuoGraph3D is conservative/fragmented; if precision also lags, inspect over-merge or semantic confusion examples before tuning thresholds.",
    ])
    write_json(summary, path.with_suffix(".json"))
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    global ROOT, PRED_EXP_NAME, MIN_OBJECT_DETECTIONS, EXPORT_SOURCE_STRATEGY
    global MIN_MEMORY_EXPORT_OBJECTS, MIN_MEMORY_EXPORT_KEY_RATIO, MIN_MEMORY_EXPORT_POINT_RATIO
    parser = argparse.ArgumentParser()
    parser.add_argument("--scenes", nargs="*", default=list(REPLICA_SCENE_IDS))
    parser.add_argument("--skip-eval", action="store_true")
    parser.add_argument("--root", type=Path, default=ROOT)
    parser.add_argument("--pred-exp-name", default=None)
    parser.add_argument("--min-object-detections", type=int, default=None)
    parser.add_argument(
        "--export-source",
        choices=["auto", "geometry", "memory", "memory-dense"],
        default=EXPORT_SOURCE_STRATEGY,
        help=(
            "Object source for official ConceptGraphs-format export. "
            "`auto` keeps mIoU coverage by falling back to geometry keys when online memory is too sparse; "
            "`memory-dense` groups dense key geometry by online-memory root IDs."
        ),
    )
    parser.add_argument("--min-memory-export-objects", type=int, default=MIN_MEMORY_EXPORT_OBJECTS)
    parser.add_argument("--min-memory-export-key-ratio", type=float, default=MIN_MEMORY_EXPORT_KEY_RATIO)
    parser.add_argument("--min-memory-export-point-ratio", type=float, default=MIN_MEMORY_EXPORT_POINT_RATIO)
    args = parser.parse_args()
    ROOT = args.root
    if args.pred_exp_name:
        PRED_EXP_NAME = args.pred_exp_name
    if args.min_object_detections is not None:
        MIN_OBJECT_DETECTIONS = max(int(args.min_object_detections), 1)
    EXPORT_SOURCE_STRATEGY = args.export_source
    MIN_MEMORY_EXPORT_OBJECTS = max(int(args.min_memory_export_objects), 0)
    MIN_MEMORY_EXPORT_KEY_RATIO = max(float(args.min_memory_export_key_ratio), 0.0)
    MIN_MEMORY_EXPORT_POINT_RATIO = max(float(args.min_memory_export_point_ratio), 0.0)
    torch.set_num_threads(4)
    ROOT.mkdir(parents=True, exist_ok=True)
    (ROOT / "logs").mkdir(exist_ok=True)

    class_all2existing = torch.ones(len(REPLICA_CLASSES)).long() * -1
    for i, c in enumerate(REPLICA_EXISTING_CLASSES):
        class_all2existing[c] = i
    class_names = [REPLICA_CLASSES[i] for i in REPLICA_EXISTING_CLASSES]
    label_to_index = {label: index for index, label in enumerate(class_names)}
    exclude_class = [class_names.index(c) for c in ["other", "floor", "wall", "ceiling", "door", "window"]]

    print("Loading CLIP text encoder", flush=True)
    clip_model, _, _ = open_clip.create_model_and_transforms("ViT-H-14", "laion2b_s32b_b79k")
    device = "cuda:0" if torch.cuda.is_available() and not args.skip_eval else "cpu"
    clip_model = clip_model.to(device)
    tokenizer = open_clip.get_tokenizer("ViT-H-14")
    text = tokenizer([f"an image of {c}" for c in class_names]).to(device)
    with torch.no_grad():
        class_feats = clip_model.encode_text(text)
        class_feats = class_feats / class_feats.norm(dim=-1, keepdim=True)
    class_feats_np = class_feats.detach().cpu().numpy().astype(np.float32)
    scene_id_map = {scene_id: scene_id_ for scene_id, scene_id_ in zip(REPLICA_SCENE_IDS, REPLICA_SCENE_IDS_)}

    all_debug = []
    manifests = []
    per_scene_rows = []
    conf_matrices = {}
    conf_matrix_all = 0
    eval_args = type("Args", (), {
        "replica_root": REPLICA_ROOT,
        "replica_semantic_root": REPLICA_SEMANTIC_ROOT,
        "pred_exp_name": PRED_EXP_NAME,
        "n_exclude": 6,
        "device": "cuda:0",
    })()

    for scene in args.scenes:
        scene_t0 = time.time()
        print(f"=== {scene}: prepare ===", flush=True)
        frames, key_data, prep, frame_debug = prepare_scene(scene, class_names, class_feats_np)
        print(json.dumps(to_builtin(prep)), flush=True)
        print(f"=== {scene}: DuoGraph3D monitored ===", flush=True)
        result, logger, branch_summary = run_duograph(scene, frames)
        report_path = write_report(scene, prep, branch_summary, logger)
        print(json.dumps(to_builtin({
            "scene": scene,
            "duograph_seconds": branch_summary["seconds"],
            "memory_node_count": branch_summary["memory_node_count"],
            "track_count": len(branch_summary.get("track_assignments", {})),
            "track_fragmentation": branch_summary.get("track_fragmentation"),
            "birth_reasons": branch_summary["association_diagnostics"].get("birth_reasons"),
        })), flush=True)
        print(f"=== {scene}: export ===", flush=True)
        track_assignments = (
            branch_summary.get("geometry_key_assignment_counts", {})
            or branch_summary.get("geometry_key_assignments", {})
            or branch_summary.get("track_assignments", {})
            or {}
        )
        shadow_undermerge = compute_shadow_undermerge(scene, key_data, track_assignments)
        manifest, export_debug, skipped_keys = write_conceptgraphs_payload(scene, result, key_data, track_assignments, branch_summary, label_to_index, class_feats_np)
        manifests.append(manifest)
        scene_debug = {
            "scene": scene,
            "prep": prep,
            "report_path": str(report_path),
            "manifest": manifest,
            "export_object_count": manifest["object_count"],
            "export_point_count": manifest["point_count"],
            "skipped_export_keys": len(skipped_keys),
            "duograph_summary": branch_summary,
            "shadow_undermerge": shadow_undermerge,
            "export_monitor": manifest.get("export_monitor", {}),
            "export_debug_sample": export_debug[:20],
            "seconds_total_before_eval": round(time.time() - scene_t0, 3),
        }
        if not args.skip_eval:
            print(f"=== {scene}: eval_replica ===", flush=True)
            conf_matrix, keep_index = eval_replica(
                scene_id=scene,
                scene_id_=scene_id_map[scene],
                class_names=class_names,
                class_feats=class_feats,
                args=eval_args,
                class_all2existing=class_all2existing,
                ignore_index=exclude_class,
            )
            conf_matrix = conf_matrix.detach().cpu()
            conf_matrix_all = conf_matrix if isinstance(conf_matrix_all, int) else conf_matrix_all + conf_matrix
            conf_matrices[scene] = {"conf_matrix": conf_matrix, "keep_index": keep_index}
            row = metrics_row(scene, conf_matrix, keep_index, class_names)
            per_scene_rows.append(row)
            scene_debug["eval_row"] = row
            print(json.dumps(to_builtin(row)), flush=True)
        scene_debug["seconds_total"] = round(time.time() - scene_t0, 3)
        all_debug.append(scene_debug)
        write_json(to_builtin({"scenes": all_debug}), ROOT / "progress_debug.json")

    if not args.skip_eval and per_scene_rows:
        keep_all = conf_matrix_all.sum(axis=1).nonzero().reshape(-1)
        conf_matrices["all"] = {"conf_matrix": conf_matrix_all, "keep_index": keep_all}
        per_scene_rows.append(metrics_row("all", conf_matrix_all, keep_all, class_names))
        with (ROOT / "duograph_monitored_results.csv").open("w", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=["scene_id", "miou", "mrecall", "mprecision", "mf1score", "fmiou"])
            writer.writeheader()
            writer.writerows(per_scene_rows)
        with gzip.open(ROOT / "duograph_monitored_conf_matrices.pkl.gz", "wb") as handle:
            pickle.dump(conf_matrices, handle)

    baseline_rows = load_baseline_rows()
    gap_rows = add_gap_rows(per_scene_rows, baseline_rows)
    if gap_rows:
        with (ROOT / "duograph_monitored_gap_vs_conceptgraphs.csv").open("w", newline="") as handle:
            fields = list(gap_rows[0].keys())
            writer = csv.DictWriter(handle, fieldnames=fields)
            writer.writeheader()
            writer.writerows(gap_rows)
    summary = {
        "pred_exp_name": PRED_EXP_NAME,
        "protocol": "DuoGraph3D over official ConceptGraphs Replica GSA detections with ConceptGraphs-inspired engineering filters/postprocess, evaluated with ConceptGraphs eval_replica_semseg n_exclude=6",
        "scenes": args.scenes,
        "parameters": {
            "voxel_size": VOXEL_SIZE,
            "min_mask_pixels": MIN_MASK_PIXELS,
            "mask_conf_threshold": MASK_CONF_THRESHOLD,
            "max_bbox_area_ratio": MAX_BBOX_AREA_RATIO,
            "min_valid_depth_points": MIN_VALID_DEPTH_POINTS,
            "min_object_detections": MIN_OBJECT_DETECTIONS,
            "class_agnostic_identity_token": CLASS_AGNOSTIC_TOKEN,
            "export_split_by_label": EXPORT_SPLIT_BY_LABEL,
            "max_points_per_obs": MAX_POINTS_PER_OBS,
            "max_points_per_object": MAX_POINTS_PER_OBJECT,
            "temporal_variant": TemporalVariant.NAIVE_FRAMEWISE.value,
            "eval_n_exclude": 6,
            "emit_association_diagnostics": True,
            "association_diagnostics_top_k": ASSOCIATION_DIAGNOSTICS_TOP_K,
            "shadow_undermerge_distance_m": SHADOW_UNDERMERGE_DISTANCE_M,
            "shadow_undermerge_clip_sim": SHADOW_UNDERMERGE_CLIP_SIM,
            "conceptgraphs_postprocess": {
                "mask_subtract_contained": True,
                "downsample_voxel_size": CG_DOWNSAMPLE_VOXEL_SIZE,
                "dbscan_eps": CG_DBSCAN_EPS,
                "dbscan_min_points": CG_DBSCAN_MIN_POINTS,
                "merge_overlap_thresh": CG_MERGE_OVERLAP_THRESH,
                "merge_visual_sim_thresh": CG_MERGE_VISUAL_SIM_THRESH,
                "merge_text_sim_thresh": CG_MERGE_TEXT_SIM_THRESH,
            },
        },
        "setting_audit": {
            "uses_all_requested_replica_scenes": args.scenes == list(REPLICA_SCENE_IDS),
            "uses_conceptgraphs_gsa_detections_none": True,
            "uses_conceptgraphs_replica_semantic_evaluator": not args.skip_eval,
            "does_not_use_deva_annotation_masks": True,
            "does_not_use_gt_sidecar": True,
            "engineering_changes_on_top_of_parity_setting": True,
        },
        "duograph_rows": per_scene_rows,
        "gap_rows": gap_rows,
        "conceptgraphs_baseline_rows": [baseline_rows.get(scene) for scene in args.scenes + (["all"] if args.scenes == list(REPLICA_SCENE_IDS) else [])],
        "manifests": manifests,
        "scene_debug": all_debug,
    }
    summary["monitor_rollup"] = monitor_rollup(all_debug, gap_rows)
    write_json(to_builtin(summary), ROOT / "merge_monitor_summary.json")
    write_markdown_report(to_builtin(summary), ROOT / "merge_monitor_report.md")
    print(ROOT / "merge_monitor_summary.json", flush=True)
    print(ROOT / "merge_monitor_report.md", flush=True)


if __name__ == "__main__":
    main()
