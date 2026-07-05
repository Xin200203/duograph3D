from __future__ import annotations

import unittest

from duograph3d.supervised_diagnosis import (
    compare_per_class_metrics,
    per_class_metrics_from_confusion,
    summarize_stage_coverage,
    top_gt_to_pred_confusions,
)


class SupervisedDiagnosisTests(unittest.TestCase):
    def test_per_class_metrics_uses_gt_rows_and_pred_columns(self) -> None:
        matrix = [
            [8, 2],
            [1, 9],
        ]
        rows = per_class_metrics_from_confusion(matrix, ["chair", "table"])
        self.assertEqual(rows[0]["gt_points"], 10)
        self.assertEqual(rows[0]["pred_points"], 9)
        self.assertEqual(rows[0]["recall"], 0.8)
        self.assertEqual(rows[0]["precision"], 0.888889)
        self.assertEqual(rows[0]["iou"], 0.727273)
        self.assertEqual(rows[1]["recall"], 0.9)
        self.assertEqual(rows[1]["precision"], 0.818182)

    def test_per_class_metrics_keep_index_matches_official_filtered_matrix(self) -> None:
        matrix = [
            [8, 2, 90],
            [1, 9, 80],
            [70, 60, 100],
        ]
        rows = per_class_metrics_from_confusion(matrix, ["chair", "table", "floor"], keep_index=[0, 1])
        self.assertEqual(rows[0]["gt_points"], 10)
        self.assertEqual(rows[0]["pred_points"], 9)
        self.assertEqual(rows[0]["precision"], 0.888889)
        self.assertEqual(rows[1]["gt_points"], 10)
        self.assertEqual(rows[1]["pred_points"], 11)
        self.assertEqual(rows[1]["precision"], 0.818182)

    def test_top_confusions_excludes_diagonal(self) -> None:
        matrix = [
            [8, 2, 0],
            [1, 9, 5],
            [0, 4, 7],
        ]
        records = top_gt_to_pred_confusions(matrix, ["chair", "table", "sofa"], top_k=2)
        self.assertEqual(records[0]["gt_class"], "table")
        self.assertEqual(records[0]["pred_class"], "sofa")
        self.assertEqual(records[0]["count"], 5)
        self.assertEqual(records[1]["gt_class"], "sofa")
        self.assertEqual(records[1]["pred_class"], "table")

    def test_compare_per_class_orders_by_worst_delta(self) -> None:
        duo = [
            {"class_index": 0, "class_name": "chair", "iou": 0.2, "recall": 0.4, "precision": 0.5, "gt_points": 10, "pred_points": 8},
            {"class_index": 1, "class_name": "table", "iou": 0.8, "recall": 0.9, "precision": 0.9, "gt_points": 10, "pred_points": 11},
        ]
        base = [
            {"class_index": 0, "class_name": "chair", "iou": 0.6, "recall": 0.7, "precision": 0.8, "gt_points": 10, "pred_points": 9},
            {"class_index": 1, "class_name": "table", "iou": 0.7, "recall": 0.8, "precision": 0.8, "gt_points": 10, "pred_points": 10},
        ]
        compared = compare_per_class_metrics(duo, base)
        self.assertEqual(compared[0]["class_name"], "chair")
        self.assertEqual(compared[0]["delta_iou"], -0.4)
        self.assertEqual(compared[1]["delta_iou"], 0.1)

    def test_stage_coverage_ratios(self) -> None:
        summary = summarize_stage_coverage(init_unique_targets=100, layer1_unique_targets=80, layer2_unique_targets=60)
        self.assertEqual(summary["layer1_coverage_vs_init"], 0.8)
        self.assertEqual(summary["layer2_coverage_vs_init"], 0.6)
        self.assertEqual(summary["layer2_coverage_vs_layer1"], 0.75)


if __name__ == "__main__":
    unittest.main()
