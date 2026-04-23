import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from duograph3d.paper_table import build_paper_main_table, render_paper_main_table_markdown


class PaperTableTests(unittest.TestCase):
    def test_build_and_render(self) -> None:
        summary = {
            "regime_rows": [
                {
                    "regime": "outputs_large_baseline",
                    "report_coverage": 20,
                    "metrics": {
                        "identity_fragmentation_count": {"mean": 0.0, "min": 0.0, "max": 0.0},
                        "reentry_reduction": {"mean": 5.4, "min": 4.0, "max": 7.0},
                        "ambiguity_correction_rate": {"mean": 1.0, "min": 1.0, "max": 1.0},
                        "authority_activation_rate": {"mean": 0.6, "min": 0.2, "max": 1.0},
                        "geometry_support_mean": {"mean": 1.0, "min": 0.5, "max": 1.5},
                    },
                }
            ]
        }
        table = build_paper_main_table(summary)
        self.assertEqual(len(table["rows"]), 1)
        md = render_paper_main_table_markdown(table)
        self.assertIn("outputs_large_baseline", md)
        self.assertIn("reentry_reduction", md)


if __name__ == "__main__":
    unittest.main()
