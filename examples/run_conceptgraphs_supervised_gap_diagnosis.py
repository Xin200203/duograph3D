from __future__ import annotations

import argparse
import csv
import gzip
import json
import pickle
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, "/home/nebula/xxy/DuoGraph3D/src")
sys.path.insert(0, "/home/nebula/xxy/concept-graphs-main")

from duograph3d.io_utils import write_json
from duograph3d.supervised_diagnosis import (
    compare_per_class_metrics,
    per_class_metrics_from_confusion,
    top_gt_to_pred_confusions,
)

DEFAULT_DUO_EXP = "duograph3d_memory_dense_hybrid_room0_room1_20260428"
DEFAULT_BASELINE_EXP = "none_overlap_maskconf0.95_simsum1.2_dbscan.1_merge20_masksub"
DEFAULT_ARTIFACT_ROOT = Path("/home/nebula/xxy/duograph3d_artifacts")
DEFAULT_CONCEPTGRAPHS_ROOT = Path("/home/nebula/xxy/concept-graphs-main/conceptgraph")


def load_json(path: Path) -> dict[str, Any]:
    if not path or not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def load_pickle_maybe_gzip(path: Path) -> Any:
    opener = gzip.open if path.suffix == ".gz" else open
    with opener(path, "rb") as handle:
        return pickle.load(handle)


def load_replica_class_names() -> list[str]:
    from conceptgraph.dataset.replica_constants import REPLICA_CLASSES, REPLICA_EXISTING_CLASSES

    return [REPLICA_CLASSES[i] for i in REPLICA_EXISTING_CLASSES]


def scene_debug_by_name(merge_summary: dict[str, Any]) -> dict[str, dict[str, Any]]:
    scene_debug = merge_summary.get("scene_debug") or []
    if isinstance(scene_debug, dict):
        return {str(key): value for key, value in scene_debug.items() if isinstance(value, dict)}
    result = {}
    for item in scene_debug:
        if isinstance(item, dict) and item.get("scene"):
            result[str(item["scene"])] = item
    return result


def gt_layer_scene_by_name(gt_summary: dict[str, Any]) -> dict[str, dict[str, Any]]:
    result = {}
    for item in gt_summary.get("scenes") or []:
        if isinstance(item, dict) and item.get("scene"):
            result[str(item["scene"])] = item
    return result


def annotate_ambiguous_examples(
    scene: str,
    merge_scene: dict[str, Any],
    gt_scene: dict[str, Any],
    *,
    limit: int,
) -> list[dict[str, Any]]:
    probe = (((merge_scene.get("export_monitor") or {}).get("memory_dense_export_probe") or {}))
    examples = probe.get("ambiguous_assignment_examples") or []
    key_gt_monitor = gt_scene.get("geometry_key_gt_monitor") or {}
    records: list[dict[str, Any]] = []
    for item in examples:
        if not isinstance(item, dict):
            continue
        key = str(item.get("base_geometry_key") or "")
        gt_info = key_gt_monitor.get(key, {}) if isinstance(key_gt_monitor, dict) else {}
        resolved_counts = item.get("resolved_root_counts") or {}
        assigned_counts = item.get("assigned_object_counts") or {}
        root_count = len(resolved_counts) if isinstance(resolved_counts, dict) else 0
        selected_share = float(item.get("selected_root_share") or 0.0)
        record = {
            "scene": scene,
            "base_geometry_key": key,
            "assignment_status": item.get("assignment_status", ""),
            "selected_root_id": item.get("selected_root_id", ""),
            "selected_root_share": round(selected_share, 6),
            "resolved_root_count": root_count,
            "resolved_root_counts": resolved_counts,
            "assigned_object_counts": assigned_counts,
            "eval_keep_observation_count": gt_info.get("eval_keep_observation_count", 0),
            "dominant_pred_label": gt_info.get("dominant_pred_label", ""),
            "dominant_gt_class": gt_info.get("dominant_gt_class", ""),
            "semantic_accuracy": gt_info.get("semantic_accuracy", 0.0),
            "unique_gt_target_count": gt_info.get("unique_gt_target_count", 0),
            "dominant_target_id": gt_info.get("dominant_target_id", ""),
            "gt_class_counts": gt_info.get("gt_class_counts", {}),
            "pred_label_counts": gt_info.get("pred_label_counts", {}),
            "target_counts": gt_info.get("target_counts", {}),
            "clip_margin": gt_info.get("clip_margin", {}),
        }
        records.append(record)
    records.sort(
        key=lambda rec: (
            float(rec.get("selected_root_share") or 0.0),
            -int(rec.get("resolved_root_count") or 0),
            -int(rec.get("eval_keep_observation_count") or 0),
        )
    )
    return records[:limit]


def stage_row(scene: str, gt_scene: dict[str, Any]) -> dict[str, Any]:
    init = gt_scene.get("init") or {}
    layer1 = gt_scene.get("layer1") or {}
    layer2 = gt_scene.get("layer2") or {}
    coverage = gt_scene.get("stage_coverage") or {}
    return {
        "scene": scene,
        "init_valid_eval_observations": init.get("valid_eval_observations", 0),
        "init_unique_targets": init.get("unique_gt_target_count", 0),
        "init_semantic_accuracy": init.get("semantic_accuracy", 0.0),
        "init_dup_rate_global": (init.get("global_semantic_cell_duplicates") or {}).get("duplicate_rate", 0.0),
        "layer1_hypotheses": layer1.get("hypothesis_count_eval_keep", 0),
        "layer1_unique_targets": layer1.get("unique_gt_target_count", 0),
        "layer1_coverage_vs_init": coverage.get("layer1_coverage_vs_init", layer1.get("coverage_vs_init", 0.0)),
        "layer1_semantic_accuracy": layer1.get("semantic_accuracy", 0.0),
        "layer1_dup_rate_global": (layer1.get("global_semantic_cell_duplicates") or {}).get("duplicate_rate", 0.0),
        "layer1_false_merge_rate": layer1.get("false_merge_hypothesis_rate", 0.0),
        "layer1_pair_precision": layer1.get("merge_pair_precision", 0.0),
        "layer2_decisions": layer2.get("valid_decision_count", 0),
        "layer2_unique_targets": layer2.get("unique_gt_target_count", 0),
        "layer2_coverage_vs_init": coverage.get("layer2_coverage_vs_init", layer2.get("coverage_vs_init", 0.0)),
        "layer2_decision_accuracy": layer2.get("decision_accuracy", 0.0),
        "layer2_decision_accuracy_after_merge": layer2.get("decision_accuracy_after_object_merge", 0.0),
        "layer2_semantic_accuracy": layer2.get("decision_semantic_accuracy", 0.0),
        "layer2_duplicate_birth_rate": layer2.get("duplicate_birth_rate", 0.0),
        "layer2_id_switch_rate": layer2.get("id_switch_rate_per_revisit", 0.0),
        "layer2_fragmented_target_rate": layer2.get("fragmented_gt_target_rate", 0.0),
        "layer2_gt_target_fragmentation": layer2.get("gt_target_fragmentation", 0),
    }


def write_csv(path: Path, rows: list[dict[str, Any]], fieldnames: list[str] | None = None) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if not fieldnames:
        fieldnames = sorted({key for row in rows for key in row})
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow({key: row.get(key, "") for key in fieldnames})


def summarize_room_gap(compared_rows: list[dict[str, Any]]) -> dict[str, Any]:
    if not compared_rows:
        return {}
    count = len(compared_rows)
    avg_recall_gap = sum(float(row["delta_recall"]) for row in compared_rows) / max(count, 1)
    avg_precision_gap = sum(float(row["delta_precision"]) for row in compared_rows) / max(count, 1)
    avg_iou_gap = sum(float(row["delta_iou"]) for row in compared_rows) / max(count, 1)
    recall_bad = [row for row in compared_rows if float(row["delta_recall"]) < -0.05]
    precision_bad = [row for row in compared_rows if float(row["delta_precision"]) < -0.05]
    precision_much_worse = avg_precision_gap < avg_recall_gap - 0.05
    if precision_much_worse:
        leading = "precision_gap_dominant"
        explanation = "room差距更像是语义误投/对象混合带来的false positive，而不是单纯没有覆盖到GT点。"
    elif avg_recall_gap < avg_precision_gap - 0.05:
        leading = "recall_gap_dominant"
        explanation = "room差距更像是目标类别覆盖不足或被过滤/漏检。"
    else:
        leading = "mixed_recall_precision_gap"
        explanation = "recall与precision都在损失，需要同时看语义误投和对象拆合。"
    return {
        "avg_delta_iou": round(avg_iou_gap, 6),
        "avg_delta_recall": round(avg_recall_gap, 6),
        "avg_delta_precision": round(avg_precision_gap, 6),
        "classes_with_recall_gap_gt_5pt": len(recall_bad),
        "classes_with_precision_gap_gt_5pt": len(precision_bad),
        "leading_failure_mode": leading,
        "plain_language_explanation": explanation,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=DEFAULT_ARTIFACT_ROOT / "duograph3d_supervised_gap_diagnosis_room0_room1_20260428")
    parser.add_argument("--scenes", nargs="*", default=["room0", "room1"])
    parser.add_argument("--duograph-exp-name", default=DEFAULT_DUO_EXP)
    parser.add_argument("--conceptgraphs-exp-name", default=DEFAULT_BASELINE_EXP)
    parser.add_argument("--duograph-conf-matrices", type=Path, default=None)
    parser.add_argument("--conceptgraphs-conf-matrices", type=Path, default=None)
    parser.add_argument("--merge-monitor-summary", type=Path, default=None)
    parser.add_argument("--gt-layer-summary", type=Path, default=None)
    parser.add_argument("--ambiguous-sample-limit", type=int, default=20)
    args = parser.parse_args()

    root = args.root
    root.mkdir(parents=True, exist_ok=True)
    class_names = load_replica_class_names()
    duo_conf_path = args.duograph_conf_matrices or (DEFAULT_ARTIFACT_ROOT / args.duograph_exp_name / "duograph_monitored_conf_matrices.pkl.gz")
    cg_conf_path = args.conceptgraphs_conf_matrices or (DEFAULT_CONCEPTGRAPHS_ROOT / "results" / args.conceptgraphs_exp_name / "replica_ex6_conf_matrices.pkl")
    merge_summary_path = args.merge_monitor_summary or (DEFAULT_ARTIFACT_ROOT / args.duograph_exp_name / "merge_monitor_summary.json")
    gt_layer_summary_path = args.gt_layer_summary or (DEFAULT_ARTIFACT_ROOT / "duograph3d_supervised_gt_layer_room0_room1_20260428" / "gt_layer_monitor_summary.json")

    duo_conf = load_pickle_maybe_gzip(duo_conf_path)
    cg_conf = load_pickle_maybe_gzip(cg_conf_path)
    merge_summary = load_json(merge_summary_path)
    gt_summary = load_json(gt_layer_summary_path)
    merge_by_scene = scene_debug_by_name(merge_summary)
    gt_by_scene = gt_layer_scene_by_name(gt_summary)

    per_class_rows: list[dict[str, Any]] = []
    confusion_rows: list[dict[str, Any]] = []
    room_diagnosis: dict[str, Any] = {}
    for scene in list(args.scenes) + ["all"]:
        if scene not in duo_conf or scene not in cg_conf:
            continue
        duo_keep = duo_conf[scene].get("keep_index")
        cg_keep = cg_conf[scene].get("keep_index")
        # Use DuoGraph keep_index for direct scene comparison; ConceptGraphs uses the same Replica GT keep-set per scene.
        keep = duo_keep if duo_keep is not None else cg_keep
        duo_metrics = per_class_metrics_from_confusion(duo_conf[scene]["conf_matrix"], class_names, keep)
        cg_metrics = per_class_metrics_from_confusion(cg_conf[scene]["conf_matrix"], class_names, keep)
        compared = compare_per_class_metrics(duo_metrics, cg_metrics)
        for row in compared:
            row = dict(row)
            row["scene"] = scene
            per_class_rows.append(row)
        for system, conf in [("duograph3d", duo_conf), ("conceptgraphs", cg_conf)]:
            for rec in top_gt_to_pred_confusions(conf[scene]["conf_matrix"], class_names, keep, top_k=20):
                rec = dict(rec)
                rec["scene"] = scene
                rec["system"] = system
                confusion_rows.append(rec)
        room_diagnosis[scene] = summarize_room_gap(compared)

    stage_rows = [stage_row(scene, gt_by_scene.get(scene, {})) for scene in args.scenes]
    ambiguous_records: list[dict[str, Any]] = []
    ambiguity_rollup: dict[str, Any] = {}
    for scene in args.scenes:
        merge_scene = merge_by_scene.get(scene, {})
        probe = (((merge_scene.get("export_monitor") or {}).get("memory_dense_export_probe") or {}))
        ambiguity_rollup[scene] = {
            "candidate_key_object_count": probe.get("candidate_key_object_count", 0),
            "assigned_key_count": probe.get("assigned_key_count", 0),
            "raw_assignment_status_counts": probe.get("raw_assignment_status_counts", {}),
            "assignment_status_counts": probe.get("assignment_status_counts", {}),
            "selected_root_share": probe.get("selected_root_share", {}),
            "memory_dense_min_root_share": probe.get("memory_dense_min_root_share", None),
            "memory_dense_geometry_fallback": probe.get("memory_dense_geometry_fallback", None),
        }
        ambiguous_records.extend(
            annotate_ambiguous_examples(
                scene,
                merge_scene,
                gt_by_scene.get(scene, {}),
                limit=args.ambiguous_sample_limit,
            )
        )

    per_class_fields = [
        "scene", "class_index", "class_name", "gt_points",
        "duograph_iou", "conceptgraphs_iou", "delta_iou",
        "duograph_recall", "conceptgraphs_recall", "delta_recall",
        "duograph_precision", "conceptgraphs_precision", "delta_precision",
        "duograph_pred_points", "conceptgraphs_pred_points",
    ]
    write_csv(root / "per_class_gap.csv", per_class_rows, per_class_fields)
    write_csv(root / "top_confusions.csv", confusion_rows, ["scene", "system", "gt_class", "pred_class", "count", "gt_error_share", "gt_class_index", "pred_class_index"])
    write_csv(root / "stage_supervision.csv", stage_rows)
    write_json(ambiguous_records, root / "ambiguous_memory_assignment_examples_gt.json")

    summary = {
        "protocol": "Supervised ConceptGraphs parity diagnosis: official Replica confusion matrices + GT-aware DuoGraph3D stage monitor + memory-dense ambiguous assignment samples.",
        "paths": {
            "duograph_conf_matrices": str(duo_conf_path),
            "conceptgraphs_conf_matrices": str(cg_conf_path),
            "merge_monitor_summary": str(merge_summary_path),
            "gt_layer_summary": str(gt_layer_summary_path),
        },
        "scenes": args.scenes,
        "room_gap_diagnosis": room_diagnosis,
        "stage_supervision": stage_rows,
        "ambiguity_rollup": ambiguity_rollup,
        "worst_per_class_gaps": per_class_rows[:30],
        "top_confusions": confusion_rows[:80],
        "ambiguous_memory_assignment_examples_gt": ambiguous_records[: args.ambiguous_sample_limit * max(len(args.scenes), 1)],
    }
    write_json(summary, root / "supervised_gap_diagnosis_summary.json")

    room1_rows = [row for row in per_class_rows if row.get("scene") == "room1"]
    room1_worst = sorted(room1_rows, key=lambda row: (float(row["delta_iou"]), float(row["delta_precision"])))[:10]
    room1_conf = [row for row in confusion_rows if row.get("scene") == "room1" and row.get("system") == "duograph3d"][:10]
    room1_amb = [row for row in ambiguous_records if row.get("scene") == "room1"][:8]
    lines = [
        "# Supervised ConceptGraphs parity diagnosis",
        "",
        "This report combines: (1) official Replica semantic confusion matrices, (2) GT-aware stage supervision for init/Layer1/Layer2, and (3) memory-dense ambiguous assignment samples enriched by geometry-key GT summaries.",
        "",
        "## Stage supervision",
        "",
        "| scene | init targets | L1 coverage | L1 dup | L1 pair precision | L2 coverage | L2 acc | L2 acc after merge | L2 duplicate birth | L2 id-switch |",
        "| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    for row in stage_rows:
        lines.append(
            f"| {row['scene']} | {row['init_unique_targets']} | {float(row['layer1_coverage_vs_init']):.3f} | "
            f"{float(row['layer1_dup_rate_global']):.3f} | {float(row['layer1_pair_precision']):.3f} | "
            f"{float(row['layer2_coverage_vs_init']):.3f} | {float(row['layer2_decision_accuracy']):.3f} | "
            f"{float(row['layer2_decision_accuracy_after_merge']):.3f} | {float(row['layer2_duplicate_birth_rate']):.3f} | "
            f"{float(row['layer2_id_switch_rate']):.3f} |"
        )
    lines.extend([
        "",
        "## Room-level diagnosis",
        "",
    ])
    for scene, diag in room_diagnosis.items():
        if scene not in args.scenes and scene != "all":
            continue
        lines.append(
            f"- **{scene}**: ΔIoU={diag.get('avg_delta_iou', 0):.3f}, "
            f"ΔRecall={diag.get('avg_delta_recall', 0):.3f}, "
            f"ΔPrecision={diag.get('avg_delta_precision', 0):.3f}; "
            f"{diag.get('leading_failure_mode', '')}. {diag.get('plain_language_explanation', '')}"
        )
    lines.extend([
        "",
        "## room1 worst per-class gaps",
        "",
        "| class | GT pts | ΔIoU | Duo R | CG R | ΔR | Duo P | CG P | ΔP |",
        "| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
    ])
    for row in room1_worst:
        lines.append(
            f"| {row['class_name']} | {row['gt_points']} | {float(row['delta_iou']):.3f} | "
            f"{float(row['duograph_recall']):.3f} | {float(row['conceptgraphs_recall']):.3f} | {float(row['delta_recall']):.3f} | "
            f"{float(row['duograph_precision']):.3f} | {float(row['conceptgraphs_precision']):.3f} | {float(row['delta_precision']):.3f} |"
        )
    lines.extend([
        "",
        "## room1 DuoGraph3D top GT→pred confusions",
        "",
        "| GT | predicted | points | GT error share |",
        "| --- | --- | ---: | ---: |",
    ])
    for row in room1_conf:
        lines.append(f"| {row['gt_class']} | {row['pred_class']} | {row['count']} | {float(row['gt_error_share']):.3f} |")
    lines.extend([
        "",
        "## room1 ambiguous memory assignment examples with GT",
        "",
        "| key | selected share | roots | pred label | GT class | semantic acc | eval obs | unique GT targets |",
        "| --- | ---: | ---: | --- | --- | ---: | ---: | ---: |",
    ])
    for row in room1_amb:
        lines.append(
            f"| `{row['base_geometry_key']}` | {float(row['selected_root_share']):.3f} | {int(row['resolved_root_count'])} | "
            f"{row.get('dominant_pred_label', '')} | {row.get('dominant_gt_class', '')} | "
            f"{float(row.get('semantic_accuracy') or 0):.3f} | {int(row.get('eval_keep_observation_count') or 0)} | {int(row.get('unique_gt_target_count') or 0)} |"
        )
    lines.extend([
        "",
        "## Interpretation",
        "",
        "Recall low means: among all GT points of a class, many points were finally assigned to another predicted class. In the ConceptGraphs evaluator, predictions are resampled onto the SLAM cloud, so this is usually a label/assignment problem rather than simply no point existing. If recall is worse but precision is okay, the class is missed or absorbed by other labels. If precision is much worse, the predicted class has swallowed many wrong GT points, usually from semantic confusion or cross-object merge/assignment noise.",
        "",
        "For room1, compare the ΔRecall and ΔPrecision columns plus the ambiguous samples above. If ΔPrecision is the larger loss and ambiguous keys show low selected-root share or wrong dominant GT class, the gap is mainly semantic/object assignment pollution; if ΔRecall is the larger loss and few ambiguous samples touch that class, the gap is mainly missed coverage/filtering.",
    ])
    (root / "supervised_gap_diagnosis_report.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(root / "supervised_gap_diagnosis_summary.json", flush=True)
    print(root / "supervised_gap_diagnosis_report.md", flush=True)


if __name__ == "__main__":
    main()
