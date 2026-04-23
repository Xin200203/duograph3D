import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from duograph3d.contracts import FrameInput, Observation, ObservationSupport, TemporalVariant
from duograph3d.events import (
    BRANCH_COUNTERFACTUAL,
    BRANCH_DENSE_EXPORT,
    BRANCH_DUOGRAPH3D,
    BRANCH_SINGLE_LAYER,
)
from duograph3d.rivals import SingleLayerRival, run_all_branches


class RivalTests(unittest.TestCase):
    def test_all_required_branches_run(self) -> None:
        frames = [
            FrameInput(frame_id="f1", observations=[Observation(observation_id="o1", descriptor="chair", geometry_key="g-chair")]),
            FrameInput(frame_id="f2", observations=[Observation(observation_id="o2", descriptor="chair", geometry_key="g-chair")]),
        ]
        results = run_all_branches("seq-rivals", frames)
        self.assertEqual(set(results), {BRANCH_DUOGRAPH3D, BRANCH_SINGLE_LAYER, BRANCH_DENSE_EXPORT, BRANCH_COUNTERFACTUAL})
        self.assertGreater(len(results[BRANCH_DUOGRAPH3D][0].memory_nodes), 0)
        self.assertGreater(len(results[BRANCH_DENSE_EXPORT][0].memory_nodes), 0)

    def test_single_layer_rival_keeps_support_signals_for_association(self) -> None:
        frames = [
            FrameInput(
                frame_id="f1",
                observations=[
                    Observation(
                        observation_id="o1",
                        descriptor="chair",
                        geometry_key="g-chair-a",
                        repair_group_id="scene:objectA",
                        support=ObservationSupport(
                            proposal_id="p1",
                            frame_token="f1",
                            pose_token="pose:1",
                            source_kind="replica_frame",
                            support_size=0.4,
                            depth_scale=1.1,
                            appearance_key="chair",
                            continuity_key="scene:objectA",
                            geometry_support=0.6,
                        ),
                    )
                ],
            ),
            FrameInput(
                frame_id="f2",
                observations=[
                    Observation(
                        observation_id="o2",
                        descriptor="chair",
                        geometry_key="g-chair-b",
                        repair_group_id="scene:objectA",
                        support=ObservationSupport(
                            proposal_id="p2",
                            frame_token="f2",
                            pose_token="pose:2",
                            source_kind="replica_frame",
                            support_size=0.4,
                            depth_scale=1.1,
                            appearance_key="chair",
                            continuity_key="scene:objectA",
                            geometry_support=0.6,
                        ),
                    )
                ],
            ),
        ]
        result, _logger = SingleLayerRival().run_sequence(
            sequence_id="seq-support-rival",
            frames=frames,
            temporal_variant=TemporalVariant.DEVA_STYLE,
        )
        self.assertEqual(len(result.memory_nodes), 1)


if __name__ == "__main__":
    unittest.main()
