import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from duograph3d.summary_merge import merge_suite_summaries


class SummaryMergeTests(unittest.TestCase):
    def test_merge_suite_summaries(self) -> None:
        merged = merge_suite_summaries(
            [
                {
                    "scene_count": 2,
                    "dataset_counts": {"replica": 2},
                    "row_pass_counts": {"identity_churn_proxy": 2},
                    "row_total_counts": {"identity_churn_proxy": 2},
                    "signature_counts": {"single_layer_fragmentation": 2},
                    "all_scenes_pass": True,
                    "scene_rows": [{"scene": "a"}],
                },
                {
                    "scene_count": 3,
                    "dataset_counts": {"scannet": 3},
                    "row_pass_counts": {"identity_churn_proxy": 3},
                    "row_total_counts": {"identity_churn_proxy": 3},
                    "signature_counts": {"single_layer_fragmentation": 3},
                    "all_scenes_pass": True,
                    "scene_rows": [{"scene": "b"}],
                },
            ]
        )
        self.assertEqual(merged["scene_count"], 5)
        self.assertEqual(merged["dataset_counts"]["replica"], 2)
        self.assertEqual(merged["dataset_counts"]["scannet"], 3)
        self.assertEqual(merged["row_pass_counts"]["identity_churn_proxy"], 5)
        self.assertEqual(merged["signature_counts"]["single_layer_fragmentation"], 5)
        self.assertTrue(merged["all_scenes_pass"])


if __name__ == "__main__":
    unittest.main()
