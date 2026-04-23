import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from duograph3d.external_comparison import build_external_comparison, render_external_comparison_markdown


class ExternalComparisonTests(unittest.TestCase):
    def test_build_and_render(self) -> None:
        duo_summary = {
            "rows": [
                {
                    "dataset": "replica",
                    "scene": "office0",
                    "rows": {
                        "identity_fragmentation_count": 0.0,
                        "reentry_reduction": 4.0,
                        "authority_activation_rate": 0.5,
                    },
                }
            ]
        }
        deva_summary = {
            "rows": [
                {
                    "scene": "office0",
                    "avg_segments_per_frame": 1.0,
                    "unique_track_ids": 1,
                    "frames_with_segments": 6,
                }
            ]
        }
        summary = build_external_comparison(duo_summary, deva_summary)
        self.assertEqual(summary["scene_count"], 1)
        self.assertEqual(summary["deva_active_scene_count"], 1)
        md = render_external_comparison_markdown(summary)
        self.assertIn("replica/office0", md)
        self.assertIn("DEVA avg seg/frame", md)


if __name__ == "__main__":
    unittest.main()
