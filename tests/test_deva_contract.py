import base64
import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from duograph3d.deva_contract import export_replica_deva_contract, export_replica_deva_contract_batch


_ONE_BY_ONE_JPEG = base64.b64decode(
    "/9j/4AAQSkZJRgABAQAAAQABAAD/2wCEAAkGBxAQEBAQEA8PEA8PDw8PDw8PDw8PDw8QFREWFhURFRUYHSggGBolGxUVITEhJSkrLi4uFx8zODMsNygtLisBCgoKDQ0NDg0NDisZFRkrKysrKysrKysrKysrKysrKysrKysrKysrKysrKysrKysrKysrKysrKysrKysrK//AABEIAAEAAQMBIgACEQEDEQH/xAAXAAADAQAAAAAAAAAAAAAAAAAAAQID/8QAFBABAAAAAAAAAAAAAAAAAAAAAP/aAAwDAQACEAMQAAAByA//xAAZEAEAAwEBAAAAAAAAAAAAAAABAAIREjH/2gAIAQEAAT8AqzB1M//EABQRAQAAAAAAAAAAAAAAAAAAABD/2gAIAQIBAT8Af//EABQRAQAAAAAAAAAAAAAAAAAAABD/2gAIAQMBAT8Af//Z"
)


class DevaContractTests(unittest.TestCase):
    def test_export_replica_contract(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir) / "office0"
            results = root / "results"
            results.mkdir(parents=True)
            (root / "traj.txt").write_text(" ".join(["0"] * 16) + "\n")
            (root.parent / "office0_mesh.ply").write_text("ply\nformat ascii 1.0\nelement vertex 12\nend_header\n")
            (root.parent / "cam_params.json").write_text("{}")
            (results / "frame000000.jpg").write_bytes(_ONE_BY_ONE_JPEG)
            (results / "depth000000.png").write_text("depth")
            output_root = Path(tmpdir) / "deva_contract"
            summary = export_replica_deva_contract(root, output_root, limit=1, allow_placeholder_canvas=True)
            self.assertEqual(summary["scene"], "office0")
            self.assertEqual(summary["exported_frames"], 1)
            self.assertEqual(summary["placeholder_canvas_frames"], 1)
            self.assertGreater(summary["avg_mask_pixels_per_frame"], 0)
            mask_dir = output_root / "mask_path" / "office0"
            image_dir = output_root / "img_path" / "office0"
            json_files = list(mask_dir.glob("*.json"))
            png_files = list(mask_dir.glob("*.png"))
            self.assertEqual(len(json_files), 1)
            self.assertEqual(len(png_files), 1)
            self.assertEqual(len(list(image_dir.glob("*.jpg"))), 1)
            payload = json.loads(json_files[0].read_text())
            self.assertGreaterEqual(len(payload), 1)
            self.assertIn("bbox", payload[0])
            self.assertIn("mask_area", payload[0])

    def test_export_replica_contract_batch(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            roots = []
            for scene in ["office0", "office1"]:
                root = Path(tmpdir) / scene
                results = root / "results"
                results.mkdir(parents=True)
                (root / "traj.txt").write_text(" ".join(["0"] * 16) + "\n")
                (root.parent / f"{scene}_mesh.ply").write_text("ply\nformat ascii 1.0\nelement vertex 12\nend_header\n")
                (root.parent / "cam_params.json").write_text("{}")
                (results / "frame000000.jpg").write_bytes(_ONE_BY_ONE_JPEG)
                (results / "depth000000.png").write_text("depth")
                roots.append(root)
            output_root = Path(tmpdir) / "deva_batch"
            summary = export_replica_deva_contract_batch(roots, output_root, limit=1, allow_placeholder_canvas=True)
            self.assertEqual(summary["scene_count"], 2)
            self.assertEqual(summary["total_frames"], 2)
            self.assertEqual(len(summary["scenes"]), 2)
            self.assertGreater(summary["avg_mask_pixels_per_scene_frame"], 0)

    def test_export_uses_paired_order_not_frame_id_suffix(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir) / "office0"
            results = root / "results"
            results.mkdir(parents=True)
            (root / "traj.txt").write_text("\n".join([" ".join(["0"] * 16)] * 2) + "\n")
            (root.parent / "office0_mesh.ply").write_text("ply\nformat ascii 1.0\nelement vertex 12\nend_header\n")
            (root.parent / "cam_params.json").write_text("{}")
            (results / "frame000000.jpg").write_bytes(_ONE_BY_ONE_JPEG)
            (results / "depth000000.png").write_text("depth")
            (results / "frame000001.jpg").write_bytes(_ONE_BY_ONE_JPEG)
            (results / "depth000001.png").write_text("depth")
            output_root = Path(tmpdir) / "deva_contract"
            summary = export_replica_deva_contract(root, output_root, limit=2, allow_placeholder_canvas=True)
            self.assertEqual(summary["exported_frames"], 2)


if __name__ == "__main__":
    unittest.main()
