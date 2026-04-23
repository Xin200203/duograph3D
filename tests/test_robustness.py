import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from duograph3d.robustness import compare_suite_summaries, render_robustness_markdown


class RobustnessTests(unittest.TestCase):
    def test_compare_and_render(self) -> None:
        summaries = [
            (
                "baseline",
                {
                    "scene_count": 2,
                    "all_scenes_pass": True,
                    "row_pass_counts": {"identity_churn_proxy": 2},
                    "row_total_counts": {"identity_churn_proxy": 2},
                    "signature_counts": {},
                    "scene_rows": [{"dataset": "replica", "scene": "office0", "all_rows_pass": True}],
                },
            ),
            (
                "stress",
                {
                    "scene_count": 2,
                    "all_scenes_pass": True,
                    "row_pass_counts": {"identity_churn_proxy": 2},
                    "row_total_counts": {"identity_churn_proxy": 2},
                    "signature_counts": {},
                    "scene_rows": [{"dataset": "replica", "scene": "office0", "all_rows_pass": True}],
                },
            ),
        ]
        report = compare_suite_summaries(summaries)
        self.assertTrue(report["all_regimes_pass"])
        self.assertTrue(report["row_stability"]["identity_churn_proxy"])
        markdown = render_robustness_markdown(report)
        self.assertIn("Robustness Summary", markdown)
        self.assertIn("baseline", markdown)


if __name__ == "__main__":
    unittest.main()
