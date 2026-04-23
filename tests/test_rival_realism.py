import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))

from duograph3d.rival_realism import render_rival_realism_markdown, summarize_rival_realism


class RivalRealismTests(unittest.TestCase):
    def test_summary(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            suite = Path(tmpdir)
            report = {
                'dataset': 'replica',
                'scene': 'office0',
                'rows': {'dense_authority_gap_proxy': {'value': 2}},
                'branches': {'dense_authority_export_rival': {}},
                'branch_event_files': {'dense_authority_export_rival': 'events_replica_office0_dense_authority_export_rival.json'},
            }
            (suite / 'bounded_slice_replica_office0.json').write_text(json.dumps(report))
            events = [
                {'event_type': 'dense_authority_update', 'step_id': 1, 'payload': {}},
                {'event_type': 'dense_keepalive', 'step_id': 2, 'payload': {}},
            ]
            (suite / 'events_replica_office0_dense_authority_export_rival.json').write_text(json.dumps(events))
            summary = summarize_rival_realism([suite])
            self.assertEqual(summary['scene_count'], 1)
            self.assertEqual(summary['dense_nonzero_keepalive_scenes'], 1)
            md = render_rival_realism_markdown(summary)
            self.assertIn('Rival Realism Summary', md)
            self.assertIn('keepalive', md)


if __name__ == '__main__':
    unittest.main()
