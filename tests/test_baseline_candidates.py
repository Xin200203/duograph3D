import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from duograph3d.baseline_candidates import build_candidate_lanes, render_candidate_lane_summary_markdown, summarize_candidate_lanes


class BaselineCandidateTests(unittest.TestCase):
    def test_build_and_summarize_candidates(self) -> None:
        report = {
            "dataset": "scannet",
            "scene": "scene0000_02",
            "branches": {
                "duograph3d_full": {"memory_node_count": 4, "track_fragmentation": 0, "memory_authority_events": 3},
                "full_fair_counterfactual": {"memory_node_count": 5, "track_fragmentation": 1, "memory_authority_events": 0},
                "dense_authority_export_rival": {"memory_node_count": 4, "track_fragmentation": 0, "memory_authority_events": 0},
            },
        }
        lanes = build_candidate_lanes(report)
        self.assertEqual(len(lanes), 2)
        with tempfile.TemporaryDirectory() as tmpdir:
            report_path = Path(tmpdir) / "bounded_slice_scannet_scene0000_02.json"
            report_path.write_text(json.dumps(report))
            summary = summarize_candidate_lanes([str(report_path)])
        self.assertEqual(summary["report_coverage"], 1)
        md = render_candidate_lane_summary_markdown(summary)
        self.assertIn("Temporal-only strong candidate", md)
        self.assertIn("Dense-owner strong candidate", md)


if __name__ == "__main__":
    unittest.main()
