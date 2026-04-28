from __future__ import annotations

from collections import Counter
from typing import Any, Iterable, Sequence


def _as_number(value: Any) -> float:
    if hasattr(value, "item"):
        return float(value.item())
    return float(value)


def to_matrix_lists(matrix: Any) -> list[list[int]]:
    """Return a plain integer confusion matrix from numpy/torch/list input."""
    if hasattr(matrix, "detach"):
        matrix = matrix.detach().cpu().numpy()
    elif hasattr(matrix, "cpu"):
        matrix = matrix.cpu().numpy()
    elif hasattr(matrix, "tolist"):
        matrix = matrix.tolist()
    return [[int(round(_as_number(cell))) for cell in row] for row in matrix]


def to_index_list(indices: Any) -> list[int]:
    if indices is None:
        return []
    if hasattr(indices, "detach"):
        indices = indices.detach().cpu().numpy()
    elif hasattr(indices, "cpu"):
        indices = indices.cpu().numpy()
    if hasattr(indices, "tolist"):
        indices = indices.tolist()
    return [int(v) for v in indices]


def safe_div(numerator: float, denominator: float) -> float:
    return float(numerator) / float(denominator) if denominator else 0.0


def round6(value: float) -> float:
    return round(float(value), 6)


def per_class_metrics_from_confusion(
    conf_matrix: Any,
    class_names: Sequence[str],
    keep_index: Iterable[int] | None = None,
) -> list[dict[str, Any]]:
    """Compute ConceptGraphs-style per-class metrics.

    ConceptGraphs' Replica evaluator stores confusion matrices as rows=GT class
    and columns=predicted class.  Recall is therefore TP / row_sum, precision is
    TP / column_sum, and IoU is TP / (row_sum + column_sum - TP).
    """
    matrix = to_matrix_lists(conf_matrix)
    keep = list(range(len(matrix))) if keep_index is None else list(keep_index)
    rows: list[dict[str, Any]] = []
    for idx in keep:
        if idx < 0 or idx >= len(matrix):
            continue
        tp = int(matrix[idx][idx])
        gt_points = int(sum(matrix[idx]))
        pred_points = int(sum(row[idx] for row in matrix))
        union = gt_points + pred_points - tp
        rows.append(
            {
                "class_index": idx,
                "class_name": class_names[idx] if idx < len(class_names) else str(idx),
                "gt_points": gt_points,
                "pred_points": pred_points,
                "true_positive": tp,
                "recall": round6(safe_div(tp, gt_points)),
                "precision": round6(safe_div(tp, pred_points)),
                "iou": round6(safe_div(tp, union)),
            }
        )
    return rows


def top_gt_to_pred_confusions(
    conf_matrix: Any,
    class_names: Sequence[str],
    keep_index: Iterable[int] | None = None,
    *,
    top_k: int = 12,
    min_count: int = 1,
) -> list[dict[str, Any]]:
    matrix = to_matrix_lists(conf_matrix)
    keep = set(range(len(matrix))) if keep_index is None else set(int(i) for i in keep_index)
    records: list[dict[str, Any]] = []
    for gt_idx in sorted(keep):
        if gt_idx < 0 or gt_idx >= len(matrix):
            continue
        row_total = int(sum(matrix[gt_idx][pred_idx] for pred_idx in keep if pred_idx < len(matrix[gt_idx])))
        for pred_idx in sorted(keep):
            if pred_idx == gt_idx or pred_idx < 0 or pred_idx >= len(matrix[gt_idx]):
                continue
            count = int(matrix[gt_idx][pred_idx])
            if count < min_count:
                continue
            records.append(
                {
                    "gt_class_index": gt_idx,
                    "gt_class": class_names[gt_idx] if gt_idx < len(class_names) else str(gt_idx),
                    "pred_class_index": pred_idx,
                    "pred_class": class_names[pred_idx] if pred_idx < len(class_names) else str(pred_idx),
                    "count": count,
                    "gt_error_share": round6(safe_div(count, row_total)),
                }
            )
    records.sort(key=lambda item: (int(item["count"]), float(item["gt_error_share"])), reverse=True)
    return records[:top_k]


def compare_per_class_metrics(
    duograph_rows: Sequence[dict[str, Any]],
    baseline_rows: Sequence[dict[str, Any]],
) -> list[dict[str, Any]]:
    baseline_by_idx = {int(row["class_index"]): row for row in baseline_rows}
    compared: list[dict[str, Any]] = []
    for duo in duograph_rows:
        idx = int(duo["class_index"])
        base = baseline_by_idx.get(idx, {})
        record = {
            "class_index": idx,
            "class_name": duo["class_name"],
            "gt_points": int(max(int(duo.get("gt_points", 0)), int(base.get("gt_points", 0) or 0))),
            "duograph_iou": float(duo.get("iou", 0.0)),
            "conceptgraphs_iou": float(base.get("iou", 0.0) or 0.0),
            "delta_iou": round6(float(duo.get("iou", 0.0)) - float(base.get("iou", 0.0) or 0.0)),
            "duograph_recall": float(duo.get("recall", 0.0)),
            "conceptgraphs_recall": float(base.get("recall", 0.0) or 0.0),
            "delta_recall": round6(float(duo.get("recall", 0.0)) - float(base.get("recall", 0.0) or 0.0)),
            "duograph_precision": float(duo.get("precision", 0.0)),
            "conceptgraphs_precision": float(base.get("precision", 0.0) or 0.0),
            "delta_precision": round6(float(duo.get("precision", 0.0)) - float(base.get("precision", 0.0) or 0.0)),
            "duograph_pred_points": int(duo.get("pred_points", 0)),
            "conceptgraphs_pred_points": int(base.get("pred_points", 0) or 0),
        }
        compared.append(record)
    compared.sort(key=lambda item: (float(item["delta_iou"]), float(item["delta_recall"])))
    return compared


def summarize_stage_coverage(
    *,
    init_unique_targets: int,
    layer1_unique_targets: int,
    layer2_unique_targets: int,
) -> dict[str, Any]:
    return {
        "init_unique_targets": int(init_unique_targets),
        "layer1_unique_targets": int(layer1_unique_targets),
        "layer1_coverage_vs_init": round6(safe_div(layer1_unique_targets, init_unique_targets)),
        "layer2_unique_targets": int(layer2_unique_targets),
        "layer2_coverage_vs_init": round6(safe_div(layer2_unique_targets, init_unique_targets)),
        "layer2_coverage_vs_layer1": round6(safe_div(layer2_unique_targets, layer1_unique_targets)),
    }


def top_counter_items(counter: Counter[str] | dict[str, int], limit: int = 12) -> list[dict[str, Any]]:
    items = Counter(counter).most_common(limit)
    total = sum(int(v) for _, v in items) if items else 0
    return [
        {"name": str(name), "count": int(count), "share_in_top": round6(safe_div(int(count), total))}
        for name, count in items
    ]
