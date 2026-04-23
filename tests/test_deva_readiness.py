import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from duograph3d.deva_readiness import render_deva_readiness_markdown, summarize_deva_contract


class DevaReadinessTests(unittest.TestCase):
    def test_summarize_and_render(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            img_dir = root / "img_path" / "office0"
            mask_dir = root / "mask_path" / "office0"
            img_dir.mkdir(parents=True)
            mask_dir.mkdir(parents=True)
            (img_dir / "frame000000.jpg").write_bytes(b"jpg")
            (img_dir / "frame000001.jpg").write_bytes(b"jpg")
            (mask_dir / "frame000000.png").write_bytes(b"png")
            (mask_dir / "frame000001.png").write_bytes(b"png")
            (mask_dir / "frame000000.json").write_text(json.dumps([{"id": 1, "bbox": [0, 0, 10, 10], "mask_area": 100}]))
            (mask_dir / "frame000001.json").write_text(json.dumps([{"id": 1, "bbox": [0, 0, 10, 10], "mask_area": 90}]))
            summary = summarize_deva_contract(root)
            self.assertEqual(summary["scene_count"], 1)
            self.assertTrue(summary["all_frames_matched"])
            self.assertTrue(summary["all_scene_json_fields_present"])
            self.assertEqual(summary["scene_rows"][0]["min_segment_count"], 1)
            self.assertEqual(summary["scene_rows"][0]["max_segment_count"], 1)
            md = render_deva_readiness_markdown(summary)
            self.assertIn("office0", md)
            self.assertIn("All bbox", md)


if __name__ == "__main__":
    unittest.main()
