from __future__ import annotations

"""Official-style semantic evaluation for ScanNet scenes (NYU40 protocol).

Mirrors ConceptGraphs' Replica protocol on ScanNet: every GT mesh vertex is
assigned the label of its nearest predicted-map point; per-object labels come
from CLIP feature argmax against the NYU40 text bank; structural / person /
other-* classes are excluded from scoring (exclusion set documented in the
output).  GT loading supports both `*_vh_clean_2.labels.ply` and, where that
file is absent, reconstruction from `segs.json` + `aggregation.json` + the
scannetv2 label-mapping TSV.
"""

import argparse
import csv
import gzip
import json
import os
import pickle
import sys
from pathlib import Path

import numpy as np
import torch
import open_clip

_CODE_ROOT = os.environ.get("DUOGRAPH_CODE_ROOT", "/home/nebula/xxy/DuoGraph3D")
sys.path.insert(0, _CODE_ROOT)
sys.path.insert(0, os.path.join(_CODE_ROOT, "src"))

import examples.run_conceptgraphs_engineered_parity as runner
from duograph3d.io_utils import write_json

NYU40_CLASSES = [
    "wall", "floor", "cabinet", "bed", "chair", "sofa", "table", "door",
    "window", "bookshelf", "picture", "counter", "blinds", "desk", "shelves",
    "curtain", "dresser", "pillow", "mirror", "floor mat", "clothes",
    "ceiling", "books", "refridgerator", "television", "paper", "towel",
    "shower curtain", "box", "whiteboard", "person", "night stand", "toilet",
    "sink", "lamp", "bathtub", "bag", "otherstructure", "otherfurniture",
    "otherprop",
]
EXCLUDED_CLASSES = {
    "wall", "floor", "ceiling", "door", "window",
    "person", "otherstructure", "otherfurniture", "otherprop",
}


def load_gt_vertices(scans_root: Path, scene: str, label_tsv: Path) -> tuple[np.ndarray, np.ndarray]:
    from plyfile import PlyData

    scene_dir = scans_root / scene
    labels_ply = scene_dir / f"{scene}_vh_clean_2.labels.ply"
    if labels_ply.exists():
        ply = PlyData.read(str(labels_ply))
        vertex = ply["vertex"]
        coords = np.stack([np.asarray(vertex[axis]) for axis in ("x", "y", "z")], axis=1).astype(np.float32)
        labels = np.asarray(vertex["label"]).astype(np.int64)
        return coords, labels
    # Reconstruct: vertex -> segment (segs.json), segment-group -> raw label
    # (aggregation.json), raw label -> nyu40 id (tsv).
    mesh_ply = scene_dir / f"{scene}_vh_clean_2.ply"
    ply = PlyData.read(str(mesh_ply))
    vertex = ply["vertex"]
    coords = np.stack([np.asarray(vertex[axis]) for axis in ("x", "y", "z")], axis=1).astype(np.float32)
    segs = json.loads((scene_dir / f"{scene}_vh_clean_2.0.010000.segs.json").read_text())
    seg_indices = np.asarray(segs["segIndices"], dtype=np.int64)
    agg = json.loads((scene_dir / f"{scene}.aggregation.json").read_text())
    raw_to_nyu40: dict[str, int] = {}
    with label_tsv.open() as handle:
        for row in csv.DictReader(handle, delimiter="\t"):
            try:
                raw_to_nyu40[row["raw_category"]] = int(row["nyu40id"])
            except (KeyError, ValueError):
                continue
    seg_to_label: dict[int, int] = {}
    for group in agg.get("segGroups", []):
        nyu40 = raw_to_nyu40.get(str(group.get("label", "")), 0)
        for seg in group.get("segments", []):
            seg_to_label[int(seg)] = nyu40
    labels = np.asarray([seg_to_label.get(int(s), 0) for s in seg_indices], dtype=np.int64)
    return coords, labels


def load_pred_points(stage_root: Path, scene: str, pred: str) -> tuple[np.ndarray, list[np.ndarray]]:
    path = stage_root / scene / "pcd_saves" / f"full_pcd_{pred}.pkl.gz"
    with gzip.open(path, "rb") as handle:
        payload = pickle.load(handle)
    objects = payload["objects"] if isinstance(payload, dict) else payload
    points, feats = [], []
    for obj in objects:
        pts = np.asarray(obj["pcd_np"], dtype=np.float32)
        if not len(pts):
            continue
        points.append(pts)
        feats.append(np.asarray(obj["clip_ft"], dtype=np.float32).reshape(-1))
    return points, feats


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--scenes", nargs="+", required=True)
    parser.add_argument("--pred-exp-name", required=True)
    parser.add_argument("--stage-root", type=Path, default=Path("/home/nebula/xxy/dataset/scannet_cg"))
    parser.add_argument("--scans-root", type=Path, default=Path("/home/nebula/xxy/dataset/scannet_v2/scans"))
    parser.add_argument(
        "--label-tsv", type=Path,
        default=Path("/home/nebula/xxy/dataset/scannet_v2/scannetv2-labels.combined.tsv"),
    )
    parser.add_argument("--output-root", type=Path, required=True)
    parser.add_argument("--device", default="cuda:0")
    args = parser.parse_args()
    args.output_root.mkdir(parents=True, exist_ok=True)

    print("Loading CLIP text bank (NYU40)", flush=True)
    clip_model, _, _ = open_clip.create_model_and_transforms("ViT-H-14", "laion2b_s32b_b79k")
    clip_model = clip_model.to(args.device)
    tokenizer = open_clip.get_tokenizer("ViT-H-14")
    text = tokenizer([f"an image of {c}" for c in NYU40_CLASSES]).to(args.device)
    with torch.no_grad():
        bank = clip_model.encode_text(text)
        bank = bank / bank.norm(dim=-1, keepdim=True)
    bank_np = bank.detach().cpu().numpy().astype(np.float32)
    excluded_ids = {NYU40_CLASSES.index(c) + 1 for c in EXCLUDED_CLASSES}

    n_cls = len(NYU40_CLASSES)
    per_scene_rows = []
    conf_all = torch.zeros((n_cls, n_cls), dtype=torch.long)
    reports = []
    for scene in args.scenes:
        coords, gt_labels = load_gt_vertices(args.scans_root, scene, args.label_tsv)
        obj_points, obj_feats = load_pred_points(args.stage_root, scene, args.pred_exp_name)
        if not obj_points:
            print(f"{scene}: no predicted objects, skipping", flush=True)
            continue
        feats = np.stack(obj_feats, axis=0)
        norms = np.linalg.norm(feats, axis=1, keepdims=True)
        norms[norms == 0] = 1.0
        obj_labels = np.argmax((feats / norms) @ bank_np.T, axis=1) + 1  # nyu40 ids 1..40
        pred_pts = np.concatenate(obj_points, axis=0)
        pred_lbl = np.concatenate([
            np.full((len(p),), obj_labels[i], dtype=np.int64) for i, p in enumerate(obj_points)
        ])
        keep_mask = (gt_labels > 0) & ~np.isin(gt_labels, list(excluded_ids))
        gt_xyz = torch.from_numpy(coords[keep_mask]).to(args.device)
        gt_lab = gt_labels[keep_mask]
        pred_xyz = torch.from_numpy(pred_pts).to(args.device)
        assigned = np.empty((len(gt_xyz),), dtype=np.int64)
        chunk = 20000
        with torch.no_grad():
            for start in range(0, len(gt_xyz), chunk):
                d = torch.cdist(gt_xyz[start:start + chunk], pred_xyz)
                assigned[start:start + chunk] = d.argmin(dim=1).cpu().numpy()
        pred_for_gt = pred_lbl[assigned]
        conf = torch.zeros((n_cls, n_cls), dtype=torch.long)
        for g, p in zip(gt_lab, pred_for_gt):
            conf[int(g) - 1, int(p) - 1] += 1
        conf_all += conf
        keep_index = torch.tensor(sorted(set(int(g) - 1 for g in gt_lab)), dtype=torch.long)
        row = runner.metrics_row(scene, conf.float(), keep_index, NYU40_CLASSES)
        per_scene_rows.append(row)
        print(json.dumps(runner.to_builtin(row)), flush=True)
        reports.append({
            "scene": scene,
            "gt_vertices_scored": int(keep_mask.sum()),
            "pred_points": int(len(pred_pts)),
            "pred_objects": int(len(obj_points)),
            "gt_classes": [NYU40_CLASSES[i] for i in keep_index.tolist()],
        })

    if per_scene_rows:
        keep_all = conf_all.sum(dim=1).nonzero().reshape(-1)
        per_scene_rows.append(runner.metrics_row("all", conf_all.float(), keep_all, NYU40_CLASSES))
    summary = {
        "protocol": "ScanNet NYU40 nearest-point semantic transfer eval; exclusions: " + ", ".join(sorted(EXCLUDED_CLASSES)),
        "pred_exp_name": args.pred_exp_name,
        "rows": per_scene_rows,
        "scene_reports": reports,
    }
    write_json(runner.to_builtin(summary), args.output_root / f"scannet_semseg_{args.pred_exp_name}.json")
    for row in per_scene_rows:
        print(f"SCANNET {row['scene_id']}: mIoU={row['miou']}", flush=True)
    print("SCANNET_EVAL_DONE", flush=True)


if __name__ == "__main__":
    main()
