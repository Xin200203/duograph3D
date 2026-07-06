from __future__ import annotations

import argparse
import csv
import gzip
import json
import math
import pickle
import sys
import time
import os
from collections import Counter, defaultdict
from pathlib import Path
from types import SimpleNamespace
from typing import Iterable

import numpy as np
from PIL import Image
import torch
import open_clip
import open3d as o3d

# Host-specific roots are env-overridable so the same runner works on 184 (default)
# and mirrored setups such as 76 (/datadisk3/xxy/duograph3d).  Defaults preserve
# the legacy 184 behavior exactly.
sys.path.insert(0, os.environ.get("DUOGRAPH_SRC", "/home/nebula/xxy/DuoGraph3D/src"))
sys.path.insert(0, os.environ.get("DUOGRAPH_CG_MAIN", "/home/nebula/xxy/concept-graphs-main"))

from duograph3d.contracts import FrameInput, ObjectObservationPayload, Observation, ObservationSupport, PipelineConfig, TemporalVariant
from duograph3d.events import BRANCH_DUOGRAPH3D
from duograph3d.export_policy import (
    GEOMETRY_EXPORT_SOURCE,
    MEMORY_DENSE_EXPORT_SOURCE,
    ExportCoveragePolicy,
    choose_export_source,
    label_cluster_veto,
    spatial_connected_components,
)
from duograph3d.scale_priors import (
    DEFAULT_MAX_EXTENT_PRIORS,
    SCANNET_NYU40_MAX_EXTENT_PRIORS,
    scale_prior_violation,
    select_scale_prior_target,
)

# Active per-vocabulary frozen priors; swapped to the NYU40 table in scannet mode.
ACTIVE_SCALE_PRIORS = DEFAULT_MAX_EXTENT_PRIORS
from duograph3d.experiment_logger import export_event_stream_jsonl
from duograph3d.io_utils import write_json
from duograph3d.memory import ObjectGraphMemory
from duograph3d.metrics import summarize_run
from duograph3d.pipeline import DuoGraph3DPipeline
from duograph3d.shadow_metrics import generate_shadow_report
from conceptgraph.dataset.replica_constants import REPLICA_CLASSES, REPLICA_EXISTING_CLASSES, REPLICA_SCENE_IDS, REPLICA_SCENE_IDS_
from conceptgraph.scripts.eval_replica_semseg import eval_replica
from conceptgraph.slam.slam_classes import MapObjectList
from conceptgraph.slam.utils import (
    compute_overlap_matrix,
    denoise_objects,
    filter_objects,
    get_bounding_box,
    merge_obj2_into_obj1,
    merge_objects,
    process_pcd,
)
from conceptgraph.utils.general_utils import to_tensor
import torch.nn.functional as F
from conceptgraph.utils.ious import mask_subtract_contained
from conceptgraph.utils.eval import compute_metrics

ROOT = Path(os.environ.get(
    "DUOGRAPH_ARTIFACT_ROOT",
    "/home/nebula/xxy/duograph3d_artifacts/duograph3d_conceptgraphs_engineered_20260426",
))
REPLICA_ROOT = Path(os.environ.get("DUOGRAPH_REPLICA_ROOT", "/home/nebula/xxy/dataset/Replica"))
REPLICA_SEMANTIC_ROOT = Path(os.environ.get(
    "DUOGRAPH_REPLICA_SEMANTIC_ROOT", "/home/nebula/xxy/dataset/Replica-semantic"
))
BASELINE_CSV = Path(os.environ.get(
    "DUOGRAPH_BASELINE_CSV",
    "/home/nebula/xxy/duograph3d_artifacts/conceptgraphs_replica_official_20260423/replica_ex6_results.csv",
))
PRED_EXP_NAME = "duograph3d_gsa_engineered_monitor"
# Dataset mode: `replica` (default, official protocol) or `scannet` (25k-export
# staged scenes for the mechanism-transfer table).  ScanNet mode loads per-scene
# intrinsics/poses, uses the NYU40 vocabulary + its frozen scale priors, and
# always defers evaluation to examples/eval_scannet_semseg.py.
DATASET_MODE = os.environ.get("DUOGRAPH_DATASET", "replica")
SCANNET_STAGE_ROOT = Path(os.environ.get("DUOGRAPH_SCANNET_STAGE_ROOT", "/home/nebula/xxy/dataset/scannet_cg"))
NYU40_CLASSES = [
    "wall", "floor", "cabinet", "bed", "chair", "sofa", "table", "door",
    "window", "bookshelf", "picture", "counter", "blinds", "desk", "shelves",
    "curtain", "dresser", "pillow", "mirror", "floor mat", "clothes",
    "ceiling", "books", "refridgerator", "television", "paper", "towel",
    "shower curtain", "box", "whiteboard", "person", "night stand", "toilet",
    "sink", "lamp", "bathtub", "bag", "otherstructure", "otherfurniture",
    "otherprop",
]
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
DROP_POST_SUBTRACT_TINY = False
EXPORT_SOURCE_STRATEGY = "auto"
# consolidation-auto substrate routing threshold: memory/key ratio below this
# selects the dense export (see duograph3d.export_policy.choose_export_source).
EXPORT_CONSOLIDATION_DENSE_MAX_RATIO = float(
    os.environ.get("DUOGRAPH_EXPORT_CONSOLIDATION_DENSE_MAX_RATIO", "0.175")
)
# Mechanism scope: the label gate and scale-prior repairs require multi-view
# object-level declared evidence, which only the consolidated (memory-dense)
# substrate provides; raw geometry-key buckets carry boundary-noise label
# mixes that make both mechanisms misfire (office0 geometry arm: 148 vetoes +
# 15 junk declared relabels).  `consolidated-only` disables both on
# geometry-routed exports; `all-substrates` keeps legacy behavior.
MECHANISMS_SCOPE = os.environ.get("DUOGRAPH_MECHANISMS_SCOPE", "all-substrates")
MIN_MEMORY_EXPORT_OBJECTS = 100
MIN_MEMORY_EXPORT_KEY_RATIO = 0.10
MIN_MEMORY_EXPORT_POINT_RATIO = 0.05
MEMORY_DENSE_MIN_ROOT_SHARE = 0.60
MEMORY_DENSE_GEOMETRY_FALLBACK = True
MEMORY_DENSE_SPLIT_BY_LABEL = True
MEMORY_DENSE_SPLIT_MIN_OBSERVATIONS = 1
MEMORY_DENSE_SPLIT_MIN_ROOT_LABEL_ENTROPY = 0.5
MEMORY_DENSE_SPLIT_MAX_ROOT_TOP_SHARE = 0.9
CLASS_AGNOSTIC_TOKEN = "item"
TEXT_FEATURE_MODE = os.environ.get("DUOGRAPH_TEXT_FEATURE_MODE", "item")
CLIP_FEATURE_MODE = os.environ.get("DUOGRAPH_CLIP_FEATURE_MODE", "image")
CLIP_FEATURE_BLEND_ALPHA = float(os.environ.get("DUOGRAPH_CLIP_FEATURE_BLEND_ALPHA", "0.50"))
EXPORT_CLIP_MIN_MARGIN = float(os.environ.get("DUOGRAPH_EXPORT_CLIP_MIN_MARGIN", "0.0"))
ADAPTIVE_CLIP_SINK_LABELS = os.environ.get(
    "DUOGRAPH_ADAPTIVE_CLIP_SINK_LABELS",
    "vent,monitor,bin,desk-organizer,indoor-plant,cushion",
)
ADAPTIVE_CLIP_MIN_HIGH_MARGIN_COUNT = int(os.environ.get("DUOGRAPH_ADAPTIVE_CLIP_MIN_HIGH_MARGIN_COUNT", "3"))
ADAPTIVE_CLIP_MIN_HIGH_MARGIN_RATE = float(os.environ.get("DUOGRAPH_ADAPTIVE_CLIP_MIN_HIGH_MARGIN_RATE", "0.20"))
ADAPTIVE_CLIP_MIN_ENTROPY = float(os.environ.get("DUOGRAPH_ADAPTIVE_CLIP_MIN_ENTROPY", "0.75"))
EXPORT_SPLIT_BY_LABEL = False
EXPORT_SPLIT_POLICY = "all"
EXPORT_SPLIT_MIN_OBSERVATIONS = 1
EXPORT_SPLIT_MIN_KEY_ENTROPY = 0.0
EXPORT_SPLIT_MAX_KEY_TOP_SHARE = 1.0
EXPORT_SPLIT_MIN_LABEL_SHARE = 0.0
EXPORT_SPLIT_MIN_CENTROID_SEPARATION = 0.0
EXPORT_SPLIT_MIN_SCENE_SPLIT_RATE = 0.0
MULTIRES_EXPORT_ENABLED = False
MULTIRES_FINE_VOXEL_SIZE = 0.25
MULTIRES_FINE_LABELS = "sofa,cushion,chair,bench,table,tv-stand,tablet"
MULTIRES_RISKY_LABELS = "vent,switch,wall-plug,tv-stand,desk-organizer,tablet,bin"
MULTIRES_FINE_SPLIT_BY_LABEL = True
MULTIRES_FINE_MIN_OBSERVATIONS = 1
MULTIRES_FINE_TAKEOVER_MIN_POINTS = 0
MULTIRES_RISKY_MIN_POINTS = 8000
MULTIRES_REPLACEMENT_MODE = "replace"
GEOMETRY_REPAIR_KEEP_LABELS = ""
GEOMETRY_REPAIR_VENT_TO_SOFA_DELTA = -1.0
GEOMETRY_REPAIR_CUSHION_SHRINK_RADIUS = 0.0
GEOMETRY_REPAIR_CARVE_RULES = os.environ.get("DUOGRAPH_GEOMETRY_REPAIR_CARVE_RULES", "")
GEOMETRY_REPAIR_LARGE_LABEL_RULES = os.environ.get("DUOGRAPH_GEOMETRY_REPAIR_LARGE_LABEL_RULES", "")
GEOMETRY_REPAIR_LARGE_LABEL_EVIDENCE_MODE = os.environ.get(
    "DUOGRAPH_GEOMETRY_REPAIR_LARGE_LABEL_EVIDENCE_MODE",
    "off",
)
GEOMETRY_REPAIR_LARGE_LABEL_SOURCE_MODE = os.environ.get(
    "DUOGRAPH_GEOMETRY_REPAIR_LARGE_LABEL_SOURCE_MODE",
    "clip-top1",
)
GEOMETRY_REPAIR_LARGE_LABEL_REQUIRE_TARGET_DECLARED = os.environ.get(
    "DUOGRAPH_GEOMETRY_REPAIR_LARGE_LABEL_REQUIRE_TARGET_DECLARED",
    "",
)
GEOMETRY_REPAIR_LARGE_LABEL_MAX_POINT_RATE = float(
    os.environ.get("DUOGRAPH_GEOMETRY_REPAIR_LARGE_LABEL_MAX_POINT_RATE", "1.0")
)
GEOMETRY_REPAIR_LARGE_LABEL_MIN_OBSERVATIONS = int(
    os.environ.get("DUOGRAPH_GEOMETRY_REPAIR_LARGE_LABEL_MIN_OBSERVATIONS", "0")
)
GEOMETRY_REPAIR_LARGE_LABEL_MIN_SOURCE_SHARE = float(
    os.environ.get("DUOGRAPH_GEOMETRY_REPAIR_LARGE_LABEL_MIN_SOURCE_SHARE", "0.0")
)
# 方案 B: scene-independent generalization of the hand-written label-pair rules.
# keep-mode `declared-auto` derives the evaluator-facing repair source set from
# the scene's own multi-view declared labels (GT-free) instead of a hand list.
# scale-prior mode replaces `source:target:threshold` rules with per-label
# physical max-extent priors (duograph3d.scale_priors, frozen commonsense table)
# plus declared-evidence target selection; `log-only` records every violation
# and selection without touching labels so priors/guards are set from
# diagnostics, never from evaluation feedback.
GEOMETRY_REPAIR_KEEP_MODE = os.environ.get("DUOGRAPH_GEOMETRY_REPAIR_KEEP_MODE", "configured")
GEOMETRY_REPAIR_KEEP_AUTO_MIN_COUNT = int(
    os.environ.get("DUOGRAPH_GEOMETRY_REPAIR_KEEP_AUTO_MIN_COUNT", "3")
)
GEOMETRY_REPAIR_SCALE_PRIOR_MODE = os.environ.get(
    "DUOGRAPH_GEOMETRY_REPAIR_SCALE_PRIOR_MODE",
    "off",
)
GEOMETRY_REPAIR_SCALE_PRIOR_TOLERANCE = float(
    os.environ.get("DUOGRAPH_GEOMETRY_REPAIR_SCALE_PRIOR_TOLERANCE", "1.0")
)
GEOMETRY_REPAIR_SCALE_PRIOR_MIN_TARGET_SHARE = float(
    os.environ.get("DUOGRAPH_GEOMETRY_REPAIR_SCALE_PRIOR_MIN_TARGET_SHARE", "0.15")
)
GEOMETRY_REPAIR_SCALE_PRIOR_MAX_SOURCE_SHARE = float(
    os.environ.get("DUOGRAPH_GEOMETRY_REPAIR_SCALE_PRIOR_MAX_SOURCE_SHARE", "0.60")
)
# Physical-impossibility override: past this multiple of the source prior,
# unanimous multi-view readout is treated as systematic detector bias (the
# office1 1.4m "tissue-paper" at 3.1x prior) — the consensus guard is skipped
# and, when the declared distribution offers no alternative, the target falls
# back to the top CLIP label among physically-compatible classes.
GEOMETRY_REPAIR_SCALE_PRIOR_HARD_RATIO = float(
    os.environ.get("DUOGRAPH_GEOMETRY_REPAIR_SCALE_PRIOR_HARD_RATIO", "2.0")
)
# The CLIP-compatible re-readout fallback is OFF by default: PB2 showed the
# compatible-label CLIP ranking on hard-violating carriers is noise-level
# (scores ~0.25, margins ~0.01) and fired 7/7 junk relabels on office1,
# including tissue-paper->comforter on the carrier whose true class is cloth.
# Scale-prior targets must come from declared multi-view evidence unless this
# is explicitly enabled for diagnostics.
GEOMETRY_REPAIR_SCALE_PRIOR_CLIP_FALLBACK = int(
    os.environ.get("DUOGRAPH_GEOMETRY_REPAIR_SCALE_PRIOR_CLIP_FALLBACK", "0")
)
STRUCTURAL_EXPORT_LABELS = frozenset({"other", "floor", "wall", "ceiling", "door", "window"})
# O2b: split memory-dense buckets whose member keys are not spatially coherent
# (the office4 wall-strip mega-bucket disease).  Each spatial component is
# re-accumulated from its own keys, so features and labels are recomputed per
# component.  Default off (legacy behavior).
MEMORY_DENSE_SPATIAL_SPLIT = int(os.environ.get("DUOGRAPH_MEMORY_DENSE_SPATIAL_SPLIT", "0"))
MEMORY_DENSE_SPATIAL_SPLIT_EPS = float(os.environ.get("DUOGRAPH_MEMORY_DENSE_SPATIAL_SPLIT_EPS", "0.35"))
CG_DOWNSAMPLE_VOXEL_SIZE = 0.025
CG_DBSCAN_EPS = 0.1
CG_DBSCAN_MIN_POINTS = 10
CG_MERGE_OVERLAP_THRESH = 0.7
CG_MERGE_VISUAL_SIM_THRESH = 0.8
CG_MERGE_TEXT_SIM_THRESH = 0.8
# Per-pair carrier-preservation gate for the CG-style postprocess merge.  Legacy
# behavior keeps a single global overlap threshold (1.0 = merging fully off, the
# E70 office1 policy; 0.7 = merging on, the office2 policy).  The label gate
# replaces that scene-level binary: pairs that CG would merge are vetoed only
# when both objects carry distinct, well-supported declared-label clusters.
CG_MERGE_LABEL_GATE = int(os.environ.get("DUOGRAPH_CG_MERGE_LABEL_GATE", "0"))
CG_MERGE_LABEL_GATE_MIN_SHARE = float(os.environ.get("DUOGRAPH_CG_MERGE_LABEL_GATE_MIN_SHARE", "0.60"))
CG_MERGE_LABEL_GATE_MIN_OBS = int(os.environ.get("DUOGRAPH_CG_MERGE_LABEL_GATE_MIN_OBS", "2"))
# Mutual-containment guard: when BOTH containment directions exceed this
# threshold the two point sets spatially coincide — one observation stream split
# by readout noise, not two objects — so the pair always follows CG merging and
# the label veto is skipped.  Distinct carriers show one-directional containment
# (small object against a larger absorber).  Set negative to disable.
CG_MERGE_LABEL_GATE_MUTUAL_THRESH = float(
    os.environ.get("DUOGRAPH_CG_MERGE_LABEL_GATE_MUTUAL_THRESH", "0.7")
)
L2_OCCLUDED_AFTER_MISSES = int(os.environ.get("DUOGRAPH_L2_OCCLUDED_AFTER_MISSES", "1"))
L2_DORMANT_AFTER_MISSES = int(os.environ.get("DUOGRAPH_L2_DORMANT_AFTER_MISSES", "2"))
L2_RETIRE_AFTER_MISSES = int(os.environ.get("DUOGRAPH_L2_RETIRE_AFTER_MISSES", "4"))
L2_RELATION_BONUS_WEIGHT = float(os.environ.get("DUOGRAPH_L2_RELATION_BONUS_WEIGHT", "0.25"))
L2_RELATION_BONUS_CAP = float(os.environ.get("DUOGRAPH_L2_RELATION_BONUS_CAP", "0.35"))


def normalize_np(arr: np.ndarray) -> np.ndarray:
    arr = np.asarray(arr, dtype=np.float32)
    norm = np.linalg.norm(arr, axis=-1, keepdims=True)
    norm[norm == 0] = 1.0
    return arr / norm


def parse_csv_set(value: str) -> set[str]:
    return {item.strip() for item in str(value or "").split(",") if item.strip()}


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


def label_top_share(counter: Counter) -> float:
    total = sum(counter.values())
    if total <= 0:
        return 0.0
    return round(counter.most_common(1)[0][1] / total, 6)


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


def quant_key_for_voxel(scene: str, label: str, centroid: np.ndarray, voxel_size: float) -> str:
    q = np.floor(centroid / max(float(voxel_size), 1e-6)).astype(int)
    # ConceptGraphs `gsa_variant=none` is effectively class-agnostic during
    # online mapping.  Keep semantics in object feature histograms, not in the
    # identity key, so low-margin CLIP label flips do not split tracks.
    del label
    return f"{scene}:gsa:{CLASS_AGNOSTIC_TOKEN}:{q[0]}:{q[1]}:{q[2]}"


def quant_key(scene: str, label: str, centroid: np.ndarray) -> str:
    return quant_key_for_voxel(scene, label, centroid, VOXEL_SIZE)


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


def selected_text_feature(class_i: int, class_feats_np: np.ndarray) -> np.ndarray:
    """Text feature used by ConceptGraphs overlap post-merge.

    Official `gsa_detections_none` stores a generic `item` text feature.  The
    Replica evaluator predicts semantics from `clip_ft`, not `class_name` or
    `text_ft`; `text_ft` mainly gates overlap merges.  Keeping it class-agnostic
    avoids turning low-margin CLIP top-1 labels into hard merge barriers while
    still recording recovered labels in monitoring and label buckets.
    """

    mode = str(TEXT_FEATURE_MODE or "item").lower().replace("_", "-")
    if mode in {"item", "class-agnostic", "class-agnostic-item"}:
        return class_agnostic_text_anchor(class_feats_np.shape[1]).astype(np.float32)
    if mode == "class":
        return class_feats_np[class_i].astype(np.float32)
    raise ValueError(f"unsupported text feature mode: {TEXT_FEATURE_MODE}")


def selected_clip_feature(
    image_clip: np.ndarray,
    *,
    label: str,
    label_to_index: dict[str, int],
    class_feats_np: np.ndarray,
) -> np.ndarray:
    """Feature exported as ConceptGraphs `clip_ft` for official semantic eval.

    The default preserves ConceptGraphs parity by using averaged detection image
    CLIP features.  Diagnostic modes let us test whether low-margin image CLIP
    averages are being pulled toward frequent distractors such as `vent`.
    """

    image = normalize_np(np.asarray(image_clip, dtype=np.float32).reshape(1, -1))[0]
    mode = str(CLIP_FEATURE_MODE or "image").lower().replace("_", "-")
    label_index = int(label_to_index.get(str(label), -1))
    if label_index < 0 or label_index >= len(class_feats_np):
        return image.astype(np.float32)
    label_feature = normalize_np(np.asarray(class_feats_np[label_index], dtype=np.float32).reshape(1, -1))[0]
    if mode in {"image", "dominant-label-image", "adaptive"}:
        return image.astype(np.float32)
    if mode in {"label-text", "label"}:
        return label_feature.astype(np.float32)
    if mode == "blend":
        alpha = min(max(float(CLIP_FEATURE_BLEND_ALPHA), 0.0), 1.0)
        return normalize_np(((1.0 - alpha) * image + alpha * label_feature).reshape(1, -1))[0].astype(np.float32)
    raise ValueError(f"unsupported clip feature mode: {CLIP_FEATURE_MODE}")


def export_image_clip_feature(data: dict[str, object], label: str) -> np.ndarray:
    """Choose the image-CLIP aggregate before optional semantic calibration."""

    mode = str(CLIP_FEATURE_MODE or "image").lower().replace("_", "-")
    if mode == "dominant-label-image":
        label_data = (data.get("label_buckets") or {}).get(label)
        if label_data and int(label_data.get("feature_count", 0)) > 0:
            return clip_average(label_data, prefer_export=True)
    return clip_average(data, prefer_export=True)


def clip_average(bucket: dict[str, object], *, prefer_export: bool) -> np.ndarray:
    """Average all or high-margin image CLIP observations from one carrier bucket."""

    if prefer_export:
        export_count = int(bucket.get("export_clip_count", 0) or 0)
        export_sum = bucket.get("export_clip_sum")
        if export_count > 0 and export_sum is not None:
            return normalize_np((np.asarray(export_sum, dtype=np.float64) / export_count).reshape(1, -1))[0].astype(np.float32)
    return average_feature(bucket, "clip_sum")


def selected_export_clip_feature(
    data: dict[str, object],
    label: str,
    *,
    label_to_index: dict[str, int],
    class_feats_np: np.ndarray,
) -> tuple[np.ndarray, dict[str, object]]:
    """Choose final exported `clip_ft` plus diagnostics for one carrier.

    `adaptive` is intentionally carrier-local: it only trusts high-margin image
    CLIP when the carrier has enough high-margin evidence and either the label is
    a known over-expansion sink or the carrier is semantically mixed.  Otherwise
    it falls back to the ConceptGraphs-style all-image average.  This keeps the
    E39/E41 default behavior untouched while making the E44/E45 failure mode a
    reproducible experimental branch rather than a scene-wide hard threshold.
    """

    mode = str(CLIP_FEATURE_MODE or "image").lower().replace("_", "-")
    if mode != "adaptive":
        image_feature = export_image_clip_feature(data, label)
        return selected_clip_feature(
            image_feature,
            label=label,
            label_to_index=label_to_index,
            class_feats_np=class_feats_np,
        ), {
            "clip_readout_source": mode,
            "clip_readout_reason": "legacy_mode",
            "high_margin_count": int(data.get("export_clip_count", 0) or 0),
            "feature_count": int(data.get("feature_count", 0) or 0),
        }

    feature_count = max(int(data.get("feature_count", 0) or 0), 1)
    high_count = int(data.get("export_clip_count", 0) or 0)
    high_rate = high_count / feature_count
    label_counts = data.get("label_counts") or Counter()
    entropy_value = label_entropy(label_counts)
    sink_labels = parse_csv_set(ADAPTIVE_CLIP_SINK_LABELS)
    enough_high_margin = (
        high_count >= max(int(ADAPTIVE_CLIP_MIN_HIGH_MARGIN_COUNT), 1)
        and high_rate >= max(float(ADAPTIVE_CLIP_MIN_HIGH_MARGIN_RATE), 0.0)
    )
    sink_label = label in sink_labels
    mixed_carrier = entropy_value >= max(float(ADAPTIVE_CLIP_MIN_ENTROPY), 0.0)
    use_high_margin = enough_high_margin and (sink_label or mixed_carrier)
    readout_source = "high_margin_image" if use_high_margin else "all_image"
    reason = (
        "sink_or_mixed_high_margin"
        if use_high_margin
        else "insufficient_high_margin_or_stable_non_sink"
    )
    image_feature = clip_average(data, prefer_export=use_high_margin)
    return selected_clip_feature(
        image_feature,
        label=label,
        label_to_index=label_to_index,
        class_feats_np=class_feats_np,
    ), {
        "clip_readout_source": readout_source,
        "clip_readout_reason": reason,
        "high_margin_count": high_count,
        "feature_count": feature_count,
        "high_margin_rate": round(high_rate, 6),
        "label_entropy": entropy_value,
        "sink_label": sink_label,
        "mixed_carrier": mixed_carrier,
    }


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


def choose_semantic_label(
    *,
    det_i: int,
    gsa_class_ids: np.ndarray,
    gsa_classes: list[str],
    class_names: list[str],
    sims: np.ndarray,
) -> tuple[int, str, str]:
    """Choose the semantic label used for memory/export.

    ConceptGraphs GSA detections may be class-agnostic (`classes == ["item"]`).
    In that case, using the raw class_id collapses all objects to `item`; instead
    recover the open-vocabulary semantic label from CLIP image/text similarity.
    """

    raw_index = int(gsa_class_ids[det_i]) if len(gsa_class_ids) > det_i else -1
    raw_label = ""
    if 0 <= raw_index < len(gsa_classes):
        raw_label = str(gsa_classes[raw_index])
    normalized_raw = raw_label.strip().lower()
    if raw_label and normalized_raw not in {"item", "object", "objects"} and raw_label in class_names:
        return class_names.index(raw_label), raw_label, "gsa_class"
    clip_index = int(np.argmax(sims[det_i]))
    return clip_index, str(class_names[clip_index]), "clip_top1"


def new_export_bucket(feature_template: np.ndarray) -> dict[str, object]:
    return {
        "label_counts": Counter(),
        "clip_sum": np.zeros_like(feature_template, dtype=np.float64),
        "export_clip_sum": np.zeros_like(feature_template, dtype=np.float64),
        "export_clip_count": 0,
        "text_sum": np.zeros_like(feature_template, dtype=np.float64),
        "feature_count": 0,
        "points": [],
        "colors": [],
        "mask_pixels": 0,
        "confidence_sum": 0.0,
        "centroid_sum": np.zeros(3, dtype=np.float64),
        "valid_depth_ratio_sum": 0.0,
        "clip_margin_sum": 0.0,
        "label_buckets": {},
    }


def add_observation_to_key_data(
    key_data: dict[str, dict[str, object]],
    *,
    key: str,
    label: str,
    image_feature: np.ndarray,
    text_feature: np.ndarray,
    points: np.ndarray,
    colors: np.ndarray,
    mask_area: int,
    confidence: float,
    centroid: np.ndarray,
    valid_depth_ratio: float,
    clip_margin_value: float,
    export_clip_min_margin: float,
) -> None:
    feature_template = np.asarray(image_feature, dtype=np.float64)
    bucket = key_data.setdefault(key, new_export_bucket(feature_template))
    bucket["label_counts"][label] += 1
    bucket["clip_sum"] += feature_template
    if clip_margin_value >= export_clip_min_margin:
        bucket["export_clip_sum"] += feature_template
        bucket["export_clip_count"] += 1
    bucket["text_sum"] += np.asarray(text_feature, dtype=np.float64)
    bucket["feature_count"] += 1
    bucket["points"].append(points)
    bucket["colors"].append(colors)
    bucket["mask_pixels"] += int(mask_area)
    bucket["confidence_sum"] += float(confidence)
    bucket["centroid_sum"] += np.asarray(centroid, dtype=np.float64)
    bucket["valid_depth_ratio_sum"] += float(valid_depth_ratio)
    bucket["clip_margin_sum"] += float(clip_margin_value)

    label_buckets = bucket["label_buckets"]
    label_bucket = label_buckets.setdefault(label, new_export_bucket(feature_template))
    label_bucket["label_counts"][label] += 1
    label_bucket["clip_sum"] += feature_template
    if clip_margin_value >= export_clip_min_margin:
        label_bucket["export_clip_sum"] += feature_template
        label_bucket["export_clip_count"] += 1
    label_bucket["text_sum"] += np.asarray(text_feature, dtype=np.float64)
    label_bucket["feature_count"] += 1
    label_bucket["points"].append(points)
    label_bucket["colors"].append(colors)
    label_bucket["mask_pixels"] += int(mask_area)
    label_bucket["confidence_sum"] += float(confidence)
    label_bucket["centroid_sum"] += np.asarray(centroid, dtype=np.float64)
    label_bucket["valid_depth_ratio_sum"] += float(valid_depth_ratio)
    label_bucket["clip_margin_sum"] += float(clip_margin_value)


def prepare_scene(
    scene: str,
    class_names: list[str],
    class_feats_np: np.ndarray,
    *,
    frame_limit: int | None = None,
    frame_stride: int = 1,
):
    t0 = time.time()
    global FX, FY, CX, CY, DEPTH_SCALE
    if DATASET_MODE == "scannet":
        scene_root = SCANNET_STAGE_ROOT / scene
        gsa_dir = scene_root / "gsa_detections_none"
        intrinsic = np.loadtxt(scene_root / "intrinsic" / "intrinsic_color.txt", dtype=np.float32)
        FX, FY = float(intrinsic[0, 0]), float(intrinsic[1, 1])
        CX, CY = float(intrinsic[0, 2]), float(intrinsic[1, 2])
        DEPTH_SCALE = 1000.0
        poses = None
    else:
        scene_root = REPLICA_ROOT / scene
        gsa_dir = scene_root / "gsa_detections_none"
        poses = np.loadtxt(scene_root / "traj.txt", dtype=np.float32).reshape(-1, 4, 4)
    # Per-observation text feature is aligned to the selected evaluation label.
    key_data: dict[str, dict[str, object]] = {}
    multires_key_data: dict[str, dict[str, object]] = {}
    frames: list[FrameInput] = []
    frame_debug = []
    total_raw_dets = 0
    total_kept = 0
    monitor = {
        "raw_mask_pixels": [],
        "pre_subtract_kept_mask_pixels": [],
        "post_subtract_candidate_mask_pixels": [],
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
        "post_subtract_empty_mask_count": 0,
        "post_subtract_tiny_mask_count": 0,
        "label_counts": Counter(),
        "label_source_counts": Counter(),
    }
    if DATASET_MODE == "scannet":
        det_paths = sorted(gsa_dir.glob("*.pkl.gz"), key=lambda p: int(p.name.split(".")[0]))
    else:
        det_paths = sorted(gsa_dir.glob("frame*.pkl.gz"))
    det_paths = det_paths[:: max(int(frame_stride), 1)]
    if frame_limit is not None:
        det_paths = det_paths[: max(int(frame_limit), 0)]
    for det_path in det_paths:
        frame_stem = det_path.name.split(".")[0]
        observations: list[Observation] = []
        if DATASET_MODE == "scannet":
            frame_idx = int(frame_stem)
            depth = np.asarray(Image.open(scene_root / "depth" / f"{frame_stem}.png"), dtype=np.float32) / DEPTH_SCALE
            rgb_image = np.asarray(Image.open(scene_root / "color" / f"{frame_stem}.jpg").convert("RGB"), dtype=np.float32) / 255.0
            pose = np.loadtxt(scene_root / "pose" / f"{frame_stem}.txt", dtype=np.float32)
            if not np.isfinite(pose).all():
                continue
            if depth.shape[:2] != rgb_image.shape[:2]:
                # 25k export ships color and depth at the same 640x480 size; guard anyway.
                continue
        else:
            frame_idx = int(frame_stem[len("frame"):])
            depth = np.asarray(Image.open(REPLICA_ROOT / scene / "results" / f"depth{frame_idx:06d}.png"), dtype=np.float32) / DEPTH_SCALE
            rgb_image = np.asarray(Image.open(REPLICA_ROOT / scene / "results" / f"frame{frame_idx:06d}.jpg").convert("RGB"), dtype=np.float32) / 255.0
            pose = poses[frame_idx]
        with gzip.open(det_path, "rb") as handle:
            det = pickle.load(handle)
        image_feats = normalize_np(det["image_feats"].astype(np.float32))
        sims = image_feats @ class_feats_np.T  # kept for monitoring
        gsa_class_ids = det["class_id"]
        gsa_classes = det["classes"]
        masks = np.asarray(det["mask"]).astype(bool)
        xyxy = np.asarray(det.get("xyxy", np.zeros((len(masks), 4), dtype=np.float32)))
        confidences = det.get("confidence", np.ones(len(masks), dtype=np.float32))
        total_raw_dets += int(len(masks))
        pre_keep_indices = []
        for det_i in range(len(masks)):
            raw_area = int(masks[det_i].sum())
            monitor["raw_mask_pixels"].append(raw_area)
            if raw_area < MIN_MASK_PIXELS:
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
            pre_keep_indices.append(det_i)

        if pre_keep_indices:
            frame_masks = masks[pre_keep_indices]
            monitor["pre_subtract_kept_mask_pixels"].extend(int(mask.sum()) for mask in frame_masks)
            if len(xyxy) == len(masks):
                before_pixels = int(frame_masks.sum())
                frame_masks = mask_subtract_contained(xyxy[pre_keep_indices], frame_masks).astype(bool)
                monitor["mask_pixels_subtracted"] += max(before_pixels - int(frame_masks.sum()), 0)
            else:
                frame_masks = frame_masks.astype(bool)
        else:
            frame_masks = np.zeros((0,) + masks.shape[1:], dtype=bool) if masks.ndim == 3 else np.zeros((0, 0, 0), dtype=bool)

        for local_i, det_i in enumerate(pre_keep_indices):
            class_i, label, label_source = choose_semantic_label(
                det_i=det_i,
                gsa_class_ids=gsa_class_ids,
                gsa_classes=gsa_classes,
                class_names=class_names,
                sims=sims,
            )
            mask = frame_masks[local_i]
            area = int(mask.sum())
            monitor["post_subtract_candidate_mask_pixels"].append(area)
            if area == 0:
                monitor["post_subtract_empty_mask_count"] += 1
                continue
            elif area < MIN_MASK_PIXELS:
                monitor["post_subtract_tiny_mask_count"] += 1
                if DROP_POST_SUBTRACT_TINY:
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
            top1 = float(sims[det_i, class_i])
            if margin < LOW_CLIP_MARGIN:
                monitor["low_clip_margin_count"] += 1
            if valid_ratio < LOW_VALID_DEPTH_RATIO:
                monitor["low_valid_depth_count"] += 1
            key = quant_key(scene, label, centroid)
            raw_conf = float(confidences[det_i])
            conf = float(np.clip(raw_conf, 0.0, 1.0))
            text_feature = selected_text_feature(class_i, class_feats_np)
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
                        text_feature=text_feature,
                        mask_area=area,
                    ),
                ))
            add_observation_to_key_data(
                key_data,
                key=key,
                label=label,
                image_feature=image_feats[det_i],
                text_feature=text_feature,
                points=world,
                colors=colors,
                mask_area=area,
                confidence=conf,
                centroid=centroid,
                valid_depth_ratio=valid_ratio,
                clip_margin_value=margin,
                export_clip_min_margin=EXPORT_CLIP_MIN_MARGIN,
            )
            if MULTIRES_EXPORT_ENABLED:
                fine_key = quant_key_for_voxel(scene, label, centroid, MULTIRES_FINE_VOXEL_SIZE)
                add_observation_to_key_data(
                    multires_key_data,
                    key=fine_key,
                    label=label,
                    image_feature=image_feats[det_i],
                    text_feature=text_feature,
                    points=world,
                    colors=colors,
                    mask_area=area,
                    confidence=conf,
                    centroid=centroid,
                    valid_depth_ratio=valid_ratio,
                    clip_margin_value=margin,
                    export_clip_min_margin=EXPORT_CLIP_MIN_MARGIN,
                )
            monitor["kept_mask_pixels"].append(area)
            monitor["confidence"].append(conf)
            monitor["valid_depth_ratio"].append(valid_ratio)
            monitor["clip_margin"].append(margin)
            monitor["top1_similarity"].append(top1)
            monitor["label_counts"][label] += 1
            monitor["label_source_counts"][label_source] += 1
            total_kept += 1
        frames.append(FrameInput(frame_id=f"replica-{scene}-{frame_idx:06d}", observations=observations))
        monitor["frame_observation_counts"].append(len(observations))
        frame_debug.append({"frame": frame_stem, "observations": len(observations)})
    obs_per_key = [int(data["feature_count"]) for data in key_data.values()]
    export_clip_selected_count = sum(int(data.get("export_clip_count", 0) or 0) for data in key_data.values())
    entropy_by_key = [label_entropy(data["label_counts"]) for data in key_data.values()]
    prep_monitor = {
        "mask_pixels_raw": numeric_summary(monitor["raw_mask_pixels"]),
        "mask_pixels_pre_subtract_kept": numeric_summary(monitor["pre_subtract_kept_mask_pixels"]),
        "mask_pixels_post_subtract_candidate": numeric_summary(monitor["post_subtract_candidate_mask_pixels"]),
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
        "post_subtract_empty_mask_count": int(monitor["post_subtract_empty_mask_count"]),
        "post_subtract_tiny_mask_count": int(monitor["post_subtract_tiny_mask_count"]),
        "singleton_key_count": sum(1 for value in obs_per_key if value == 1),
        "singleton_key_rate": round(sum(1 for value in obs_per_key if value == 1) / max(len(obs_per_key), 1), 6),
        "top_labels": monitor["label_counts"].most_common(15),
        "label_source_counts": dict(monitor["label_source_counts"]),
        "export_clip_min_margin": EXPORT_CLIP_MIN_MARGIN,
        "export_clip_selected_observation_count": export_clip_selected_count,
        "export_clip_selected_observation_rate": round(export_clip_selected_count / max(total_kept, 1), 6),
    }
    prep = {
        "scene": scene,
        "frame_count": len(frames),
        "frames_with_observations": sum(1 for frame in frames if frame.observations),
        "raw_detection_count": total_raw_dets,
        "kept_observation_count": total_kept,
        "key_count": len(key_data),
        "multires_key_count": len(multires_key_data),
        "seconds": round(time.time() - t0, 3),
        "parameters": {
            "duograph_phase": os.environ.get("DUOGRAPH_PHASE", "baseline"),
            "text_feature_mode": TEXT_FEATURE_MODE,
            "clip_feature_mode": CLIP_FEATURE_MODE,
            "clip_feature_blend_alpha": CLIP_FEATURE_BLEND_ALPHA,
            "export_clip_min_margin": EXPORT_CLIP_MIN_MARGIN,
            "adaptive_clip_sink_labels": ADAPTIVE_CLIP_SINK_LABELS,
            "adaptive_clip_min_high_margin_count": ADAPTIVE_CLIP_MIN_HIGH_MARGIN_COUNT,
            "adaptive_clip_min_high_margin_rate": ADAPTIVE_CLIP_MIN_HIGH_MARGIN_RATE,
            "adaptive_clip_min_entropy": ADAPTIVE_CLIP_MIN_ENTROPY,
            "voxel_size": VOXEL_SIZE,
            "multires_export_enabled": MULTIRES_EXPORT_ENABLED,
            "multires_fine_voxel_size": MULTIRES_FINE_VOXEL_SIZE,
            "multires_fine_split_by_label": MULTIRES_FINE_SPLIT_BY_LABEL,
            "multires_fine_min_observations": MULTIRES_FINE_MIN_OBSERVATIONS,
            "multires_fine_takeover_min_points": MULTIRES_FINE_TAKEOVER_MIN_POINTS,
            "multires_risky_min_points": MULTIRES_RISKY_MIN_POINTS,
            "multires_replacement_mode": MULTIRES_REPLACEMENT_MODE,
            "geometry_repair_keep_labels": GEOMETRY_REPAIR_KEEP_LABELS,
            "geometry_repair_vent_to_sofa_delta": GEOMETRY_REPAIR_VENT_TO_SOFA_DELTA,
            "geometry_repair_cushion_shrink_radius": GEOMETRY_REPAIR_CUSHION_SHRINK_RADIUS,
            "geometry_repair_carve_rules": GEOMETRY_REPAIR_CARVE_RULES,
            "geometry_repair_large_label_rules": GEOMETRY_REPAIR_LARGE_LABEL_RULES,
            "geometry_repair_large_label_evidence_mode": GEOMETRY_REPAIR_LARGE_LABEL_EVIDENCE_MODE,
            "geometry_repair_large_label_source_mode": GEOMETRY_REPAIR_LARGE_LABEL_SOURCE_MODE,
            "geometry_repair_large_label_require_target_declared": GEOMETRY_REPAIR_LARGE_LABEL_REQUIRE_TARGET_DECLARED,
            "geometry_repair_large_label_max_point_rate": GEOMETRY_REPAIR_LARGE_LABEL_MAX_POINT_RATE,
            "geometry_repair_large_label_min_observations": GEOMETRY_REPAIR_LARGE_LABEL_MIN_OBSERVATIONS,
            "geometry_repair_large_label_min_source_share": GEOMETRY_REPAIR_LARGE_LABEL_MIN_SOURCE_SHARE,
            "min_mask_pixels": MIN_MASK_PIXELS,
            "mask_conf_threshold": MASK_CONF_THRESHOLD,
            "max_bbox_area_ratio": MAX_BBOX_AREA_RATIO,
            "min_valid_depth_points": MIN_VALID_DEPTH_POINTS,
            "drop_post_subtract_tiny": DROP_POST_SUBTRACT_TINY,
            "class_agnostic_identity_token": CLASS_AGNOSTIC_TOKEN,
            "max_points_per_obs": MAX_POINTS_PER_OBS,
            "max_points_per_object": MAX_POINTS_PER_OBJECT,
            "frame_limit": frame_limit,
            "frame_stride": frame_stride,
            "l2_occluded_after_misses": L2_OCCLUDED_AFTER_MISSES,
            "l2_dormant_after_misses": L2_DORMANT_AFTER_MISSES,
            "l2_retire_after_misses": L2_RETIRE_AFTER_MISSES,
            "l2_relation_bonus_weight": L2_RELATION_BONUS_WEIGHT,
            "l2_relation_bonus_cap": L2_RELATION_BONUS_CAP,
            "temporal_variant": TemporalVariant.NAIVE_FRAMEWISE.value,
            "mask_subtract_order": "conceptgraphs_filter_then_subtract",
        },
        "monitor": prep_monitor,
    }
    return frames, key_data, multires_key_data, prep, frame_debug


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


def summarize_l1_diagnostics(logger) -> dict[str, object]:
    records = logger.filter(event_type="current_hypothesis_emit")
    evidence_counts = []
    geometry_counts = []
    label_entropy_values = []
    label_top_share_values = []
    mixed_label_count = 0
    mixed_label_mass = 0.0
    neg_edge_count = 0
    merge_reasons = Counter()
    payload_labels = Counter()
    for record in records:
        payload = record.payload
        evidence_count = int(payload.get("evidence_count") or 0)
        geometry_count = int(payload.get("component_geometry_key_count") or 0)
        evidence_counts.append(evidence_count)
        geometry_counts.append(geometry_count)
        label_entropy = payload.get("label_entropy")
        label_top_share = payload.get("label_top_share")
        if label_entropy is not None:
            label_entropy_values.append(float(label_entropy))
        if label_top_share is not None:
            top_share = float(label_top_share)
            label_top_share_values.append(top_share)
            if top_share < 0.999:
                mixed_label_count += 1
                mixed_label_mass += max(0.0, 1.0 - top_share) * max(evidence_count, 1)
        neg_edge_count += int(payload.get("neg_edge_count") or 0)
        for reason in payload.get("merge_reasons") or []:
            merge_reasons[str(reason)] += 1
        label = str(payload.get("payload_label") or "")
        if label:
            payload_labels[label] += 1
    total_weight = max(sum(max(value, 1) for value in evidence_counts), 1)
    return {
        "hypothesis_count": len(records),
        "evidence_count": numeric_summary(evidence_counts),
        "component_geometry_key_count": numeric_summary(geometry_counts),
        "label_entropy": numeric_summary(label_entropy_values),
        "label_top_share": numeric_summary(label_top_share_values),
        "mixed_label_hypothesis_count": mixed_label_count,
        "mixed_label_hypothesis_rate": round(mixed_label_count / max(len(records), 1), 6),
        "mixed_label_mass": round(mixed_label_mass / total_weight, 6),
        "neg_edge_count": neg_edge_count,
        "merge_reasons": dict(merge_reasons),
        "top_payload_labels": payload_labels.most_common(15),
    }


def run_duograph(scene: str, frames: list[FrameInput]):
    t0 = time.time()
    phase = os.environ.get('DUOGRAPH_PHASE', 'baseline')
    l1_phases = ('l1', 'beta', 'gamma', 'delta', 'all')
    cand_phases = ('cand', 'beta', 'gamma', 'delta', 'all')
    tentative_phases = ('gamma', 'delta', 'all')
    entity_phases = ('delta', 'all')
    config = PipelineConfig(
        emit_association_diagnostics=True,
        association_diagnostics_top_k=ASSOCIATION_DIAGNOSTICS_TOP_K,
        occluded_after_misses=L2_OCCLUDED_AFTER_MISSES,
        dormant_after_misses=L2_DORMANT_AFTER_MISSES,
        retire_after_misses=L2_RETIRE_AFTER_MISSES,
        # Phase 乙: candidate v2 + signed L1
        l1_neg_edge_enable=(phase in l1_phases),
        l1_preserve_label_distribution=(phase in l1_phases),
        cand_include_adj_key=(phase in cand_phases),
        cand_include_ann=(phase in cand_phases),
        cand_track_sources=(phase in cand_phases),
        cand_adj_radius=1,
        cand_ann_top_k=8,
        candidate_retrieval_budget=32 if phase in cand_phases else 12,
        candidate_retrieval_channel_budget=8 if phase in cand_phases else 5,
        # Phase 丙: tentative/promotion/stable memory
        enable_tentative_fragments=(phase in tentative_phases),
        enable_stable_memory=(phase in tentative_phases),
        promotion_min_hits=3,
        # Phase 丁: equivalence partition
        entity_graph_enable=(phase in entity_phases),
        layer2_relation_bonus_weight=L2_RELATION_BONUS_WEIGHT,
        layer2_relation_bonus_cap=L2_RELATION_BONUS_CAP,
    )
    result, logger = DuoGraph3DPipeline(config).run_sequence(
        sequence_id=f"replica-{scene}-conceptgraphs-gsa-monitor",
        frames=frames,
        temporal_variant=TemporalVariant.NAIVE_FRAMEWISE,
        branch_id=BRANCH_DUOGRAPH3D,
    )
    summary = summarize_run(result, logger)
    summary["temporal_variant"] = TemporalVariant.NAIVE_FRAMEWISE.value
    summary["duograph_phase"] = phase
    summary["seconds"] = round(time.time() - t0, 3)
    summary["association_diagnostics"] = summarize_association_diagnostics(logger)
    summary["layer1_diagnostics"] = summarize_l1_diagnostics(logger)
    return result, logger, summary


def write_report(scene: str, prep: dict, branch_summary: dict, logger) -> Path:
    outdir = ROOT / "reports" / scene
    outdir.mkdir(parents=True, exist_ok=True)
    event_stream_path = outdir / f"event_stream_replica_{scene}_duograph3d_full.jsonl"
    export_event_stream_jsonl(logger, event_stream_path)
    shadow_metrics_dir = outdir / "shadow_metrics"
    shadow_report = generate_shadow_report(
        event_stream_path,
        run_id=f"{PRED_EXP_NAME}_{scene}",
        scene_id=scene,
        output_dir=shadow_metrics_dir,
    )
    diagnostic_sample = []
    for record in logger.records:
        if record.event_type in {
            "association_candidate_diagnostic",
            "association_birth_diagnostic",
            "association_frame_summary",
            "memory_relation_update",
            "memory_object_consolidation",
        }:
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
            "mask_subtract_order": "conceptgraphs_filter_then_subtract",
            "association_diagnostics_top_k": ASSOCIATION_DIAGNOSTICS_TOP_K,
            "l2_occluded_after_misses": L2_OCCLUDED_AFTER_MISSES,
            "l2_dormant_after_misses": L2_DORMANT_AFTER_MISSES,
            "l2_retire_after_misses": L2_RETIRE_AFTER_MISSES,
            "l2_relation_bonus_weight": L2_RELATION_BONUS_WEIGHT,
            "l2_relation_bonus_cap": L2_RELATION_BONUS_CAP,
        },
        "preparation_monitor": prep.get("monitor", {}),
        "branches": {BRANCH_DUOGRAPH3D: branch_summary},
        "branch_event_files": {
            BRANCH_DUOGRAPH3D: str(event_path),
            f"{BRANCH_DUOGRAPH3D}_jsonl": str(event_stream_path),
        },
        "shadow_metrics_dir": str(shadow_metrics_dir),
        "shadow_report_excerpt": {
            "candidate_recall": {
                key: value
                for key, value in (shadow_report.get("candidate_recall") or {}).items()
                if key != "rows"
            },
            "memory_purity": {
                key: value
                for key, value in (shadow_report.get("memory_purity") or {}).items()
                if key != "rows"
            },
            "promotion_pending": {
                key: value
                for key, value in (shadow_report.get("promotion_pending") or {}).items()
                if key != "step_counts"
            },
        },
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


def sanitize_point_color_arrays(points: object, colors: object) -> tuple[np.ndarray, np.ndarray]:
    pts = np.asarray(points, dtype=np.float32)
    if pts.ndim != 2 or pts.shape[1] < 3:
        return np.zeros((0, 3), dtype=np.float32), np.zeros((0, 3), dtype=np.float32)
    pts = pts[:, :3]
    finite = np.isfinite(pts).all(axis=1)
    pts = pts[finite]
    cols = np.asarray(colors, dtype=np.float32)
    if cols.ndim != 2 or cols.shape[0] != finite.shape[0] or cols.shape[1] < 3:
        cols = np.zeros((finite.shape[0], 3), dtype=np.float32)
    else:
        cols = cols[:, :3]
    cols = cols[finite]
    if not np.isfinite(cols).all():
        cols = np.nan_to_num(cols, nan=0.0, posinf=1.0, neginf=0.0)
    return pts.astype(np.float32, copy=False), cols.astype(np.float32, copy=False)


def make_open3d_pcd(points: np.ndarray, colors: np.ndarray) -> o3d.geometry.PointCloud:
    points, colors = sanitize_point_color_arrays(points, colors)
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


def _bucket_centroid(data: dict[str, object]) -> np.ndarray:
    count = max(int(data.get("feature_count", 0) or 0), 1)
    centroid_sum = np.asarray(data.get("centroid_sum", np.zeros(3, dtype=np.float64)), dtype=np.float64)
    if centroid_sum.shape != (3,):
        return np.zeros(3, dtype=np.float64)
    return centroid_sum / count


def _max_label_centroid_separation(label_buckets: dict[str, dict[str, object]]) -> float:
    centroids = [
        _bucket_centroid(label_data)
        for label_data in label_buckets.values()
        if int(label_data.get("feature_count", 0) or 0) >= EXPORT_SPLIT_MIN_OBSERVATIONS
    ]
    if len(centroids) < 2:
        return 0.0
    max_distance = 0.0
    for left_i, left in enumerate(centroids):
        for right in centroids[left_i + 1:]:
            max_distance = max(max_distance, float(np.linalg.norm(left - right)))
    return round(max_distance, 6)


def should_split_export_key(data: dict[str, object]) -> tuple[bool, dict[str, object]]:
    label_buckets = data.get("label_buckets") or {}
    label_counts = data.get("label_counts") or Counter()
    if not EXPORT_SPLIT_BY_LABEL or not label_buckets or len(label_buckets) <= 1:
        return False, {"reason": "disabled_or_single_label"}
    if EXPORT_SPLIT_POLICY == "all":
        return True, {"reason": "all"}
    entropy_value = label_entropy(label_counts)
    top_share_value = label_top_share(label_counts)
    separation = _max_label_centroid_separation(label_buckets)
    split = (
        entropy_value >= EXPORT_SPLIT_MIN_KEY_ENTROPY
        and top_share_value <= EXPORT_SPLIT_MAX_KEY_TOP_SHARE
        and separation >= EXPORT_SPLIT_MIN_CENTROID_SEPARATION
    )
    return split, {
        "reason": "adaptive_pass" if split else "adaptive_reject",
        "label_entropy": entropy_value,
        "top_label_share": top_share_value,
        "max_label_centroid_separation": separation,
    }


def export_scene_split_gate(key_data: dict[str, dict[str, object]]) -> dict[str, object]:
    if not EXPORT_SPLIT_BY_LABEL:
        return {"allowed": False, "candidate_split_key_count": 0, "candidate_split_key_rate": 0.0, "reason": "disabled"}
    candidate_count = 0
    for data in key_data.values():
        split, _debug = should_split_export_key(data)
        if split:
            candidate_count += 1
    rate = candidate_count / max(len(key_data), 1)
    allowed = rate >= EXPORT_SPLIT_MIN_SCENE_SPLIT_RATE
    return {
        "allowed": allowed,
        "candidate_split_key_count": candidate_count,
        "candidate_split_key_rate": round(rate, 6),
        "min_scene_split_rate": EXPORT_SPLIT_MIN_SCENE_SPLIT_RATE,
        "reason": "scene_split_rate_pass" if allowed else "scene_split_rate_below_threshold",
    }


def iter_key_export_items(
    key_data: dict[str, dict[str, object]],
) -> list[tuple[str, str, dict[str, object], str]]:
    export_items: list[tuple[str, str, dict[str, object], str]] = []
    scene_gate = export_scene_split_gate(key_data)
    scene_allows_split = bool(scene_gate.get("allowed", False))
    for key, data in sorted(key_data.items()):
        label_buckets = data.get("label_buckets") or {}
        should_split, _split_debug = should_split_export_key(data)
        if scene_allows_split and should_split:
            total_count = max(int(data.get("feature_count", 0) or 0), 1)
            for label, label_data in sorted(label_buckets.items()):
                label_count = int(label_data.get("feature_count", 0) or 0)
                label_share = label_count / total_count
                if label_count < EXPORT_SPLIT_MIN_OBSERVATIONS:
                    continue
                if label_share < EXPORT_SPLIT_MIN_LABEL_SHARE:
                    continue
                export_items.append((key, f"{key}:label:{label}", label_data, str(label)))
            if export_items and any(item[0] == key for item in export_items):
                continue
            label = str(data["label_counts"].most_common(1)[0][0])
            export_items.append((key, key, data, label))
        else:
            label = str(data["label_counts"].most_common(1)[0][0])
            export_items.append((key, key, data, label))
    return export_items


def parse_label_set(value: str) -> set[str]:
    return {item.strip() for item in str(value or "").split(",") if item.strip()}


def iter_plain_key_export_items(
    key_data: dict[str, dict[str, object]],
    *,
    allowed_labels: set[str] | None = None,
    export_suffix: str = "",
) -> list[tuple[str, str, dict[str, object], str]]:
    export_items: list[tuple[str, str, dict[str, object], str]] = []
    for key, data in sorted(key_data.items()):
        label = str(data["label_counts"].most_common(1)[0][0])
        if allowed_labels is not None and label not in allowed_labels:
            continue
        export_key = f"{key}{export_suffix}" if export_suffix else key
        export_items.append((key, export_key, data, label))
    return export_items


def iter_label_bucket_export_items(
    key_data: dict[str, dict[str, object]],
    *,
    allowed_labels: set[str] | None = None,
    min_observations: int = 1,
    export_suffix: str = "",
) -> list[tuple[str, str, dict[str, object], str]]:
    export_items: list[tuple[str, str, dict[str, object], str]] = []
    for key, data in sorted(key_data.items()):
        label_buckets = data.get("label_buckets") or {}
        for label, label_data in sorted(label_buckets.items()):
            if allowed_labels is not None and label not in allowed_labels:
                continue
            if int(label_data.get("feature_count", 0) or 0) < min_observations:
                continue
            export_key = f"{key}{export_suffix}:label:{label}" if export_suffix else f"{key}:label:{label}"
            export_items.append((key, export_key, label_data, str(label)))
    return export_items


def summarize_export_split_decisions(key_data: dict[str, dict[str, object]]) -> dict[str, object]:
    reason_counts: Counter[str] = Counter()
    split_key_count = 0
    exported_bucket_count = 0
    separation_values = []
    entropy_values = []
    top_share_values = []
    for _key, data in sorted(key_data.items()):
        split, debug = should_split_export_key(data)
        reason = str(debug.get("reason", "unknown"))
        reason_counts[reason] += 1
        if "max_label_centroid_separation" in debug:
            separation_values.append(float(debug["max_label_centroid_separation"]))
        if "label_entropy" in debug:
            entropy_values.append(float(debug["label_entropy"]))
        if "top_label_share" in debug:
            top_share_values.append(float(debug["top_label_share"]))
        if split:
            split_key_count += 1
            total_count = max(int(data.get("feature_count", 0) or 0), 1)
            for label_data in (data.get("label_buckets") or {}).values():
                label_count = int(label_data.get("feature_count", 0) or 0)
                if label_count < EXPORT_SPLIT_MIN_OBSERVATIONS:
                    continue
                if label_count / total_count < EXPORT_SPLIT_MIN_LABEL_SHARE:
                    continue
                exported_bucket_count += 1
    return {
        "export_split_by_label": EXPORT_SPLIT_BY_LABEL,
        "export_split_policy": EXPORT_SPLIT_POLICY,
        "export_split_min_observations": EXPORT_SPLIT_MIN_OBSERVATIONS,
        "export_split_min_key_entropy": EXPORT_SPLIT_MIN_KEY_ENTROPY,
        "export_split_max_key_top_share": EXPORT_SPLIT_MAX_KEY_TOP_SHARE,
        "export_split_min_label_share": EXPORT_SPLIT_MIN_LABEL_SHARE,
        "export_split_min_centroid_separation": EXPORT_SPLIT_MIN_CENTROID_SEPARATION,
        "export_split_min_scene_split_rate": EXPORT_SPLIT_MIN_SCENE_SPLIT_RATE,
        "scene_split_gate": export_scene_split_gate(key_data),
        "key_count": len(key_data),
        "split_key_count": split_key_count,
        "split_key_rate": round(split_key_count / max(len(key_data), 1), 6),
        "exported_split_bucket_count": exported_bucket_count,
        "decision_reasons": dict(reason_counts),
        "candidate_key_label_entropy": numeric_summary(entropy_values),
        "candidate_key_top_label_share": numeric_summary(top_share_values),
        "candidate_key_max_label_centroid_separation": numeric_summary(separation_values),
    }


def iter_memory_dense_export_items(
    key_data: dict[str, dict[str, object]],
) -> list[tuple[str, str, dict[str, object], str]]:
    """Return dense geometry chunks for online-memory export.

    Online memory root IDs remain the identity authority, but a root can become a
    mixed semantic bucket after aggressive identity repair.  Splitting the dense
    export by the original per-key label bucket prevents a large mixed root from
    collapsing minority classes (for example pillow) into the majority label.
    """

    if not MEMORY_DENSE_SPLIT_BY_LABEL:
        return iter_key_export_items(key_data)
    export_items: list[tuple[str, str, dict[str, object], str]] = []
    for key, data in sorted(key_data.items()):
        label_buckets = data.get("label_buckets") or {}
        if not label_buckets:
            label = str(data["label_counts"].most_common(1)[0][0])
            export_items.append((key, key, data, label))
            continue
        for label, label_data in sorted(label_buckets.items()):
            if int(label_data.get("feature_count", 0) or 0) < MEMORY_DENSE_SPLIT_MIN_OBSERVATIONS:
                continue
            export_items.append((key, f"{key}:label:{label}", label_data, str(label)))
    return export_items


def should_split_memory_dense_root(label_counts: Counter) -> bool:
    if not MEMORY_DENSE_SPLIT_BY_LABEL:
        return False
    if len(label_counts) <= 1:
        return False
    return (
        label_entropy(label_counts) >= MEMORY_DENSE_SPLIT_MIN_ROOT_LABEL_ENTROPY
        and label_top_share(label_counts) <= MEMORY_DENSE_SPLIT_MAX_ROOT_TOP_SHARE
    )


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
    class_feats_np: np.ndarray,
    *,
    export_items: list[tuple[str, str, dict[str, object], str]] | None = None,
    carrier: str = "coarse_geometry",
) -> tuple[MapObjectList, list[dict[str, object]], list[str]]:
    cfg = conceptgraphs_postprocess_cfg()
    objects = MapObjectList()
    export_debug = []
    skipped_keys = []
    if export_items is None:
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
        clip_ft, clip_readout_debug = selected_export_clip_feature(
            data,
            label=label,
            label_to_index=label_to_index,
            class_feats_np=class_feats_np,
        )
        text_ft = average_feature(data, "text_sum")
        conf = float(data["confidence_sum"] / count)
        object_ids = track_assignments.get(base_key, [])
        obj = {
            "image_idx": [],
            "mask_idx": [],
            "color_path": [],
            "class_name": [label],
            "class_id": [int(label_to_index.get(label, -1))],
            "declared_label_counts": [[str(k), int(v)] for k, v in sorted((data.get("label_counts") or {}).items())],
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
            "export_clip_min_margin": EXPORT_CLIP_MIN_MARGIN,
            "export_clip_count": int(data.get("export_clip_count", 0) or 0),
            **clip_readout_debug,
            "carrier": carrier,
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
        points, colors = sanitize_point_color_arrays(node.sampled_points, node.sampled_colors)
        if len(points) < 4:
            skipped.append(f"{object_id}:invalid_sampled_points")
            continue
        if len(points) > MAX_POINTS_PER_OBJECT:
            keep = sample_indices(len(points), MAX_POINTS_PER_OBJECT)
            points = points[keep]
            colors = colors[keep]
        label = ObjectGraphMemory.dominant_semantic_label(node) or node.appearance_key_recent or node.descriptor_recent
        label_index = int(label_to_index.get(label, -1))
        text_ft = np.asarray(node.text_feature, dtype=np.float32)
        if text_ft.shape != class_feats_np[0].shape:
            text_ft = class_agnostic_text_anchor(class_feats_np.shape[1]).astype(np.float32)
        clip_ft = np.asarray(node.clip_feature, dtype=np.float32)
        if clip_ft.shape != text_ft.shape:
            clip_ft = text_ft
        clip_ft = selected_clip_feature(
            clip_ft,
            label=label,
            label_to_index=label_to_index,
            class_feats_np=class_feats_np,
        )
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
            "declared_label_counts": [[str(k), int(v)] for k, v in sorted((node.class_counts or {}).items())],
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
    class_feats_np: np.ndarray,
) -> tuple[MapObjectList, list[dict[str, object]], list[str], dict[str, object]]:
    """Export online memory IDs with dense ConceptGraphs-style geometry.

    The online memory node is the object authority, but its `sampled_points` are
    intentionally capped for matching speed.  For official mIoU, reuse the dense
    per-geometry-key points staged from GSA masks and group those keys by the
    memory root selected by Layer2/merge aliases.
    """

    cfg = conceptgraphs_postprocess_cfg()
    root_buckets: dict[str, dict[str, object]] = {}
    bucket_members: dict[str, list] = {}
    skipped: list[str] = []
    assignment_status_counts: Counter[str] = Counter()
    raw_assignment_status_counts: Counter[str] = Counter()
    root_share_values = []
    ambiguous_examples = []
    export_items = iter_memory_dense_export_items(key_data)
    root_label_counts: dict[str, Counter] = defaultdict(Counter)
    for base_key, _export_key, data, _label in export_items:
        root_id, _assignment_debug = dominant_memory_root_for_key(base_key, track_assignments, result.memory_nodes)
        if not root_id:
            continue
        node = result.memory_nodes.get(root_id)
        if node is None:
            continue
        skip_reason = ObjectGraphMemory.export_skip_reason(
            node,
            min_points=0,
            min_detections=MIN_OBJECT_DETECTIONS,
        )
        if skip_reason:
            continue
        root_label_counts[root_id].update(data["label_counts"])
    split_root_ids = {root_id for root_id, counts in root_label_counts.items() if should_split_memory_dense_root(counts)}
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
        if not use_geometry_fallback and label and root_id in split_root_ids:
            bucket_id = f"{root_id}:label:{label}"
        bucket_members.setdefault(bucket_id, []).append(
            (base_key, export_key, data, label, root_id, use_geometry_fallback, status)
        )

    # O2b spatial coherence split: keys assigned to one bucket that are not
    # spatially connected become separate buckets, each re-accumulated from its
    # own keys (features/labels recomputed per component).
    spatial_split_stats = {"enabled": bool(MEMORY_DENSE_SPATIAL_SPLIT), "buckets_split": 0, "components_created": 0}
    final_members: dict[str, list] = {}
    for bucket_id, members in bucket_members.items():
        if not MEMORY_DENSE_SPATIAL_SPLIT or len(members) < 2:
            final_members[bucket_id] = members
            continue
        centroids = []
        for _base_key, _export_key, data, *_rest in members:
            pts = np.concatenate([np.asarray(p, dtype=np.float32) for p in data["points"]], axis=0) if data["points"] else np.zeros((1, 3), dtype=np.float32)
            centroids.append(pts.mean(axis=0))
        components = spatial_connected_components(centroids, MEMORY_DENSE_SPATIAL_SPLIT_EPS)
        if len(components) <= 1:
            final_members[bucket_id] = members
            continue
        spatial_split_stats["buckets_split"] += 1
        spatial_split_stats["components_created"] += len(components)
        for comp_i, comp in enumerate(components):
            final_members[f"{bucket_id}:sp{comp_i}"] = [members[i] for i in comp]

    for bucket_id, members in final_members.items():
        for base_key, export_key, data, label, root_id, use_geometry_fallback, status in members:
            bucket = root_buckets.setdefault(
                bucket_id,
                {
                    "label_counts": Counter(),
                    "clip_sum": np.zeros_like(np.asarray(data["clip_sum"], dtype=np.float64), dtype=np.float64),
                    "export_clip_sum": np.zeros_like(np.asarray(data["clip_sum"], dtype=np.float64), dtype=np.float64),
                    "export_clip_count": 0,
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
                    "split_labels": Counter(),
                },
            )
            bucket["label_counts"].update(data["label_counts"])
            bucket["clip_sum"] += np.asarray(data["clip_sum"], dtype=np.float64)
            bucket["export_clip_sum"] += np.asarray(data.get("export_clip_sum", np.zeros_like(data["clip_sum"])), dtype=np.float64)
            bucket["export_clip_count"] += int(data.get("export_clip_count", 0) or 0)
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
            if label:
                bucket["split_labels"][label] += int(data["feature_count"])

    objects = MapObjectList()
    export_debug = []
    export_label_entropy = []
    export_label_top_share = []
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
        entropy_value = label_entropy(label_counts)
        top_share_value = label_top_share(label_counts)
        export_label_entropy.append(entropy_value)
        export_label_top_share.append(top_share_value)
        label_index = int(label_to_index.get(label, -1))
        count = max(int(data["feature_count"]), 1)
        export_clip_count = int(data.get("export_clip_count", 0) or 0)
        clip_ft, clip_readout_debug = selected_export_clip_feature(
            data,
            label=label,
            label_to_index=label_to_index,
            class_feats_np=class_feats_np,
        )
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
            "declared_label_counts": [[str(k), int(v)] for k, v in sorted((data.get("label_counts") or {}).items())],
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
            "label_counts": dict(label_counts),
            "label_entropy": entropy_value,
            "top_label_share": top_share_value,
            "split_labels": dict(data["split_labels"]),
            "num_detections": count,
            "point_count_before_postprocess": int(len(pts)),
            "point_count_after_key_denoise": int(len(pcd.points)),
            "fragment_object_count": len(geometry_keys),
            "mask_pixels": int(data["mask_pixels"]),
            "avg_valid_depth_ratio": round(float(data["valid_depth_ratio_sum"] / count), 6),
            "avg_clip_margin": round(float(data["clip_margin_sum"] / count), 6),
            "export_clip_min_margin": EXPORT_CLIP_MIN_MARGIN,
            "export_clip_count": export_clip_count,
            **clip_readout_debug,
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
        "export_label_entropy": numeric_summary(export_label_entropy),
        "export_top_label_share": numeric_summary(export_label_top_share),
        "memory_dense_min_root_share": MEMORY_DENSE_MIN_ROOT_SHARE,
        "memory_dense_geometry_fallback": MEMORY_DENSE_GEOMETRY_FALLBACK,
        "memory_dense_split_by_label": MEMORY_DENSE_SPLIT_BY_LABEL,
        "memory_dense_split_min_observations": MEMORY_DENSE_SPLIT_MIN_OBSERVATIONS,
        "memory_dense_split_min_root_label_entropy": MEMORY_DENSE_SPLIT_MIN_ROOT_LABEL_ENTROPY,
        "memory_dense_split_max_root_top_share": MEMORY_DENSE_SPLIT_MAX_ROOT_TOP_SHARE,
        "memory_dense_split_root_count": len(split_root_ids),
        "memory_dense_split_root_rate": round(len(split_root_ids) / max(len(root_label_counts), 1), 6),
        "memory_dense_spatial_split": spatial_split_stats,
        "memory_dense_spatial_split_eps": MEMORY_DENSE_SPATIAL_SPLIT_EPS,
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


def merge_objects_with_label_gate(cfg, objects: MapObjectList) -> tuple[MapObjectList, dict[str, object]]:
    """ConceptGraphs merge_overlap_objects with a per-pair label-cluster veto.

    Mirrors the legacy loop exactly (same pair ordering, same overlap/visual/text
    thresholds, same kept-object bookkeeping) so any behavior difference is
    attributable to the veto alone: pairs CG would merge are skipped only when
    `label_cluster_veto` finds two distinct, well-supported declared-label
    clusters.  Every veto is recorded for the export monitor.
    """
    gate_probe: dict[str, object] = {
        "enabled": True,
        "min_top_share": CG_MERGE_LABEL_GATE_MIN_SHARE,
        "min_observations": CG_MERGE_LABEL_GATE_MIN_OBS,
        "legacy_merge_candidate_pairs": 0,
        "merged_pairs": 0,
        "vetoed_pairs": 0,
        "veto_label_pairs": {},
        "veto_examples": [],
        "merged_examples": [],
        "no_veto_reasons": {},
    }
    if cfg.merge_overlap_thresh <= 0 or len(objects) == 0:
        return objects, gate_probe
    overlap_matrix = compute_overlap_matrix(cfg, objects)
    x, y = overlap_matrix.nonzero()
    overlap_ratio = overlap_matrix[x, y]
    sort = np.argsort(overlap_ratio)[::-1]
    x = x[sort]
    y = y[sort]
    overlap_ratio = overlap_ratio[sort]
    kept_objects = np.ones(len(objects), dtype=bool)
    veto_label_pairs: Counter[str] = Counter()
    no_veto_reasons: Counter[str] = Counter()
    for i, j, ratio in zip(x, y, overlap_ratio):
        if ratio <= cfg.merge_overlap_thresh:
            break
        visual_sim = float(F.cosine_similarity(to_tensor(objects[i]["clip_ft"]), to_tensor(objects[j]["clip_ft"]), dim=0))
        text_sim = float(F.cosine_similarity(to_tensor(objects[i]["text_ft"]), to_tensor(objects[j]["text_ft"]), dim=0))
        if visual_sim <= cfg.merge_visual_sim_thresh or text_sim <= cfg.merge_text_sim_thresh:
            continue
        gate_probe["legacy_merge_candidate_pairs"] = int(gate_probe["legacy_merge_candidate_pairs"]) + 1
        reverse_ratio = float(overlap_matrix[j, i])
        mutual_containment = (
            CG_MERGE_LABEL_GATE_MUTUAL_THRESH >= 0.0
            and reverse_ratio > CG_MERGE_LABEL_GATE_MUTUAL_THRESH
        )
        veto_info = label_cluster_veto(
            dict(object_declared_label_counts(objects[i])),
            dict(object_declared_label_counts(objects[j])),
            min_top_share=CG_MERGE_LABEL_GATE_MIN_SHARE,
            min_observations=CG_MERGE_LABEL_GATE_MIN_OBS,
        )
        if mutual_containment and veto_info["veto"]:
            veto_info = dict(veto_info)
            veto_info["veto"] = False
            veto_info["reason"] = "mutual_containment"
        if veto_info["veto"]:
            gate_probe["vetoed_pairs"] = int(gate_probe["vetoed_pairs"]) + 1
            veto_label_pairs[f"{veto_info['left_top']}|{veto_info['right_top']}"] += 1
            if len(gate_probe["veto_examples"]) < 20:
                gate_probe["veto_examples"].append({
                    "overlap_ratio": round(float(ratio), 4),
                    "visual_sim": round(visual_sim, 4),
                    "text_sim": round(text_sim, 4),
                    **{k: veto_info[k] for k in (
                        "left_top", "left_share", "left_observations",
                        "right_top", "right_share", "right_observations",
                    )},
                })
            continue
        no_veto_reasons[str(veto_info["reason"])] += 1
        if len(gate_probe["merged_examples"]) < 20:
            gate_probe["merged_examples"].append({
                "overlap_ratio": round(float(ratio), 4),
                "visual_sim": round(visual_sim, 4),
                "text_sim": round(text_sim, 4),
                "no_veto_reason": veto_info["reason"],
                **{k: veto_info[k] for k in (
                    "left_top", "left_share", "left_observations",
                    "right_top", "right_share", "right_observations",
                )},
            })
        if kept_objects[j]:
            # declared_label_counts is a list of [label, count] pairs, so CG's
            # list-concatenation merge accumulates the two distributions.
            objects[j] = merge_obj2_into_obj1(cfg, objects[j], objects[i], run_dbscan=True)
            kept_objects[i] = False
            gate_probe["merged_pairs"] = int(gate_probe["merged_pairs"]) + 1
    gate_probe["veto_label_pairs"] = dict(veto_label_pairs)
    gate_probe["no_veto_reasons"] = dict(no_veto_reasons)
    new_objects = [obj for obj, keep in zip(objects, kept_objects) if keep]
    return MapObjectList(new_objects), gate_probe


def postprocess_map_objects(
    cfg,
    initial_objects: MapObjectList,
    *,
    gate_enabled: bool | None = None,
) -> tuple[MapObjectList, dict[str, object]]:
    pre_postprocess_count = len(initial_objects)
    objects = denoise_objects(cfg, initial_objects)
    post_denoise_count = len(objects)
    objects = filter_objects(cfg, objects)
    post_filter_count = len(objects)
    use_gate = bool(CG_MERGE_LABEL_GATE) if gate_enabled is None else bool(gate_enabled)
    if use_gate:
        objects, label_gate_probe = merge_objects_with_label_gate(cfg, objects)
    else:
        objects = merge_objects(cfg, objects)
        label_gate_probe = {"enabled": False}
    post_merge_count = len(objects)
    cap_object_points(objects, cfg)
    return objects, {
        "initial_object_count": pre_postprocess_count,
        "post_denoise_object_count": post_denoise_count,
        "post_filter_object_count": post_filter_count,
        "post_merge_object_count": post_merge_count,
        "label_gate_probe": label_gate_probe,
    }


def object_point_count(obj: dict[str, object]) -> int:
    if "pcd" in obj:
        try:
            return int(len(obj["pcd"].points))
        except Exception:
            pass
    if "pcd_np" in obj:
        try:
            return int(len(obj["pcd_np"]))
        except Exception:
            pass
    n_points = obj.get("n_points")
    if isinstance(n_points, list) and n_points:
        return int(max(int(value) for value in n_points))
    if n_points is not None:
        return int(n_points)
    return 0


def object_declared_labels(obj: dict[str, object]) -> set[str]:
    labels = obj.get("class_name", [])
    if isinstance(labels, str):
        return {labels}
    return {str(label) for label in labels if str(label)}


def object_declared_label_counts(obj: dict[str, object]) -> Counter[str]:
    # Prefer the true multi-view declared distribution attached at export-object
    # construction; `class_name` only carries the single aggregated readout label
    # and cannot support share/observation evidence.
    declared = obj.get("declared_label_counts")
    if declared:
        counter: Counter[str] = Counter()
        # Stored as a list of [label, count] pairs so ConceptGraphs'
        # merge_obj2_into_obj1 list-concatenation merges it losslessly
        # (dict-valued fields would raise NotImplementedError there).
        items = declared.items() if isinstance(declared, dict) else declared
        for entry in items:
            try:
                label, count = entry
                value = int(count)
            except (TypeError, ValueError):
                continue
            if value > 0 and str(label):
                counter[str(label)] += value
        if counter:
            return counter
    labels = obj.get("class_name", [])
    counter = Counter()
    if isinstance(labels, str):
        if labels:
            counter[str(labels)] += 1
        return counter
    if isinstance(labels, (list, tuple)):
        for label in labels:
            text = str(label)
            if text:
                counter[text] += 1
    return counter


def object_detection_count(obj: dict[str, object]) -> int:
    value = obj.get("num_detections")
    if isinstance(value, (list, tuple)):
        total = 0
        for item in value:
            try:
                total += int(item)
            except (TypeError, ValueError):
                continue
        return total
    try:
        return int(value)
    except (TypeError, ValueError):
        return 0


def object_clip_pred_label(obj: dict[str, object], class_feats_np: np.ndarray, index_to_label: dict[int, str]) -> str:
    clip_ft = obj.get("clip_ft")
    if clip_ft is None:
        return ""
    if isinstance(clip_ft, torch.Tensor):
        feature = clip_ft.detach().cpu().numpy()
    else:
        feature = np.asarray(clip_ft)
    feature = np.asarray(feature, dtype=np.float32).reshape(-1)
    if feature.size == 0:
        return ""
    sims = feature @ class_feats_np.T
    return index_to_label.get(int(np.argmax(sims)), "")


def object_semantic_candidates(obj: dict[str, object], class_feats_np: np.ndarray, index_to_label: dict[int, str]) -> set[str]:
    labels = object_declared_labels(obj)
    pred_label = object_clip_pred_label(obj, class_feats_np, index_to_label)
    if pred_label:
        labels.add(pred_label)
    return labels


def apply_multires_replacement(
    coarse_objects: MapObjectList,
    fine_objects: MapObjectList,
    *,
    class_feats_np: np.ndarray,
    label_to_index: dict[str, int],
) -> tuple[MapObjectList, dict[str, object]]:
    fine_labels = parse_label_set(MULTIRES_FINE_LABELS)
    risky_labels = parse_label_set(MULTIRES_RISKY_LABELS)
    replacement_mode = str(MULTIRES_REPLACEMENT_MODE or "replace").lower().replace("_", "-")
    index_to_label = {index: label for label, index in label_to_index.items()}
    kept = MapObjectList()
    dropped_reasons: Counter[str] = Counter()
    dropped_labels: Counter[str] = Counter()
    retained_takeover_candidates: Counter[str] = Counter()
    dropped_points = []
    for obj in coarse_objects:
        point_count = object_point_count(obj)
        labels = object_semantic_candidates(obj, class_feats_np, index_to_label)
        fine_label_hit = point_count >= MULTIRES_FINE_TAKEOVER_MIN_POINTS and bool(labels & fine_labels)
        risky_large_hit = point_count >= MULTIRES_RISKY_MIN_POINTS and bool(labels & risky_labels)
        drop_fine = replacement_mode == "replace" and fine_label_hit
        drop_risky = replacement_mode in {"replace", "risky-replace"} and risky_large_hit
        if drop_fine or drop_risky:
            if drop_fine and drop_risky:
                reason = "fine_label_and_risky_takeover"
            elif drop_fine:
                reason = "fine_label_takeover"
            else:
                reason = "risky_large_takeover"
            dropped_reasons[reason] += 1
            for label in sorted(labels):
                if label in fine_labels or label in risky_labels:
                    dropped_labels[label] += 1
            dropped_points.append(point_count)
            continue
        if fine_label_hit:
            retained_takeover_candidates["fine_label_candidate_retained"] += 1
        if risky_large_hit:
            retained_takeover_candidates["risky_large_candidate_retained"] += 1
        kept.append(obj)
    combined = MapObjectList()
    for obj in kept:
        combined.append(obj)
    for obj in fine_objects:
        combined.append(obj)
    fine_labels_added: Counter[str] = Counter()
    for obj in fine_objects:
        for label in object_declared_labels(obj):
            fine_labels_added[label] += 1
    diagnostics = {
        "enabled": True,
        "replacement_mode": replacement_mode,
        "fine_voxel_size": MULTIRES_FINE_VOXEL_SIZE,
        "fine_labels": sorted(fine_labels),
        "risky_labels": sorted(risky_labels),
        "fine_split_by_label": MULTIRES_FINE_SPLIT_BY_LABEL,
        "fine_min_observations": MULTIRES_FINE_MIN_OBSERVATIONS,
        "fine_takeover_min_points": MULTIRES_FINE_TAKEOVER_MIN_POINTS,
        "risky_min_points": MULTIRES_RISKY_MIN_POINTS,
        "coarse_post_merge_count": len(coarse_objects),
        "fine_post_merge_count": len(fine_objects),
        "kept_coarse_count": len(kept),
        "dropped_coarse_count": len(coarse_objects) - len(kept),
        "final_object_count": len(combined),
        "drop_reasons": dict(dropped_reasons),
        "drop_label_counts": dict(dropped_labels),
        "retained_takeover_candidate_counts": dict(retained_takeover_candidates),
        "dropped_point_count": numeric_summary(dropped_points),
        "fine_added_label_counts": dict(fine_labels_added),
    }
    return combined, diagnostics


def derive_auto_keep_labels(objects: MapObjectList, min_count: int) -> tuple[set[str], dict[str, int]]:
    """Scene-adaptive evaluator-facing source set from multi-view declared labels.

    GT-free replacement for hand-written per-scene keep lists (the office2
    16-label set): a label enters the repair source authority set when the
    scene's own detections declared it at least `min_count` times.
    """
    scene_counts: Counter[str] = Counter()
    for obj in objects:
        for label, count in object_declared_label_counts(obj).items():
            scene_counts[label] += count
    auto = {
        label
        for label, count in scene_counts.items()
        if count >= max(min_count, 1) and label not in STRUCTURAL_EXPORT_LABELS
    }
    return auto, dict(scene_counts)


def geometry_repair_keep_indices(
    label_to_index: dict[str, int],
    objects: MapObjectList | None = None,
) -> tuple[list[int], dict[str, object]]:
    keep_mode = str(GEOMETRY_REPAIR_KEEP_MODE or "configured").lower().replace("_", "-")
    keep_diag: dict[str, object] = {"keep_mode": keep_mode}
    configured = parse_label_set(GEOMETRY_REPAIR_KEEP_LABELS)
    if keep_mode == "declared-auto" and objects is not None:
        auto, scene_counts = derive_auto_keep_labels(objects, GEOMETRY_REPAIR_KEEP_AUTO_MIN_COUNT)
        keep_diag["auto_min_count"] = GEOMETRY_REPAIR_KEEP_AUTO_MIN_COUNT
        keep_diag["auto_label_count"] = len(auto)
        keep_diag["auto_labels"] = sorted(auto)
        keep_diag["scene_declared_totals"] = {
            label: count for label, count in sorted(scene_counts.items(), key=lambda kv: -kv[1])[:40]
        }
        if auto:
            configured = auto
        else:
            keep_diag["auto_fallback"] = "empty_auto_set_uses_broad_default"
    if not configured:
        configured = set(label_to_index) - set(STRUCTURAL_EXPORT_LABELS)
    indices = sorted(label_to_index[label] for label in configured if label in label_to_index)
    return indices, keep_diag


def object_repair_scores(
    obj: dict[str, object],
    class_feats_np: np.ndarray,
) -> np.ndarray:
    clip_ft = obj.get("clip_ft")
    if clip_ft is None:
        return np.zeros((len(class_feats_np),), dtype=np.float32)
    if isinstance(clip_ft, torch.Tensor):
        feature = clip_ft.detach().cpu().numpy()
    else:
        feature = np.asarray(clip_ft)
    feature = np.asarray(feature, dtype=np.float32).reshape(-1)
    norm = float(np.linalg.norm(feature))
    if norm > 0:
        feature = feature / norm
    return (feature @ class_feats_np.T).astype(np.float32)


def object_repair_pred_label(
    obj: dict[str, object],
    class_feats_np: np.ndarray,
    keep_indices: list[int],
    index_to_label: dict[int, str],
) -> tuple[str, np.ndarray]:
    scores = object_repair_scores(obj, class_feats_np)
    if not keep_indices:
        return index_to_label.get(int(np.argmax(scores)), ""), scores
    masked = np.full_like(scores, -1e10)
    masked[keep_indices] = scores[keep_indices]
    return index_to_label.get(int(np.argmax(masked)), ""), scores


def top_repair_score_labels(
    scores: np.ndarray,
    keep_indices: list[int],
    index_to_label: dict[int, str],
    *,
    limit: int = 5,
) -> list[dict[str, object]]:
    if scores.size == 0 or limit <= 0:
        return []
    if keep_indices:
        candidate_indices = list(keep_indices)
    else:
        candidate_indices = list(range(len(scores)))
    ranked = sorted(
        candidate_indices,
        key=lambda index: float(scores[index]) if 0 <= index < len(scores) else -1e10,
        reverse=True,
    )
    items: list[dict[str, object]] = []
    for index in ranked[:limit]:
        label = index_to_label.get(int(index), "")
        if not label:
            continue
        items.append({"label": label, "score": round(float(scores[index]), 6)})
    return items


def force_object_label_feature(
    obj: dict[str, object],
    label: str,
    *,
    label_to_index: dict[str, int],
    class_feats_np: np.ndarray,
) -> None:
    label_index = label_to_index.get(label)
    if label_index is None:
        return
    feature = normalize_np(np.asarray(class_feats_np[label_index], dtype=np.float32).reshape(1, -1))[0]
    obj["clip_ft"] = torch.from_numpy(feature.astype(np.float32))
    obj["text_ft"] = torch.from_numpy(feature.astype(np.float32))


def nearest_distance_to_points(points: np.ndarray, anchors: np.ndarray) -> np.ndarray:
    if len(points) == 0 or len(anchors) == 0:
        return np.full((len(points),), np.inf, dtype=np.float32)
    anchor_pcd = make_open3d_pcd(np.asarray(anchors, dtype=np.float32), np.zeros_like(anchors, dtype=np.float32))
    tree = o3d.geometry.KDTreeFlann(anchor_pcd)
    distances = np.full((len(points),), np.inf, dtype=np.float32)
    for idx, point in enumerate(np.asarray(points, dtype=np.float64)):
        count, _indices, dist2 = tree.search_knn_vector_3d(point, 1)
        if count:
            distances[idx] = float(math.sqrt(max(float(dist2[0]), 0.0)))
    return distances


def parse_geometry_carve_rules(value: str) -> list[tuple[str, str, float]]:
    """Parse target:anchor:radius geometry-carve rules.

    A rule `cushion:sofa:0.04` removes target-carrier points whose nearest
    distance to any anchor-carrier point is <= 4 cm.  The parser is deliberately
    small and strict enough to make experiment logs reproducible while still
    allowing comma/semicolon separated sweeps from shell scripts.
    """

    rules: list[tuple[str, str, float]] = []
    for raw_item in str(value or "").replace(";", ",").split(","):
        item = raw_item.strip()
        if not item:
            continue
        parts = [part.strip() for part in item.split(":")]
        if len(parts) != 3:
            raise ValueError(f"invalid geometry carve rule {item!r}; expected target:anchor:radius")
        target, anchor, radius_text = parts
        if not target or not anchor:
            raise ValueError(f"invalid geometry carve rule {item!r}; target/anchor must be non-empty")
        radius = float(radius_text)
        if radius <= 0.0:
            continue
        rules.append((target, anchor, radius))
    return rules


def parse_large_label_relabel_rules(value: str) -> list[tuple[str, str, float, float | None]]:
    """Parse source:target:min_extent geometry-aware semantic relabel rules.

    A rule `tissue-paper:cloth:0.8` says that an exported object whose current
    evaluator-facing label is `tissue-paper` and whose largest bbox extent is at
    least 0.8 m should be re-exported as `cloth`.  This keeps the repair
    geometry-gated instead of trusting all noisy semantic labels.

    A stricter four-field rule `bin:table:1.0:0.25` additionally requires a
    horizontal support-surface shape: both x/y bbox extents must be at least
    1.0 m and the z bbox extent must be at most 0.25 m.  This lets the paper
    ablation test a shared table-carrier reliability gate without turning large
    vertical surfaces into tables.
    """

    rules: list[tuple[str, str, float, float | None]] = []
    for raw_item in str(value or "").replace(";", ",").split(","):
        item = raw_item.strip()
        if not item:
            continue
        parts = [part.strip() for part in item.split(":")]
        if len(parts) not in (3, 4):
            raise ValueError(
                f"invalid large-label relabel rule {item!r}; "
                "expected source:target:min_extent[:max_z_extent]"
            )
        source, target, extent_text = parts[:3]
        if not source or not target:
            raise ValueError(f"invalid large-label relabel rule {item!r}; source/target must be non-empty")
        min_extent = float(extent_text)
        if min_extent <= 0.0:
            continue
        max_z_extent = float(parts[3]) if len(parts) == 4 else None
        if max_z_extent is not None and max_z_extent <= 0.0:
            continue
        rules.append((source, target, min_extent, max_z_extent))
    return rules


def active_geometry_carve_rules() -> list[tuple[str, str, float]]:
    rules = parse_geometry_carve_rules(GEOMETRY_REPAIR_CARVE_RULES)
    legacy_radius = float(GEOMETRY_REPAIR_CUSHION_SHRINK_RADIUS)
    if legacy_radius > 0.0 and ("cushion", "sofa", legacy_radius) not in rules:
        rules.append(("cushion", "sofa", legacy_radius))
    return rules


def active_large_label_relabel_rules() -> list[tuple[str, str, float, float | None]]:
    return parse_large_label_relabel_rules(GEOMETRY_REPAIR_LARGE_LABEL_RULES)


def active_large_label_target_declared_set() -> set[str]:
    return parse_label_set(GEOMETRY_REPAIR_LARGE_LABEL_REQUIRE_TARGET_DECLARED)


def carrier_v2_geometry_authorized(shape_diag: dict[str, object], max_z_extent: float | None) -> bool:
    if max_z_extent is None:
        return bool(float(shape_diag.get("max_extent", 0.0) or 0.0) > 0.0)
    return bool(shape_diag.get("horizontal_support_ok") and shape_diag.get("vertical_thickness_ok"))


def object_bbox_extents(obj: dict[str, object]) -> np.ndarray:
    if "pcd" not in obj:
        return np.zeros((3,), dtype=np.float32)
    try:
        points = np.asarray(obj["pcd"].points, dtype=np.float32)
    except Exception:
        return np.zeros((3,), dtype=np.float32)
    if points.ndim != 2 or points.shape[0] == 0:
        return np.zeros((3,), dtype=np.float32)
    extent = np.max(points[:, :3], axis=0) - np.min(points[:, :3], axis=0)
    if not np.isfinite(extent).all():
        return np.zeros((3,), dtype=np.float32)
    return extent.astype(np.float32)


def object_bbox_max_extent(obj: dict[str, object]) -> float:
    return float(np.max(object_bbox_extents(obj)))


def passes_large_label_shape_gate(
    obj: dict[str, object],
    min_extent: float,
    max_z_extent: float | None,
) -> tuple[bool, dict[str, object]]:
    extents = object_bbox_extents(obj)
    max_extent = float(np.max(extents))
    shape: dict[str, object] = {
        "bbox_extent_x": round(float(extents[0]), 6),
        "bbox_extent_y": round(float(extents[1]), 6),
        "bbox_extent_z": round(float(extents[2]), 6),
        "max_extent": round(max_extent, 6),
        "min_horizontal_extent": round(float(min(extents[0], extents[1])), 6),
    }
    if max_z_extent is None:
        return max_extent >= min_extent, shape
    horizontal_ok = float(extents[0]) >= min_extent and float(extents[1]) >= min_extent
    vertical_ok = float(extents[2]) <= max_z_extent
    shape["max_z_extent"] = round(float(max_z_extent), 6)
    shape["horizontal_support_ok"] = bool(horizontal_ok)
    shape["vertical_thickness_ok"] = bool(vertical_ok)
    return bool(horizontal_ok and vertical_ok), shape


def apply_geometry_repairs(
    objects: MapObjectList,
    cfg,
    *,
    class_feats_np: np.ndarray,
    label_to_index: dict[str, int],
    scale_prior_mode_override: str | None = None,
) -> tuple[MapObjectList, dict[str, object]]:
    """Apply export-only geometry repairs learned from office3 diagnostics.

    The repair order mirrors the validated posthoc experiments:
    first relabel only low-margin vent objects whose sofa score is close, then
    shrink cushion carrier points that are too close to sofa carriers.
    """

    carve_rules = active_geometry_carve_rules()
    large_label_rules = active_large_label_relabel_rules()
    scale_prior_source = (
        scale_prior_mode_override if scale_prior_mode_override is not None else GEOMETRY_REPAIR_SCALE_PRIOR_MODE
    )
    scale_prior_mode = str(scale_prior_source or "off").lower().replace("_", "-")
    enabled = (
        GEOMETRY_REPAIR_VENT_TO_SOFA_DELTA >= 0.0
        or bool(carve_rules)
        or bool(large_label_rules)
        or scale_prior_mode in {"log-only", "apply"}
    )
    if not enabled:
        return objects, {"enabled": False}

    keep_indices, keep_diag = geometry_repair_keep_indices(label_to_index, objects)
    index_to_label = {index: label for label, index in label_to_index.items()}
    relabel_counts: Counter[str] = Counter()
    relabel_points: Counter[str] = Counter()
    relabel_examples: list[dict[str, object]] = []
    evidence_mode = str(GEOMETRY_REPAIR_LARGE_LABEL_EVIDENCE_MODE or "off").lower().replace("_", "-")
    source_mode = str(GEOMETRY_REPAIR_LARGE_LABEL_SOURCE_MODE or "clip-top1").lower().replace("_", "-")
    target_declared_required = active_large_label_target_declared_set()
    max_large_label_point_rate = min(max(float(GEOMETRY_REPAIR_LARGE_LABEL_MAX_POINT_RATE), 0.0), 1.0)
    min_large_label_observations = max(int(GEOMETRY_REPAIR_LARGE_LABEL_MIN_OBSERVATIONS), 0)
    min_large_label_source_share = min(max(float(GEOMETRY_REPAIR_LARGE_LABEL_MIN_SOURCE_SHARE), 0.0), 1.0)
    total_input_points = sum(object_point_count(obj) for obj in objects)
    large_label_relabel_point_total = 0
    blocked_relabel_counts: Counter[str] = Counter()
    blocked_relabel_points: Counter[str] = Counter()
    blocked_relabel_examples: list[dict[str, object]] = []
    source_miss_counts: dict[str, Counter[str]] = defaultdict(Counter)
    source_miss_points: Counter[str] = Counter()
    source_miss_examples: list[dict[str, object]] = []
    shape_fail_counts: Counter[str] = Counter()
    shape_fail_points: Counter[str] = Counter()
    shape_fail_examples: list[dict[str, object]] = []

    if GEOMETRY_REPAIR_VENT_TO_SOFA_DELTA >= 0.0 and {"vent", "sofa"} <= set(label_to_index):
        vent_index = label_to_index["vent"]
        sofa_index = label_to_index["sofa"]
        for obj_index, obj in enumerate(objects):
            pred_label, scores = object_repair_pred_label(obj, class_feats_np, keep_indices, index_to_label)
            if pred_label != "vent":
                continue
            delta = float(scores[vent_index] - scores[sofa_index])
            if delta > GEOMETRY_REPAIR_VENT_TO_SOFA_DELTA:
                continue
            point_count = object_point_count(obj)
            relabel_counts["vent_to_sofa"] += 1
            relabel_points["vent_to_sofa"] += point_count
            if len(relabel_examples) < 20:
                relabel_examples.append({
                    "object_index": obj_index,
                    "from": "vent",
                    "to": "sofa",
                    "delta": round(delta, 6),
                    "point_count": point_count,
                    "declared_labels": sorted(object_declared_labels(obj)),
                })
            force_object_label_feature(obj, "sofa", label_to_index=label_to_index, class_feats_np=class_feats_np)

    scale_prior_probe: dict[str, object] = {"mode": scale_prior_mode}
    if scale_prior_mode in {"log-only", "apply"}:
        sp_violations_by_label: Counter[str] = Counter()
        sp_relabel_counts: Counter[str] = Counter()
        sp_relabel_points: Counter[str] = Counter()
        sp_abstain_reasons: Counter[str] = Counter()
        sp_examples: list[dict[str, object]] = []
        sp_checked = 0
        for obj_index, obj in enumerate(objects):
            pred_label, scores = object_repair_pred_label(obj, class_feats_np, keep_indices, index_to_label)
            extents = object_bbox_extents(obj)
            max_extent = float(np.max(extents))
            sp_checked += 1
            violation = scale_prior_violation(
                pred_label,
                max_extent,
                priors=ACTIVE_SCALE_PRIORS,
                tolerance=GEOMETRY_REPAIR_SCALE_PRIOR_TOLERANCE,
            )
            if not violation["violation"]:
                continue
            sp_violations_by_label[pred_label or "<empty>"] += 1
            declared_counter = object_declared_label_counts(obj)
            selection = select_scale_prior_target(
                dict(declared_counter),
                max_extent,
                priors=ACTIVE_SCALE_PRIORS,
                min_target_share=GEOMETRY_REPAIR_SCALE_PRIOR_MIN_TARGET_SHARE,
                max_source_share=GEOMETRY_REPAIR_SCALE_PRIOR_MAX_SOURCE_SHARE,
                source_label=pred_label,
                excluded_labels=STRUCTURAL_EXPORT_LABELS,
                severity_ratio=violation.get("severity_ratio"),
                hard_violation_ratio=GEOMETRY_REPAIR_SCALE_PRIOR_HARD_RATIO,
            )
            if (
                not selection["target"]
                and selection.get("hard_violation")
                and GEOMETRY_REPAIR_SCALE_PRIOR_CLIP_FALLBACK
            ):
                # Declared evidence offers no physically-compatible alternative
                # (office1: 70/70 declared tissue-paper) — re-read the object's
                # own CLIP scores restricted to labels whose prior accommodates
                # the extent.  "The most probable label that is physically
                # possible."
                compatible: list[tuple[float, str]] = []
                for label, index in label_to_index.items():
                    if label == pred_label or label in STRUCTURAL_EXPORT_LABELS:
                        continue
                    prior = ACTIVE_SCALE_PRIORS.get(label)
                    if prior is None or max_extent > float(prior):
                        continue
                    if 0 <= index < len(scores):
                        compatible.append((float(scores[index]), label))
                compatible.sort(reverse=True)
                if compatible:
                    selection = dict(selection)
                    selection["target"] = compatible[0][1]
                    selection["target_share"] = 0.0
                    selection["target_source"] = "clip-compatible-fallback"
                    selection["fallback_top_scores"] = [
                        {"label": label, "score": round(score, 6)} for score, label in compatible[:5]
                    ]
                    selection["abstain_reason"] = ""
            point_count = object_point_count(obj)
            if len(sp_examples) < 30:
                sp_examples.append({
                    "object_index": obj_index,
                    "pred_label": pred_label,
                    "max_extent": round(max_extent, 6),
                    "prior_max_extent": violation.get("prior_max_extent"),
                    "severity_ratio": violation.get("severity_ratio"),
                    "hard_violation": selection.get("hard_violation"),
                    "point_count": point_count,
                    "declared_label_counts": dict(declared_counter),
                    "selected_target": selection["target"],
                    "target_share": selection["target_share"],
                    "target_source": selection.get("target_source", "declared" if selection["target"] else ""),
                    "fallback_top_scores": selection.get("fallback_top_scores", []),
                    "source_share": selection["source_share"],
                    "abstain_reason": selection["abstain_reason"],
                    "candidates": selection["candidates"],
                })
            if selection["target"]:
                repair_key = f"scale_{pred_label}_to_{selection['target']}"
                sp_relabel_counts[repair_key] += 1
                sp_relabel_points[repair_key] += point_count
                if scale_prior_mode == "apply":
                    force_object_label_feature(
                        obj,
                        str(selection["target"]),
                        label_to_index=label_to_index,
                        class_feats_np=class_feats_np,
                    )
            else:
                sp_abstain_reasons[str(selection["abstain_reason"]) or "unknown"] += 1
        scale_prior_probe = {
            "mode": scale_prior_mode,
            "tolerance": GEOMETRY_REPAIR_SCALE_PRIOR_TOLERANCE,
            "min_target_share": GEOMETRY_REPAIR_SCALE_PRIOR_MIN_TARGET_SHARE,
            "max_source_share": GEOMETRY_REPAIR_SCALE_PRIOR_MAX_SOURCE_SHARE,
            "hard_violation_ratio": GEOMETRY_REPAIR_SCALE_PRIOR_HARD_RATIO,
            "objects_checked": sp_checked,
            "violations_by_label": dict(sp_violations_by_label),
            "relabel_counts": dict(sp_relabel_counts),
            "relabel_points": dict(sp_relabel_points),
            "abstain_reasons": dict(sp_abstain_reasons),
            "examples": sp_examples,
            "applied": scale_prior_mode == "apply",
        }

    for source_label, target_label, min_extent, max_z_extent in large_label_rules:
        if source_label not in label_to_index or target_label not in label_to_index:
            continue
        for obj_index, obj in enumerate(objects):
            point_count = object_point_count(obj)
            repair_key = f"large_{source_label}_to_{target_label}"
            pred_label, scores = object_repair_pred_label(obj, class_feats_np, keep_indices, index_to_label)
            shape_pass, shape_diag = passes_large_label_shape_gate(obj, min_extent, max_z_extent)
            declared_counter = object_declared_label_counts(obj)
            declared_labels = sorted(declared_counter)
            declared_total = max(sum(declared_counter.values()), 1)
            source_declared_share = declared_counter.get(source_label, 0) / declared_total
            target_declared_share = declared_counter.get(target_label, 0) / declared_total
            detection_count = object_detection_count(obj)
            projected_rate = (large_label_relabel_point_total + point_count) / max(total_input_points, 1)
            geometry_authorized = carrier_v2_geometry_authorized(shape_diag, max_z_extent)
            clip_source_match = pred_label == source_label
            declared_source_match = source_declared_share > 0.0
            target_declared_geometry_match = target_declared_share > 0.0 and geometry_authorized
            source_matched_by = ""
            if clip_source_match:
                source_matched_by = "clip-top1"
            elif source_mode == "declared-source-or-clip" and declared_source_match:
                source_matched_by = "declared-source"
            elif source_mode == "target-declared-geometry" and target_declared_geometry_match:
                source_matched_by = "target-declared-geometry"
            source_score = float(scores[label_to_index[source_label]]) if source_label in label_to_index else 0.0
            target_score = float(scores[label_to_index[target_label]]) if target_label in label_to_index else 0.0
            evidence_diag = {
                "evidence_decision_mode": evidence_mode,
                "source_decision_mode": source_mode,
                "source_matched_by": source_matched_by or "none",
                "pred_label": pred_label,
                "declared_label_counts": dict(declared_counter),
                "source_declared_share": round(float(source_declared_share), 6),
                "target_declared_share": round(float(target_declared_share), 6),
                "detection_count": int(detection_count),
                "geometry_authorized": bool(geometry_authorized),
                "projected_large_label_point_rate": round(float(projected_rate), 6),
                "source_score": round(source_score, 6),
                "target_score": round(target_score, 6),
                "top_repair_scores": top_repair_score_labels(scores, keep_indices, index_to_label),
            }
            if not source_matched_by:
                source_miss_counts[repair_key][pred_label or "<empty>"] += 1
                source_miss_points[repair_key] += point_count
                if len(source_miss_examples) < 20:
                    source_miss_examples.append({
                        "object_index": obj_index,
                        "from": source_label,
                        "to": target_label,
                        "min_extent": round(min_extent, 6),
                        "max_z_extent": None if max_z_extent is None else round(max_z_extent, 6),
                        **shape_diag,
                        **evidence_diag,
                        "point_count": point_count,
                        "declared_labels": declared_labels,
                        "rule": (
                            f"{source_label}:{target_label}:{min_extent}"
                            if max_z_extent is None
                            else f"{source_label}:{target_label}:{min_extent}:{max_z_extent}"
                        ),
                    })
                continue
            if not shape_pass:
                shape_fail_counts[repair_key] += 1
                shape_fail_points[repair_key] += point_count
                if len(shape_fail_examples) < 20:
                    shape_fail_examples.append({
                        "object_index": obj_index,
                        "from": source_label,
                        "to": target_label,
                        "min_extent": round(min_extent, 6),
                        "max_z_extent": None if max_z_extent is None else round(max_z_extent, 6),
                        **shape_diag,
                        **evidence_diag,
                        "point_count": point_count,
                        "declared_labels": declared_labels,
                        "rule": (
                            f"{source_label}:{target_label}:{min_extent}"
                            if max_z_extent is None
                            else f"{source_label}:{target_label}:{min_extent}:{max_z_extent}"
                        ),
                    })
                continue
            block_reasons: list[str] = []
            if evidence_mode in {"active", "evidence", "strict"}:
                if target_label in target_declared_required and target_label not in set(declared_labels):
                    block_reasons.append("target_not_declared")
                if max_large_label_point_rate < 1.0:
                    if projected_rate > max_large_label_point_rate:
                        block_reasons.append("max_point_rate_exceeded")
            elif evidence_mode in {"carrier-v2", "carrier_v2", "carrier"}:
                if min_large_label_observations and detection_count < min_large_label_observations:
                    block_reasons.append("min_observations_not_met")
                if min_large_label_source_share and source_declared_share < min_large_label_source_share:
                    block_reasons.append("min_source_share_not_met")
                if (
                    target_label in target_declared_required
                    and target_label not in set(declared_labels)
                    and not geometry_authorized
                ):
                    block_reasons.append("target_not_declared_or_geometry_weak")
                if max_large_label_point_rate < 1.0 and projected_rate > max_large_label_point_rate:
                    block_reasons.append("max_point_rate_exceeded")
            if block_reasons:
                blocked_relabel_counts[repair_key] += 1
                blocked_relabel_points[repair_key] += point_count
                if len(blocked_relabel_examples) < 20:
                    blocked_relabel_examples.append({
                        "object_index": obj_index,
                        "from": source_label,
                        "to": target_label,
                        "block_reasons": block_reasons,
                        "min_extent": round(min_extent, 6),
                        "max_z_extent": None if max_z_extent is None else round(max_z_extent, 6),
                        **shape_diag,
                        **evidence_diag,
                        "point_count": point_count,
                        "declared_labels": declared_labels,
                    })
                continue
            relabel_counts[repair_key] += 1
            relabel_points[repair_key] += point_count
            large_label_relabel_point_total += point_count
            if len(relabel_examples) < 20:
                relabel_examples.append({
                    "object_index": obj_index,
                    "from": source_label,
                    "to": target_label,
                    "min_extent": round(min_extent, 6),
                    "max_z_extent": None if max_z_extent is None else round(max_z_extent, 6),
                    **shape_diag,
                    **evidence_diag,
                    "point_count": point_count,
                    "declared_labels": declared_labels,
                    "rule": (
                        f"{source_label}:{target_label}:{min_extent}"
                        if max_z_extent is None
                        else f"{source_label}:{target_label}:{min_extent}:{max_z_extent}"
                    ),
                })
            force_object_label_feature(obj, target_label, label_to_index=label_to_index, class_feats_np=class_feats_np)

    carved_objects = 0
    dropped_objects = 0
    removed_points: Counter[str] = Counter()
    kept_points: Counter[str] = Counter()
    removed_points_by_rule: Counter[str] = Counter()
    carved_objects_by_rule: Counter[str] = Counter()
    output = MapObjectList()
    anchor_labels = sorted({anchor for _target, anchor, _radius in carve_rules})
    anchor_points_by_label: dict[str, np.ndarray] = {}
    for anchor_label in anchor_labels:
        protected_points = []
        for obj in objects:
            pred_label, _scores = object_repair_pred_label(obj, class_feats_np, keep_indices, index_to_label)
            if pred_label == anchor_label:
                pts = np.asarray(obj["pcd"].points, dtype=np.float32)
                if len(pts):
                    protected_points.append(pts)
        anchor_points_by_label[anchor_label] = (
            np.concatenate(protected_points, axis=0)
            if protected_points
            else np.zeros((0, 3), dtype=np.float32)
        )

    for obj in objects:
        pred_label, _scores = object_repair_pred_label(obj, class_feats_np, keep_indices, index_to_label)
        pts = np.asarray(obj["pcd"].points, dtype=np.float32)
        cols = np.asarray(obj["pcd"].colors, dtype=np.float32)
        if len(pts):
            object_keep_mask = np.ones((len(pts),), dtype=bool)
            object_rule_removed: Counter[str] = Counter()
            for target_label, anchor_label, radius in carve_rules:
                if pred_label != target_label:
                    continue
                anchor_points = anchor_points_by_label.get(anchor_label, np.zeros((0, 3), dtype=np.float32))
                if not len(anchor_points):
                    continue
                distances = nearest_distance_to_points(pts, anchor_points)
                rule_remove = distances <= radius
                if not np.any(rule_remove):
                    continue
                rule_key = f"{target_label}->{anchor_label}@{radius:g}"
                object_rule_removed[rule_key] += int(np.logical_and(object_keep_mask, rule_remove).sum())
                object_keep_mask &= ~rule_remove
            removed = int((~object_keep_mask).sum())
            if removed:
                carved_objects += 1
                removed_points[pred_label] += removed
                for rule_key, rule_removed in object_rule_removed.items():
                    if rule_removed:
                        removed_points_by_rule[rule_key] += int(rule_removed)
                        carved_objects_by_rule[rule_key] += 1
                pts = pts[object_keep_mask]
                cols = cols[object_keep_mask]
                if len(pts) < 4:
                    dropped_objects += 1
                    continue
                obj["pcd"] = make_open3d_pcd(pts, cols)
                obj["bbox"] = get_bounding_box(cfg, obj["pcd"])
        kept_points[pred_label] += len(pts)
        output.append(obj)

    diagnostics = {
        "enabled": True,
        "keep_labels": [index_to_label[index] for index in keep_indices],
        "keep_mode_diagnostics": keep_diag,
        "scale_prior_probe": scale_prior_probe,
        "vent_to_sofa_delta": GEOMETRY_REPAIR_VENT_TO_SOFA_DELTA,
        "cushion_shrink_radius": GEOMETRY_REPAIR_CUSHION_SHRINK_RADIUS,
        "carve_rules": [
            {"target": target, "anchor": anchor, "radius": radius}
            for target, anchor, radius in carve_rules
        ],
        "large_label_relabel_rules": [
            {
                "source": source,
                "target": target,
                "min_extent": min_extent,
                "max_z_extent": max_z_extent,
            }
            for source, target, min_extent, max_z_extent in large_label_rules
        ],
        "large_label_evidence_mode": evidence_mode,
        "large_label_source_mode": source_mode,
        "large_label_target_declared_required": sorted(target_declared_required),
        "large_label_max_point_rate": max_large_label_point_rate,
        "large_label_min_observations": min_large_label_observations,
        "large_label_min_source_share": min_large_label_source_share,
        "input_object_count": len(objects),
        "output_object_count": len(output),
        "relabel_counts": dict(relabel_counts),
        "relabel_points": dict(relabel_points),
        "relabel_examples": relabel_examples,
        "blocked_relabel_counts": dict(blocked_relabel_counts),
        "blocked_relabel_points": dict(blocked_relabel_points),
        "blocked_relabel_examples": blocked_relabel_examples,
        "source_miss_counts": {
            repair_key: dict(counter)
            for repair_key, counter in sorted(source_miss_counts.items())
        },
        "source_miss_points": dict(source_miss_points),
        "source_miss_examples": source_miss_examples,
        "shape_fail_counts": dict(shape_fail_counts),
        "shape_fail_points": dict(shape_fail_points),
        "shape_fail_examples": shape_fail_examples,
        "protected_anchor_point_counts": {
            label: int(len(points)) for label, points in sorted(anchor_points_by_label.items())
        },
        "carved_objects": carved_objects,
        "carved_objects_by_rule": dict(carved_objects_by_rule),
        "dropped_objects": dropped_objects,
        "removed_points": dict(removed_points),
        "removed_points_by_rule": dict(removed_points_by_rule),
        "kept_points": dict(kept_points),
    }
    return output, diagnostics


def write_conceptgraphs_payload(
    scene: str,
    result,
    key_data: dict[str, dict[str, object]],
    multires_key_data: dict[str, dict[str, object]],
    track_assignments: dict[str, list[str]],
    branch_summary: dict,
    label_to_index: dict[str, int],
    class_feats_np: np.ndarray,
    prepare_key_count: int | None = None,
):
    t0 = time.time()
    dataset_root = SCANNET_STAGE_ROOT if DATASET_MODE == "scannet" else REPLICA_ROOT
    pcd_dir = dataset_root / scene / "pcd_saves"
    pcd_dir.mkdir(parents=True, exist_ok=True)
    cfg = conceptgraphs_postprocess_cfg()

    memory_objects, memory_export_debug, memory_skipped_keys = build_memory_map_objects(result, label_to_index, class_feats_np)
    (
        memory_dense_objects,
        memory_dense_export_debug,
        memory_dense_skipped_keys,
        memory_dense_diagnostics,
    ) = build_memory_dense_map_objects(result, key_data, track_assignments, label_to_index, class_feats_np)
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
        consolidation_dense_max_ratio=EXPORT_CONSOLIDATION_DENSE_MAX_RATIO,
        consolidation_memory_count=len(result.memory_nodes),
        # The routing ratio is calibrated on the PREPARE-time key granularity;
        # key_data is expanded by split policies before export (room0: 436 -> 1514).
        consolidation_key_count=prepare_key_count if prepare_key_count is not None else len(key_data),
    )
    export_source = str(export_selection["selected_source"])
    mechanisms_scoped_off = (
        str(MECHANISMS_SCOPE).lower().replace("_", "-") == "consolidated-only"
        and export_source == GEOMETRY_EXPORT_SOURCE
    )
    scoped_gate_enabled = False if mechanisms_scoped_off else None
    multires_diagnostics = {"enabled": False}
    coarse_postprocess_counts: dict[str, int] = {}
    fine_postprocess_counts: dict[str, int] = {}
    fine_export_debug: list[dict[str, object]] = []
    fine_skipped_keys: list[str] = []
    if export_source == GEOMETRY_EXPORT_SOURCE:
        initial_objects, export_debug, skipped_keys = build_initial_map_objects(
            key_data,
            track_assignments,
            label_to_index,
            class_feats_np,
            carrier="coarse_geometry",
        )
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
    label_gate_probe: dict[str, object] = {"enabled": False}
    if export_source == GEOMETRY_EXPORT_SOURCE and MULTIRES_EXPORT_ENABLED:
        coarse_objects, coarse_postprocess_counts = postprocess_map_objects(
            cfg, initial_objects, gate_enabled=scoped_gate_enabled
        )
        label_gate_probe = coarse_postprocess_counts.get("label_gate_probe", {"enabled": False})
        if MULTIRES_FINE_SPLIT_BY_LABEL:
            fine_items = iter_label_bucket_export_items(
                multires_key_data,
                allowed_labels=parse_label_set(MULTIRES_FINE_LABELS),
                min_observations=MULTIRES_FINE_MIN_OBSERVATIONS,
                export_suffix=":fine",
            )
        else:
            fine_items = iter_plain_key_export_items(
                multires_key_data,
                allowed_labels=parse_label_set(MULTIRES_FINE_LABELS),
                export_suffix=":fine",
            )
        fine_initial_objects, fine_export_debug, fine_skipped_keys = build_initial_map_objects(
            multires_key_data,
            track_assignments,
            label_to_index,
            class_feats_np,
            export_items=fine_items,
            carrier="fine_geometry",
        )
        fine_objects, fine_postprocess_counts = postprocess_map_objects(
            cfg, fine_initial_objects, gate_enabled=scoped_gate_enabled
        )
        objects, multires_diagnostics = apply_multires_replacement(
            coarse_objects,
            fine_objects,
            class_feats_np=class_feats_np,
            label_to_index=label_to_index,
        )
        post_denoise_count = int(coarse_postprocess_counts.get("post_denoise_object_count", 0))
        post_filter_count = int(coarse_postprocess_counts.get("post_filter_object_count", 0))
        post_merge_count = len(objects)
        export_debug = export_debug + fine_export_debug
        skipped_keys = skipped_keys + fine_skipped_keys
    else:
        objects, postprocess_counts = postprocess_map_objects(
            cfg, initial_objects, gate_enabled=scoped_gate_enabled
        )
        post_denoise_count = int(postprocess_counts["post_denoise_object_count"])
        post_filter_count = int(postprocess_counts["post_filter_object_count"])
        post_merge_count = int(postprocess_counts["post_merge_object_count"])
        label_gate_probe = postprocess_counts.get("label_gate_probe", {"enabled": False})
    objects, geometry_repair_diagnostics = apply_geometry_repairs(
        objects,
        cfg,
        class_feats_np=class_feats_np,
        label_to_index=label_to_index,
        scale_prior_mode_override="off" if mechanisms_scoped_off else None,
    )
    post_merge_count = len(objects)
    serializable_objects = objects.to_serializable()
    payload = {"objects": serializable_objects, "bg_objects": None}
    result_path = pcd_dir / f"full_pcd_{PRED_EXP_NAME}.pkl.gz"
    with gzip.open(result_path, "wb") as handle:
        pickle.dump(payload, handle)
    point_counts = [int(len(obj["pcd_np"])) for obj in serializable_objects]
    detection_counts = [int(item["num_detections"]) for item in export_debug]
    fragment_counts = [int(item["fragment_object_count"]) for item in export_debug]
    clip_readout_sources = Counter(str(item.get("clip_readout_source", "unknown")) for item in export_debug)
    clip_readout_reasons = Counter(str(item.get("clip_readout_reason", "unknown")) for item in export_debug)
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
            "split_decisions": summarize_export_split_decisions(key_data),
        },
        "multires_export_probe": {
            **multires_diagnostics,
            "fine_key_count": len(multires_key_data),
            "fine_candidate_object_count": len(fine_export_debug),
            "fine_skipped_key_count": len(fine_skipped_keys),
            "fine_postprocess_counts": fine_postprocess_counts,
            "coarse_postprocess_counts": coarse_postprocess_counts,
        },
        "geometry_repair_probe": geometry_repair_diagnostics,
        "cg_merge_label_gate_probe": label_gate_probe,
        "mechanisms_scope": {
            "scope": MECHANISMS_SCOPE,
            "scoped_off_for_this_scene": mechanisms_scoped_off,
            "export_source": export_source,
        },
        "initial_key_object_count": pre_postprocess_count,
        "post_denoise_object_count": post_denoise_count,
        "post_filter_object_count": post_filter_count,
        "post_merge_object_count": post_merge_count,
        "skipped_key_count": len(skipped_keys),
        "objects_per_track_key": numeric_summary(fragment_counts),
        "detections_per_exported_object": numeric_summary(detection_counts),
        "points_per_exported_object": numeric_summary(point_counts),
        "clip_readout_sources": dict(clip_readout_sources),
        "clip_readout_reasons": dict(clip_readout_reasons),
        "fragmented_export_key_count": sum(1 for value in fragment_counts if value > 1),
        "fragmented_export_key_rate": round(sum(1 for value in fragment_counts if value > 1) / max(len(fragment_counts), 1), 6),
        "sample": export_debug[:20],
    }
    manifest_object_source = f"{export_source}_multires" if multires_diagnostics.get("enabled") else export_source
    proxy = {
        "scene": scene,
        "pred_exp_name": PRED_EXP_NAME,
        "object_count": len(serializable_objects),
        "point_count": int(sum(len(obj["pcd_np"]) for obj in serializable_objects)),
        "source": "duograph3d_over_conceptgraphs_gsa_detections_none_engineered",
        "object_source": manifest_object_source,
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
            "multires_export_enabled": MULTIRES_EXPORT_ENABLED,
            "multires_fine_voxel_size": MULTIRES_FINE_VOXEL_SIZE,
            "multires_fine_labels": MULTIRES_FINE_LABELS,
            "multires_risky_labels": MULTIRES_RISKY_LABELS,
            "multires_fine_split_by_label": MULTIRES_FINE_SPLIT_BY_LABEL,
            "multires_fine_min_observations": MULTIRES_FINE_MIN_OBSERVATIONS,
            "multires_fine_takeover_min_points": MULTIRES_FINE_TAKEOVER_MIN_POINTS,
            "multires_risky_min_points": MULTIRES_RISKY_MIN_POINTS,
            "multires_replacement_mode": MULTIRES_REPLACEMENT_MODE,
            "geometry_repair_keep_labels": GEOMETRY_REPAIR_KEEP_LABELS,
            "geometry_repair_vent_to_sofa_delta": GEOMETRY_REPAIR_VENT_TO_SOFA_DELTA,
            "geometry_repair_cushion_shrink_radius": GEOMETRY_REPAIR_CUSHION_SHRINK_RADIUS,
            "geometry_repair_carve_rules": GEOMETRY_REPAIR_CARVE_RULES,
            "geometry_repair_large_label_rules": GEOMETRY_REPAIR_LARGE_LABEL_RULES,
            "geometry_repair_large_label_evidence_mode": GEOMETRY_REPAIR_LARGE_LABEL_EVIDENCE_MODE,
            "geometry_repair_large_label_source_mode": GEOMETRY_REPAIR_LARGE_LABEL_SOURCE_MODE,
            "geometry_repair_large_label_require_target_declared": GEOMETRY_REPAIR_LARGE_LABEL_REQUIRE_TARGET_DECLARED,
            "geometry_repair_large_label_max_point_rate": GEOMETRY_REPAIR_LARGE_LABEL_MAX_POINT_RATE,
            "geometry_repair_large_label_min_observations": GEOMETRY_REPAIR_LARGE_LABEL_MIN_OBSERVATIONS,
            "geometry_repair_large_label_min_source_share": GEOMETRY_REPAIR_LARGE_LABEL_MIN_SOURCE_SHARE,
            "min_mask_pixels": MIN_MASK_PIXELS,
            "mask_conf_threshold": MASK_CONF_THRESHOLD,
            "max_bbox_area_ratio": MAX_BBOX_AREA_RATIO,
            "min_valid_depth_points": MIN_VALID_DEPTH_POINTS,
            "drop_post_subtract_tiny": DROP_POST_SUBTRACT_TINY,
            "min_object_detections": MIN_OBJECT_DETECTIONS,
            "export_source_strategy": EXPORT_SOURCE_STRATEGY,
            "export_consolidation_dense_max_ratio": EXPORT_CONSOLIDATION_DENSE_MAX_RATIO,
            "mechanisms_scope": MECHANISMS_SCOPE,
            "text_feature_mode": TEXT_FEATURE_MODE,
            "clip_feature_mode": CLIP_FEATURE_MODE,
            "clip_feature_blend_alpha": CLIP_FEATURE_BLEND_ALPHA,
            "export_clip_min_margin": EXPORT_CLIP_MIN_MARGIN,
            "adaptive_clip_sink_labels": ADAPTIVE_CLIP_SINK_LABELS,
            "adaptive_clip_min_high_margin_count": ADAPTIVE_CLIP_MIN_HIGH_MARGIN_COUNT,
            "adaptive_clip_min_high_margin_rate": ADAPTIVE_CLIP_MIN_HIGH_MARGIN_RATE,
            "adaptive_clip_min_entropy": ADAPTIVE_CLIP_MIN_ENTROPY,
            "memory_coverage_gate": {
                "min_memory_objects": MIN_MEMORY_EXPORT_OBJECTS,
                "min_memory_key_ratio": MIN_MEMORY_EXPORT_KEY_RATIO,
                "min_memory_point_ratio": MIN_MEMORY_EXPORT_POINT_RATIO,
                "memory_dense_min_root_share": MEMORY_DENSE_MIN_ROOT_SHARE,
                "memory_dense_geometry_fallback": MEMORY_DENSE_GEOMETRY_FALLBACK,
                "memory_dense_split_by_label": MEMORY_DENSE_SPLIT_BY_LABEL,
                "memory_dense_split_min_observations": MEMORY_DENSE_SPLIT_MIN_OBSERVATIONS,
                "memory_dense_split_min_root_label_entropy": MEMORY_DENSE_SPLIT_MIN_ROOT_LABEL_ENTROPY,
                "memory_dense_split_max_root_top_share": MEMORY_DENSE_SPLIT_MAX_ROOT_TOP_SHARE,
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
                "text_feature_mode": TEXT_FEATURE_MODE,
                "clip_feature_mode": CLIP_FEATURE_MODE,
                "clip_feature_blend_alpha": CLIP_FEATURE_BLEND_ALPHA,
                "export_clip_min_margin": EXPORT_CLIP_MIN_MARGIN,
                "export_split_by_label": EXPORT_SPLIT_BY_LABEL,
                "memory_dense_split_by_label": MEMORY_DENSE_SPLIT_BY_LABEL,
                "memory_dense_split_min_root_label_entropy": MEMORY_DENSE_SPLIT_MIN_ROOT_LABEL_ENTROPY,
                "memory_dense_split_max_root_top_share": MEMORY_DENSE_SPLIT_MAX_ROOT_TOP_SHARE,
                "mask_subtract_contained": True,
                "drop_post_subtract_tiny": DROP_POST_SUBTRACT_TINY,
                "downsample_voxel_size": CG_DOWNSAMPLE_VOXEL_SIZE,
                "dbscan_remove_noise": True,
                "dbscan_eps": CG_DBSCAN_EPS,
                "dbscan_min_points": CG_DBSCAN_MIN_POINTS,
                "merge_overlap_thresh": CG_MERGE_OVERLAP_THRESH,
                "merge_visual_sim_thresh": CG_MERGE_VISUAL_SIM_THRESH,
                "merge_text_sim_thresh": CG_MERGE_TEXT_SIM_THRESH,
                "l2_occluded_after_misses": L2_OCCLUDED_AFTER_MISSES,
                "l2_dormant_after_misses": L2_DORMANT_AFTER_MISSES,
                "l2_retire_after_misses": L2_RETIRE_AFTER_MISSES,
                "l2_relation_bonus_weight": L2_RELATION_BONUS_WEIGHT,
                "l2_relation_bonus_cap": L2_RELATION_BONUS_CAP,
            },
        },
        "branch_summary_excerpt": {
            "memory_node_count": branch_summary.get("memory_node_count"),
            "track_fragmentation": branch_summary.get("track_fragmentation"),
            "memory_relation_edge_count": branch_summary.get("memory_relation_edge_count"),
        },
        "export_monitor": export_monitor,
        "object_source": manifest_object_source,
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
    multires_probes = [
        item.get("export_monitor", {}).get("multires_export_probe", {})
        for item in scene_debug
    ]
    return {
        "raw_detection_count": sum(int(item["raw_detection_count"]) for item in prep),
        "kept_observation_count": sum(int(item["kept_observation_count"]) for item in prep),
        "key_count": sum(int(item["key_count"]) for item in prep),
        "export_object_count": sum(int(item.get("export_object_count", 0)) for item in scene_debug),
        "export_sources": dict(export_sources),
        "export_fallback_reasons": dict(fallback_reasons),
        "multires_dropped_coarse_count": sum(int(item.get("dropped_coarse_count", 0) or 0) for item in multires_probes),
        "multires_fine_post_merge_count": sum(int(item.get("fine_post_merge_count", 0) or 0) for item in multires_probes),
        "multires_drop_label_counts": dict(sum((Counter(item.get("drop_label_counts", {})) for item in multires_probes), Counter())),
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
        f"- multi-resolution dropped coarse objects / fine post-merge objects: {rollup.get('multires_dropped_coarse_count')} / {rollup.get('multires_fine_post_merge_count')}; labels: `{rollup.get('multires_drop_label_counts')}`",
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
    global EXPORT_CONSOLIDATION_DENSE_MAX_RATIO, MECHANISMS_SCOPE
    global DATASET_MODE, ACTIVE_SCALE_PRIORS, STRUCTURAL_EXPORT_LABELS
    global TEXT_FEATURE_MODE, CLIP_FEATURE_MODE, CLIP_FEATURE_BLEND_ALPHA
    global EXPORT_CLIP_MIN_MARGIN
    global ADAPTIVE_CLIP_SINK_LABELS, ADAPTIVE_CLIP_MIN_HIGH_MARGIN_COUNT
    global ADAPTIVE_CLIP_MIN_HIGH_MARGIN_RATE, ADAPTIVE_CLIP_MIN_ENTROPY
    global MAX_POINTS_PER_OBS, MAX_POINTS_PER_OBJECT, EXPORT_SPLIT_BY_LABEL
    global EXPORT_SPLIT_POLICY, EXPORT_SPLIT_MIN_OBSERVATIONS, EXPORT_SPLIT_MIN_KEY_ENTROPY
    global EXPORT_SPLIT_MAX_KEY_TOP_SHARE, EXPORT_SPLIT_MIN_LABEL_SHARE
    global EXPORT_SPLIT_MIN_CENTROID_SEPARATION, EXPORT_SPLIT_MIN_SCENE_SPLIT_RATE
    global MULTIRES_EXPORT_ENABLED, MULTIRES_FINE_VOXEL_SIZE, MULTIRES_FINE_LABELS
    global MULTIRES_RISKY_LABELS, MULTIRES_FINE_SPLIT_BY_LABEL, MULTIRES_FINE_MIN_OBSERVATIONS
    global MULTIRES_FINE_TAKEOVER_MIN_POINTS, MULTIRES_RISKY_MIN_POINTS, MULTIRES_REPLACEMENT_MODE
    global GEOMETRY_REPAIR_KEEP_LABELS, GEOMETRY_REPAIR_VENT_TO_SOFA_DELTA
    global GEOMETRY_REPAIR_CUSHION_SHRINK_RADIUS, GEOMETRY_REPAIR_CARVE_RULES, GEOMETRY_REPAIR_LARGE_LABEL_RULES
    global GEOMETRY_REPAIR_LARGE_LABEL_EVIDENCE_MODE, GEOMETRY_REPAIR_LARGE_LABEL_SOURCE_MODE
    global GEOMETRY_REPAIR_LARGE_LABEL_REQUIRE_TARGET_DECLARED
    global GEOMETRY_REPAIR_LARGE_LABEL_MAX_POINT_RATE, GEOMETRY_REPAIR_LARGE_LABEL_MIN_OBSERVATIONS
    global GEOMETRY_REPAIR_LARGE_LABEL_MIN_SOURCE_SHARE
    global GEOMETRY_REPAIR_KEEP_MODE, GEOMETRY_REPAIR_KEEP_AUTO_MIN_COUNT
    global GEOMETRY_REPAIR_SCALE_PRIOR_MODE, GEOMETRY_REPAIR_SCALE_PRIOR_TOLERANCE
    global GEOMETRY_REPAIR_SCALE_PRIOR_MIN_TARGET_SHARE, GEOMETRY_REPAIR_SCALE_PRIOR_MAX_SOURCE_SHARE
    global GEOMETRY_REPAIR_SCALE_PRIOR_HARD_RATIO, GEOMETRY_REPAIR_SCALE_PRIOR_CLIP_FALLBACK
    global VOXEL_SIZE, MIN_MASK_PIXELS, MASK_CONF_THRESHOLD, MAX_BBOX_AREA_RATIO, MIN_VALID_DEPTH_POINTS
    global DROP_POST_SUBTRACT_TINY
    global CG_DOWNSAMPLE_VOXEL_SIZE, CG_DBSCAN_EPS, CG_DBSCAN_MIN_POINTS
    global CG_MERGE_OVERLAP_THRESH, CG_MERGE_VISUAL_SIM_THRESH, CG_MERGE_TEXT_SIM_THRESH
    global CG_MERGE_LABEL_GATE, CG_MERGE_LABEL_GATE_MIN_SHARE, CG_MERGE_LABEL_GATE_MIN_OBS
    global CG_MERGE_LABEL_GATE_MUTUAL_THRESH
    global MIN_MEMORY_EXPORT_OBJECTS, MIN_MEMORY_EXPORT_KEY_RATIO, MIN_MEMORY_EXPORT_POINT_RATIO
    global MEMORY_DENSE_SPATIAL_SPLIT, MEMORY_DENSE_SPATIAL_SPLIT_EPS
    global MEMORY_DENSE_SPLIT_BY_LABEL, MEMORY_DENSE_SPLIT_MIN_OBSERVATIONS
    global MEMORY_DENSE_SPLIT_MIN_ROOT_LABEL_ENTROPY, MEMORY_DENSE_SPLIT_MAX_ROOT_TOP_SHARE
    global L2_OCCLUDED_AFTER_MISSES, L2_DORMANT_AFTER_MISSES, L2_RETIRE_AFTER_MISSES
    global L2_RELATION_BONUS_WEIGHT, L2_RELATION_BONUS_CAP
    parser = argparse.ArgumentParser()
    parser.add_argument("--scenes", nargs="*", default=list(REPLICA_SCENE_IDS))
    parser.add_argument(
        "--dataset",
        choices=["replica", "scannet"],
        default=DATASET_MODE,
        help="scannet mode: staged 25k-export scenes, NYU40 vocabulary + frozen priors, external eval only.",
    )
    parser.add_argument("--skip-eval", action="store_true")
    parser.add_argument("--root", type=Path, default=ROOT)
    parser.add_argument("--pred-exp-name", default=None)
    parser.add_argument(
        "--frame-limit",
        type=int,
        default=None,
        help="Diagnostic-only: process only the first N detection frames per scene before optional export/eval.",
    )
    parser.add_argument(
        "--frame-stride",
        type=int,
        default=1,
        help="Process every Nth detection frame. Use 5 to mirror the official ConceptGraphs Replica cfg stride.",
    )
    parser.add_argument("--voxel-size", type=float, default=VOXEL_SIZE)
    parser.add_argument("--min-mask-pixels", type=int, default=MIN_MASK_PIXELS)
    parser.add_argument("--max-points-per-obs", type=int, default=MAX_POINTS_PER_OBS)
    parser.add_argument("--max-points-per-object", type=int, default=MAX_POINTS_PER_OBJECT)
    parser.add_argument("--mask-conf-threshold", type=float, default=MASK_CONF_THRESHOLD)
    parser.add_argument("--max-bbox-area-ratio", type=float, default=MAX_BBOX_AREA_RATIO)
    parser.add_argument("--min-valid-depth-points", type=int, default=MIN_VALID_DEPTH_POINTS)
    parser.add_argument("--drop-post-subtract-tiny", type=int, choices=[0, 1], default=int(DROP_POST_SUBTRACT_TINY))
    parser.add_argument("--min-object-detections", type=int, default=None)
    parser.add_argument(
        "--export-source",
        choices=["auto", "consolidation-auto", "geometry", "memory", "memory-dense"],
        default=EXPORT_SOURCE_STRATEGY,
        help=(
            "Object source for official ConceptGraphs-format export. "
            "`auto` keeps mIoU coverage by falling back to geometry keys when online memory is too sparse; "
            "`consolidation-auto` routes the substrate by memory/key consolidation ratio (dense when memory "
            "consolidates far below key granularity, geometry otherwise); "
            "`memory-dense` groups dense key geometry by online-memory root IDs."
        ),
    )
    parser.add_argument(
        "--export-consolidation-dense-max-ratio",
        type=float,
        default=EXPORT_CONSOLIDATION_DENSE_MAX_RATIO,
    )
    parser.add_argument(
        "--mechanisms-scope",
        choices=["all-substrates", "consolidated-only"],
        default=MECHANISMS_SCOPE,
        help=(
            "`consolidated-only` disables the label gate and scale-prior repairs on geometry-routed "
            "exports: those mechanisms need multi-view object-level declared evidence, which raw "
            "geometry-key buckets (boundary-noise label mixes) do not provide."
        ),
    )
    parser.add_argument("--min-memory-export-objects", type=int, default=MIN_MEMORY_EXPORT_OBJECTS)
    parser.add_argument("--min-memory-export-key-ratio", type=float, default=MIN_MEMORY_EXPORT_KEY_RATIO)
    parser.add_argument("--min-memory-export-point-ratio", type=float, default=MIN_MEMORY_EXPORT_POINT_RATIO)
    parser.add_argument("--export-split-by-label", type=int, choices=[0, 1], default=int(EXPORT_SPLIT_BY_LABEL))
    parser.add_argument(
        "--export-split-policy",
        choices=["all", "adaptive"],
        default=EXPORT_SPLIT_POLICY,
        help=(
            "`all` preserves the legacy diagnostic behavior of splitting every geometry key by recovered label; "
            "`adaptive` splits only mixed keys whose label buckets are also spatially separated."
        ),
    )
    parser.add_argument("--export-split-min-observations", type=int, default=EXPORT_SPLIT_MIN_OBSERVATIONS)
    parser.add_argument("--export-split-min-key-entropy", type=float, default=EXPORT_SPLIT_MIN_KEY_ENTROPY)
    parser.add_argument("--export-split-max-key-top-share", type=float, default=EXPORT_SPLIT_MAX_KEY_TOP_SHARE)
    parser.add_argument("--export-split-min-label-share", type=float, default=EXPORT_SPLIT_MIN_LABEL_SHARE)
    parser.add_argument("--export-split-min-centroid-separation", type=float, default=EXPORT_SPLIT_MIN_CENTROID_SEPARATION)
    parser.add_argument("--export-split-min-scene-split-rate", type=float, default=EXPORT_SPLIT_MIN_SCENE_SPLIT_RATE)
    parser.add_argument(
        "--multires-export",
        type=int,
        choices=[0, 1],
        default=int(MULTIRES_EXPORT_ENABLED),
        help=(
            "Enable E21 export-only multi-resolution carrier: coarse geometry objects remain default, "
            "but fine geometry can take over configured large/noisy object families."
        ),
    )
    parser.add_argument("--multires-fine-voxel-size", type=float, default=MULTIRES_FINE_VOXEL_SIZE)
    parser.add_argument("--multires-fine-labels", default=MULTIRES_FINE_LABELS)
    parser.add_argument("--multires-risky-labels", default=MULTIRES_RISKY_LABELS)
    parser.add_argument("--multires-fine-split-by-label", type=int, choices=[0, 1], default=int(MULTIRES_FINE_SPLIT_BY_LABEL))
    parser.add_argument("--multires-fine-min-observations", type=int, default=MULTIRES_FINE_MIN_OBSERVATIONS)
    parser.add_argument("--multires-fine-takeover-min-points", type=int, default=MULTIRES_FINE_TAKEOVER_MIN_POINTS)
    parser.add_argument("--multires-risky-min-points", type=int, default=MULTIRES_RISKY_MIN_POINTS)
    parser.add_argument(
        "--multires-replacement-mode",
        choices=["replace", "risky-replace", "additive"],
        default=MULTIRES_REPLACEMENT_MODE,
        help=(
            "`replace` drops coarse objects claimed by fine/risky carriers; "
            "`risky-replace` keeps coarse fine-label objects and only replaces large risky-label objects; "
            "`additive` keeps every coarse object and appends fine carriers for diagnostic hierarchy tests."
        ),
    )
    parser.add_argument(
        "--geometry-repair-keep-labels",
        default=GEOMETRY_REPAIR_KEEP_LABELS,
        help=(
            "Comma-separated official eval keep-label set for geometry repairs. "
            "Set this for scene-specific repairs so low-margin decisions mirror eval_replica's GT keep-set."
        ),
    )
    parser.add_argument(
        "--geometry-repair-vent-to-sofa-delta",
        type=float,
        default=GEOMETRY_REPAIR_VENT_TO_SOFA_DELTA,
        help="Enable low-margin vent->sofa relabel when vent_score - sofa_score <= delta; negative disables it.",
    )
    parser.add_argument(
        "--geometry-repair-cushion-shrink-radius",
        type=float,
        default=GEOMETRY_REPAIR_CUSHION_SHRINK_RADIUS,
        help="Enable sofa-proximity cushion point shrink in meters; 0 disables it.",
    )
    parser.add_argument(
        "--geometry-repair-carve-rules",
        default=GEOMETRY_REPAIR_CARVE_RULES,
        help=(
            "Comma/semicolon-separated target:anchor:radius rules, e.g. "
            "`cushion:sofa:0.04`. Removes target points within radius meters of anchor points."
        ),
    )
    parser.add_argument(
        "--geometry-repair-large-label-rules",
        default=GEOMETRY_REPAIR_LARGE_LABEL_RULES,
        help=(
            "Comma/semicolon-separated source:target:min_extent rules, e.g. "
            "`tissue-paper:cloth:0.8`. Re-labels large objects when their current "
            "evaluator-facing class is implausibly small-object-like."
        ),
    )
    parser.add_argument(
        "--geometry-repair-large-label-evidence-mode",
        choices=["off", "active", "evidence", "strict", "carrier-v2"],
        default=GEOMETRY_REPAIR_LARGE_LABEL_EVIDENCE_MODE,
        help=(
            "Optional evidence gate for large-label relabel rules. `off` preserves legacy behavior; "
            "`active`/`strict` can require target-label support and point-mass guards before relabeling; "
            "`carrier-v2` treats target support as geometry-authority evidence instead of a hard scene-local label requirement."
        ),
    )
    parser.add_argument(
        "--geometry-repair-large-label-source-mode",
        choices=["clip-top1", "declared-source-or-clip", "target-declared-geometry"],
        default=GEOMETRY_REPAIR_LARGE_LABEL_SOURCE_MODE,
        help=(
            "Source-label authority for large-label repairs. `clip-top1` preserves the legacy behavior; "
            "`declared-source-or-clip` allows multi-view declared source evidence to enter the shape gate; "
            "`target-declared-geometry` is an explicit diagnostic mode for target-supported table carriers."
        ),
    )
    parser.add_argument(
        "--geometry-repair-large-label-require-target-declared",
        default=GEOMETRY_REPAIR_LARGE_LABEL_REQUIRE_TARGET_DECLARED,
        help=(
            "Comma-separated target labels that must appear in an object's declared-label history "
            "before a large-label relabel to that target is applied in active evidence mode."
        ),
    )
    parser.add_argument(
        "--geometry-repair-large-label-max-point-rate",
        type=float,
        default=GEOMETRY_REPAIR_LARGE_LABEL_MAX_POINT_RATE,
        help="Maximum fraction of input object points that large-label relabeling may affect in active evidence mode.",
    )
    parser.add_argument(
        "--geometry-repair-large-label-min-observations",
        type=int,
        default=GEOMETRY_REPAIR_LARGE_LABEL_MIN_OBSERVATIONS,
        help="carrier-v2 only: minimum merged detection count required before applying a large-label repair.",
    )
    parser.add_argument(
        "--geometry-repair-large-label-min-source-share",
        type=float,
        default=GEOMETRY_REPAIR_LARGE_LABEL_MIN_SOURCE_SHARE,
        help="carrier-v2 only: minimum declared source-label share required before applying a large-label repair.",
    )
    parser.add_argument(
        "--geometry-repair-keep-mode",
        choices=["configured", "declared-auto"],
        default=GEOMETRY_REPAIR_KEEP_MODE,
        help=(
            "How the evaluator-facing repair source authority set is built: `configured` uses "
            "--geometry-repair-keep-labels (or the broad default), `declared-auto` derives it "
            "GT-free from the scene's own multi-view declared labels."
        ),
    )
    parser.add_argument("--geometry-repair-keep-auto-min-count", type=int, default=GEOMETRY_REPAIR_KEEP_AUTO_MIN_COUNT)
    parser.add_argument(
        "--geometry-repair-scale-prior-mode",
        choices=["off", "log-only", "apply"],
        default=GEOMETRY_REPAIR_SCALE_PRIOR_MODE,
        help=(
            "Scale-prior semantic-authority check: `log-only` records extent-vs-prior violations "
            "and declared-target selections without changing labels; `apply` performs the sparse "
            "relabels.  Priors are the frozen commonsense table in duograph3d.scale_priors."
        ),
    )
    parser.add_argument("--geometry-repair-scale-prior-tolerance", type=float, default=GEOMETRY_REPAIR_SCALE_PRIOR_TOLERANCE)
    parser.add_argument("--geometry-repair-scale-prior-min-target-share", type=float, default=GEOMETRY_REPAIR_SCALE_PRIOR_MIN_TARGET_SHARE)
    parser.add_argument("--geometry-repair-scale-prior-max-source-share", type=float, default=GEOMETRY_REPAIR_SCALE_PRIOR_MAX_SOURCE_SHARE)
    parser.add_argument(
        "--geometry-repair-scale-prior-hard-ratio",
        type=float,
        default=GEOMETRY_REPAIR_SCALE_PRIOR_HARD_RATIO,
        help=(
            "Past this multiple of the source prior, unanimous readout is treated as systematic "
            "detector bias: the consensus guard is skipped and the target may fall back to the "
            "top CLIP label among physically-compatible classes."
        ),
    )
    parser.add_argument(
        "--geometry-repair-scale-prior-clip-fallback",
        type=int,
        choices=[0, 1],
        default=GEOMETRY_REPAIR_SCALE_PRIOR_CLIP_FALLBACK,
        help=(
            "Diagnostics-only: allow hard violations with no declared alternative to relabel via "
            "the physically-compatible CLIP ranking. Default off — that ranking measured as noise."
        ),
    )
    parser.add_argument(
        "--memory-dense-spatial-split",
        type=int,
        choices=[0, 1],
        default=MEMORY_DENSE_SPATIAL_SPLIT,
        help=(
            "Split memory-dense buckets whose member keys are not spatially connected "
            "(single-linkage components over key centroids); each component re-accumulates "
            "its own features and labels. A carrier whose evidence is not spatially coherent "
            "should not be one semantic entity."
        ),
    )
    parser.add_argument("--memory-dense-spatial-split-eps", type=float, default=MEMORY_DENSE_SPATIAL_SPLIT_EPS)
    parser.add_argument("--memory-dense-split-by-label", type=int, choices=[0, 1], default=int(MEMORY_DENSE_SPLIT_BY_LABEL))
    parser.add_argument("--memory-dense-split-min-observations", type=int, default=MEMORY_DENSE_SPLIT_MIN_OBSERVATIONS)
    parser.add_argument("--memory-dense-split-min-root-label-entropy", type=float, default=MEMORY_DENSE_SPLIT_MIN_ROOT_LABEL_ENTROPY)
    parser.add_argument("--memory-dense-split-max-root-top-share", type=float, default=MEMORY_DENSE_SPLIT_MAX_ROOT_TOP_SHARE)
    parser.add_argument("--cg-downsample-voxel-size", type=float, default=CG_DOWNSAMPLE_VOXEL_SIZE)
    parser.add_argument("--cg-dbscan-eps", type=float, default=CG_DBSCAN_EPS)
    parser.add_argument("--cg-dbscan-min-points", type=int, default=CG_DBSCAN_MIN_POINTS)
    parser.add_argument("--cg-merge-overlap-thresh", type=float, default=CG_MERGE_OVERLAP_THRESH)
    parser.add_argument("--cg-merge-visual-sim-thresh", type=float, default=CG_MERGE_VISUAL_SIM_THRESH)
    parser.add_argument("--cg-merge-text-sim-thresh", type=float, default=CG_MERGE_TEXT_SIM_THRESH)
    parser.add_argument(
        "--cg-merge-label-gate",
        type=int,
        choices=[0, 1],
        default=CG_MERGE_LABEL_GATE,
        help=(
            "Per-pair carrier-preservation veto inside the CG-style postprocess merge: "
            "pairs CG would merge are skipped when both objects hold distinct, "
            "well-supported declared-label clusters. 0 keeps legacy global-threshold merging."
        ),
    )
    parser.add_argument("--cg-merge-label-gate-min-share", type=float, default=CG_MERGE_LABEL_GATE_MIN_SHARE)
    parser.add_argument("--cg-merge-label-gate-min-obs", type=int, default=CG_MERGE_LABEL_GATE_MIN_OBS)
    parser.add_argument(
        "--cg-merge-label-gate-mutual-thresh",
        type=float,
        default=CG_MERGE_LABEL_GATE_MUTUAL_THRESH,
        help=(
            "Skip the label veto when both containment directions exceed this threshold: "
            "spatially coincident point sets are one observation stream split by readout "
            "noise, not independent evidence. Negative disables the guard."
        ),
    )
    parser.add_argument("--l2-occluded-after-misses", type=int, default=L2_OCCLUDED_AFTER_MISSES)
    parser.add_argument("--l2-dormant-after-misses", type=int, default=L2_DORMANT_AFTER_MISSES)
    parser.add_argument("--l2-retire-after-misses", type=int, default=L2_RETIRE_AFTER_MISSES)
    parser.add_argument("--l2-relation-bonus-weight", type=float, default=L2_RELATION_BONUS_WEIGHT)
    parser.add_argument("--l2-relation-bonus-cap", type=float, default=L2_RELATION_BONUS_CAP)
    parser.add_argument(
        "--text-feature-mode",
        choices=["item", "class"],
        default=os.environ.get("DUOGRAPH_TEXT_FEATURE_MODE", TEXT_FEATURE_MODE),
        help=(
            "`item` matches ConceptGraphs gsa_detections_none by using a generic text feature for merge gating; "
            "`class` uses recovered top-1 Replica class text features."
        ),
    )
    parser.add_argument(
        "--clip-feature-mode",
        choices=["image", "dominant-label-image", "label-text", "blend", "adaptive"],
        default=os.environ.get("DUOGRAPH_CLIP_FEATURE_MODE", CLIP_FEATURE_MODE),
        help=(
            "`image` preserves ConceptGraphs-style averaged detection CLIP features; "
            "`dominant-label-image` keeps image CLIP but averages only detections in the dominant recovered label bucket; "
            "`label-text` exports the dominant recovered Replica label text feature; "
            "`blend` interpolates image and label-text features; "
            "`adaptive` chooses all-image vs high-margin-image per carrier."
        ),
    )
    parser.add_argument(
        "--clip-feature-blend-alpha",
        type=float,
        default=float(os.environ.get("DUOGRAPH_CLIP_FEATURE_BLEND_ALPHA", CLIP_FEATURE_BLEND_ALPHA)),
    )
    parser.add_argument(
        "--export-clip-min-margin",
        type=float,
        default=EXPORT_CLIP_MIN_MARGIN,
        help="Use only detections with CLIP top1-top2 margin >= this value when averaging exported image clip_ft; falls back to all detections if none pass.",
    )
    parser.add_argument("--adaptive-clip-sink-labels", default=ADAPTIVE_CLIP_SINK_LABELS)
    parser.add_argument("--adaptive-clip-min-high-margin-count", type=int, default=ADAPTIVE_CLIP_MIN_HIGH_MARGIN_COUNT)
    parser.add_argument("--adaptive-clip-min-high-margin-rate", type=float, default=ADAPTIVE_CLIP_MIN_HIGH_MARGIN_RATE)
    parser.add_argument("--adaptive-clip-min-entropy", type=float, default=ADAPTIVE_CLIP_MIN_ENTROPY)
    parser.add_argument(
        "--phase",
        choices=["baseline", "cand", "l1", "beta", "gamma", "delta", "all"],
        default=os.environ.get("DUOGRAPH_PHASE", "baseline"),
        help=(
            "Pipeline feature phase. `cand` isolates candidate retrieval v2; "
            "`l1` isolates signed Layer1 + label distribution; `beta` enables both."
        ),
    )
    args = parser.parse_args()
    ROOT = args.root
    if args.pred_exp_name:
        PRED_EXP_NAME = args.pred_exp_name
    VOXEL_SIZE = max(float(args.voxel_size), 1e-6)
    MIN_MASK_PIXELS = max(int(args.min_mask_pixels), 1)
    MAX_POINTS_PER_OBS = max(int(args.max_points_per_obs), 1)
    MAX_POINTS_PER_OBJECT = max(int(args.max_points_per_object), 1)
    MASK_CONF_THRESHOLD = min(max(float(args.mask_conf_threshold), 0.0), 1.0)
    MAX_BBOX_AREA_RATIO = max(float(args.max_bbox_area_ratio), 0.0)
    MIN_VALID_DEPTH_POINTS = max(int(args.min_valid_depth_points), 1)
    DROP_POST_SUBTRACT_TINY = bool(args.drop_post_subtract_tiny)
    if args.min_object_detections is not None:
        MIN_OBJECT_DETECTIONS = max(int(args.min_object_detections), 1)
    EXPORT_SOURCE_STRATEGY = args.export_source
    EXPORT_CONSOLIDATION_DENSE_MAX_RATIO = min(max(float(args.export_consolidation_dense_max_ratio), 0.0), 1.0)
    MECHANISMS_SCOPE = str(args.mechanisms_scope)
    MIN_MEMORY_EXPORT_OBJECTS = max(int(args.min_memory_export_objects), 0)
    MIN_MEMORY_EXPORT_KEY_RATIO = max(float(args.min_memory_export_key_ratio), 0.0)
    MIN_MEMORY_EXPORT_POINT_RATIO = max(float(args.min_memory_export_point_ratio), 0.0)
    EXPORT_SPLIT_BY_LABEL = bool(args.export_split_by_label)
    EXPORT_SPLIT_POLICY = args.export_split_policy
    EXPORT_SPLIT_MIN_OBSERVATIONS = max(int(args.export_split_min_observations), 1)
    EXPORT_SPLIT_MIN_KEY_ENTROPY = max(float(args.export_split_min_key_entropy), 0.0)
    EXPORT_SPLIT_MAX_KEY_TOP_SHARE = min(max(float(args.export_split_max_key_top_share), 0.0), 1.0)
    EXPORT_SPLIT_MIN_LABEL_SHARE = min(max(float(args.export_split_min_label_share), 0.0), 1.0)
    EXPORT_SPLIT_MIN_CENTROID_SEPARATION = max(float(args.export_split_min_centroid_separation), 0.0)
    EXPORT_SPLIT_MIN_SCENE_SPLIT_RATE = min(max(float(args.export_split_min_scene_split_rate), 0.0), 1.0)
    MULTIRES_EXPORT_ENABLED = bool(args.multires_export)
    MULTIRES_FINE_VOXEL_SIZE = max(float(args.multires_fine_voxel_size), 1e-6)
    MULTIRES_FINE_LABELS = str(args.multires_fine_labels)
    MULTIRES_RISKY_LABELS = str(args.multires_risky_labels)
    MULTIRES_FINE_SPLIT_BY_LABEL = bool(args.multires_fine_split_by_label)
    MULTIRES_FINE_MIN_OBSERVATIONS = max(int(args.multires_fine_min_observations), 1)
    MULTIRES_FINE_TAKEOVER_MIN_POINTS = max(int(args.multires_fine_takeover_min_points), 0)
    MULTIRES_RISKY_MIN_POINTS = max(int(args.multires_risky_min_points), 1)
    MULTIRES_REPLACEMENT_MODE = str(args.multires_replacement_mode)
    GEOMETRY_REPAIR_KEEP_LABELS = str(args.geometry_repair_keep_labels)
    GEOMETRY_REPAIR_VENT_TO_SOFA_DELTA = float(args.geometry_repair_vent_to_sofa_delta)
    GEOMETRY_REPAIR_CUSHION_SHRINK_RADIUS = max(float(args.geometry_repair_cushion_shrink_radius), 0.0)
    GEOMETRY_REPAIR_CARVE_RULES = str(args.geometry_repair_carve_rules)
    GEOMETRY_REPAIR_LARGE_LABEL_RULES = str(args.geometry_repair_large_label_rules)
    GEOMETRY_REPAIR_LARGE_LABEL_EVIDENCE_MODE = str(args.geometry_repair_large_label_evidence_mode)
    GEOMETRY_REPAIR_LARGE_LABEL_SOURCE_MODE = str(args.geometry_repair_large_label_source_mode)
    GEOMETRY_REPAIR_LARGE_LABEL_REQUIRE_TARGET_DECLARED = str(args.geometry_repair_large_label_require_target_declared)
    GEOMETRY_REPAIR_LARGE_LABEL_MAX_POINT_RATE = float(args.geometry_repair_large_label_max_point_rate)
    GEOMETRY_REPAIR_LARGE_LABEL_MIN_OBSERVATIONS = max(int(args.geometry_repair_large_label_min_observations), 0)
    GEOMETRY_REPAIR_LARGE_LABEL_MIN_SOURCE_SHARE = min(max(float(args.geometry_repair_large_label_min_source_share), 0.0), 1.0)
    GEOMETRY_REPAIR_KEEP_MODE = str(args.geometry_repair_keep_mode)
    GEOMETRY_REPAIR_KEEP_AUTO_MIN_COUNT = max(int(args.geometry_repair_keep_auto_min_count), 1)
    GEOMETRY_REPAIR_SCALE_PRIOR_MODE = str(args.geometry_repair_scale_prior_mode)
    GEOMETRY_REPAIR_SCALE_PRIOR_TOLERANCE = max(float(args.geometry_repair_scale_prior_tolerance), 0.1)
    GEOMETRY_REPAIR_SCALE_PRIOR_MIN_TARGET_SHARE = min(max(float(args.geometry_repair_scale_prior_min_target_share), 0.0), 1.0)
    GEOMETRY_REPAIR_SCALE_PRIOR_MAX_SOURCE_SHARE = min(max(float(args.geometry_repair_scale_prior_max_source_share), 0.0), 1.0)
    GEOMETRY_REPAIR_SCALE_PRIOR_HARD_RATIO = max(float(args.geometry_repair_scale_prior_hard_ratio), 1.0)
    GEOMETRY_REPAIR_SCALE_PRIOR_CLIP_FALLBACK = int(args.geometry_repair_scale_prior_clip_fallback)
    MEMORY_DENSE_SPATIAL_SPLIT = int(args.memory_dense_spatial_split)
    MEMORY_DENSE_SPATIAL_SPLIT_EPS = max(float(args.memory_dense_spatial_split_eps), 0.05)
    MEMORY_DENSE_SPLIT_BY_LABEL = bool(args.memory_dense_split_by_label)
    MEMORY_DENSE_SPLIT_MIN_OBSERVATIONS = max(int(args.memory_dense_split_min_observations), 1)
    MEMORY_DENSE_SPLIT_MIN_ROOT_LABEL_ENTROPY = max(float(args.memory_dense_split_min_root_label_entropy), 0.0)
    MEMORY_DENSE_SPLIT_MAX_ROOT_TOP_SHARE = min(max(float(args.memory_dense_split_max_root_top_share), 0.0), 1.0)
    CG_DOWNSAMPLE_VOXEL_SIZE = max(float(args.cg_downsample_voxel_size), 1e-6)
    CG_DBSCAN_EPS = max(float(args.cg_dbscan_eps), 1e-6)
    CG_DBSCAN_MIN_POINTS = max(int(args.cg_dbscan_min_points), 1)
    CG_MERGE_OVERLAP_THRESH = min(max(float(args.cg_merge_overlap_thresh), 0.0), 1.0)
    CG_MERGE_VISUAL_SIM_THRESH = min(max(float(args.cg_merge_visual_sim_thresh), -1.0), 1.0)
    CG_MERGE_TEXT_SIM_THRESH = min(max(float(args.cg_merge_text_sim_thresh), -1.0), 1.0)
    CG_MERGE_LABEL_GATE = int(args.cg_merge_label_gate)
    CG_MERGE_LABEL_GATE_MIN_SHARE = min(max(float(args.cg_merge_label_gate_min_share), 0.0), 1.0)
    CG_MERGE_LABEL_GATE_MIN_OBS = max(int(args.cg_merge_label_gate_min_obs), 1)
    CG_MERGE_LABEL_GATE_MUTUAL_THRESH = min(float(args.cg_merge_label_gate_mutual_thresh), 1.0)
    L2_OCCLUDED_AFTER_MISSES = max(int(args.l2_occluded_after_misses), 1)
    L2_DORMANT_AFTER_MISSES = max(int(args.l2_dormant_after_misses), L2_OCCLUDED_AFTER_MISSES)
    L2_RETIRE_AFTER_MISSES = max(int(args.l2_retire_after_misses), L2_DORMANT_AFTER_MISSES + 1)
    L2_RELATION_BONUS_WEIGHT = max(float(args.l2_relation_bonus_weight), 0.0)
    L2_RELATION_BONUS_CAP = max(float(args.l2_relation_bonus_cap), 0.0)
    TEXT_FEATURE_MODE = args.text_feature_mode
    CLIP_FEATURE_MODE = args.clip_feature_mode
    CLIP_FEATURE_BLEND_ALPHA = min(max(float(args.clip_feature_blend_alpha), 0.0), 1.0)
    EXPORT_CLIP_MIN_MARGIN = max(float(args.export_clip_min_margin), 0.0)
    ADAPTIVE_CLIP_SINK_LABELS = args.adaptive_clip_sink_labels
    ADAPTIVE_CLIP_MIN_HIGH_MARGIN_COUNT = max(int(args.adaptive_clip_min_high_margin_count), 1)
    ADAPTIVE_CLIP_MIN_HIGH_MARGIN_RATE = min(max(float(args.adaptive_clip_min_high_margin_rate), 0.0), 1.0)
    ADAPTIVE_CLIP_MIN_ENTROPY = max(float(args.adaptive_clip_min_entropy), 0.0)
    os.environ["DUOGRAPH_TEXT_FEATURE_MODE"] = TEXT_FEATURE_MODE
    os.environ["DUOGRAPH_CLIP_FEATURE_MODE"] = CLIP_FEATURE_MODE
    os.environ["DUOGRAPH_CLIP_FEATURE_BLEND_ALPHA"] = str(CLIP_FEATURE_BLEND_ALPHA)
    os.environ["DUOGRAPH_EXPORT_CLIP_MIN_MARGIN"] = str(EXPORT_CLIP_MIN_MARGIN)
    os.environ["DUOGRAPH_GEOMETRY_REPAIR_LARGE_LABEL_RULES"] = GEOMETRY_REPAIR_LARGE_LABEL_RULES
    os.environ["DUOGRAPH_GEOMETRY_REPAIR_LARGE_LABEL_EVIDENCE_MODE"] = GEOMETRY_REPAIR_LARGE_LABEL_EVIDENCE_MODE
    os.environ["DUOGRAPH_GEOMETRY_REPAIR_LARGE_LABEL_REQUIRE_TARGET_DECLARED"] = GEOMETRY_REPAIR_LARGE_LABEL_REQUIRE_TARGET_DECLARED
    os.environ["DUOGRAPH_GEOMETRY_REPAIR_LARGE_LABEL_MAX_POINT_RATE"] = str(GEOMETRY_REPAIR_LARGE_LABEL_MAX_POINT_RATE)
    os.environ["DUOGRAPH_GEOMETRY_REPAIR_LARGE_LABEL_MIN_OBSERVATIONS"] = str(GEOMETRY_REPAIR_LARGE_LABEL_MIN_OBSERVATIONS)
    os.environ["DUOGRAPH_GEOMETRY_REPAIR_LARGE_LABEL_MIN_SOURCE_SHARE"] = str(GEOMETRY_REPAIR_LARGE_LABEL_MIN_SOURCE_SHARE)
    os.environ["DUOGRAPH_ADAPTIVE_CLIP_SINK_LABELS"] = ADAPTIVE_CLIP_SINK_LABELS
    os.environ["DUOGRAPH_ADAPTIVE_CLIP_MIN_HIGH_MARGIN_COUNT"] = str(ADAPTIVE_CLIP_MIN_HIGH_MARGIN_COUNT)
    os.environ["DUOGRAPH_ADAPTIVE_CLIP_MIN_HIGH_MARGIN_RATE"] = str(ADAPTIVE_CLIP_MIN_HIGH_MARGIN_RATE)
    os.environ["DUOGRAPH_ADAPTIVE_CLIP_MIN_ENTROPY"] = str(ADAPTIVE_CLIP_MIN_ENTROPY)
    os.environ["DUOGRAPH_PHASE"] = args.phase
    DATASET_MODE = str(args.dataset)
    if DATASET_MODE == "scannet":
        # ScanNet mode: NYU40 frozen priors, NYU40 structural set, external eval.
        ACTIVE_SCALE_PRIORS = SCANNET_NYU40_MAX_EXTENT_PRIORS
        STRUCTURAL_EXPORT_LABELS = frozenset({
            "wall", "floor", "ceiling", "door", "window",
            "person", "otherstructure", "otherfurniture", "otherprop",
        })
        args.skip_eval = True
    torch.set_num_threads(4)
    ROOT.mkdir(parents=True, exist_ok=True)
    (ROOT / "logs").mkdir(exist_ok=True)

    class_all2existing = torch.ones(len(REPLICA_CLASSES)).long() * -1
    for i, c in enumerate(REPLICA_EXISTING_CLASSES):
        class_all2existing[c] = i
    if DATASET_MODE == "scannet":
        class_names = list(NYU40_CLASSES)
        exclude_class = []
    else:
        class_names = [REPLICA_CLASSES[i] for i in REPLICA_EXISTING_CLASSES]
        exclude_class = [class_names.index(c) for c in ["other", "floor", "wall", "ceiling", "door", "window"]]
    label_to_index = {label: index for index, label in enumerate(class_names)}

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
        frames, key_data, multires_key_data, prep, frame_debug = prepare_scene(
            scene,
            class_names,
            class_feats_np,
            frame_limit=args.frame_limit,
            frame_stride=args.frame_stride,
        )
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
        manifest, export_debug, skipped_keys = write_conceptgraphs_payload(
            scene,
            result,
            key_data,
            multires_key_data,
            track_assignments,
            branch_summary,
            label_to_index,
            class_feats_np,
            prepare_key_count=int(prep.get("key_count", 0)) or None,
        )
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

    if DATASET_MODE == "scannet":
        baseline_rows = {}
        gap_rows = []
    else:
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
            "drop_post_subtract_tiny": DROP_POST_SUBTRACT_TINY,
            "class_agnostic_identity_token": CLASS_AGNOSTIC_TOKEN,
            "text_feature_mode": TEXT_FEATURE_MODE,
            "clip_feature_mode": CLIP_FEATURE_MODE,
            "clip_feature_blend_alpha": CLIP_FEATURE_BLEND_ALPHA,
            "export_clip_min_margin": EXPORT_CLIP_MIN_MARGIN,
            "adaptive_clip_sink_labels": ADAPTIVE_CLIP_SINK_LABELS,
            "adaptive_clip_min_high_margin_count": ADAPTIVE_CLIP_MIN_HIGH_MARGIN_COUNT,
            "adaptive_clip_min_high_margin_rate": ADAPTIVE_CLIP_MIN_HIGH_MARGIN_RATE,
            "adaptive_clip_min_entropy": ADAPTIVE_CLIP_MIN_ENTROPY,
            "export_split_by_label": EXPORT_SPLIT_BY_LABEL,
            "export_split_policy": EXPORT_SPLIT_POLICY,
            "export_split_min_observations": EXPORT_SPLIT_MIN_OBSERVATIONS,
            "export_split_min_key_entropy": EXPORT_SPLIT_MIN_KEY_ENTROPY,
            "export_split_max_key_top_share": EXPORT_SPLIT_MAX_KEY_TOP_SHARE,
            "export_split_min_label_share": EXPORT_SPLIT_MIN_LABEL_SHARE,
            "export_split_min_centroid_separation": EXPORT_SPLIT_MIN_CENTROID_SEPARATION,
            "export_split_min_scene_split_rate": EXPORT_SPLIT_MIN_SCENE_SPLIT_RATE,
            "multires_export_enabled": MULTIRES_EXPORT_ENABLED,
            "multires_fine_voxel_size": MULTIRES_FINE_VOXEL_SIZE,
            "multires_fine_labels": MULTIRES_FINE_LABELS,
            "multires_risky_labels": MULTIRES_RISKY_LABELS,
            "multires_fine_split_by_label": MULTIRES_FINE_SPLIT_BY_LABEL,
            "multires_fine_min_observations": MULTIRES_FINE_MIN_OBSERVATIONS,
            "multires_fine_takeover_min_points": MULTIRES_FINE_TAKEOVER_MIN_POINTS,
            "multires_risky_min_points": MULTIRES_RISKY_MIN_POINTS,
            "multires_replacement_mode": MULTIRES_REPLACEMENT_MODE,
            "geometry_repair_keep_labels": GEOMETRY_REPAIR_KEEP_LABELS,
                "geometry_repair_vent_to_sofa_delta": GEOMETRY_REPAIR_VENT_TO_SOFA_DELTA,
                "geometry_repair_cushion_shrink_radius": GEOMETRY_REPAIR_CUSHION_SHRINK_RADIUS,
                "geometry_repair_carve_rules": GEOMETRY_REPAIR_CARVE_RULES,
                "geometry_repair_large_label_rules": GEOMETRY_REPAIR_LARGE_LABEL_RULES,
                "geometry_repair_large_label_evidence_mode": GEOMETRY_REPAIR_LARGE_LABEL_EVIDENCE_MODE,
                "geometry_repair_large_label_source_mode": GEOMETRY_REPAIR_LARGE_LABEL_SOURCE_MODE,
                "geometry_repair_large_label_require_target_declared": GEOMETRY_REPAIR_LARGE_LABEL_REQUIRE_TARGET_DECLARED,
                "geometry_repair_large_label_max_point_rate": GEOMETRY_REPAIR_LARGE_LABEL_MAX_POINT_RATE,
                "geometry_repair_large_label_min_observations": GEOMETRY_REPAIR_LARGE_LABEL_MIN_OBSERVATIONS,
                "geometry_repair_large_label_min_source_share": GEOMETRY_REPAIR_LARGE_LABEL_MIN_SOURCE_SHARE,
                "geometry_repair_keep_mode": GEOMETRY_REPAIR_KEEP_MODE,
                "geometry_repair_keep_auto_min_count": GEOMETRY_REPAIR_KEEP_AUTO_MIN_COUNT,
                "geometry_repair_scale_prior_mode": GEOMETRY_REPAIR_SCALE_PRIOR_MODE,
                "geometry_repair_scale_prior_tolerance": GEOMETRY_REPAIR_SCALE_PRIOR_TOLERANCE,
                "geometry_repair_scale_prior_min_target_share": GEOMETRY_REPAIR_SCALE_PRIOR_MIN_TARGET_SHARE,
                "geometry_repair_scale_prior_max_source_share": GEOMETRY_REPAIR_SCALE_PRIOR_MAX_SOURCE_SHARE,
                "geometry_repair_scale_prior_hard_ratio": GEOMETRY_REPAIR_SCALE_PRIOR_HARD_RATIO,
                "geometry_repair_scale_prior_clip_fallback": GEOMETRY_REPAIR_SCALE_PRIOR_CLIP_FALLBACK,
                "memory_dense_split_by_label": MEMORY_DENSE_SPLIT_BY_LABEL,
            "memory_dense_spatial_split": MEMORY_DENSE_SPATIAL_SPLIT,
            "memory_dense_spatial_split_eps": MEMORY_DENSE_SPATIAL_SPLIT_EPS,
            "memory_dense_split_min_observations": MEMORY_DENSE_SPLIT_MIN_OBSERVATIONS,
            "memory_dense_split_min_root_label_entropy": MEMORY_DENSE_SPLIT_MIN_ROOT_LABEL_ENTROPY,
            "memory_dense_split_max_root_top_share": MEMORY_DENSE_SPLIT_MAX_ROOT_TOP_SHARE,
            "max_points_per_obs": MAX_POINTS_PER_OBS,
            "max_points_per_object": MAX_POINTS_PER_OBJECT,
            "frame_limit": args.frame_limit,
            "frame_stride": args.frame_stride,
            "l2_occluded_after_misses": L2_OCCLUDED_AFTER_MISSES,
            "l2_dormant_after_misses": L2_DORMANT_AFTER_MISSES,
            "l2_retire_after_misses": L2_RETIRE_AFTER_MISSES,
            "l2_relation_bonus_weight": L2_RELATION_BONUS_WEIGHT,
            "l2_relation_bonus_cap": L2_RELATION_BONUS_CAP,
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
                "merge_label_gate": CG_MERGE_LABEL_GATE,
                "merge_label_gate_min_share": CG_MERGE_LABEL_GATE_MIN_SHARE,
                "merge_label_gate_min_obs": CG_MERGE_LABEL_GATE_MIN_OBS,
                "merge_label_gate_mutual_thresh": CG_MERGE_LABEL_GATE_MUTUAL_THRESH,
            },
        },
        "setting_audit": {
            "uses_all_requested_replica_scenes": args.scenes == list(REPLICA_SCENE_IDS),
            "uses_conceptgraphs_gsa_detections_none": True,
            "uses_conceptgraphs_replica_semantic_evaluator": not args.skip_eval,
            "does_not_use_deva_annotation_masks": True,
            "does_not_use_gt_sidecar": True,
            "engineering_changes_on_top_of_parity_setting": True,
            "diagnostic_frame_limited": args.frame_limit is not None,
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
