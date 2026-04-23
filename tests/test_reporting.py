import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from duograph3d.reporting import aggregate_g2_summaries, render_g2_table_markdown


class ReportingTests(unittest.TestCase):
    def test_aggregate_and_render(self) -> None:
        summaries = [
            {
                "dataset": "replica",
                "scene": "office0",
                "all_rows_pass": True,
                "rows": {
                    "identity_churn_proxy": {"pass": True, "value": 1, "detail": "ok"},
                    "reentry_recovery_proxy": {"pass": True, "value": 2, "detail": "ok"},
                    "memory_authority_usage": {"pass": True, "value": 2, "detail": "ok"},
                    "counterfactual_divergence_proxy": {"pass": True, "value": 1, "detail": "ok"},
                    "dense_authority_gap_proxy": {"pass": True, "value": 1, "detail": "ok"},
                },
                "failure_signatures": [{"name": "temporal_reentry_gap", "triggered": True, "detail": "ok"}],
            }
        ]
        aggregate = aggregate_g2_summaries(summaries)
        self.assertTrue(aggregate["all_scenes_pass"])
        markdown = render_g2_table_markdown(aggregate, ["/tmp/g2_summary_replica_office0.json"])
        self.assertIn("Identity churn", markdown)
        self.assertIn("temporal_reentry_gap", markdown)


if __name__ == "__main__":
    unittest.main()
