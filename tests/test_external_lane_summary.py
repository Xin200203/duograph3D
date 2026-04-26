from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from duograph3d.external_lane_summary import (
    build_external_lane_summary,
    parse_health_log,
    parse_onlineanyseg_eval_log,
    render_external_lane_summary_markdown,
)


class ExternalLaneSummaryTests(unittest.TestCase):
    def test_parse_onlineanyseg_eval_log(self) -> None:
        payload = """
There are 1 sequences needed to be evaluated totally, 0 selected sequences are missing...
Final pred instance num: 119; final GT instance num 31 (with valid labels)
scans processed: 1 / 1
average        :          0.550          0.610          0.630
"""
        parsed = parse_onlineanyseg_eval_log(payload)
        self.assertTrue(parsed["evaluator_completed"])
        self.assertEqual(parsed["selected_sequences"], 1)
        self.assertEqual(parsed["missing_sequences"], 0)
        self.assertEqual(parsed["pred_instance_count"], 119)
        self.assertAlmostEqual(parsed["all_ap"], 0.55)

    def test_parse_onlineanyseg_eval_log_sums_multi_scene_counts(self) -> None:
        payload = """
There are 2 sequences needed to be evaluated totally, 0 selected sequences are missing...
Begin to process sequence scene0000_00 (1 / 2)
Final pred instance num: 12; final GT instance num 20 (with valid labels)
Begin to process sequence scene0001_00 (2 / 2)
Final pred instance num: 7; final GT instance num 9 (with valid labels)
scans processed: 2 / 2
average        :          0.100          0.200          0.300
"""
        parsed = parse_onlineanyseg_eval_log(payload)
        self.assertEqual(parsed["pred_instance_count"], 19)
        self.assertEqual(parsed["gt_instance_count"], 29)
        self.assertEqual(len(parsed["sequence_instance_counts"]), 2)
        self.assertEqual(parsed["sequence_instance_counts"][0]["scene"], "scene0000_00")

    def test_build_and_render_lane_summary(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            health = root / "health.txt"
            eval_log = root / "eval.log"
            health.write_text(
                "\n".join(
                    [
                        "repo=/tmp/OnlineAnySeg",
                        "commit=abc123",
                        "remote=https://example.invalid/repo.git",
                        "env=conceptgraph-cu118",
                        "main FAIL ModuleNotFoundError No module named 'MinkowskiEngine.MinkowskiFunctional'",
                    ]
                )
            )
            eval_log.write_text(
                "There are 1 sequences needed to be evaluated totally, 0 selected sequences are missing...\n"
                "Final pred instance num: 31; final GT instance num 31 (with valid labels)\n"
                "scans processed: 1 / 1\n"
                "average        :          0.849          0.968          1.000\n"
            )

            summary = build_external_lane_summary(
                lane_id="onlineanyseg_minimal_20260423",
                role="direct-neighbor evaluator bring-up",
                status="evaluator-smoke-passed",
                health_log_path=health,
                evaluator_log_path=eval_log,
                artifacts={"eval_log": str(eval_log)},
            )

        self.assertTrue(summary["health"]["has_failures"])
        self.assertEqual(summary["evaluator_smoke"]["gt_instance_count"], 31)
        self.assertTrue(parse_health_log("x OK\n")["checks"])
        md = render_external_lane_summary_markdown(summary)
        self.assertIn("AP / AP50 / AP25", md)
        self.assertIn("MinkowskiEngine", md)


if __name__ == "__main__":
    unittest.main()
