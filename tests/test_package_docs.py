import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from duograph3d.package_docs import render_g3_package_markdown


class PackageDocsTests(unittest.TestCase):
    def test_render_package_contains_sections(self) -> None:
        text = render_g3_package_markdown(
            mega_summary={
                'scene_count': 10,
                'all_scenes_pass': True,
                'row_pass_counts': {'identity_churn_proxy': 10},
                'row_total_counts': {'identity_churn_proxy': 10},
            },
            robustness_summary={
                'regime_count': 2,
                'all_regimes_pass': True,
                'regimes': {'baseline': {'scene_count': 10, 'all_scenes_pass': True}},
            },
            casebook={'representatives': [{'signal': 'identity_churn_proxy', 'dataset': 'replica', 'scene': 'office0', 'value': 1, 'detail': 'ok'}]},
            metadata_summary={'unique_scene_count': 10, 'replica_mesh_coverage': 2, 'replica_scene_count': 2, 'scannet_label_mesh_coverage': 8, 'scannet_scene_count': 8, 'avg_template_count': 4.2},
            statistics_summary={
                'identity_churn_proxy': {
                    'mean': 1.0,
                    'min': 1.0,
                    'max': 1.0,
                    'worst_scene': {'dataset': 'replica', 'scene': 'office0', 'value': 1.0},
                    'best_scene': {'dataset': 'replica', 'scene': 'office0', 'value': 1.0},
                }
            },
            paper_metrics_summary={
                'aggregate_rows': [
                    {'metric': 'identity_fragmentation_count', 'mean': 0.0, 'min': 0.0, 'max': 0.0}
                ]
            },
        )
        self.assertIn('G3 Evidence Package', text)
        self.assertIn('Global robustness summary', text)
        self.assertIn('Paper-facing metrics', text)
        self.assertIn('Representative casebook signals', text)
        self.assertIn('Metadata grounding summary', text)


if __name__ == '__main__':
    unittest.main()
