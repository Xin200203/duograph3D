import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from duograph3d.data import build_replica_bounded_slice
from duograph3d.io_utils import write_json
from duograph3d.rivals import run_all_branches
from duograph3d.metrics import summarize_run
from duograph3d.presets import SuiteSpec
from duograph3d.suite_runner import run_suite


class RunnerTests(unittest.TestCase):
    def test_bounded_slice_report_writes(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir) / "office0"
            results = root / "results"
            results.mkdir(parents=True)
            (root / "traj.txt").write_text("traj")
            (root.parent / "office0_mesh.ply").write_text("ply\nformat ascii 1.0\nelement vertex 9\nend_header\n")
            (root.parent / "cam_params.json").write_text("{}")
            for idx in [0, 10, 20]:
                (results / f"frame{idx:06d}.jpg").write_text("rgb")
                (results / f"depth{idx:06d}.png").write_text("depth")
            bounded = build_replica_bounded_slice(root, limit=2)
            report = {
                "frame_count": len(bounded.frames),
                "scene_metadata": bounded.metadata,
                "branches": {branch_id: summarize_run(result, logger) for branch_id, (result, logger) in run_all_branches("replica-office0", bounded.frames).items()},
            }
            output = write_json(report, Path(tmpdir) / "report.json")
            loaded = json.loads(output.read_text())
            self.assertEqual(loaded["frame_count"], 2)
            self.assertIn("duograph3d_full", loaded["branches"])
            self.assertIn("mesh_vertex_count", loaded["scene_metadata"])

    def test_run_suite_respects_custom_replica_scene_list(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            import duograph3d.suite_runner as suite_runner

            calls = []

            def fake_run_one(dataset: str, scene: str, spec: SuiteSpec, output_dir: Path):
                calls.append((dataset, scene))
                summary_path = output_dir / f"g2_summary_{dataset}_{scene}.json"
                summary = {
                    "dataset": dataset,
                    "scene": scene,
                    "rows": {
                        "identity_churn_proxy": {"pass": True, "value": 1, "detail": "ok"},
                        "reentry_recovery_proxy": {"pass": True, "value": 1, "detail": "ok"},
                        "memory_authority_usage": {"pass": True, "value": 1, "detail": "ok"},
                        "counterfactual_divergence_proxy": {"pass": True, "value": 1, "detail": "ok"},
                        "dense_authority_gap_proxy": {"pass": True, "value": 1, "detail": "ok"},
                    },
                    "failure_signatures": [],
                    "all_rows_pass": True,
                }
                summary_path.write_text(json.dumps(summary))
                return output_dir / f"bounded_slice_{dataset}_{scene}.json", summary_path

            original = suite_runner.run_one
            suite_runner.run_one = fake_run_one
            try:
                spec = SuiteSpec(name="custom_suite", scannet_scenes=["scene0008_00"], replica_scenes=["office0"])
                aggregate_path, _ = run_suite(spec, Path(tmpdir))
                self.assertTrue(aggregate_path.exists())
                self.assertEqual(calls, [("replica", "office0"), ("scannet", "scene0008_00")])
            finally:
                suite_runner.run_one = original


if __name__ == "__main__":
    unittest.main()
