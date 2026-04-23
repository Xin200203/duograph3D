import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))

from duograph3d.metadata_grounding import render_metadata_grounding_markdown, summarize_metadata_grounding


class MetadataGroundingTests(unittest.TestCase):
    def test_summary(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            report1 = {
                'dataset': 'replica',
                'scene': 'office0',
                'scene_metadata': {'mesh_vertex_count': 10},
            }
            report2 = {
                'dataset': 'scannet',
                'scene': 'scene0000_00',
                'scene_metadata': {'mesh_vertex_count': 20, 'object_label_count': 3, 'top_labels': ['chair']},
            }
            (root / 'bounded_slice_replica_office0.json').write_text(json.dumps(report1))
            (root / 'bounded_slice_scannet_scene0000_00.json').write_text(json.dumps(report2))
            summary = summarize_metadata_grounding([root])
            self.assertEqual(summary['unique_scene_count'], 2)
            self.assertEqual(summary['replica_scene_count'], 1)
            self.assertEqual(summary['scannet_scene_count'], 1)
            md = render_metadata_grounding_markdown(summary)
            self.assertIn('Metadata Grounding Summary', md)
            self.assertIn('Replica scenes', md)


if __name__ == '__main__':
    unittest.main()
