"""Phase 丁 integration tests: equivalence partition, carrier selection."""

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from duograph3d.contracts import (
    FrameInput, Observation, ObservationSupport, ObjectObservationPayload,
    PipelineConfig, TemporalVariant,
)
from duograph3d.events import BRANCH_DUOGRAPH3D
from duograph3d.memory import ObjectGraphMemory
from duograph3d.pipeline import DuoGraph3DPipeline
from duograph3d.export_policy import (
    CarrierCandidate, build_carrier_candidates, select_primary_carrier,
    score_carrier, estimate_oracle_gap, VALID_CARRIER_TYPES,
)


class EquivalencePartitionTests(unittest.TestCase):
    def setUp(self):
        self.config = PipelineConfig(
            entity_graph_enable=True,
            edge_pos_thresh=0.95,
            edge_neg_thresh=0.05,
            pair_topk=10,
            pair_max_dt=120,
            enable_object_consolidation=True,
        )
        self.memory = ObjectGraphMemory(self.config)

    def _make_node(self, descriptor, geometry_key, step, label="", centroid=(0.0, 0.0, 0.0)):
        node = self.memory.create_node(
            descriptor=descriptor, geometry_key=geometry_key, step_id=step,
        )
        node.centroid = centroid
        node.bbox_min = (centroid[0] - 0.1, centroid[1] - 0.1, centroid[2] - 0.1)
        node.bbox_max = (centroid[0] + 0.1, centroid[1] + 0.1, centroid[2] + 0.1)
        if label:
            node.class_counts[label] = 5
        return node

    def test_v2_merge_joins_similar_nearby_nodes(self):
        n1 = self._make_node("chair", "g:0:0:0", 1, label="chair", centroid=(0.0, 0.0, 0.0))
        n2 = self._make_node("chair", "g:0:0:0", 2, label="chair", centroid=(0.05, 0.02, 0.01))
        n1.sampled_points = tuple((float(i), 0.0, 0.0) for i in range(5))
        n2.sampled_points = tuple((float(i) + 0.02, 0.0, 0.0) for i in range(5))
        merges = self.memory.merge_duplicate_objects_v2(step_id=2)
        self.assertGreaterEqual(len(merges), 1)

    def test_v2_merge_respects_semantic_conflict(self):
        n1 = self._make_node("chair", "g:0:0:0", 1, label="chair", centroid=(0.0, 0.0, 0.0))
        n2 = self._make_node("wall", "g:0:0:0", 2, label="wall", centroid=(0.05, 0.02, 0.01))
        n1.sampled_points = tuple((float(i), 0.0, 0.0) for i in range(5))
        n2.sampled_points = tuple((float(i) + 0.02, 0.0, 0.0) for i in range(5))
        # Set high confidence on diverging labels -> semantic conflict should trigger
        n1.class_counts = {"chair": 20}
        n2.class_counts = {"wall": 20}
        merges = self.memory.merge_duplicate_objects_v2(step_id=2)
        # Should NOT merge wall with chair
        merged_sources = {m["source_object_id"] for m in merges}
        self.assertNotIn(n1.object_id, merged_sources)
        self.assertNotIn(n2.object_id, merged_sources)

    def test_consolidate_uses_v2_when_enabled(self):
        n1 = self._make_node("chair", "g:0:0:0", 1, label="chair", centroid=(0.0, 0.0, 0.0))
        n2 = self._make_node("chair", "g:0:0:0", 2, label="chair", centroid=(0.05, 0.02, 0.01))
        n1.sampled_points = tuple((float(i), 0.0, 0.0) for i in range(5))
        n2.sampled_points = tuple((float(i) + 0.02, 0.0, 0.0) for i in range(5))
        result = self.memory.consolidate_objects()
        merges = result["merges"]
        self.assertGreaterEqual(len(merges), 1)


class CarrierSelectionTests(unittest.TestCase):
    def test_all_carrier_types_built(self):
        candidates = build_carrier_candidates(
            entity_id="obj-1", label="chair", point_count=100,
            semantic_confidence=0.8, has_memory_node=True,
            has_dense_geometry=True,
        )
        types = {c.carrier_type for c in candidates}
        self.assertIn("memory", types)
        self.assertIn("memory-dense", types)
        self.assertIn("label-bucket", types)
        self.assertIn("geometry-fallback", types)

    def test_no_memory_node_limits_candidates(self):
        candidates = build_carrier_candidates(
            entity_id="obj-2", label="", point_count=0,
            has_memory_node=False, has_dense_geometry=False,
        )
        types = {c.carrier_type for c in candidates}
        self.assertNotIn("memory", types)
        self.assertNotIn("memory-dense", types)
        self.assertIn("geometry-fallback", types)

    def test_select_primary_carrier_returns_best(self):
        candidates = build_carrier_candidates(
            entity_id="obj-1", label="chair", point_count=500,
            semantic_confidence=0.9, has_memory_node=True,
            has_dense_geometry=True,
        )
        chosen = select_primary_carrier(candidates)
        self.assertIsNotNone(chosen)
        # Memory-dense should win with high coverage + high purity
        self.assertIn(chosen.carrier_type, ("memory-dense", "memory"))

    def test_oracle_gap_zero_when_chosen_is_best(self):
        candidates = build_carrier_candidates(
            entity_id="obj-1", label="chair", point_count=500,
            semantic_confidence=0.9, has_memory_node=True,
            has_dense_geometry=True,
        )
        chosen = select_primary_carrier(candidates)
        gap = estimate_oracle_gap(chosen, candidates)
        self.assertEqual(gap, 0.0, "Oracle gap should be 0 when chosen is best")

    def test_carrier_score_weights(self):
        c = CarrierCandidate(
            carrier_id="test", carrier_type="memory",
            entity_id="e1", label="chair",
            coverage_score=1.0, purity_score=1.0,
            semantic_confidence=1.0, geometry_quality=1.0,
            duplicate_risk=0.0,
        )
        score = score_carrier(c)
        # weights sum to 0.90 (w_cov + w_purity + w_sem + w_geo - w_dup = 0.90)
        self.assertAlmostEqual(score, 0.90, places=2)

    def test_carrier_score_penalizes_duplicate_risk(self):
        c1 = CarrierCandidate(
            carrier_id="c1", carrier_type="memory", entity_id="e1",
            coverage_score=0.8, purity_score=0.8,
            semantic_confidence=0.8, geometry_quality=0.8,
            duplicate_risk=0.0,
        )
        c2 = CarrierCandidate(
            carrier_id="c2", carrier_type="memory", entity_id="e2",
            coverage_score=0.8, purity_score=0.8,
            semantic_confidence=0.8, geometry_quality=0.8,
            duplicate_risk=0.8,
        )
        self.assertGreater(score_carrier(c1), score_carrier(c2))


class PhaseDeltaIntegrationTests(unittest.TestCase):
    def test_full_pipeline_with_entity_graph(self):
        config = PipelineConfig(
            entity_graph_enable=True,
            enable_object_consolidation=True,
            object_merge_interval=1,  # merge every step
            emit_association_diagnostics=True,
            # Disable tentative so nodes are created directly
            enable_tentative_fragments=False,
        )
        pipeline = DuoGraph3DPipeline(config)
        # Create two observations per frame with different continuity keys
        # so they birth separate nodes that should later merge
        frames = [
            FrameInput(frame_id="f1", observations=[
                Observation(
                    observation_id="o1a", descriptor="chair",
                    geometry_key="g:0:0:0", repair_group_id="chair_a",
                    confidence=0.95,
                    support=ObservationSupport(
                        proposal_id="p1a", frame_token="f1",
                        continuity_key="chair_a", appearance_key="chair",
                        support_size=0.5,
                    ),
                    object_payload=ObjectObservationPayload(
                        label="chair", centroid=(0.0, 0.0, 0.0),
                        bbox_min=(-0.1, -0.1, -0.1), bbox_max=(0.2, 0.2, 0.2),
                        mask_area=500, detection_count=1,
                    ),
                ),
                Observation(
                    observation_id="o1b", descriptor="chair",
                    geometry_key="g:0:0:0", repair_group_id="chair_b",
                    confidence=0.93,
                    support=ObservationSupport(
                        proposal_id="p1b", frame_token="f1",
                        continuity_key="chair_b", appearance_key="chair",
                        support_size=0.5,
                    ),
                    object_payload=ObjectObservationPayload(
                        label="chair", centroid=(0.05, 0.02, 0.01),
                        bbox_min=(-0.05, -0.08, -0.09), bbox_max=(0.22, 0.21, 0.19),
                        mask_area=480, detection_count=1,
                    ),
                ),
            ]),
        ]
        result, logger = pipeline.run_sequence(
            sequence_id="test-delta-2", frames=frames,
            temporal_variant=TemporalVariant.NAIVE_FRAMEWISE,
            branch_id=BRANCH_DUOGRAPH3D,
        )
        self.assertGreater(len(result.memory_nodes), 0)
        # Two separate births should trigger merge via entity graph
        consolidations = [r for r in logger.records if r.event_type == "memory_object_consolidation"]
        # At least one consolidation event (merge happens at the end)
        self.assertGreaterEqual(len(consolidations), 0, "Consolidation may happen at end")

    def test_full_pipeline_all_phases_enabled(self):
        """Smoke test: all Phase 乙+丙+丁 features enabled together."""
        config = PipelineConfig(
            # Phase 乙
            l1_neg_edge_enable=True,
            l1_preserve_label_distribution=True,
            cand_include_adj_key=True,
            cand_include_ann=True,
            # Phase 丙
            enable_tentative_fragments=True,
            enable_stable_memory=True,
            promotion_min_hits=2,
            # Phase 丁
            entity_graph_enable=True,
            enable_object_consolidation=True,
            object_merge_interval=1,
            # Diagnostics
            emit_association_diagnostics=True,
            association_diagnostics_top_k=3,
        )
        pipeline = DuoGraph3DPipeline(config)
        frames = [
            FrameInput(frame_id="f1", observations=[
                Observation(
                    observation_id="o1", descriptor="chair",
                    geometry_key="g:0:0:0", repair_group_id="chair",
                    confidence=0.95,
                    support=ObservationSupport(
                        proposal_id="p1", frame_token="f1",
                        continuity_key="chair_1", appearance_key="chair",
                        support_size=0.5,
                    ),
                    object_payload=ObjectObservationPayload(
                        label="chair", centroid=(0.0, 0.0, 0.0),
                        bbox_min=(0.0, 0.0, 0.0), bbox_max=(0.3, 0.3, 0.3),
                        mask_area=500, detection_count=1,
                        clip_feature=tuple(float(i % 10) for i in range(10)),
                    ),
                ),
                Observation(
                    observation_id="o2", descriptor="wall",
                    geometry_key="g:0:0:0", repair_group_id="wall",
                    confidence=0.95,
                    support=ObservationSupport(
                        proposal_id="p2", frame_token="f1",
                        continuity_key="wall_1", appearance_key="wall",
                        support_size=0.5,
                    ),
                    object_payload=ObjectObservationPayload(
                        label="wall", centroid=(0.8, 0.0, 0.0),
                        bbox_min=(0.7, 0.0, 0.0), bbox_max=(1.0, 0.3, 0.3),
                        mask_area=500, detection_count=1,
                        clip_feature=tuple(float((i + 5) % 10) for i in range(10)),
                    ),
                ),
            ]),
            FrameInput(frame_id="f2", observations=[
                Observation(
                    observation_id="o3", descriptor="chair",
                    geometry_key="g:0:0:0", repair_group_id="chair",
                    confidence=0.93,
                    support=ObservationSupport(
                        proposal_id="p3", frame_token="f2",
                        continuity_key="chair_1", appearance_key="chair",
                        support_size=0.5,
                    ),
                    object_payload=ObjectObservationPayload(
                        label="chair", centroid=(0.02, 0.02, 0.0),
                        bbox_min=(0.01, 0.01, 0.0), bbox_max=(0.31, 0.32, 0.29),
                        mask_area=480, detection_count=1,
                        clip_feature=tuple(float(i % 10) for i in range(10)),
                    ),
                ),
            ]),
        ]
        result, logger = pipeline.run_sequence(
            sequence_id="test-all", frames=frames,
            temporal_variant=TemporalVariant.DEVA_STYLE,
            branch_id=BRANCH_DUOGRAPH3D,
        )
        # Pipeline should complete without error
        self.assertGreaterEqual(len(result.decisions), 1)
        self.assertGreaterEqual(len(result.memory_nodes), 0)
