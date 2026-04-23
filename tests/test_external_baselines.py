import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from duograph3d.external_baselines import deva_official_target, render_external_baseline_target_markdown


class ExternalBaselineTargetTests(unittest.TestCase):
    def test_deva_target_and_markdown(self) -> None:
        target = deva_official_target("404a112df77f9644d5c7211811329ccd8174b8c3")
        self.assertEqual(target["baseline_id"], "deva_official_offline")
        self.assertIn("mask_path", target["required_inputs"])
        md = render_external_baseline_target_markdown(target)
        self.assertIn("Tracking-Anything-with-DEVA", md)
        self.assertIn("eval_with_detections.py", md)


if __name__ == "__main__":
    unittest.main()
