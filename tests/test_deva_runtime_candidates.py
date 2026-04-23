import os
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from duograph3d.deva_runtime import find_deva_runtime_candidates, render_deva_runtime_candidates_markdown


class DevaRuntimeCandidateTests(unittest.TestCase):
    def test_find_candidates(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            candidate = root / "python3"
            os.symlink(sys.executable, candidate)
            summary = find_deva_runtime_candidates([root], max_depth=1)
            self.assertEqual(summary["candidate_count"], 1)
            md = render_deva_runtime_candidates_markdown(summary)
            self.assertIn("Candidate count", md)


if __name__ == "__main__":
    unittest.main()
