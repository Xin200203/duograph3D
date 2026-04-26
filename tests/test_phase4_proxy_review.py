import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from duograph3d.phase4_proxy_review import build_phase4_proxy_review, render_phase4_proxy_review_markdown


class Phase4ProxyReviewTests(unittest.TestCase):
    def test_build_proxy_review(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            report_path = root / "bounded_slice_replica_office0.json"
            g2_path = root / "g2_summary_replica_office0.json"
            report_path.write_text(
                json.dumps(
                    {
                        "dataset": "replica",
                        "scene": "office0",
                        "scene_metadata": {"observation_mode": "real_deva_output_json"},
                        "branches": {
                            "duograph3d_full": {
                                "memory_authority_events": 0,
                                "hypotheses_with_ambiguity": 0,
                                "track_fragmentation": 3,
                            }
                        },
                    }
                )
            )
            g2_path.write_text(
                json.dumps(
                    {
                        "rows": {
                            "identity_churn_proxy": {"value": 0},
                            "memory_authority_usage": {"value": 0},
                            "counterfactual_divergence_proxy": {"value": 1},
                        }
                    }
                )
            )
            review = build_phase4_proxy_review([str(report_path)])
            self.assertEqual(review["report_coverage"], 1)
            self.assertTrue(review["legacy_proxy_reference_only_candidate"])
            markdown = render_phase4_proxy_review_markdown(review)
            self.assertIn("Phase 4 Legacy Proxy Review", markdown)
            self.assertIn("office0", markdown)


if __name__ == "__main__":
    unittest.main()
