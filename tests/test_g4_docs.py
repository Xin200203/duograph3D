import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))

from duograph3d.g4_docs import render_paper_outline, render_submission_readiness


class G4DocsTests(unittest.TestCase):
    def test_renderers(self) -> None:
        mega = {'scene_count': 100}
        readiness = {
            'regime_count': 5,
            'all_scenes_pass': True,
            'all_regimes_pass': True,
            'all_core_rows_pass': True,
            'prototype_backed': True,
            'paper_grade': False,
            'remaining_gap': ['gap1'],
        }
        self.assertIn('Paper Outline', render_paper_outline(mega, readiness))
        self.assertIn('Submission Readiness Summary', render_submission_readiness(readiness, mega))


if __name__ == '__main__':
    unittest.main()
