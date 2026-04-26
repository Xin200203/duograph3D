import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from duograph3d.observation_metrics import (
    build_observation_grounded_metrics,
    render_observation_grounded_metrics_markdown,
    summarize_observation_grounded_metrics,
)


class ObservationMetricsTests(unittest.TestCase):
    def test_build_and_summarize(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            report_path = Path(tmpdir) / "bounded_slice_replica_office0.json"
            event_path = Path(tmpdir) / "events_replica_office0_duograph3d_full.json"
            event_path.write_text(
                json.dumps(
                    [
                        {
                            "event_type": "birth_commit",
                            "payload": {"track_hint": "track-A", "object_id": "obj-1"},
                        },
                        {
                            "event_type": "association_commit",
                            "payload": {"track_hint": "track-A", "object_id": "obj-1"},
                        },
                        {
                            "event_type": "birth_commit",
                            "payload": {"track_hint": "track-B", "object_id": "obj-2"},
                        },
                    ]
                )
            )
            report_path.write_text(
                json.dumps(
                    {
                        "dataset": "replica",
                        "scene": "office0",
                        "frame_count": 4,
                        "frames_with_observations": 3,
                        "scene_metadata": {"observation_mode": "real_deva_output_json"},
                        "branch_event_files": {"duograph3d_full": str(event_path)},
                        "branches": {
                            "duograph3d_full": {
                                "track_fragmentation": 0,
                                "avg_geometry_support": 0.6,
                                "memory_relation_edge_count": 1,
                                "memory_node_count": 2,
                            }
                        },
                    }
                )
            )
            metrics = build_observation_grounded_metrics(json.loads(report_path.read_text()))
            self.assertEqual(metrics["rows"]["identity_fragmentation_count"], 0.0)
            self.assertEqual(metrics["rows"]["track_consistency_rate"], 1.0)
            self.assertEqual(metrics["rows"]["memory_object_purity"], 1.0)
            self.assertEqual(metrics["rows"]["real_observation_frame_rate"], 0.75)
            summary = summarize_observation_grounded_metrics([str(report_path)])
            self.assertEqual(summary["report_coverage"], 1)
            md = render_observation_grounded_metrics_markdown(summary)
            self.assertIn("Observation-Grounded Metrics Summary", md)
            self.assertIn("track_consistency_rate", md)


if __name__ == "__main__":
    unittest.main()
