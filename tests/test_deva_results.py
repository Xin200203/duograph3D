import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from duograph3d.deva_results import deva_scene_as_lane, render_deva_output_markdown, summarize_deva_output


class DevaResultsTests(unittest.TestCase):
    def test_summarize_and_lane(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            json_dir = Path(tmpdir) / "JSONFiles"
            json_dir.mkdir(parents=True)
            payload = {
                "annotations": [
                    {"file_name": "f0.jpg", "segments_info": [{"id": 1, "area": 10}, {"id": 2, "area": 20}]},
                    {"file_name": "f1.jpg", "segments_info": [{"id": 1, "area": 30}]},
                ]
            }
            (json_dir / "office0.json").write_text(json.dumps(payload))
            summary = summarize_deva_output(tmpdir)
            self.assertEqual(summary["scene_count"], 1)
            self.assertEqual(summary["rows"][0]["unique_track_ids"], 2)
            lane = deva_scene_as_lane(summary["rows"][0])
            self.assertEqual(lane["baseline_id"], "deva_official_offline")
            md = render_deva_output_markdown(summary)
            self.assertIn("office0", md)


if __name__ == "__main__":
    unittest.main()
