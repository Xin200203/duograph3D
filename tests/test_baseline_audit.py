import sys
import tempfile
import unittest
from pathlib import Path
import json

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from duograph3d.baseline_audit import (
    normalize_baseline_audit,
    render_baseline_audit_markdown,
    render_baseline_audit_summary_markdown,
    summarize_baseline_audits,
)


class BaselineAuditTests(unittest.TestCase):
    def test_normalize_and_render(self) -> None:
        report = {
            "dataset": "replica",
            "scene": "office0",
            "branches": {
                "duograph3d_full": {
                    "memory_node_count": 3,
                    "track_fragmentation": 0,
                    "memory_authority_events": 2,
                },
                "single_layer_rival": {
                    "memory_node_count": 4,
                    "track_fragmentation": 1,
                    "memory_authority_events": 0,
                },
                "dense_authority_export_rival": {
                    "memory_node_count": 4,
                    "track_fragmentation": 0,
                    "memory_authority_events": 0,
                },
            },
            "temporal_triplet": {
                "temporal_none": {
                    "memory_node_count": 3,
                    "track_fragmentation": 1,
                    "memory_authority_events": 2,
                }
            },
        }
        audit = normalize_baseline_audit(report)
        self.assertEqual(audit["dataset"], "replica")
        self.assertEqual(len(audit["rows"]), 3)
        md = render_baseline_audit_markdown(audit)
        self.assertIn("Single-layer rival", md)
        self.assertIn("Dense-authority export rival", md)
        self.assertIn("Temporal none", md)

    def test_summarize_audits(self) -> None:
        report = {
            "dataset": "replica",
            "scene": "office0",
            "branches": {
                "duograph3d_full": {"memory_node_count": 3, "track_fragmentation": 0, "memory_authority_events": 2},
                "single_layer_rival": {"memory_node_count": 4, "track_fragmentation": 1, "memory_authority_events": 0},
            },
            "temporal_triplet": {
                "temporal_none": {"memory_node_count": 3, "track_fragmentation": 1, "memory_authority_events": 2}
            },
        }
        with tempfile.TemporaryDirectory() as tmpdir:
            report_path = Path(tmpdir) / "bounded_slice_replica_office0.json"
            report_path.write_text(json.dumps(report))
            summary = summarize_baseline_audits([str(report_path)])
        self.assertEqual(summary["report_count"], 1)
        self.assertEqual(summary["unique_scene_count"], 1)
        md = render_baseline_audit_summary_markdown(summary)
        self.assertIn("Single-layer rival", md)
        self.assertIn("Temporal none", md)

    def test_unknown_temporal_lane_falls_back(self) -> None:
        report = {
            "dataset": "scannet",
            "scene": "scene0000_00",
            "branches": {"duograph3d_full": {"memory_node_count": 3, "track_fragmentation": 0, "memory_authority_events": 2}},
            "temporal_triplet": {
                "temporal_future_lane": {"memory_node_count": 3, "track_fragmentation": 0, "memory_authority_events": 1}
            },
        }
        audit = normalize_baseline_audit(report)
        self.assertEqual(audit["rows"][0]["baseline_id"], "temporal_future_lane")
        self.assertEqual(audit["rows"][0]["family"], "unknown_temporal")


if __name__ == "__main__":
    unittest.main()
