import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from duograph3d.g3_docs import render_results_matrix_markdown, render_g3_defense_table_markdown


class G3DocsTests(unittest.TestCase):
    def test_renderers_include_expected_labels(self) -> None:
        aggregate = {
            "all_scenes_pass": True,
            "scene_count": 2,
            "row_pass_counts": {"identity_churn_proxy": 2, "reentry_recovery_proxy": 2, "memory_authority_usage": 2, "counterfactual_divergence_proxy": 2, "dense_authority_gap_proxy": 2},
            "row_total_counts": {"identity_churn_proxy": 2, "reentry_recovery_proxy": 2, "memory_authority_usage": 2, "counterfactual_divergence_proxy": 2, "dense_authority_gap_proxy": 2},
            "signature_counts": {"single_layer_fragmentation": 2},
            "scene_rows": [],
        }
        self.assertIn("Results Matrix", render_results_matrix_markdown(aggregate))
        self.assertIn("Two-layer necessity", render_g3_defense_table_markdown(aggregate))


if __name__ == "__main__":
    unittest.main()
