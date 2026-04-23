import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from duograph3d.paper_metrics import build_paper_metrics, render_paper_metrics_markdown, summarize_paper_metrics


class PaperMetricsTests(unittest.TestCase):
    def test_build_and_summarize(self) -> None:
        report = {
            "dataset": "replica",
            "scene": "office0",
            "frames_with_observations": 4,
            "branches": {
                "duograph3d_full": {
                    "track_fragmentation": 0,
                    "memory_authority_events": 2,
                    "hypotheses_with_ambiguity": 4,
                    "avg_geometry_support": 0.75,
                }
            },
            "temporal_triplet": {
                "temporal_none": {"reentries": 4},
                "temporal_naive_framewise": {"reentries": 4},
                "temporal_deva_style": {"reentries": 1},
            },
        }
        metrics = build_paper_metrics(report)
        self.assertEqual(metrics["rows"]["reentry_reduction"], 3.0)
        self.assertEqual(metrics["rows"]["ambiguity_correction_rate"], 0.5)
        with tempfile.TemporaryDirectory() as tmpdir:
            regime_dir = Path(tmpdir) / "outputs_large_baseline"
            regime_dir.mkdir()
            path = regime_dir / "bounded_slice_replica_office0.json"
            path.write_text(json.dumps(report))
            summary = summarize_paper_metrics([str(path)])
        self.assertEqual(summary["report_coverage"], 1)
        self.assertEqual(summary["regime_rows"][0]["regime"], "outputs_large_baseline")
        md = render_paper_metrics_markdown(summary)
        self.assertIn("geometry_support_mean", md)
        self.assertIn("By regime", md)


if __name__ == "__main__":
    unittest.main()
