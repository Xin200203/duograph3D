from __future__ import annotations

"""Apply DuoGraph3D's carrier-authority mechanisms to ConceptGraphs' OWN maps.

Main-table experiment: load CG's official pre-postprocess object maps
(`full_pcd_none_*.pkl.gz`, the exact artifact the official baseline was
evaluated on), rebuild the true multi-view declared-label distributions from
the GSA detections each object absorbed (objects record image_idx/mask_idx into
the filter_gobs-filtered detection arrays), then run our postprocess with the
label-cluster merge gate and/or the scale-prior authority repair — one global
config, zero scene names — and evaluate with the identical official protocol.

Rows (one process per row; config via --row):
  cg_legacy   CG map + CG-style postprocess (denoise/filter/legacy merge)
  cg_gate     CG map + gated postprocess (label-cluster veto, floor2+mutual)
  cg_sp       CG map + legacy postprocess + scale-prior repair (declared-auto)
  cg_gate_sp  CG map + gated postprocess + scale-prior repair

Alignment safety: for every object we verify its stored clip_ft against the
mean of its detections' image_feats; scenes failing the cosine check abort
rather than silently mis-attributing votes.
"""

import argparse
import gzip
import json
import os
import pickle
import sys
import time
from collections import Counter
from pathlib import Path

import numpy as np
import torch
import open_clip

_CODE_ROOT = os.environ.get("DUOGRAPH_CODE_ROOT", "/home/nebula/xxy/DuoGraph3D")
sys.path.insert(0, _CODE_ROOT)
sys.path.insert(0, os.path.join(_CODE_ROOT, "src"))
sys.path.insert(0, os.environ.get("DUOGRAPH_CG_MAIN", "/home/nebula/xxy/concept-graphs-main"))

from conceptgraph.dataset.replica_constants import (
    REPLICA_CLASSES,
    REPLICA_EXISTING_CLASSES,
    REPLICA_SCENE_IDS,
    REPLICA_SCENE_IDS_,
)
from conceptgraph.scripts.eval_replica_semseg import eval_replica
from conceptgraph.slam.slam_classes import MapObjectList
from conceptgraph.slam.utils import filter_gobs, get_bounding_box

import examples.run_conceptgraphs_engineered_parity as runner
from duograph3d.io_utils import write_json

CG_OFFICIAL_PRED = "none_overlap_maskconf0.95_simsum1.2_dbscan.1_merge20_masksub"
STRIDE = 5  # the official cfslam run consumed every 5th frame

ROW_CONFIGS = {
    "cg_legacy": {"gate": False, "sp": False},
    "cg_gate": {"gate": True, "sp": False},
    "cg_sp": {"gate": False, "sp": True},
    "cg_gate_sp": {"gate": True, "sp": True},
}


def official_filter_cfg():
    from types import SimpleNamespace

    return SimpleNamespace(
        mask_area_threshold=25,
        mask_conf_threshold=0.95,
        max_bbox_area_ratio=0.5,
        skip_bg=True,
    )


def load_cg_map(scene: str) -> list[dict]:
    path = runner.REPLICA_ROOT / scene / "pcd_saves" / f"full_pcd_{CG_OFFICIAL_PRED}.pkl.gz"
    with gzip.open(path, "rb") as handle:
        payload = pickle.load(handle)
    objects = payload["objects"] if isinstance(payload, dict) else payload
    return list(objects)


def frame_votes_and_feats(scene: str, frame_idx: int, class_feats_np: np.ndarray, cache: dict):
    """Per-detection CLIP top-1 labels for one frame, in filter_gobs order."""
    if frame_idx in cache:
        return cache[frame_idx]
    # CG's image_idx is the strided consumption index (0..399); GSA files are
    # named by raw frame number (frame000000, frame000005, ...).
    raw_frame = frame_idx * STRIDE
    det_path = runner.REPLICA_ROOT / scene / "gsa_detections_none" / f"frame{raw_frame:06d}.pkl.gz"
    with gzip.open(det_path, "rb") as handle:
        gobs = pickle.load(handle)
    masks = np.asarray(gobs["mask"])
    image_hw = masks.shape[1:3] if masks.ndim == 3 else (680, 1200)
    dummy_image = np.zeros((image_hw[0], image_hw[1], 3), dtype=np.uint8)
    gobs = filter_gobs(official_filter_cfg(), gobs, dummy_image)
    feats = np.asarray(gobs["image_feats"], dtype=np.float32)
    norms = np.linalg.norm(feats, axis=1, keepdims=True)
    norms[norms == 0] = 1.0
    feats = feats / norms
    votes = np.argmax(feats @ class_feats_np.T, axis=1)
    cache[frame_idx] = (votes, feats)
    return cache[frame_idx]


def attach_declared_distributions(
    scene: str,
    objects: list[dict],
    class_names: list[str],
    class_feats_np: np.ndarray,
) -> dict:
    cache: dict = {}
    alignment_cosines: list[float] = []
    vote_totals = 0
    missing_pairs = 0
    for obj in objects:
        counts: Counter[str] = Counter()
        det_feats: list[np.ndarray] = []
        for frame_idx, mask_idx in zip(obj.get("image_idx", []), obj.get("mask_idx", [])):
            votes, feats = frame_votes_and_feats(scene, int(frame_idx), class_feats_np, cache)
            if int(mask_idx) >= len(votes):
                missing_pairs += 1
                continue
            counts[class_names[int(votes[int(mask_idx)])]] += 1
            det_feats.append(feats[int(mask_idx)])
            vote_totals += 1
        obj["declared_label_counts"] = [[label, int(n)] for label, n in sorted(counts.items())]
        if det_feats:
            mean_feat = np.mean(np.stack(det_feats, axis=0), axis=0)
            mean_feat = mean_feat / max(float(np.linalg.norm(mean_feat)), 1e-8)
            obj_ft = np.asarray(obj["clip_ft"], dtype=np.float32).reshape(-1)
            obj_ft = obj_ft / max(float(np.linalg.norm(obj_ft)), 1e-8)
            alignment_cosines.append(float(np.dot(mean_feat, obj_ft)))
    return {
        "vote_totals": vote_totals,
        "missing_pairs": missing_pairs,
        "alignment_cos_mean": round(float(np.mean(alignment_cosines)), 4) if alignment_cosines else None,
        "alignment_cos_min": round(float(np.min(alignment_cosines)), 4) if alignment_cosines else None,
        "frames_loaded": len(cache),
    }


def rebuild_runtime_objects(objects: list[dict], cfg) -> MapObjectList:
    rebuilt = MapObjectList()
    for obj in objects:
        entry = dict(obj)
        pcd_np = np.asarray(entry.pop("pcd_np"))
        color_np = np.asarray(entry.pop("pcd_color_np"))
        entry.pop("bbox_np", None)
        # Per-detection masks/boxes are unused downstream and their ndarray
        # forms would break merge_obj2_into_obj1's list-concatenation merging.
        entry.pop("mask", None)
        entry.pop("xyxy", None)
        entry["pcd"] = runner.make_open3d_pcd(pcd_np, color_np)
        entry["bbox"] = get_bounding_box(cfg, entry["pcd"])
        entry["clip_ft"] = torch.from_numpy(np.asarray(entry["clip_ft"], dtype=np.float32))
        entry["text_ft"] = torch.from_numpy(np.asarray(entry["text_ft"], dtype=np.float32))
        rebuilt.append(entry)
    return rebuilt


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--row", choices=sorted(ROW_CONFIGS), required=True)
    parser.add_argument("--scenes", nargs="*", default=list(REPLICA_SCENE_IDS))
    parser.add_argument("--output-root", type=Path, required=True)
    parser.add_argument("--pred-exp-name", default=None)
    parser.add_argument("--device", default="cuda:0")
    args = parser.parse_args()
    row_cfg = ROW_CONFIGS[args.row]
    pred = args.pred_exp_name or f"cg_authority_{args.row}"
    args.output_root.mkdir(parents=True, exist_ok=True)

    # Scale-prior rows use the scene-adaptive declared-auto source set.
    runner.GEOMETRY_REPAIR_KEEP_MODE = "declared-auto"

    class_all2existing = torch.ones(len(REPLICA_CLASSES)).long() * -1
    for i, c in enumerate(REPLICA_EXISTING_CLASSES):
        class_all2existing[c] = i
    class_names = [REPLICA_CLASSES[i] for i in REPLICA_EXISTING_CLASSES]
    exclude_class = [class_names.index(c) for c in ["other", "floor", "wall", "ceiling", "door", "window"]]
    scene_id_map = {a: b for a, b in zip(REPLICA_SCENE_IDS, REPLICA_SCENE_IDS_)}
    label_to_index = {name: idx for idx, name in enumerate(class_names)}

    print("Loading CLIP text encoder", flush=True)
    clip_model, _, _ = open_clip.create_model_and_transforms("ViT-H-14", "laion2b_s32b_b79k")
    clip_model = clip_model.to(args.device)
    tokenizer = open_clip.get_tokenizer("ViT-H-14")
    text = tokenizer([f"an image of {c}" for c in class_names]).to(args.device)
    with torch.no_grad():
        class_feats = clip_model.encode_text(text)
        class_feats = class_feats / class_feats.norm(dim=-1, keepdim=True)
    class_feats_np = class_feats.detach().cpu().numpy().astype(np.float32)

    eval_args = type("Args", (), {
        "replica_root": runner.REPLICA_ROOT,
        "replica_semantic_root": runner.REPLICA_SEMANTIC_ROOT,
        "pred_exp_name": pred,
        "n_exclude": 6,
        "device": args.device,
    })()

    cfg = runner.conceptgraphs_postprocess_cfg()
    per_scene_rows = []
    scene_reports = []
    conf_matrix_all = None
    for scene in args.scenes:
        t0 = time.time()
        print(f"=== {scene}: load CG map + rebuild declared votes ===", flush=True)
        raw_objects = load_cg_map(scene)
        vote_report = attach_declared_distributions(scene, raw_objects, class_names, class_feats_np)
        if vote_report["alignment_cos_mean"] is not None and vote_report["alignment_cos_mean"] < 0.97:
            raise RuntimeError(f"{scene}: detection-object alignment failed: {vote_report}")
        objects = rebuild_runtime_objects(raw_objects, cfg)
        pre_count = len(objects)
        objects, post_counts = runner.postprocess_map_objects(cfg, objects, gate_enabled=row_cfg["gate"])
        objects, repair_diag = runner.apply_geometry_repairs(
            objects,
            cfg,
            class_feats_np=class_feats_np,
            label_to_index=label_to_index,
            scale_prior_mode_override="apply" if row_cfg["sp"] else "off",
        )
        serializable = objects.to_serializable()
        pcd_dir = runner.REPLICA_ROOT / scene / "pcd_saves"
        with gzip.open(pcd_dir / f"full_pcd_{pred}.pkl.gz", "wb") as handle:
            pickle.dump({"objects": serializable, "bg_objects": None}, handle)
        print(f"=== {scene}: eval_replica ({pre_count} -> {len(objects)} objects) ===", flush=True)
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
        conf_matrix_all = conf_matrix if conf_matrix_all is None else conf_matrix_all + conf_matrix
        row = runner.metrics_row(scene, conf_matrix, keep_index, class_names)
        per_scene_rows.append(row)
        print(json.dumps(runner.to_builtin(row)), flush=True)
        gate_probe = post_counts.get("label_gate_probe", {"enabled": False})
        sp_probe = (repair_diag or {}).get("scale_prior_probe", {})
        scene_reports.append({
            "scene": scene,
            "pre_postprocess_objects": pre_count,
            "post_objects": len(objects),
            "vote_report": vote_report,
            "gate_probe": {k: gate_probe.get(k) for k in (
                "enabled", "legacy_merge_candidate_pairs", "merged_pairs", "vetoed_pairs",
                "veto_label_pairs", "no_veto_reasons",
            )},
            "gate_veto_examples": (gate_probe.get("veto_examples") or [])[:10],
            "scale_prior_probe": {k: sp_probe.get(k) for k in (
                "mode", "violations_by_label", "relabel_counts", "abstain_reasons",
            )},
            "scale_prior_examples": (sp_probe.get("examples") or [])[:10],
            "seconds": round(time.time() - t0, 1),
        })

    if per_scene_rows and len(args.scenes) == len(REPLICA_SCENE_IDS):
        keep_all = conf_matrix_all.sum(axis=1).nonzero().reshape(-1)
        per_scene_rows.append(runner.metrics_row("all", conf_matrix_all, keep_all, class_names))
    baseline_rows = runner.load_baseline_rows()
    gap_rows = runner.add_gap_rows(per_scene_rows, baseline_rows)

    summary = {
        "row": args.row,
        "row_config": row_cfg,
        "pred_exp_name": pred,
        "source_pred": CG_OFFICIAL_PRED,
        "protocol": "CG official pre-postprocess maps + DuoGraph3D authority postprocess, eval_replica_semseg n_exclude=6",
        "mechanism_parameters": {
            "gate_min_share": runner.CG_MERGE_LABEL_GATE_MIN_SHARE,
            "gate_min_obs": runner.CG_MERGE_LABEL_GATE_MIN_OBS,
            "gate_mutual_thresh": runner.CG_MERGE_LABEL_GATE_MUTUAL_THRESH,
            "merge_overlap_thresh": runner.CG_MERGE_OVERLAP_THRESH,
            "sp_tolerance": runner.GEOMETRY_REPAIR_SCALE_PRIOR_TOLERANCE,
            "sp_min_target_share": runner.GEOMETRY_REPAIR_SCALE_PRIOR_MIN_TARGET_SHARE,
            "sp_max_source_share": runner.GEOMETRY_REPAIR_SCALE_PRIOR_MAX_SOURCE_SHARE,
            "sp_hard_ratio": runner.GEOMETRY_REPAIR_SCALE_PRIOR_HARD_RATIO,
            "keep_mode": runner.GEOMETRY_REPAIR_KEEP_MODE,
        },
        "rows": per_scene_rows,
        "gap_rows": gap_rows,
        "scene_reports": scene_reports,
    }
    write_json(runner.to_builtin(summary), args.output_root / f"cg_authority_{args.row}_summary.json")
    fields = list(gap_rows[0].keys()) if gap_rows else []
    if fields:
        import csv as _csv

        with (args.output_root / f"cg_authority_{args.row}_gap.csv").open("w", newline="") as handle:
            writer = _csv.DictWriter(handle, fieldnames=fields)
            writer.writeheader()
            writer.writerows([runner.to_builtin(r) for r in gap_rows])
    for row in gap_rows:
        print(f"GAP {row.get('scene_id')}: {row.get('gap_miou')}", flush=True)
    print(f"CG_AUTHORITY_ROW_DONE {args.row}", flush=True)


if __name__ == "__main__":
    main()
