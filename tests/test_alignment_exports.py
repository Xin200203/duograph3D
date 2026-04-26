from __future__ import annotations

import gzip
import json
import pickle
import tempfile
import unittest
import zipfile
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from duograph3d.alignment_exports import export_conceptgraphs_alignment, export_onlineanyseg_alignment


class AlignmentExportTests(unittest.TestCase):
    def _write_report(self, root: Path) -> Path:
        report = {
            "dataset": "scannet",
            "scene": "scene0000_00",
            "branches": {
                "duograph3d_full": {
                    "memory_node_count": 2,
                    "avg_geometry_support": 0.75,
                    "track_assignments": {
                        "track-a": ["obj-1"],
                        "track-b": ["obj-2"],
                    },
                }
            },
        }
        path = root / "bounded_slice_scannet_scene0000_00.json"
        path.write_text(json.dumps(report))
        return path

    def _write_dense_geometry(self, root: Path) -> Path:
        geometry = {
            "source": "unit-test-dense-geometry",
            "coordinate_frame": "gt_reconstruction",
            "gt_aligned": True,
            "points": [
                [0.0, 0.0, 0.0],
                [1.0, 0.0, 0.0],
                [0.0, 1.0, 0.0],
                [1.0, 1.0, 0.0],
            ],
            "colors": [
                [255, 0, 0],
                [255, 0, 0],
                [0, 255, 0],
                [0, 255, 0],
            ],
            "objects": [
                {
                    "object_id": "obj-1",
                    "track_hint": "track-a",
                    "point_indices": [0, 1],
                    "class_id": 5,
                    "class_name": "chair",
                    "score": 0.91,
                    "clip_ft": [1.0, 0.0, 0.0, 0.0],
                    "text_ft": [1.0, 0.0, 0.0, 0.0],
                },
                {
                    "object_id": "obj-2",
                    "track_hint": "track-b",
                    "point_indices": [2, 3],
                    "class_id": 8,
                    "class_name": "table",
                    "score": 0.82,
                    "clip_ft": [0.0, 1.0, 0.0, 0.0],
                    "text_ft": [0.0, 1.0, 0.0, 0.0],
                },
            ],
        }
        path = root / "dense_geometry.json"
        path.write_text(json.dumps(geometry))
        return path

    def test_onlineanyseg_alignment_writes_expected_surface(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            report = self._write_report(root)
            manifest = export_onlineanyseg_alignment(report, root / "oas", points_per_object=4)
            self.assertFalse(manifest["official_evaluation_ready"])
            scene_dir = root / "oas" / "scene0000_00"
            self.assertTrue((scene_dir / "final.ply").exists())
            npz_path = scene_dir / "ckpt_final.npz"
            self.assertTrue(npz_path.exists())
            with zipfile.ZipFile(npz_path) as archive:
                self.assertEqual(
                    sorted(archive.namelist()),
                    ["pred_classes.npy", "pred_masks.npy", "pred_score.npy"],
                )
            saved_manifest = json.loads((scene_dir / "duograph3d_onlineanyseg_alignment_manifest.json").read_text())
            self.assertEqual(saved_manifest["object_count"], 2)
            self.assertEqual(saved_manifest["point_count"], 8)
            self.assertEqual(saved_manifest["alignment_mode"], "proxy_geometry")

    def test_conceptgraphs_alignment_writes_serialized_object_map(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            report = self._write_report(root)
            manifest = export_conceptgraphs_alignment(report, root / "cg", feature_dim=8, points_per_object=4)
            self.assertFalse(manifest["official_evaluation_ready"])
            result_path = Path(manifest["files"]["conceptgraphs_pkl_gz"])
            self.assertTrue(result_path.exists())
            with gzip.open(result_path, "rb") as handle:
                payload = pickle.load(handle)
            self.assertIn("objects", payload)
            self.assertIsNone(payload["bg_objects"])
            self.assertEqual(len(payload["objects"]), 2)
            self.assertIn("pcd_np", payload["objects"][0])
            self.assertIn("clip_ft", payload["objects"][0])
            saved_manifest = json.loads((result_path.parent / "duograph3d_conceptgraphs_alignment_manifest.json").read_text())
            self.assertEqual(saved_manifest["pred_exp_name"], "duograph3d_alignment")

    def test_dense_geometry_promotes_onlineanyseg_to_official_ready_surface(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            report = self._write_report(root)
            geometry = self._write_dense_geometry(root)
            manifest = export_onlineanyseg_alignment(report, root / "oas", geometry_path=geometry)
            self.assertTrue(manifest["official_evaluation_ready"])
            self.assertEqual(manifest["status"], "format_aligned_official_ready")
            self.assertEqual(manifest["point_count"], 4)
            self.assertEqual(manifest["readiness"]["explicit_class_ids"], True)
            ply_text = (root / "oas" / "scene0000_00" / "final.ply").read_text()
            self.assertIn("element vertex 4", ply_text)
            self.assertIn("property uchar red", ply_text)
            with zipfile.ZipFile(root / "oas" / "scene0000_00" / "ckpt_final.npz") as archive:
                pred_classes = archive.read("pred_classes.npy")
            self.assertIn(b"(2,)", pred_classes)

    def test_dense_geometry_promotes_conceptgraphs_to_official_ready_surface(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            report = self._write_report(root)
            geometry = self._write_dense_geometry(root)
            manifest = export_conceptgraphs_alignment(report, root / "cg", geometry_path=geometry, feature_dim=4)
            self.assertTrue(manifest["official_evaluation_ready"])
            self.assertEqual(manifest["status"], "format_aligned_official_ready")
            result_path = Path(manifest["files"]["conceptgraphs_pkl_gz"])
            with gzip.open(result_path, "rb") as handle:
                payload = pickle.load(handle)
            self.assertEqual(payload["objects"][0]["pcd_np"], [(0.0, 0.0, 0.0), (1.0, 0.0, 0.0)])
            self.assertEqual(payload["objects"][0]["class_name"], ["chair"])
            self.assertEqual(payload["objects"][0]["clip_ft"], [1.0, 0.0, 0.0, 0.0])


if __name__ == "__main__":
    unittest.main()
