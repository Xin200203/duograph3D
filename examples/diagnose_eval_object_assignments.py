from __future__ import annotations

import argparse
import csv
import gzip
import glob
import json
import os
import pickle
import sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

import numpy as np
import torch

try:
    import open_clip
except ImportError as exc:  # pragma: no cover - dependency lives in ConceptGraphs env.
    raise SystemExit("open_clip is required; run this in the ConceptGraphs/DuoGraph3D remote env") from exc

DEFAULT_CONCEPTGRAPHS_ROOT = Path(os.environ.get("CONCEPTGRAPHS_ROOT", "/home/nebula/xxy/concept-graphs-main"))
if str(DEFAULT_CONCEPTGRAPHS_ROOT) not in sys.path:
    sys.path.insert(0, str(DEFAULT_CONCEPTGRAPHS_ROOT))

from chamferdist.chamfer import knn_points  # noqa: E402
from conceptgraph.dataset.replica_constants import (  # noqa: E402
    REPLICA_CLASSES,
    REPLICA_EXISTING_CLASSES,
    REPLICA_SCENE_IDS,
    REPLICA_SCENE_IDS_,
)
from conceptgraph.slam.slam_classes import MapObjectList  # noqa: E402
from conceptgraph.scripts.eval_replica_semseg import _duograph_load_pointcloud_from_h5  # noqa: E402
from conceptgraph.utils.eval import compute_pred_gt_associations  # noqa: E402

EXCLUDE_BY_N = {
    1: ["other"],
    4: ["other", "floor", "wall", "ceiling"],
    6: ["other", "floor", "wall", "ceiling", "door", "window"],
}


def norm_label(value: Any) -> str:
    if isinstance(value, (list, tuple)):
        value = value[0] if value else ""
    return str(value).strip().lower()


def to_jsonable(value: Any) -> Any:
    if isinstance(value, dict):
        return {str(k): to_jsonable(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [to_jsonable(v) for v in value]
    if isinstance(value, (np.integer,)):
        return int(value)
    if isinstance(value, (np.floating,)):
        return float(value)
    if hasattr(value, "item"):
        try:
            return value.item()
        except Exception:
            return str(value)
    return value


def round6(value: float) -> float:
    return round(float(value), 6)


def newest_prediction_path(replica_root: Path, scene: str, pred_exp_name: str) -> Path:
    paths = sorted(
        glob.glob(str(replica_root / scene / "pcd_saves" / f"full_pcd_{pred_exp_name}*.pkl.gz")),
        key=os.path.getmtime,
    )
    if not paths:
        raise FileNotFoundError(f"no full_pcd for scene={scene!r}, pred_exp_name={pred_exp_name!r}")
    return Path(paths[-1])


def load_prediction(path: Path) -> tuple[list[dict[str, Any]], MapObjectList]:
    with gzip.open(path, "rb") as handle:
        payload = pickle.load(handle)
    raw_objects = list(payload.get("objects") or [])
    objects = MapObjectList()
    objects.load_serializable(raw_objects)
    return raw_objects, objects


def build_class_context(n_exclude: int, device: str) -> tuple[list[str], torch.Tensor, torch.Tensor, list[int]]:
    class_names = [REPLICA_CLASSES[index] for index in REPLICA_EXISTING_CLASSES]
    class_all2existing = torch.ones(len(REPLICA_CLASSES)).long() * -1
    for i, c in enumerate(REPLICA_EXISTING_CLASSES):
        class_all2existing[c] = i
    exclude_names = EXCLUDE_BY_N[n_exclude]
    exclude_indices = [class_names.index(name) for name in exclude_names]

    model, _, _ = open_clip.create_model_and_transforms("ViT-H-14", "laion2b_s32b_b79k")
    model = model.to(device)
    tokenizer = open_clip.get_tokenizer("ViT-H-14")
    text = tokenizer([f"an image of {name}" for name in class_names]).to(device)
    with torch.no_grad():
        class_feats = model.encode_text(text)
        class_feats = class_feats / class_feats.norm(dim=-1, keepdim=True)
    return class_names, class_feats, class_all2existing, exclude_indices


def object_point_count(raw_obj: dict[str, Any], loaded_obj: dict[str, Any]) -> int:
    pcd_np = raw_obj.get("pcd_np")
    if hasattr(pcd_np, "shape"):
        return int(pcd_np.shape[0])
    try:
        return int(len(loaded_obj["pcd"].points))
    except Exception:
        return 0


def object_bbox(points: np.ndarray) -> dict[str, Any]:
    if points.size == 0:
        return {"min": [], "max": [], "center": [], "extent": []}
    mn = points.min(axis=0)
    mx = points.max(axis=0)
    return {
        "min": [round6(v) for v in mn.tolist()],
        "max": [round6(v) for v in mx.tolist()],
        "center": [round6(v) for v in ((mn + mx) / 2.0).tolist()],
        "extent": [round6(v) for v in (mx - mn).tolist()],
    }


def counter_to_records(counter: Counter[int], class_names: list[str], total: int, limit: int) -> list[dict[str, Any]]:
    records = []
    for idx, count in counter.most_common(limit):
        records.append(
            {
                "class_index": int(idx),
                "class_name": class_names[int(idx)] if 0 <= int(idx) < len(class_names) else str(idx),
                "count": int(count),
                "share": round6(int(count) / max(int(total), 1)),
            }
        )
    return records


def object_counter_to_records(
    counter: Counter[int],
    *,
    object_pred_classes: list[int],
    raw_objects: list[dict[str, Any]],
    loaded_objects: MapObjectList,
    class_names: list[str],
    total: int,
    limit: int,
) -> list[dict[str, Any]]:
    records = []
    for obj_idx, count in counter.most_common(limit):
        idx = int(obj_idx)
        pred_idx = object_pred_classes[idx] if 0 <= idx < len(object_pred_classes) else -1
        raw = raw_objects[idx] if 0 <= idx < len(raw_objects) else {}
        loaded = loaded_objects[idx] if 0 <= idx < len(loaded_objects) else {}
        pts = np.asarray(loaded.get("pcd").points) if loaded and loaded.get("pcd") is not None else np.zeros((0, 3))
        bbox = object_bbox(pts)
        records.append(
            {
                "object_index": idx,
                "count": int(count),
                "share": round6(int(count) / max(int(total), 1)),
                "pred_class": class_names[pred_idx] if 0 <= pred_idx < len(class_names) else str(pred_idx),
                "export_class_name": norm_label(raw.get("class_name")),
                "source_key": norm_label(raw.get("source_key")),
                "base_geometry_key": norm_label(raw.get("base_geometry_key")),
                "num_detections": int(raw.get("num_detections") or 0),
                "pcd_points": object_point_count(raw, loaded),
                "bbox_center": bbox["center"],
                "bbox_extent": bbox["extent"],
            }
        )
    return records


def write_csv(path: Path, rows: list[dict[str, Any]], fieldnames: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow({key: row.get(key, "") for key in fieldnames})


def analyze_scene(
    *,
    scene: str,
    scene_id_: str,
    pred_exp_name: str,
    replica_root: Path,
    replica_semantic_root: Path,
    class_names: list[str],
    class_feats: torch.Tensor,
    class_all2existing: torch.Tensor,
    base_ignore_indices: list[int],
    focus_classes: set[str],
    top_k: int,
    device: str,
) -> dict[str, Any]:
    gt_pc_path = replica_semantic_root / scene_id_ / "Sequence_1" / "saved-maps-gt"
    gt_pose_path = replica_semantic_root / scene_id_ / "Sequence_1" / "traj_w_c.txt"
    gt_map = _duograph_load_pointcloud_from_h5(gt_pc_path, device="cpu")
    gt_poses_np = np.loadtxt(gt_pose_path)
    gt_poses = torch.from_numpy(gt_poses_np.reshape(-1, 4, 4)).float()
    gt_xyz = gt_map.points_padded[0]
    gt_embedding = gt_map.embeddings_padded[0]
    gt_class = gt_embedding.argmax(dim=1)
    gt_class = class_all2existing[gt_class]
    gt_xyz = gt_xyz @ gt_poses[0, :3, :3].t() + gt_poses[0, :3, 3]

    all_class_index = np.arange(len(class_names))
    existing_index = gt_class.unique().cpu().numpy()
    ignore_index = np.asarray(list(base_ignore_indices) + np.setdiff1d(all_class_index, existing_index).tolist(), dtype=np.int64)
    keep_index = np.setdiff1d(all_class_index, ignore_index)
    keep_tensor = torch.from_numpy(keep_index).long()

    pred_path = newest_prediction_path(replica_root, scene, pred_exp_name)
    raw_objects, objects = load_prediction(pred_path)
    object_feats = objects.get_stacked_values_torch("clip_ft").to(device)
    object_feats = object_feats / object_feats.norm(dim=-1, keepdim=True).clamp_min(1e-12)
    object_class_sim = object_feats @ class_feats.T
    object_class_sim[:, ignore_index] = -1e10
    object_class = object_class_sim.argmax(dim=-1).detach().cpu().long()
    object_pred_classes = [int(v) for v in object_class.tolist()]
    object_margin = []
    with torch.no_grad():
        top2 = torch.topk(object_class_sim.detach().cpu(), k=2, dim=1)
        for i in range(top2.values.shape[0]):
            object_margin.append(float(top2.values[i, 0] - top2.values[i, 1]))

    pred_xyz_parts = []
    pred_class_parts = []
    pred_object_parts = []
    for i in range(len(objects)):
        pts = np.asarray(objects[i]["pcd"].points)
        if pts.size == 0:
            continue
        cls = int(object_class[i].item())
        pred_xyz_parts.append(pts)
        pred_class_parts.append(np.full(len(pts), cls, dtype=np.int64))
        pred_object_parts.append(np.full(len(pts), i, dtype=np.int64))
    if not pred_xyz_parts:
        raise RuntimeError(f"no prediction points for {scene} {pred_exp_name}")
    pred_xyz_full = torch.from_numpy(np.concatenate(pred_xyz_parts, axis=0)).float()
    pred_class_full = torch.from_numpy(np.concatenate(pred_class_parts, axis=0)).long()
    pred_object_full = torch.from_numpy(np.concatenate(pred_object_parts, axis=0)).long()

    slam_path = replica_root / scene / "rgb_cloud"
    slam_pointclouds = _duograph_load_pointcloud_from_h5(slam_path, device="cpu")
    slam_xyz = slam_pointclouds.points_padded[0]

    slam_nn_in_pred = knn_points(
        slam_xyz.unsqueeze(0).to(device).contiguous().float(),
        pred_xyz_full.unsqueeze(0).to(device).contiguous().float(),
        lengths1=None,
        lengths2=None,
        return_nn=True,
        return_sorted=True,
        K=1,
    )
    idx_slam_to_pred = slam_nn_in_pred.idx.squeeze(0).squeeze(-1).cpu()
    pred_xyz = slam_xyz
    pred_class = pred_class_full[idx_slam_to_pred]
    pred_object = pred_object_full[idx_slam_to_pred]

    idx_pred_to_gt, _ = compute_pred_gt_associations(
        pred_xyz.unsqueeze(0).to(device).contiguous().float(),
        gt_xyz.unsqueeze(0).to(device).contiguous().float(),
    )
    idx_pred_to_gt = idx_pred_to_gt.cpu()
    label_gt = gt_class[idx_pred_to_gt]
    pred_keep_idx = torch.isin(label_gt, keep_tensor)
    kept_gt = label_gt[pred_keep_idx].long().cpu()
    kept_pred_class = pred_class[pred_keep_idx].long().cpu()
    kept_pred_object = pred_object[pred_keep_idx].long().cpu()

    object_gt_counts: dict[int, Counter[int]] = defaultdict(Counter)
    gt_pred_counts: dict[int, Counter[int]] = defaultdict(Counter)
    gt_object_counts: dict[int, Counter[int]] = defaultdict(Counter)
    predclass_gt_counts: dict[int, Counter[int]] = defaultdict(Counter)
    confusion_counts: Counter[tuple[int, int]] = Counter()
    for gt_idx, pred_idx, obj_idx in zip(kept_gt.tolist(), kept_pred_class.tolist(), kept_pred_object.tolist()):
        object_gt_counts[int(obj_idx)][int(gt_idx)] += 1
        gt_pred_counts[int(gt_idx)][int(pred_idx)] += 1
        gt_object_counts[int(gt_idx)][int(obj_idx)] += 1
        predclass_gt_counts[int(pred_idx)][int(gt_idx)] += 1
        if int(gt_idx) != int(pred_idx):
            confusion_counts[(int(gt_idx), int(pred_idx))] += 1

    object_rows = []
    for i in range(len(objects)):
        loaded = objects[i]
        raw = raw_objects[i] if i < len(raw_objects) else {}
        pts = np.asarray(loaded["pcd"].points)
        gt_counter = object_gt_counts.get(i, Counter())
        eval_points = sum(gt_counter.values())
        dominant_gt_idx, dominant_gt_count = gt_counter.most_common(1)[0] if gt_counter else (-1, 0)
        pred_idx = object_pred_classes[i]
        focus_hits = {
            name: int(gt_counter.get(class_names.index(name), 0))
            for name in focus_classes
            if name in class_names
        }
        bbox = object_bbox(pts)
        object_rows.append(
            {
                "scene": scene,
                "object_index": i,
                "eval_points": int(eval_points),
                "pcd_points": object_point_count(raw, loaded),
                "pred_class": class_names[pred_idx] if 0 <= pred_idx < len(class_names) else str(pred_idx),
                "clip_margin": round6(object_margin[i]) if i < len(object_margin) else "",
                "export_class_name": norm_label(raw.get("class_name")),
                "source_key": norm_label(raw.get("source_key")),
                "base_geometry_key": norm_label(raw.get("base_geometry_key")),
                "num_detections": int(raw.get("num_detections") or 0),
                "dominant_gt_class": class_names[dominant_gt_idx] if 0 <= dominant_gt_idx < len(class_names) else "",
                "dominant_gt_count": int(dominant_gt_count),
                "dominant_gt_share": round6(int(dominant_gt_count) / max(int(eval_points), 1)),
                "top_gt_classes_json": json.dumps(counter_to_records(gt_counter, class_names, eval_points, top_k), ensure_ascii=False),
                "focus_gt_counts_json": json.dumps(focus_hits, ensure_ascii=False, sort_keys=True),
                "bbox_center_json": json.dumps(bbox["center"]),
                "bbox_extent_json": json.dumps(bbox["extent"]),
            }
        )

    gt_rows = []
    for gt_idx in sorted(gt_pred_counts):
        total = sum(gt_pred_counts[gt_idx].values())
        pred_records = counter_to_records(gt_pred_counts[gt_idx], class_names, total, top_k)
        object_records = object_counter_to_records(
            gt_object_counts[gt_idx],
            object_pred_classes=object_pred_classes,
            raw_objects=raw_objects,
            loaded_objects=objects,
            class_names=class_names,
            total=total,
            limit=top_k,
        )
        gt_name = class_names[gt_idx]
        gt_rows.append(
            {
                "scene": scene,
                "gt_class": gt_name,
                "gt_class_index": int(gt_idx),
                "eval_points": int(total),
                "true_positive": int(gt_pred_counts[gt_idx].get(gt_idx, 0)),
                "recall": round6(gt_pred_counts[gt_idx].get(gt_idx, 0) / max(total, 1)),
                "focus": int(gt_name in focus_classes),
                "top_pred_classes_json": json.dumps(pred_records, ensure_ascii=False),
                "top_objects_json": json.dumps(object_records, ensure_ascii=False),
            }
        )

    pred_rows = []
    for pred_idx in sorted(predclass_gt_counts):
        total = sum(predclass_gt_counts[pred_idx].values())
        pred_rows.append(
            {
                "scene": scene,
                "pred_class": class_names[pred_idx] if 0 <= pred_idx < len(class_names) else str(pred_idx),
                "pred_class_index": int(pred_idx),
                "eval_points": int(total),
                "true_positive": int(predclass_gt_counts[pred_idx].get(pred_idx, 0)),
                "precision": round6(predclass_gt_counts[pred_idx].get(pred_idx, 0) / max(total, 1)),
                "top_gt_classes_json": json.dumps(counter_to_records(predclass_gt_counts[pred_idx], class_names, total, top_k), ensure_ascii=False),
            }
        )

    confusion_rows = []
    for (gt_idx, pred_idx), count in confusion_counts.most_common(top_k * 4):
        total = sum(gt_pred_counts[gt_idx].values())
        confusion_rows.append(
            {
                "scene": scene,
                "gt_class": class_names[gt_idx],
                "pred_class": class_names[pred_idx],
                "count": int(count),
                "gt_error_share": round6(int(count) / max(total, 1)),
            }
        )

    focus_summary = {}
    for name in sorted(focus_classes):
        if name not in class_names:
            continue
        idx = class_names.index(name)
        total = sum(gt_pred_counts.get(idx, Counter()).values())
        focus_summary[name] = {
            "eval_points": int(total),
            "recall": round6(gt_pred_counts.get(idx, Counter()).get(idx, 0) / max(total, 1)),
            "top_pred_classes": counter_to_records(gt_pred_counts.get(idx, Counter()), class_names, total, top_k),
            "top_objects": object_counter_to_records(
                gt_object_counts.get(idx, Counter()),
                object_pred_classes=object_pred_classes,
                raw_objects=raw_objects,
                loaded_objects=objects,
                class_names=class_names,
                total=total,
                limit=top_k,
            ),
        }

    return {
        "summary": {
            "scene": scene,
            "pred_exp_name": pred_exp_name,
            "prediction_path": str(pred_path),
            "object_count": len(objects),
            "raw_pred_points": int(len(pred_xyz_full)),
            "slam_points": int(len(slam_xyz)),
            "eval_keep_points": int(len(kept_gt)),
            "keep_classes": [class_names[int(i)] for i in keep_index],
            "focus_classes": sorted(focus_classes),
            "focus_summary": focus_summary,
        },
        "object_rows": object_rows,
        "gt_rows": gt_rows,
        "pred_rows": pred_rows,
        "confusion_rows": confusion_rows,
    }


def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "Mirror the official ConceptGraphs Replica evaluator, but keep object IDs so failures can be traced "
            "from GT class -> predicted class -> exported object/source geometry."
        )
    )
    parser.add_argument("--replica-root", type=Path, default=Path("/home/nebula/xxy/dataset/Replica"))
    parser.add_argument("--replica-semantic-root", type=Path, default=Path("/home/nebula/xxy/dataset/Replica-semantic"))
    parser.add_argument("--pred-exp-name", required=True)
    parser.add_argument("--scenes", nargs="+", required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--focus-classes", nargs="*", default=[])
    parser.add_argument("--n-exclude", type=int, choices=[1, 4, 6], default=6)
    parser.add_argument("--top-k", type=int, default=12)
    parser.add_argument("--device", default="cuda:0" if torch.cuda.is_available() else "cpu")
    args = parser.parse_args()

    if args.device == "cpu":
        raise SystemExit("This diagnostic mirrors ConceptGraphs eval and requires CUDA chamferdist; use --device cuda:0")

    scene_map = dict(zip(REPLICA_SCENE_IDS, REPLICA_SCENE_IDS_))
    missing = [scene for scene in args.scenes if scene not in scene_map]
    if missing:
        raise ValueError(f"unknown Replica scene(s): {missing}")

    args.output_dir.mkdir(parents=True, exist_ok=True)
    focus_classes = {str(name).strip().lower() for name in args.focus_classes if str(name).strip()}
    class_names, class_feats, class_all2existing, base_ignore_indices = build_class_context(args.n_exclude, args.device)

    summary = {
        "pred_exp_name": args.pred_exp_name,
        "n_exclude": args.n_exclude,
        "device": args.device,
        "scenes": [],
    }
    all_object_rows: list[dict[str, Any]] = []
    all_gt_rows: list[dict[str, Any]] = []
    all_pred_rows: list[dict[str, Any]] = []
    all_confusion_rows: list[dict[str, Any]] = []

    for scene in args.scenes:
        print(f"=== diagnostic eval assignments: {scene} {args.pred_exp_name} ===", flush=True)
        result = analyze_scene(
            scene=scene,
            scene_id_=scene_map[scene],
            pred_exp_name=args.pred_exp_name,
            replica_root=args.replica_root,
            replica_semantic_root=args.replica_semantic_root,
            class_names=class_names,
            class_feats=class_feats,
            class_all2existing=class_all2existing,
            base_ignore_indices=base_ignore_indices,
            focus_classes=focus_classes,
            top_k=args.top_k,
            device=args.device,
        )
        scene_summary = result["summary"]
        summary["scenes"].append(scene_summary)
        all_object_rows.extend(result["object_rows"])
        all_gt_rows.extend(result["gt_rows"])
        all_pred_rows.extend(result["pred_rows"])
        all_confusion_rows.extend(result["confusion_rows"])
        (args.output_dir / f"{scene}_summary.json").write_text(
            json.dumps(to_jsonable(scene_summary), indent=2, ensure_ascii=False),
            encoding="utf-8",
        )

    write_csv(
        args.output_dir / "eval_object_assignment_rows.csv",
        all_object_rows,
        [
            "scene",
            "object_index",
            "eval_points",
            "pcd_points",
            "pred_class",
            "clip_margin",
            "export_class_name",
            "source_key",
            "base_geometry_key",
            "num_detections",
            "dominant_gt_class",
            "dominant_gt_count",
            "dominant_gt_share",
            "top_gt_classes_json",
            "focus_gt_counts_json",
            "bbox_center_json",
            "bbox_extent_json",
        ],
    )
    write_csv(
        args.output_dir / "eval_gt_class_rows.csv",
        all_gt_rows,
        ["scene", "gt_class", "gt_class_index", "eval_points", "true_positive", "recall", "focus", "top_pred_classes_json", "top_objects_json"],
    )
    write_csv(
        args.output_dir / "eval_pred_class_rows.csv",
        all_pred_rows,
        ["scene", "pred_class", "pred_class_index", "eval_points", "true_positive", "precision", "top_gt_classes_json"],
    )
    write_csv(
        args.output_dir / "eval_top_confusions.csv",
        all_confusion_rows,
        ["scene", "gt_class", "pred_class", "count", "gt_error_share"],
    )
    summary_path = args.output_dir / "eval_assignment_summary.json"
    summary_path.write_text(json.dumps(to_jsonable(summary), indent=2, ensure_ascii=False), encoding="utf-8")
    print(summary_path, flush=True)


if __name__ == "__main__":
    main()
