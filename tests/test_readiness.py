import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from duograph3d.readiness import build_g3_readiness, render_g3_readiness_markdown


class ReadinessTests(unittest.TestCase):
    def test_build_readiness(self) -> None:
        readiness = build_g3_readiness(
            mega_summary={
                'scene_count': 10,
                'all_scenes_pass': True,
                'row_total_counts': {'identity_churn_proxy': 10},
                'row_pass_counts': {'identity_churn_proxy': 10},
            },
            robustness_summary={'regime_count': 3, 'all_regimes_pass': True},
            casebook={'representatives': [1, 2, 3]},
            metadata_summary={'unique_scene_count': 10},
        )
        self.assertTrue(readiness['all_core_rows_pass'])
        self.assertTrue(readiness['metadata_grounded'])
        md = render_g3_readiness_markdown(readiness)
        self.assertIn('G3 Readiness Summary', md)
        self.assertIn('identity_churn_proxy', md)


if __name__ == '__main__':
    unittest.main()
