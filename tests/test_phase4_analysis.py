import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from duograph3d.phase4_analysis import (
    build_failure_casebook,
    build_phase4_ablation_table,
    build_phase4_main_table,
    build_worst_best_analysis,
    render_failure_casebook_markdown,
    render_phase4_ablation_table_markdown,
    render_phase4_main_table_markdown,
    render_worst_best_markdown,
)


class Phase4AnalysisTests(unittest.TestCase):
    def setUp(self) -> None:
        self.summary = {
            "rows": [
                {
                    "dataset": "replica",
                    "scene": "office0",
                    "observation_mode": "real_deva_output_json",
                    "rows": {
                        "identity_fragmentation_count": 0.0,
                        "track_consistency_rate": 1.0,
                        "memory_object_purity": 1.0,
                        "real_observation_frame_rate": 1.0,
                        "relation_density": 0.0,
                        "memory_relation_edge_count": 0.0,
                        "geometry_support_mean": 0.5,
                    },
                },
                {
                    "dataset": "scannet",
                    "scene": "scene0568_00",
                    "observation_mode": "real_scannet_online_monitor_json",
                    "rows": {
                        "identity_fragmentation_count": 10.0,
                        "track_consistency_rate": 0.5,
                        "memory_object_purity": 1.0,
                        "real_observation_frame_rate": 0.5,
                        "relation_density": 0.2,
                        "memory_relation_edge_count": 50.0,
                        "geometry_support_mean": 0.3,
                    },
                },
            ],
            "regime_rows": [
                {
                    "regime": "phase4_baseline",
                    "report_coverage": 2,
                    "metrics": {
                        "identity_fragmentation_count": {"mean": 5.0, "min": 0.0, "max": 10.0},
                        "track_consistency_rate": {"mean": 0.75, "min": 0.5, "max": 1.0},
                        "real_observation_frame_rate": {"mean": 0.75, "min": 0.5, "max": 1.0},
                        "geometry_support_mean": {"mean": 0.4, "min": 0.3, "max": 0.5},
                    },
                }
            ],
        }

    def test_build_phase4_main_table(self) -> None:
        table = build_phase4_main_table(self.summary)
        self.assertEqual(len(table["rows"]), 1)
        self.assertEqual(table["rows"][0]["regime"], "phase4_baseline")
        markdown = render_phase4_main_table_markdown(table)
        self.assertIn("Phase 4 Main Table Candidate", markdown)
        self.assertIn("identity_fragmentation_count", markdown)

    def test_build_worst_best_analysis(self) -> None:
        analysis = build_worst_best_analysis(self.summary)
        self.assertEqual(len(analysis["rows"]), 4)
        markdown = render_worst_best_markdown(analysis)
        self.assertIn("Phase 4 Worst/Best Analysis", markdown)
        self.assertIn("office0", markdown)

    def test_build_phase4_ablation_table(self) -> None:
        self.summary["regime_rows"].append(
            {
                "regime": "phase4_stress",
                "report_coverage": 2,
                "metrics": {
                    "identity_fragmentation_count": {"mean": 4.0, "min": 0.0, "max": 8.0},
                    "track_consistency_rate": {"mean": 0.8, "min": 0.6, "max": 1.0},
                    "real_observation_frame_rate": {"mean": 0.7, "min": 0.4, "max": 1.0},
                    "geometry_support_mean": {"mean": 0.45, "min": 0.3, "max": 0.6},
                },
            }
        )
        table = build_phase4_ablation_table(self.summary)
        self.assertEqual(table["baseline_regime"], "phase4_baseline")
        self.assertEqual(len(table["rows"]), 1)
        self.assertEqual(table["rows"][0]["metrics"]["identity_fragmentation_count"]["delta_vs_baseline"], 1.0)
        markdown = render_phase4_ablation_table_markdown(table)
        self.assertIn("Phase 4 Ablation Table Candidate", markdown)
        self.assertIn("phase4_stress", markdown)

    def test_build_failure_casebook(self) -> None:
        casebook = build_failure_casebook(self.summary, top_k=1)
        self.assertEqual(casebook["rows"][0]["scene"], "scene0568_00")
        markdown = render_failure_casebook_markdown(casebook)
        self.assertIn("Phase 4 Failure Casebook", markdown)
        self.assertIn("scene0568_00", markdown)


if __name__ == "__main__":
    unittest.main()
