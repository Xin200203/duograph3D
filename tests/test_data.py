import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from duograph3d.data import ReplicaSequence, ScanNetPoseCenteredScene, ScanNetRawScene


class DataTests(unittest.TestCase):
    def test_replica_sequence_detects_frames(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir) / "office0"
            results = root / "results"
            results.mkdir(parents=True)
            (root / "traj.txt").write_text(" ".join(["0"] * 16) + "\n")
            (root.parent / "office0_mesh.ply").write_text("ply\nformat ascii 1.0\nelement vertex 12\nend_header\n")
            (root.parent / "cam_params.json").write_text("{}")
            (results / "frame000000.jpg").write_text("rgb")
            (results / "depth000000.png").write_text("depth")
            seq = ReplicaSequence.from_root(root)
            self.assertEqual(seq.validate(), [])
            frame_inputs = seq.to_frame_inputs(limit=1)
            self.assertEqual(len(frame_inputs), 1)
            self.assertGreaterEqual(len(frame_inputs[0].observations), 1)
            self.assertIsNotNone(frame_inputs[0].observations[0].support)
            self.assertEqual(frame_inputs[0].observations[0].support.source_kind, "replica_frame")
            self.assertEqual(seq.metadata()["mesh_vertex_count"], 12)
            self.assertEqual(seq.metadata()["template_count"], 3)

    def test_scannet_scene_validation(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir) / "scene0008_00"
            root.mkdir()
            for suffix in ["_vh_clean_2.ply", "_vh_clean_2.labels.ply", ".aggregation.json", "_vh_clean_2.0.010000.segs.json", ".txt"]:
                if suffix == ".aggregation.json":
                    (root / f"scene0008_00{suffix}").write_text(json.dumps({"segGroups": [{"label": "chair"}]}))
                else:
                    (root / f"scene0008_00{suffix}").write_text("x")
            scene = ScanNetRawScene.from_root(root)
            self.assertEqual(scene.validate(), [])
            self.assertEqual(scene.object_labels(), ["chair"])
            self.assertEqual(scene.metadata()["object_label_count"], 1)
            self.assertEqual(scene.metadata()["template_count"], 4)

    def test_pose_centered_scene_detects_npy(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir) / "scene0008_00"
            root.mkdir()
            (root / "0.npy").write_bytes(b"npy")
            scene = ScanNetPoseCenteredScene.from_root(root)
            self.assertEqual(scene.validate(), [])
            frame_inputs = scene.to_frame_inputs(["chair"], limit=1)
            self.assertEqual(len(frame_inputs), 1)
            self.assertIsNotNone(frame_inputs[0].observations[0].support)
            self.assertEqual(frame_inputs[0].observations[0].support.source_kind, "scannet_pose")


if __name__ == "__main__":
    unittest.main()
