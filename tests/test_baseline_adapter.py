import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from duograph3d.baseline_adapter import normalize_baseline_lane, render_baseline_lane_markdown


class BaselineAdapterTests(unittest.TestCase):
    def test_normalize_and_render_lane(self) -> None:
        lane = normalize_baseline_lane(
            baseline_id="temporal_only_strong",
            label="Temporal-only strong lane",
            dataset="scannet",
            scene="scene0000_02",
            family="external_candidate",
            faithfulness="adapter_wrapped",
            primary_metric_name="identity_fragmentation",
            primary_metric_value=2.0,
            metrics={"identity_fragmentation": 2.0, "reentry_recovery_rate": 0.5},
            notes=["wrapped via normalized adapter"],
        )
        self.assertEqual(lane["baseline_id"], "temporal_only_strong")
        self.assertEqual(lane["primary_metric_value"], 2.0)
        md = render_baseline_lane_markdown(lane)
        self.assertIn("Temporal-only strong lane", md)
        self.assertIn("identity_fragmentation", md)


if __name__ == "__main__":
    unittest.main()
