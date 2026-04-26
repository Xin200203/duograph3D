import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from duograph3d.esam_results import esam_summary_as_lane, render_esam_output_markdown, summarize_esam_scannet_output


class EsamResultsTests(unittest.TestCase):
    def test_summarize_and_lane(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            metric_json = Path(tmpdir) / "metric.json"
            monitor_json = Path(tmpdir) / "monitor_summary.json"
            metric_json.write_text(
                json.dumps(
                    {
                        "all_ap": 0.41,
                        "all_ap_50%": 0.63,
                        "all_ap_25%": 0.78,
                        "time": 4.27,
                    }
                )
            )
            monitor_json.write_text(
                json.dumps(
                    {
                        "counts": {"scenes": 312, "frames": 13430},
                        "match_rate": {"mean": 0.82},
                        "birth_rate": {"mean": 0.18},
                        "mem_size_full": {"mean": 62.93},
                        "mem_size_kept": {"mean": 56.93},
                    }
                )
            )
            summary = summarize_esam_scannet_output(
                metric_json=metric_json,
                online_monitor_summary_json=monitor_json,
                executed_repo_root="/remote/esam-fork",
            )
            self.assertEqual(summary["counts"]["scenes"], 312)
            self.assertAlmostEqual(summary["all_ap"], 0.41)
            lane = esam_summary_as_lane(summary)
            self.assertEqual(lane["baseline_id"], "esam_official_scannet_mv")
            self.assertEqual(lane["primary_metric_name"], "all_ap")
            self.assertAlmostEqual(lane["metrics"]["match_rate_mean"], 0.82)
            markdown = render_esam_output_markdown(summary)
            self.assertIn("ESAM Output Summary", markdown)
            self.assertIn("all_ap", markdown)


if __name__ == "__main__":
    unittest.main()
