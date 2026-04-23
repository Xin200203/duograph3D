import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))

from duograph3d.presets import build_all_suite_specs, expected_scene_count


class PresetTests(unittest.TestCase):
    def test_expected_scene_count(self) -> None:
        specs = build_all_suite_specs()
        self.assertEqual(len(specs), 27)
        self.assertEqual(expected_scene_count(), 540)


if __name__ == '__main__':
    unittest.main()
