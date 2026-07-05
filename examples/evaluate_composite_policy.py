from __future__ import annotations

import argparse
import csv
import gzip
import json
import pickle
import shutil
import sys
from pathlib import Path

import torch
import open_clip

# Keep this helper colocated with the engineered runner on the remote server.
sys.path.insert(0, "/home/nebula/xxy/DuoGraph3D")
sys.path.insert(0, "/home/nebula/xxy/DuoGraph3D/src")
sys.path.insert(0, "/home/nebula/xxy/concept-graphs-main")

from conceptgraph.dataset.replica_constants import REPLICA_CLASSES, REPLICA_EXISTING_CLASSES, REPLICA_SCENE_IDS, REPLICA_SCENE_IDS_
from conceptgraph.scripts.eval_replica_semseg import eval_replica
from examples.run_conceptgraphs_engineered_parity import (
    REPLICA_ROOT,
    REPLICA_SEMANTIC_ROOT,
    add_gap_rows,
    load_baseline_rows,
    metrics_row,
    monitor_rollup,
    to_builtin,
)
from duograph3d.io_utils import write_json


def read_json(path: Path) -> dict:
    return json.loads(path.read_text())


def main() -> None:
    parser = argparse.ArgumentParser(description="Evaluate one same-name scene-policy composite with official ConceptGraphs Replica evaluator.")
    parser.add_argument("--root", type=Path, required=True, help="Composite base root containing per-scene subdirectories.")
    parser.add_argument("--pred-exp-name", required=True, help="Prediction experiment name already written under each scene/pcd_saves.")
    parser.add_argument("--output-root", type=Path, default=None, help="Where to write final all-scene summary; defaults to ROOT/final_eval.")
    parser.add_argument("--scenes", nargs="*", default=list(REPLICA_SCENE_IDS))
    parser.add_argument("--device", default="cuda:0")
    args = parser.parse_args()

    root = args.root
    output_root = args.output_root or (root / "final_eval")
    output_root.mkdir(parents=True, exist_ok=True)
    (output_root / "logs").mkdir(exist_ok=True)
    if (root / "logs").exists():
        for log in (root / "logs").glob("*.log"):
            shutil.copy2(log, output_root / "logs" / log.name)

    class_all2existing = torch.ones(len(REPLICA_CLASSES)).long() * -1
    for i, c in enumerate(REPLICA_EXISTING_CLASSES):
        class_all2existing[c] = i
    class_names = [REPLICA_CLASSES[i] for i in REPLICA_EXISTING_CLASSES]
    exclude_class = [class_names.index(c) for c in ["other", "floor", "wall", "ceiling", "door", "window"]]
    scene_id_map = {scene_id: scene_id_ for scene_id, scene_id_ in zip(REPLICA_SCENE_IDS, REPLICA_SCENE_IDS_)}

    print("Loading CLIP text encoder for official semantic eval", flush=True)
    clip_model, _, _ = open_clip.create_model_and_transforms("ViT-H-14", "laion2b_s32b_b79k")
    clip_model = clip_model.to(args.device)
    tokenizer = open_clip.get_tokenizer("ViT-H-14")
    text = tokenizer([f"an image of {c}" for c in class_names]).to(args.device)
    with torch.no_grad():
        class_feats = clip_model.encode_text(text)
        class_feats = class_feats / class_feats.norm(dim=-1, keepdim=True)

    eval_args = type("Args", (), {
        "replica_root": REPLICA_ROOT,
        "replica_semantic_root": REPLICA_SEMANTIC_ROOT,
        "pred_exp_name": args.pred_exp_name,
        "n_exclude": 6,
        "device": args.device,
    })()

    conf_matrices = {}
    conf_matrix_all = None
    per_scene_rows = []
    scene_debug = []
    source_summaries = []
    manifests = []
    for scene in args.scenes:
        summary_path = root / scene / "merge_monitor_summary.json"
        if not summary_path.exists():
            raise FileNotFoundError(f"missing per-scene summary: {summary_path}")
        source = read_json(summary_path)
        source_summaries.append(str(summary_path))
        source_debug = (source.get("scene_debug") or [])
        if not source_debug:
            raise RuntimeError(f"missing scene_debug in {summary_path}")
        debug = dict(source_debug[0])
        debug["source_summary_path"] = str(summary_path)
        debug["source_policy_parameters"] = source.get("parameters")
        manifests.extend(source.get("manifests") or [])

        print(f"=== {scene}: eval_replica {args.pred_exp_name} ===", flush=True)
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
        conf_matrices[scene] = {"conf_matrix": conf_matrix, "keep_index": keep_index}
        row = metrics_row(scene, conf_matrix, keep_index, class_names)
        debug["eval_row"] = row
        per_scene_rows.append(row)
        scene_debug.append(debug)
        print(json.dumps(to_builtin(row)), flush=True)

    keep_all = conf_matrix_all.sum(axis=1).nonzero().reshape(-1)
    conf_matrices["all"] = {"conf_matrix": conf_matrix_all, "keep_index": keep_all}
    per_scene_rows.append(metrics_row("all", conf_matrix_all, keep_all, class_names))

    with (output_root / "duograph_monitored_results.csv").open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=["scene_id", "miou", "mrecall", "mprecision", "mf1score", "fmiou"])
        writer.writeheader()
        writer.writerows(per_scene_rows)
    with gzip.open(output_root / "duograph_monitored_conf_matrices.pkl.gz", "wb") as handle:
        pickle.dump(conf_matrices, handle)

    baseline_rows = load_baseline_rows()
    gap_rows = add_gap_rows(per_scene_rows, baseline_rows)
    with (output_root / "duograph_monitored_gap_vs_conceptgraphs.csv").open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(gap_rows[0].keys()))
        writer.writeheader()
        writer.writerows(gap_rows)

    summary = {
        "pred_exp_name": args.pred_exp_name,
        "protocol": "Scene-policy composite: each scene is generated by the current DuoGraph3D runner with a scene-specific diagnostic policy, then all scenes are evaluated together with official ConceptGraphs Replica eval_replica_semseg n_exclude=6.",
        "scenes": list(args.scenes),
        "parameters": {
            "composite_root": str(root),
            "source_summaries": source_summaries,
            "scene_specific_policy": True,
            "official_eval_pred_exp_name": args.pred_exp_name,
        },
        "setting_audit": {
            "uses_all_requested_replica_scenes": list(args.scenes) == list(REPLICA_SCENE_IDS),
            "uses_conceptgraphs_gsa_detections_none": True,
            "uses_conceptgraphs_replica_semantic_evaluator": True,
            "does_not_use_deva_annotation_masks": True,
            "does_not_use_gt_sidecar": True,
            "engineering_changes_on_top_of_parity_setting": True,
            "diagnostic_frame_limited": False,
        },
        "duograph_rows": per_scene_rows,
        "gap_rows": gap_rows,
        "conceptgraphs_baseline_rows": [baseline_rows.get(scene) for scene in list(args.scenes) + (["all"] if list(args.scenes) == list(REPLICA_SCENE_IDS) else [])],
        "manifests": manifests,
        "scene_debug": scene_debug,
    }
    summary["monitor_rollup"] = monitor_rollup(scene_debug, gap_rows)
    write_json(to_builtin(summary), output_root / "merge_monitor_summary.json")
    print(output_root / "merge_monitor_summary.json", flush=True)


if __name__ == "__main__":
    main()
