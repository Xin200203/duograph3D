import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from duograph3d.contracts import FrameInput, Observation, TemporalVariant
from duograph3d.pipeline import DuoGraph3DPipeline


class TemporalTests(unittest.TestCase):
    def test_deva_style_keeps_object_alive_longer_than_no_temporal(self) -> None:
        frames = [
            FrameInput(frame_id="f1", observations=[Observation(observation_id="o1", descriptor="chair", geometry_key="g-chair", repair_group_id="chair")]),
            FrameInput(frame_id="f2", observations=[]),
        ]
        pipeline = DuoGraph3DPipeline()
        no_temporal_result, no_temporal_logger = pipeline.run_sequence(
            sequence_id="seq-none", frames=frames, temporal_variant=TemporalVariant.NONE
        )
        deva_result, deva_logger = pipeline.run_sequence(
            sequence_id="seq-deva", frames=frames, temporal_variant=TemporalVariant.DEVA_STYLE
        )
        no_temporal_node = next(iter(no_temporal_result.memory_nodes.values()))
        deva_node = next(iter(deva_result.memory_nodes.values()))
        self.assertGreaterEqual(no_temporal_node.miss_count, 1)
        self.assertEqual(deva_node.miss_count, 0)
        self.assertEqual(deva_logger.count("temporal_propagation_used"), 1)
        self.assertEqual(no_temporal_logger.count("temporal_propagation_used"), 0)


if __name__ == "__main__":
    unittest.main()
