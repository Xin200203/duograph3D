"""Phase 丙 integration tests: tentative fragments, promotion gate, working/stable memory."""

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from duograph3d.contracts import (
    CurrentObjectHypothesis, EvidenceProvenance, FrameInput,
    ObjectObservationPayload, Observation, ObservationSupport, PipelineConfig,
    TemporalVariant, FragmentStatus,
)
from duograph3d.events import BRANCH_DUOGRAPH3D
from duograph3d.pipeline import DuoGraph3DPipeline
from duograph3d.memory import ObjectGraphMemory


def _make_obs(obs_id, descriptor, geom_key, repair_group, label="", step=1):
    return Observation(
        observation_id=obs_id, descriptor=descriptor,
        geometry_key=geom_key, confidence=0.95,
        repair_group_id=repair_group,
        support=ObservationSupport(
            proposal_id=f"p-{obs_id}", frame_token=f"f{step}",
            continuity_key=repair_group, appearance_key=descriptor,
            support_size=0.5, geometry_support=0.7,
        ),
        object_payload=ObjectObservationPayload(
            label=label or descriptor, centroid=(0.0, 0.0, float(step) * 0.1),
            mask_area=500, detection_count=1,
            clip_feature=tuple(float(i % 10) for i in range(10)),
        ),
    )


class TentativeFragmentTests(unittest.TestCase):
    def test_tentative_fragment_created_instead_of_direct_birth(self):
        config = PipelineConfig(
            enable_tentative_fragments=True,
            promotion_min_hits=3,
            emit_association_diagnostics=True,
        )
        pipeline = DuoGraph3DPipeline(config)
        frames = [
            FrameInput(frame_id="f1", observations=[
                _make_obs("o1", "chair", "g:0:0:0", "chair", step=1),
            ]),
        ]
        result, logger = pipeline.run_sequence(
            sequence_id="test", frames=frames,
            temporal_variant=TemporalVariant.NAIVE_FRAMEWISE,
            branch_id=BRANCH_DUOGRAPH3D,
        )
        # With tentative enabled, should NOT have birth_commit (direct birth)
        births = [r for r in logger.records if r.event_type == "birth_commit"]
        tentatives = [r for r in logger.records if r.event_type == "tentative_fragment_created"]
        self.assertEqual(len(births), 0, "No direct births expected with tentative mode")
        self.assertEqual(len(tentatives), 1, "Expected one tentative fragment")
        self.assertEqual(result.decisions[0].action, "tentative_birth")

    def test_tentative_fragment_promotes_after_enough_hits(self):
        config = PipelineConfig(
            enable_tentative_fragments=True,
            promotion_min_hits=2,
            emit_association_diagnostics=True,
        )
        pipeline = DuoGraph3DPipeline(config)
        frames = [
            FrameInput(frame_id="f1", observations=[
                _make_obs("o1", "chair", "g:0:0:0", "chair", step=1),
            ]),
            FrameInput(frame_id="f2", observations=[
                _make_obs("o2", "chair", "g:0:0:0", "chair", step=2),
            ]),
        ]
        result, logger = pipeline.run_sequence(
            sequence_id="test", frames=frames,
            temporal_variant=TemporalVariant.NAIVE_FRAMEWISE,
            branch_id=BRANCH_DUOGRAPH3D,
        )
        tentatives = [r for r in logger.records if r.event_type == "tentative_fragment_created"]
        promotions = [r for r in logger.records if r.event_type == "fragment_promotion"]
        births = [r for r in logger.records if r.event_type == "birth_commit"]
        self.assertEqual(len(tentatives), 1, "Should create 1 tentative fragment")
        self.assertEqual(len(promotions), 1, "Should promote after 2 hits")
        self.assertEqual(len(births), 1, "Should have 1 birth_commit from promotion")

    def test_direct_birth_when_tentative_disabled(self):
        config = PipelineConfig(
            enable_tentative_fragments=False,
            emit_association_diagnostics=True,
        )
        pipeline = DuoGraph3DPipeline(config)
        frames = [
            FrameInput(frame_id="f1", observations=[
                _make_obs("o1", "chair", "g:0:0:0", "chair", step=1),
            ]),
        ]
        result, logger = pipeline.run_sequence(
            sequence_id="test", frames=frames,
            temporal_variant=TemporalVariant.NAIVE_FRAMEWISE,
            branch_id=BRANCH_DUOGRAPH3D,
        )
        births = [r for r in logger.records if r.event_type == "birth_commit"]
        tentatives = [r for r in logger.records if r.event_type == "tentative_fragment_created"]
        self.assertEqual(len(births), 1, "Direct birth expected when disabled")
        self.assertEqual(len(tentatives), 0, "No tentative fragments expected")


class StableMemoryTests(unittest.TestCase):
    def test_stable_prototype_update_via_ema(self):
        memory = ObjectGraphMemory(PipelineConfig(
            enable_stable_memory=True,
            stable_ema_alpha=0.05,
        ))
        node = memory.create_node(descriptor="chair", geometry_key="g:0", step_id=1)
        feature = tuple(float(i) for i in range(10))
        memory._update_stable_prototype(node, feature, key="clip")
        self.assertEqual(len(node.stable_clip_feature), 10)
        self.assertEqual(node.stable_write_count, 1)

    def test_stable_write_gate_low_margin_rejected(self):
        memory = ObjectGraphMemory(PipelineConfig(
            enable_stable_memory=True,
            stable_write_margin=0.25,
        ))
        ok, reason = memory.stable_write_gate(
            margin=0.1, conflict_count=0, has_identity=True,
        )
        self.assertFalse(ok)
        self.assertEqual(reason, "low_margin")

    def test_stable_write_gate_has_conflicts_rejected(self):
        memory = ObjectGraphMemory(PipelineConfig(
            enable_stable_memory=True,
            stable_write_margin=0.25,
        ))
        ok, reason = memory.stable_write_gate(
            margin=0.5, conflict_count=1, has_identity=True,
        )
        self.assertFalse(ok)
        self.assertEqual(reason, "has_conflicts")

    def test_stable_write_gate_passes(self):
        memory = ObjectGraphMemory(PipelineConfig(
            enable_stable_memory=True,
            stable_write_margin=0.25,
        ))
        ok, reason = memory.stable_write_gate(
            margin=0.5, conflict_count=0, has_identity=True,
        )
        self.assertTrue(ok)


class PromotionGateTests(unittest.TestCase):
    def test_promotion_gate_insufficient_hits(self):
        memory = ObjectGraphMemory(PipelineConfig(
            enable_tentative_fragments=True,
            promotion_min_hits=3,
        ))
        frag = memory.create_tentative_fragment(
            descriptor="chair", geometry_key="g:0", step_id=1,
        )
        frag.hits = 1
        ok, reason = memory.promotion_gate(frag)
        self.assertFalse(ok)
        self.assertEqual(reason, "insufficient_hits")

    def test_promotion_gate_passes_with_enough_hits(self):
        memory = ObjectGraphMemory(PipelineConfig(
            enable_tentative_fragments=True,
            promotion_min_hits=2,
            promotion_min_sc=0.0,
            promotion_min_gc=0.0,
            promotion_max_conflict_rate=1.0,
        ))
        frag = memory.create_tentative_fragment(
            descriptor="chair", geometry_key="g:0", step_id=1,
        )
        frag.hits = 3
        frag.self_consistency = 0.8
        frag.geometry_consistency = 0.7
        ok, reason = memory.promotion_gate(frag)
        self.assertTrue(ok, f"Expected promotion, got: {reason}")


class PhaseGammaIntegrationTests(unittest.TestCase):
    """End-to-end: tentative + promotion + stable memory together."""

    def test_multi_frame_tentative_promotion_cycle(self):
        config = PipelineConfig(
            enable_tentative_fragments=True,
            promotion_min_hits=3,
            enable_stable_memory=True,
            stable_write_margin=0.2,
            stable_ema_alpha=0.05,
            emit_association_diagnostics=True,
        )
        pipeline = DuoGraph3DPipeline(config)
        frames = [
            FrameInput(frame_id=f"f{i}", observations=[
                _make_obs(f"o{i}", "chair", "g:0:0:0", "chair", step=i),
            ])
            for i in range(1, 6)
        ]
        result, logger = pipeline.run_sequence(
            sequence_id="test-gamma", frames=frames,
            temporal_variant=TemporalVariant.DEVA_STYLE,
            branch_id=BRANCH_DUOGRAPH3D,
        )
        # Should have 1 tentative at frame 1, promotion by frame 3
        tentatives = [r for r in logger.records if r.event_type == "tentative_fragment_created"]
        promotions = [r for r in logger.records if r.event_type == "fragment_promotion"]
        births = [r for r in logger.records if r.event_type == "birth_commit"]
        self.assertEqual(len(tentatives), 1)
        self.assertEqual(len(promotions), 1)
        self.assertEqual(len(births), 1)
        self.assertGreaterEqual(len(result.memory_nodes), 1)
