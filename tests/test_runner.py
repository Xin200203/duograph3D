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


if __name__ == "__main__":
    unittest.main()
