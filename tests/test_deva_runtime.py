import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from duograph3d.deva_runtime import build_deva_offline_command, evaluate_deva_runtime, render_deva_runtime_markdown


class DevaRuntimeTests(unittest.TestCase):
    def test_build_command(self) -> None:
        command = build_deva_offline_command(
            repo_root="/repo",
            python_executable="/usr/bin/python3",
            img_path="/contract/img_path",
            mask_path="/contract/mask_path",
            output_dir="/out",
            dataset="demo",
            temporal_setting="semionline",
            chunk_size=1,
            model_path="/model.pth",
        )
        self.assertIn("evaluation/eval_with_detections.py", command)
        self.assertIn("--mask_path", command)
        self.assertIn("/model.pth", command)

    def test_evaluate_runtime_reports_missing_paths(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            repo_root = Path(tmpdir) / "repo"
            contract_root = Path(tmpdir) / "contract"
            report = evaluate_deva_runtime(
                repo_root=repo_root,
                python_executable=sys.executable,
                contract_root=contract_root,
            )
        self.assertFalse(report["ready"])
        self.assertTrue(any("missing repo root" in blocker for blocker in report["blockers"]))
        md = render_deva_runtime_markdown(report)
        self.assertIn("Blockers", md)


if __name__ == "__main__":
    unittest.main()
