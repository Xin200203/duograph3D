from __future__ import annotations

from pathlib import Path
import unittest


class ConceptGraphsPreprocessOrderTests(unittest.TestCase):
    def test_engineered_runner_filters_before_mask_subtraction(self) -> None:
        source = Path("examples/run_conceptgraphs_engineered_parity.py").read_text(encoding="utf-8")
        self.assertIn('"mask_subtract_order": "conceptgraphs_filter_then_subtract"', source)
        keep_pos = source.index("pre_keep_indices.append(det_i)")
        subtract_pos = source.index("mask_subtract_contained(xyxy[pre_keep_indices], frame_masks)")
        project_pos = source.index("world_points_from_mask_arrays(mask, depth, rgb_image, pose)")
        self.assertLess(keep_pos, subtract_pos)
        self.assertLess(subtract_pos, project_pos)

    def test_gt_monitor_uses_same_preprocess_order_as_runner(self) -> None:
        source = Path("examples/run_conceptgraphs_gt_layer_monitor.py").read_text(encoding="utf-8")
        self.assertIn('"mask_subtract_order": "conceptgraphs_filter_then_subtract"', source)
        keep_pos = source.index("pre_keep_indices.append(det_i)")
        subtract_pos = source.index("mask_subtract_contained(xyxy[pre_keep_indices], frame_masks)")
        project_pos = source.index("world_points_from_mask_arrays(mask, depth, pose)")
        self.assertLess(keep_pos, subtract_pos)
        self.assertLess(subtract_pos, project_pos)


if __name__ == "__main__":
    unittest.main()
