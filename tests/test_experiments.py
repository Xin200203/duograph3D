import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from duograph3d.contracts import FrameInput, Observation
from duograph3d.experiments import apply_burst_occlusion, apply_observation_dropout, apply_occlusion_regime, apply_random_occlusion, ensure_temporal_bridge, run_temporal_triplet


class ExperimentTests(unittest.TestCase):
    def test_dropout_clears_middle_frames(self) -> None:
        frames = [FrameInput(frame_id=f"f{i}", observations=[Observation(observation_id=f"o{i}", descriptor="chair", geometry_key="g")]) for i in range(4)]
        dropped = apply_observation_dropout(frames, drop_every=2)
        self.assertEqual(len(dropped[0].observations), 1)
        self.assertEqual(len(dropped[1].observations), 0)
        self.assertEqual(len(dropped[-1].observations), 1)

    def test_dropout_forces_middle_drop_when_pattern_keeps_all(self) -> None:
        frames = [FrameInput(frame_id=f"f{i}", observations=[Observation(observation_id=f"o{i}", descriptor="chair", geometry_key="g")]) for i in range(3)]
        dropped = apply_observation_dropout(frames, drop_every=3)
        self.assertEqual(len(dropped[0].observations), 1)
        self.assertEqual(len(dropped[1].observations), 0)
        self.assertEqual(len(dropped[2].observations), 1)

    def test_ensure_temporal_bridge_inserts_empty_frame(self) -> None:
        frames = [
            FrameInput(frame_id="f0", observations=[Observation(observation_id="o0", descriptor="chair", geometry_key="g")]),
            FrameInput(frame_id="f1", observations=[Observation(observation_id="o1", descriptor="chair", geometry_key="g")]),
        ]
        bridged = ensure_temporal_bridge(frames)
        self.assertEqual(len(bridged), 3)
        self.assertEqual(len(bridged[1].observations), 0)

    def test_burst_occlusion_drops_consecutive_middle_frames(self) -> None:
        frames = [FrameInput(frame_id=f"f{i}", observations=[Observation(observation_id=f"o{i}", descriptor="chair", geometry_key="g")]) for i in range(5)]
        dropped = apply_burst_occlusion(frames, burst_size=2, start_index=1)
        self.assertEqual(len(dropped[0].observations), 1)
        self.assertEqual(len(dropped[1].observations), 0)
        self.assertEqual(len(dropped[2].observations), 0)
        self.assertEqual(len(dropped[4].observations), 1)

    def test_alternate_dropout_respects_offset(self) -> None:
        frames = [FrameInput(frame_id=f"f{i}", observations=[Observation(observation_id=f"o{i}", descriptor="chair", geometry_key="g")]) for i in range(5)]
        dropped = apply_occlusion_regime(frames, mode="alternate", drop_every=3, drop_offset=2)
        self.assertEqual(len(dropped[0].observations), 1)
        self.assertEqual(len(dropped[1].observations), 0)

    def test_random_occlusion_is_seeded(self) -> None:
        frames = [FrameInput(frame_id=f"f{i}", observations=[Observation(observation_id=f"o{i}", descriptor="chair", geometry_key="g")]) for i in range(6)]
        dropped_a = apply_random_occlusion(frames, drop_probability=0.5, seed=7)
        dropped_b = apply_random_occlusion(frames, drop_probability=0.5, seed=7)
        self.assertEqual([len(f.observations) for f in dropped_a], [len(f.observations) for f in dropped_b])

    def test_temporal_triplet_reports_variants(self) -> None:
        frames = [
            FrameInput(frame_id="f0", observations=[Observation(observation_id="o0", descriptor="chair", geometry_key="g")]),
            FrameInput(frame_id="f1", observations=[]),
            FrameInput(frame_id="f2", observations=[Observation(observation_id="o2", descriptor="chair", geometry_key="g")]),
        ]
        report = run_temporal_triplet("seq", frames)
        self.assertIn("temporal_none", report)
        self.assertIn("temporal_deva_style", report)
        self.assertGreater(report["temporal_deva_style"]["temporal_events"], report["temporal_none"]["temporal_events"])


if __name__ == "__main__":
    unittest.main()
