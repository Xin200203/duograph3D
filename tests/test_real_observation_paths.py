import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from duograph3d.data import build_replica_bounded_slice, build_scannet_bounded_slice


class RealObservationPathTests(unittest.TestCase):
    def test_replica_deva_output_alignment_uses_real_observations(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir) / "office0"
            results = root / "results"
            results.mkdir(parents=True)
            (root / "traj.txt").write_text(" ".join(["0"] * 16) + "\n" * 3)
            (root.parent / "office0_mesh.ply").write_text("ply\nformat ascii 1.0\nelement vertex 12\nend_header\n")
            (root.parent / "cam_params.json").write_text("{}")
            for idx in [0, 10, 20]:
                (results / f"frame{idx:06d}.jpg").write_text("rgb")
                (results / f"depth{idx:06d}.png").write_text("depth")
            observation_json = Path(tmpdir) / "office0_deva.json"
            observation_json.write_text(
                json.dumps(
                    {
                        "annotations": [
                            {
                                "file_name": "frame000020.jpg",
                                "segments_info": [{"category_id": 3, "id": 9020, "score": 0.83, "area": 22000}],
                            },
                            {
                                "file_name": "frame000000.jpg",
                                "segments_info": [{"category_id": 2, "id": 9000, "score": 0.91, "area": 18000}],
                            },
                        ]
                    }
                )
            )
            bounded = build_replica_bounded_slice(
                root,
                limit=2,
                observation_json=observation_json,
                observation_format="deva_output",
                allow_synthetic_fallback=False,
            )
            self.assertEqual(bounded.metadata["observation_mode"], "real_deva_output_json")
            self.assertEqual(len(bounded.frames), 2)
            self.assertEqual(bounded.frames[0].frame_id, "replica-office0-000000")
            self.assertEqual(bounded.frames[1].frame_id, "replica-office0-000020")
            self.assertEqual(bounded.frames[0].observations[0].repair_group_id, "office0:deva-track:9000")
            self.assertEqual(bounded.frames[0].observations[0].support.source_kind, "deva_output_json")
            self.assertEqual(bounded.frames[1].observations[0].repair_group_id, "office0:deva-track:9020")

    def test_replica_missing_real_observation_is_reported(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir) / "office0"
            results = root / "results"
            results.mkdir(parents=True)
            (root / "traj.txt").write_text(" ".join(["0"] * 16) + "\n" * 3)
            (root.parent / "office0_mesh.ply").write_text("ply\nformat ascii 1.0\nelement vertex 12\nend_header\n")
            (root.parent / "cam_params.json").write_text("{}")
            for idx in [0, 20]:
                (results / f"frame{idx:06d}.jpg").write_text("rgb")
                (results / f"depth{idx:06d}.png").write_text("depth")
            observation_json = Path(tmpdir) / "office0_deva.json"
            observation_json.write_text(
                json.dumps(
                    {
                        "annotations": [
                            {
                                "file_name": "frame000000.jpg",
                                "segments_info": [],
                            }
                        ]
                    }
                )
            )
            bounded = build_replica_bounded_slice(
                root,
                limit=2,
                observation_json=observation_json,
                observation_format="deva_output",
                allow_synthetic_fallback=False,
            )
            self.assertEqual(bounded.frames[0].observations, [])
            self.assertEqual(bounded.frames[1].observations, [])
            self.assertTrue(any("missing observation frame for replica `office0`" in issue for issue in bounded.issues))

    def test_scannet_generic_observation_json_alignment(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            raw_root = Path(tmpdir) / "scene0008_00"
            raw_root.mkdir()
            for suffix in ["_vh_clean_2.ply", "_vh_clean_2.labels.ply", ".aggregation.json", "_vh_clean_2.0.010000.segs.json", ".txt"]:
                if suffix == ".aggregation.json":
                    (raw_root / f"scene0008_00{suffix}").write_text(json.dumps({"segGroups": [{"label": "chair"}]}))
                else:
                    (raw_root / f"scene0008_00{suffix}").write_text("x")
            pose_root = Path(tmpdir) / "pose_centered" / "scene0008_00"
            pose_root.mkdir(parents=True)
            for stem in ["0", "2"]:
                (pose_root / f"{stem}.npy").write_bytes(b"npy")
            observation_json = Path(tmpdir) / "scene0008_obs.json"
            observation_json.write_text(
                json.dumps(
                    {
                        "frames": [
                            {
                                "pose_name": "2.npy",
                                "frame_id": "scannet-scene0008_00-2",
                                "observations": [
                                    {
                                        "observation_id": "obs-2",
                                        "descriptor": "chair",
                                        "geometry_key": "track-2",
                                        "repair_group_id": "track-2",
                                        "confidence": 0.9,
                                        "support": {
                                            "proposal_id": "proposal-2",
                                            "support_size": 0.12,
                                            "depth_scale": 1.1,
                                            "appearance_key": "chair",
                                            "continuity_key": "track-2",
                                            "geometry_support": 0.8,
                                        },
                                    }
                                ],
                            },
                            {
                                "pose_name": "0.npy",
                                "frame_id": "scannet-scene0008_00-0",
                                "observations": [
                                    {
                                        "observation_id": "obs-0",
                                        "descriptor": "chair",
                                        "geometry_key": "track-0",
                                        "repair_group_id": "track-0",
                                        "confidence": 0.95,
                                        "support": {
                                            "proposal_id": "proposal-0",
                                            "support_size": 0.2,
                                            "depth_scale": 1.0,
                                            "appearance_key": "chair",
                                            "continuity_key": "track-0",
                                            "geometry_support": 0.9,
                                        },
                                    }
                                ],
                            },
                        ]
                    }
                )
            )
            bounded = build_scannet_bounded_slice(
                raw_root,
                pose_root,
                limit=2,
                observation_json=observation_json,
                allow_synthetic_fallback=False,
            )
            self.assertEqual(bounded.metadata["observation_mode"], "real_frame_observation_json")
            self.assertEqual([frame.frame_id for frame in bounded.frames], ["scannet-scene0008_00-0", "scannet-scene0008_00-2"])
            self.assertEqual(bounded.frames[0].observations[0].repair_group_id, "track-0")
            self.assertEqual(bounded.frames[0].observations[0].support.source_kind, "scannet_observation_json")
            self.assertEqual(bounded.frames[1].observations[0].repair_group_id, "track-2")

    def test_scannet_online_monitor_alignment(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            raw_root = Path(tmpdir) / "scene0008_00"
            raw_root.mkdir()
            for suffix in ["_vh_clean_2.ply", "_vh_clean_2.labels.ply", ".aggregation.json", "_vh_clean_2.0.010000.segs.json", ".txt"]:
                if suffix == ".aggregation.json":
                    (raw_root / f"scene0008_00{suffix}").write_text(json.dumps({"segGroups": [{"label": "chair"}]}))
                else:
                    (raw_root / f"scene0008_00{suffix}").write_text("x")
            pose_root = Path(tmpdir) / "pose_centered" / "scene0008_00"
            pose_root.mkdir(parents=True)
            for stem in ["0", "2"]:
                (pose_root / f"{stem}.npy").write_bytes(b"npy")
            observation_json = Path(tmpdir) / "scene0008_monitor.json"
            observation_json.write_text(
                json.dumps(
                    [
                        {
                            "scene_id": "scene0008_00",
                            "frames": [
                                {"frame_i": 2, "matched_track_ids": [7], "birth_track_ids": [8]},
                                {"frame_i": 0, "matched_track_ids": [1], "birth_track_ids": []},
                            ],
                        }
                    ]
                )
            )
            bounded = build_scannet_bounded_slice(
                raw_root,
                pose_root,
                limit=2,
                observation_json=observation_json,
                observation_format="scannet_online_monitor",
                allow_synthetic_fallback=False,
            )
            self.assertEqual(bounded.metadata["observation_mode"], "real_scannet_online_monitor_json")
            self.assertEqual([frame.frame_id for frame in bounded.frames], ["scannet-scene0008_00-monitor-0000", "scannet-scene0008_00-monitor-0002"])
            self.assertEqual(bounded.frames[0].observations[0].repair_group_id, "scene0008_00:track:1")
            self.assertEqual(bounded.frames[0].observations[0].support.source_kind, "scannet_online_monitor_json")
            self.assertEqual(
                [obs.repair_group_id for obs in bounded.frames[1].observations],
                ["scene0008_00:track:7", "scene0008_00:track:8"],
            )


if __name__ == "__main__":
    unittest.main()
