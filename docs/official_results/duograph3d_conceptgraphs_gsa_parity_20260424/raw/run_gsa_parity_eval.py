from __future__ import annotations

import argparse
import csv
import gzip
import json
import os
import pickle
import sys
import time
from collections import Counter, defaultdict
from pathlib import Path

import numpy as np
from PIL import Image
import torch
import open_clip

sys.path.insert(0, "/home/nebula/xxy/DuoGraph3D/src")
sys.path.insert(0, "/home/nebula/xxy/concept-graphs-main")

from duograph3d.contracts import FrameInput, Observation, ObservationSupport, TemporalVariant
from duograph3d.events import BRANCH_DUOGRAPH3D
from duograph3d.io_utils import write_json
from duograph3d.metrics import serialize_records, summarize_run
from duograph3d.pipeline import DuoGraph3DPipeline
from conceptgraph.scripts.eval_replica_semseg import eval_replica
from conceptgraph.dataset.replica_constants import REPLICA_EXISTING_CLASSES, REPLICA_CLASSES, REPLICA_SCENE_IDS, REPLICA_SCENE_IDS_
from conceptgraph.utils.eval import compute_metrics

ROOT = Path("/home/nebula/xxy/duograph3d_artifacts/duograph3d_conceptgraphs_gsa_parity_20260424")
REPLICA_ROOT = Path("/home/nebula/xxy/dataset/Replica")
REPLICA_SEMANTIC_ROOT = Path("/home/nebula/xxy/dataset/Replica-semantic")
BASELINE_CSV = Path("/home/nebula/xxy/duograph3d_artifacts/conceptgraphs_replica_official_20260423/replica_ex6_results.csv")
PRED_EXP_NAME = "duograph3d_gsa_parity_naive"
FX = 600.0
FY = 600.0
CX = 599.5
CY = 339.5
DEPTH_SCALE = 6553.5
VOXEL_SIZE = 0.75
MIN_MASK_PIXELS = 300
MAX_POINTS_PER_OBS = 48
MAX_POINTS_PER_OBJECT = 4096


def normalize_np(arr: np.ndarray) -> np.ndarray:
    arr = np.asarray(arr, dtype=np.float32)
    norm = np.linalg.norm(arr, axis=-1, keepdims=True)
    norm[norm == 0] = 1.0
    return arr / norm


def sample_indices(count: int, limit: int) -> np.ndarray:
    if count <= limit:
        return np.arange(count, dtype=np.int64)
    return np.linspace(0, count - 1, num=limit, dtype=np.int64)


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
    return f"{scene}:gsa:{label}:{q[0]}:{q[1]}:{q[2]}"


def world_points_from_mask_arrays(mask: np.ndarray, depth: np.ndarray, rgb_image: np.ndarray, pose: np.ndarray):
    valid = mask & (depth > 1e-6)
    ys, xs = np.nonzero(valid)
    if len(xs) == 0:
        return None, None, None
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
    return world, rgb, centroid


def prepare_scene(scene: str, class_names: list[str], class_feats_np: np.ndarray):
    t0 = time.time()
    gsa_dir = REPLICA_ROOT / scene / "gsa_detections_none"
    poses = np.loadtxt(REPLICA_ROOT / scene / "traj.txt", dtype=np.float32).reshape(-1, 4, 4)
    key_data: dict[str, dict[str, object]] = {}
    frames: list[FrameInput] = []
    frame_debug = []
    total_raw_dets = 0
    total_kept = 0
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
        masks = det["mask"]
        confidences = det.get("confidence", np.ones(len(masks), dtype=np.float32))
        total_raw_dets += int(len(masks))
        for det_i, class_i in enumerate(label_idx):
            mask = masks[det_i]
            area = int(mask.sum())
            if area < MIN_MASK_PIXELS:
                continue
            world, colors, centroid = world_points_from_mask_arrays(mask, depth, rgb_image, pose)
            if world is None:
                continue
            label = class_names[int(class_i)]
            key = quant_key(scene, label, centroid)
            conf = float(np.clip(float(confidences[det_i]), 0.0, 1.0))
            support_size = round(area / 1_000_000.0, 4)
            depth_scale = round(float(np.linalg.norm(centroid)), 4)
            geometry_support = round(min(max(area / 200000.0, 0.2), 1.5), 4)
            obs_id = f"{frame_stem}:gsa-{det_i:03d}"
            observations.append(Observation(
                observation_id=obs_id,
                descriptor=f"{scene}:{label}",
                geometry_key=key,
                confidence=conf,
                repair_group_id=key,
                support_tokens=(frame_stem, label, key),
                support=ObservationSupport(
                    proposal_id=obs_id,
                    frame_token=frame_stem,
                    source_kind="conceptgraphs_gsa_none",
                    support_size=support_size,
                    depth_scale=depth_scale,
                    appearance_key=label,
                    continuity_key=key,
                    geometry_support=geometry_support,
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
            })
            bucket["label_counts"][label] += 1
            bucket["clip_sum"] += image_feats[det_i].astype(np.float64)
            bucket["text_sum"] += class_feats_np[int(class_i)].astype(np.float64)
            bucket["feature_count"] += 1
            bucket["points"].append(world)
            bucket["colors"].append(colors)
            bucket["mask_pixels"] += area
            bucket["confidence_sum"] += conf
            total_kept += 1
        frames.append(FrameInput(frame_id=f"replica-{scene}-{frame_idx:06d}", observations=observations))
        frame_debug.append({"frame": frame_stem, "observations": len(observations)})
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
            "max_points_per_obs": MAX_POINTS_PER_OBS,
            "max_points_per_object": MAX_POINTS_PER_OBJECT,
            "temporal_variant": TemporalVariant.NAIVE_FRAMEWISE.value,
        },
    }
    return frames, key_data, prep, frame_debug


def run_duograph(scene: str, frames: list[FrameInput]):
    t0 = time.time()
    result, logger = DuoGraph3DPipeline().run_sequence(
        sequence_id=f"replica-{scene}-conceptgraphs-gsa-parity",
        frames=frames,
        temporal_variant=TemporalVariant.NAIVE_FRAMEWISE,
        branch_id=BRANCH_DUOGRAPH3D,
    )
    summary = summarize_run(result, logger)
    summary["temporal_variant"] = TemporalVariant.NAIVE_FRAMEWISE.value
    summary["seconds"] = round(time.time() - t0, 3)
    return result, logger, summary


def write_report(scene: str, prep: dict, branch_summary: dict, logger) -> Path:
    outdir = ROOT / "reports" / scene
    outdir.mkdir(parents=True, exist_ok=True)
    event_path = outdir / f"events_replica_{scene}_duograph3d_full.json"
    write_json(serialize_records(logger), event_path)
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
            "max_points_per_obs": MAX_POINTS_PER_OBS,
            "max_points_per_object": MAX_POINTS_PER_OBJECT,
            "temporal_variant": TemporalVariant.NAIVE_FRAMEWISE.value,
        },
        "branches": {BRANCH_DUOGRAPH3D: branch_summary},
        "branch_event_files": {BRANCH_DUOGRAPH3D: str(event_path)},
    }
    path = outdir / f"bounded_slice_replica_{scene}.json"
    write_json(report, path)
    return path


def write_conceptgraphs_payload(scene: str, key_data: dict[str, dict[str, object]], track_assignments: dict[str, list[str]], branch_summary: dict):
    t0 = time.time()
    pcd_dir = REPLICA_ROOT / scene / "pcd_saves"
    pcd_dir.mkdir(parents=True, exist_ok=True)
    objects = []
    export_debug = []
    missing_keys = []
    for key, object_ids in sorted(track_assignments.items()):
        if key not in key_data:
            missing_keys.append(key)
            continue
        if not object_ids:
            continue
        data = key_data[key]
        pts_chunks = data["points"]
        col_chunks = data["colors"]
        if not pts_chunks:
            continue
        pts = np.concatenate(pts_chunks, axis=0).astype(np.float32)
        cols = np.concatenate(col_chunks, axis=0).astype(np.float32)
        keep = sample_indices(len(pts), MAX_POINTS_PER_OBJECT)
        pts = pts[keep]
        cols = cols[keep]
        label = data["label_counts"].most_common(1)[0][0]
        count = max(int(data["feature_count"]), 1)
        clip_ft = normalize_np((data["clip_sum"] / count).reshape(1, -1))[0].astype(np.float32)
        text_ft = normalize_np((data["text_sum"] / count).reshape(1, -1))[0].astype(np.float32)
        conf = float(data["confidence_sum"] / count)
        objects.append({
            "object_id": str(object_ids[0]),
            "track_hint": key,
            "class_name": [label],
            "class_id": [1],
            "conf": [conf],
            "clip_ft": clip_ft,
            "text_ft": text_ft,
            "pcd_np": pts,
            "pcd_color_np": cols,
            "bbox_np": bbox_from_points(pts),
            "num_detections": count,
        })
        export_debug.append({
            "track_hint": key,
            "object_id": str(object_ids[0]),
            "label": label,
            "num_detections": count,
            "point_count": int(len(pts)),
            "fragment_object_count": len(object_ids),
            "mask_pixels": int(data["mask_pixels"]),
        })
    payload = {"objects": objects, "bg_objects": None}
    result_path = pcd_dir / f"full_pcd_{PRED_EXP_NAME}.pkl.gz"
    with gzip.open(result_path, "wb") as handle:
        pickle.dump(payload, handle)
    proxy = {
        "scene": scene,
        "pred_exp_name": PRED_EXP_NAME,
        "object_count": len(objects),
        "point_count": int(sum(len(obj["pcd_np"]) for obj in objects)),
        "source": "duograph3d_over_conceptgraphs_gsa_detections_none",
        "temporal_variant": TemporalVariant.NAIVE_FRAMEWISE.value,
        "readiness": {
            "same_replica_scene_list_as_conceptgraphs": True,
            "same_gsa_detections_as_conceptgraphs": True,
            "same_eval_replica_semseg": True,
            "n_exclude": 6,
        },
    }
    write_json(proxy, pcd_dir / f"{PRED_EXP_NAME}_semantic_proxy.json")
    manifest = {
        "adapter": "conceptgraphs",
        "status": "format_aligned_official_evaluated",
        "dataset": "replica",
        "scene": scene,
        "branch_id": BRANCH_DUOGRAPH3D,
        "pred_exp_name": PRED_EXP_NAME,
        "object_count": len(objects),
        "point_count": proxy["point_count"],
        "feature_dim": int(objects[0]["clip_ft"].shape[0]) if objects else 0,
        "files": {
            "conceptgraphs_pkl_gz": str(result_path),
            "semantic_proxy_json": str(pcd_dir / f"{PRED_EXP_NAME}_semantic_proxy.json"),
        },
        "export_parameters": {
            "voxel_size": VOXEL_SIZE,
            "min_mask_pixels": MIN_MASK_PIXELS,
            "max_points_per_obs": MAX_POINTS_PER_OBS,
            "max_points_per_object": MAX_POINTS_PER_OBJECT,
            "temporal_variant": TemporalVariant.NAIVE_FRAMEWISE.value,
            "fragmentation_policy": "one exported object per observation track key; if DuoGraph3D fragmented one key into multiple memory ids, the first id anchors the exported object and fragment count is logged",
        },
        "branch_summary_excerpt": {
            "memory_node_count": branch_summary.get("memory_node_count"),
            "track_fragmentation": branch_summary.get("track_fragmentation"),
            "memory_relation_edge_count": branch_summary.get("memory_relation_edge_count"),
        },
        "seconds": round(time.time() - t0, 3),
    }
    write_json(manifest, pcd_dir / "duograph3d_gsa_parity_manifest.json")
    return manifest, export_debug, missing_keys


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


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--scenes", nargs="*", default=list(REPLICA_SCENE_IDS))
    parser.add_argument("--skip-eval", action="store_true")
    args = parser.parse_args()
    torch.set_num_threads(4)
    ROOT.mkdir(parents=True, exist_ok=True)
    (ROOT / "logs").mkdir(exist_ok=True)

    class_all2existing = torch.ones(len(REPLICA_CLASSES)).long() * -1
    for i, c in enumerate(REPLICA_EXISTING_CLASSES):
        class_all2existing[c] = i
    class_names = [REPLICA_CLASSES[i] for i in REPLICA_EXISTING_CLASSES]
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
        print(json.dumps(prep), flush=True)
        print(f"=== {scene}: DuoGraph3D ===", flush=True)
        result, logger, branch_summary = run_duograph(scene, frames)
        report_path = write_report(scene, prep, branch_summary, logger)
        print(json.dumps({"scene": scene, "duograph_seconds": branch_summary["seconds"], "memory_node_count": branch_summary["memory_node_count"], "track_count": len(branch_summary.get("track_assignments", {}))}), flush=True)
        print(f"=== {scene}: export ===", flush=True)
        manifest, export_debug, missing_keys = write_conceptgraphs_payload(scene, key_data, branch_summary.get("track_assignments", {}) or {}, branch_summary)
        manifests.append(manifest)
        scene_debug = {
            "scene": scene,
            "prep": prep,
            "report_path": str(report_path),
            "manifest": manifest,
            "export_object_count": manifest["object_count"],
            "export_point_count": manifest["point_count"],
            "missing_track_keys": len(missing_keys),
            "duograph_summary": branch_summary,
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
            print(json.dumps(row), flush=True)
        scene_debug["seconds_total"] = round(time.time() - scene_t0, 3)
        all_debug.append(scene_debug)
        write_json({"scenes": all_debug}, ROOT / "progress_debug.json")

    if not args.skip_eval and per_scene_rows:
        keep_all = conf_matrix_all.sum(axis=1).nonzero().reshape(-1)
        conf_matrices["all"] = {"conf_matrix": conf_matrix_all, "keep_index": keep_all}
        per_scene_rows.append(metrics_row("all", conf_matrix_all, keep_all, class_names))
        with (ROOT / "duograph_gsa_parity_results.csv").open("w", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=["scene_id", "miou", "mrecall", "mprecision", "mf1score", "fmiou"])
            writer.writeheader()
            writer.writerows(per_scene_rows)
        with gzip.open(ROOT / "duograph_gsa_parity_conf_matrices.pkl.gz", "wb") as handle:
            pickle.dump(conf_matrices, handle)

    baseline_rows = load_baseline_rows()
    summary = {
        "pred_exp_name": PRED_EXP_NAME,
        "protocol": "DuoGraph3D over official ConceptGraphs Replica GSA detections, evaluated with ConceptGraphs eval_replica_semseg n_exclude=6",
        "scenes": args.scenes,
        "parameters": {
            "voxel_size": VOXEL_SIZE,
            "min_mask_pixels": MIN_MASK_PIXELS,
            "max_points_per_obs": MAX_POINTS_PER_OBS,
            "max_points_per_object": MAX_POINTS_PER_OBJECT,
            "temporal_variant": TemporalVariant.NAIVE_FRAMEWISE.value,
            "eval_n_exclude": 6,
        },
        "setting_audit": {
            "corrects_prior_deva_subset_mismatch": True,
            "uses_all_requested_replica_scenes": args.scenes == list(REPLICA_SCENE_IDS),
            "uses_conceptgraphs_gsa_detections_none": True,
            "uses_conceptgraphs_replica_semantic_evaluator": not args.skip_eval,
            "does_not_use_deva_annotation_masks": True,
            "does_not_use_gt_sidecar": True,
        },
        "duograph_rows": per_scene_rows,
        "conceptgraphs_baseline_rows": [baseline_rows.get(scene) for scene in args.scenes + (["all"] if args.scenes == list(REPLICA_SCENE_IDS) else [])],
        "manifests": manifests,
        "scene_debug": all_debug,
    }
    write_json(summary, ROOT / "duograph_gsa_parity_summary.json")
    print(ROOT / "duograph_gsa_parity_summary.json", flush=True)


if __name__ == "__main__":
    main()
