import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from duograph3d.g2 import build_g2_summary


class G2SummaryTests(unittest.TestCase):
    def test_build_g2_summary_detects_expected_gaps(self) -> None:
        report = {
            "dataset": "replica",
            "scene": "office0",
            "frame_count": 6,
            "frames_with_observations": 4,
            "branches": {
                "duograph3d_full": {"memory_node_count": 1, "memory_authority_events": 2, "track_fragmentation": 0},
                "single_layer_rival": {"memory_node_count": 2, "track_fragmentation": 2},
                "dense_authority_export_rival": {"memory_node_count": 2, "track_fragmentation": 1},
                "full_fair_counterfactual": {"memory_node_count": 2, "track_fragmentation": 2},
            },
            "temporal_triplet": {
                "temporal_none": {"reentries": 2},
                "temporal_naive_framewise": {"reentries": 2},
                "temporal_deva_style": {"reentries": 0},
            },
        }
        summary = build_g2_summary(report)
        self.assertTrue(summary["rows"]["identity_churn_proxy"]["pass"])
        self.assertTrue(summary["rows"]["reentry_recovery_proxy"]["pass"])
        self.assertTrue(summary["rows"]["memory_authority_usage"]["pass"])
        self.assertTrue(summary["all_rows_pass"])


if __name__ == "__main__":
    unittest.main()
