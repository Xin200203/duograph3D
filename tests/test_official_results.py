from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from duograph3d.official_results import OfficialRun, compare_official_runs, render_official_comparison_markdown


class OfficialResultsTests(unittest.TestCase):
    def test_compare_official_runs_reports_metric_deltas(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            baseline_metrics = root / "baseline_metrics.json"
            candidate_metrics = root / "candidate_metrics.json"
            baseline_monitor = root / "baseline_monitor.json"
            candidate_monitor = root / "candidate_monitor.json"
            baseline_metrics.write_text(json.dumps({"all_ap": 0.5, "all_ap_50%": 0.7, "all_ap_25%": 0.8}))
            candidate_metrics.write_text(json.dumps({"all_ap": 0.55, "all_ap_50%": 0.72, "all_ap_25%": 0.84}))
            baseline_monitor.write_text(json.dumps({"counts": {"scenes": 5, "frames": 100}, "match_rate": {"mean": 0.7}, "birth_rate": {"mean": 0.3}}))
            candidate_monitor.write_text(json.dumps({"counts": {"scenes": 5, "frames": 100}, "match_rate": {"mean": 0.6}, "birth_rate": {"mean": 0.25}, "rescued": {"mean": 2.0}}))

            comparison = compare_official_runs(
                baseline=OfficialRun("baseline", baseline_metrics, baseline_monitor),
                candidate=OfficialRun("candidate", candidate_metrics, candidate_monitor),
            )

            self.assertTrue(comparison["candidate_beats_baseline"])
            self.assertAlmostEqual(comparison["delta"]["all_ap"], 0.05)
            self.assertEqual(comparison["candidate"]["scene_count"], 5)
            markdown = render_official_comparison_markdown(comparison)
            self.assertIn("Candidate - baseline", markdown)
            self.assertIn("+0.0500", markdown)


if __name__ == "__main__":
    unittest.main()
