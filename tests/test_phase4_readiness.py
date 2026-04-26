import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from duograph3d.phase4_readiness import build_phase4_readiness, render_phase4_readiness_markdown


class Phase4ReadinessTests(unittest.TestCase):
    def test_build_readiness(self) -> None:
        readiness = build_phase4_readiness(
            mega_summary={"scene_count": 24, "all_scenes_pass": False},
            robustness_summary={"all_regimes_pass": False},
            observation_summary={"report_coverage": 24},
            proxy_review={"legacy_proxy_reference_only_candidate": True},
            has_main_table_candidate=True,
            has_ablation_table_candidate=True,
            has_worst_best_analysis=True,
            has_failure_casebook=True,
            has_representative_casebook=True,
            has_external_baseline_matrix=True,
        )
        self.assertTrue(readiness["candidate_package_complete"])
        self.assertTrue(readiness["paper_grade_candidate"])
        markdown = render_phase4_readiness_markdown(readiness)
        self.assertIn("Phase 4 Readiness Summary", markdown)
        self.assertIn("Legacy proxy gates are reference-only candidate: Yes", markdown)


if __name__ == "__main__":
    unittest.main()
