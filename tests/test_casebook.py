import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from duograph3d.casebook import build_casebook, render_casebook_markdown


class CasebookTests(unittest.TestCase):
    def test_build_casebook(self) -> None:
        mega = {
            "scene_count": 2,
            "all_scenes_pass": True,
            "scene_rows": [
                {
                    "dataset": "replica",
                    "scene": "office0",
                    "rows": {
                        "identity_churn_proxy": {"value": 1},
                        "reentry_recovery_proxy": {"value": 2},
                        "memory_authority_usage": {"value": 3},
                        "counterfactual_divergence_proxy": {"value": 1},
                        "dense_authority_gap_proxy": {"value": 1},
                    },
                }
            ],
        }
        with tempfile.TemporaryDirectory() as tmpdir:
            suite = Path(tmpdir)
            (suite / 'g2_summary_replica_office0.json').write_text('{}')
            for branch in ['duograph3d_full', 'single_layer_rival', 'full_fair_counterfactual']:
                (suite / f'events_replica_office0_{branch}.json').write_text(json.dumps([{"event_type": "birth_commit", "step_id": 1, "payload": {}}]))
            casebook = build_casebook(mega, [suite])
            self.assertEqual(len(casebook['representatives']), 5)
            markdown = render_casebook_markdown(casebook)
            self.assertIn('G3 Casebook', markdown)
            self.assertIn('identity_churn_proxy', markdown)


if __name__ == '__main__':
    unittest.main()
