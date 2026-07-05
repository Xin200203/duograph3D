from __future__ import annotations

import argparse
import csv
import gzip
import glob
import json
import math
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

from conceptgraph.dataset.replica_constants import REPLICA_CLASSES, REPLICA_EXISTING_CLASSES  # noqa: E402

EXCLUDED_EVAL_CLASSES = {"other", "floor", "wall", "ceiling", "door", "window"}


def norm_label(value: Any) -> str:
    if isinstance(value, (list, tuple)):
        value = value[0] if value else ""
    return str(value).strip().lower()


def load_objects(replica_root: Path, scene: str, pred_exp_name: str) -> tuple[Path, list[dict[str, Any]]]:
    paths = sorted(
        glob.glob(str(replica_root / scene / "pcd_saves" / f"full_pcd_{pred_exp_name}*.pkl.gz")),
        key=os.path.getmtime,
    )
    if not paths:
        raise FileNotFoundError(f"no full_pcd for scene={scene!r}, pred_exp_name={pred_exp_name!r}")
    path = Path(paths[-1])
    with gzip.open(path, "rb") as handle:
        payload = pickle.load(handle)
    return path, list(payload.get("objects") or [])


def build_text_features(class_names: list[str], device: str) -> torch.Tensor:
    model, _, _ = open_clip.create_model_and_transforms("ViT-H-14", "laion2b_s32b_b79k")
    model = model.to(device)
    tokenizer = open_clip.get_tokenizer("ViT-H-14")
    text = tokenizer([f"an image of {name}" for name in class_names]).to(device)
    with torch.no_grad():
        feats = model.encode_text(text)
        return feats / feats.norm(dim=-1, keepdim=True)


def object_points(obj: dict[str, Any]) -> int:
    pcd = obj.get("pcd_np")
    if hasattr(pcd, "shape"):
        return int(pcd.shape[0])
    n_points = obj.get("n_points")
    if isinstance(n_points, (list, tuple)) and n_points:
        return int(n_points[0])
    try:
        return int(n_points)
    except (TypeError, ValueError):
        return 0


def feature_top(
    obj: dict[str, Any],
    *,
    class_feats: torch.Tensor,
    class_names: list[str],
    ignore_indices: set[int],
    device: str,
) -> tuple[str, float, float]:
    feature = np.asarray(obj.get("clip_ft"), dtype=np.float32).reshape(1, -1)
    if feature.size == 0 or not np.isfinite(feature).all():
        return "", float("nan"), float("nan")
    tensor = torch.from_numpy(feature).to(device)
    tensor = tensor / tensor.norm(dim=-1, keepdim=True).clamp_min(1e-12)
    with torch.no_grad():
        sim = (tensor @ class_feats.T).reshape(-1)
        for idx in ignore_indices:
            sim[idx] = -1e10
        top = torch.topk(sim, k=2)
    best = int(top.indices[0].item())
    margin = float(top.values[0].item() - top.values[1].item())
    return class_names[best], float(top.values[0].item()), margin


def write_csv(path: Path, rows: list[dict[str, Any]], fieldnames: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "Probe exported ConceptGraphs-format objects for semantic-carrier mismatch: "
            "export class_name versus evaluator-style clip_ft top-1."
        )
    )
    parser.add_argument("--replica-root", type=Path, default=Path("/home/nebula/xxy/dataset/Replica"))
    parser.add_argument("--pred-exp-name", required=True)
    parser.add_argument("--scenes", nargs="+", required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--device", default="cuda:0" if torch.cuda.is_available() else "cpu")
    args = parser.parse_args()

    class_names = [REPLICA_CLASSES[index] for index in REPLICA_EXISTING_CLASSES]
    label_to_index = {name: index for index, name in enumerate(class_names)}
    ignore_indices = {label_to_index[name] for name in EXCLUDED_EVAL_CLASSES if name in label_to_index}
    args.output_dir.mkdir(parents=True, exist_ok=True)
    class_feats = build_text_features(class_names, args.device)

    object_rows: list[dict[str, Any]] = []
    pair_rows: list[dict[str, Any]] = []
    summary: dict[str, Any] = {"pred_exp_name": args.pred_exp_name, "scenes": []}

    for scene in args.scenes:
        path, objects = load_objects(args.replica_root, scene, args.pred_exp_name)
        point_total = 0
        mismatch_objects = 0
        mismatch_points = 0
        pair_counter: Counter[tuple[str, str]] = Counter()
        pair_margins: dict[tuple[str, str], list[float]] = defaultdict(list)
        export_label_points: Counter[str] = Counter()
        clip_label_points: Counter[str] = Counter()

        for object_index, obj in enumerate(objects):
            points = object_points(obj)
            point_total += points
            label = norm_label(obj.get("class_name"))
            top_label, top_score, margin = feature_top(
                obj,
                class_feats=class_feats,
                class_names=class_names,
                ignore_indices=ignore_indices,
                device=args.device,
            )
            export_label_points[label] += points
            clip_label_points[top_label] += points
            mismatch = label != top_label
            if mismatch:
                mismatch_objects += 1
                mismatch_points += points
                pair_counter[(label, top_label)] += points
                pair_margins[(label, top_label)].append(margin)
            object_rows.append(
                {
                    "scene": scene,
                    "object_index": object_index,
                    "points": points,
                    "class_name": label,
                    "clip_top1": top_label,
                    "clip_top1_score": round(top_score, 6) if math.isfinite(top_score) else "",
                    "clip_margin": round(margin, 6) if math.isfinite(margin) else "",
                    "mismatch": int(mismatch),
                    "source_key": norm_label(obj.get("source_key")),
                    "base_geometry_key": norm_label(obj.get("base_geometry_key")),
                    "num_detections": int(obj.get("num_detections") or 0),
                }
            )

        top_pairs = []
        for (label, top_label), points in pair_counter.most_common(30):
            margins = pair_margins[(label, top_label)]
            record = {
                "scene": scene,
                "class_name": label,
                "clip_top1": top_label,
                "points": int(points),
                "point_share": round(points / max(point_total, 1), 6),
                "mean_margin": round(sum(margins) / max(len(margins), 1), 6),
                "object_count": len(margins),
            }
            pair_rows.append(record)
            top_pairs.append(record)

        summary["scenes"].append(
            {
                "scene": scene,
                "pkl": str(path),
                "objects": len(objects),
                "points": point_total,
                "mismatch_objects": mismatch_objects,
                "mismatch_object_rate": round(mismatch_objects / max(len(objects), 1), 6),
                "mismatch_points": mismatch_points,
                "mismatch_point_rate": round(mismatch_points / max(point_total, 1), 6),
                "top_export_class_points": export_label_points.most_common(12),
                "top_clip_class_points": clip_label_points.most_common(12),
                "top_mismatch_pairs": top_pairs[:15],
            }
        )

    write_csv(
        args.output_dir / "object_label_vs_clip_rows.csv",
        object_rows,
        [
            "scene",
            "object_index",
            "points",
            "class_name",
            "clip_top1",
            "clip_top1_score",
            "clip_margin",
            "mismatch",
            "source_key",
            "base_geometry_key",
            "num_detections",
        ],
    )
    write_csv(
        args.output_dir / "object_label_vs_clip_mismatch_pairs.csv",
        pair_rows,
        ["scene", "class_name", "clip_top1", "points", "point_share", "mean_margin", "object_count"],
    )
    summary_path = args.output_dir / "semantic_carrier_probe_summary.json"
    summary_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(summary_path, flush=True)


if __name__ == "__main__":
    main()
