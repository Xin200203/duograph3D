import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from duograph3d.phase4_casebook import build_phase4_representative_casebook, render_phase4_casebook_markdown


class Phase4CasebookTests(unittest.TestCase):
    def test_build_casebook(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            report_paths = []
            rows = [
                ("replica", "office0", 0.0, 1.0, 0.5),
                ("scannet", "scene0568_00", 10.0, 0.5, 0.2),
            ]
            for dataset, scene, frag, consistency, geometry in rows:
                event_path = root / f"events_{dataset}_{scene}_duograph3d_full.json"
                event_path.write_text(
                    json.dumps(
                        [
                            {
                                "event_type": "birth_commit",
                                "step_id": 1,
                                "payload": {"track_hint": f"{scene}:track", "object_id": "obj-1"},
                            },
                            {
                                "event_type": "association_commit",
                                "step_id": 2,
                                "payload": {"track_hint": f"{scene}:track", "object_id": "obj-1"},
                            },
                        ]
                    )
                )
                report_path = root / f"bounded_slice_{dataset}_{scene}.json"
                report_path.write_text(
                    json.dumps(
                        {
                            "dataset": dataset,
                            "scene": scene,
                            "frame_count": 4,
                            "frames_with_observations": 4,
                            "scene_metadata": {"observation_mode": "real"},
                            "branch_event_files": {"duograph3d_full": str(event_path)},
                            "branches": {
                                "duograph3d_full": {
                                    "track_fragmentation": frag,
                                    "avg_geometry_support": geometry,
                                    "memory_relation_edge_count": 1,
                                    "memory_node_count": 2,
                                }
                            },
                        }
                    )
                )
                report_paths.append(str(report_path))
            casebook = build_phase4_representative_casebook(report_paths)
            self.assertEqual(len(casebook["cases"]), 4)
            markdown = render_phase4_casebook_markdown(casebook)
            self.assertIn("Phase 4 Representative Casebook", markdown)
            self.assertIn("best_identity_stability", markdown)
            self.assertIn("worst_fragmentation", markdown)


if __name__ == "__main__":
    unittest.main()
