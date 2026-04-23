import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from duograph3d.statistics import compute_row_statistics, render_statistics_markdown


class StatisticsTests(unittest.TestCase):
    def test_compute_statistics(self) -> None:
        mega = {
            "scene_count": 2,
            "all_scenes_pass": True,
            "scene_rows": [
                {"dataset": "replica", "scene": "office0", "rows": {"identity_churn_proxy": {"value": 1}}},
                {"dataset": "scannet", "scene": "scene0000_00", "rows": {"identity_churn_proxy": {"value": 3}}},
            ],
        }
        stats = compute_row_statistics(mega)
        self.assertEqual(stats["identity_churn_proxy"]["min"], 1.0)
        self.assertEqual(stats["identity_churn_proxy"]["max"], 3.0)
        md = render_statistics_markdown(mega, stats)
        self.assertIn("G3 Statistical Summary", md)
        self.assertIn("identity_churn_proxy", md)


if __name__ == "__main__":
    unittest.main()
