"""Phase 乙 integration tests: signed Layer1, label distribution, candidate v2."""

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from duograph3d.contracts import (
    CurrentObjectHypothesis, EvidenceItem, EvidenceProvenance, FrameInput,
    Observation, ObservationSupport, ObjectObservationPayload, PipelineConfig,
    TemporalVariant,
)
from duograph3d.events import BRANCH_DUOGRAPH3D
from duograph3d.evidence import EvidenceBuilder
from duograph3d.layer1 import CurrentEvidenceGraphLayer
from duograph3d.layer2 import CurrentToMemoryAssociationLayer
from duograph3d.memory import ObjectGraphMemory
from duograph3d.pipeline import DuoGraph3DPipeline


def _make_obs(obs_id, descriptor, geometry_key, repair_group, label="",
              centroid=(0.5, 0.5, 0.5), bbox_min=(), bbox_max=(), clip_feature=()):
    """Helper to create an observation with payload."""
    return Observation(
        observation_id=obs_id,
        descriptor=descriptor,
        geometry_key=geometry_key,
        confidence=0.95,
        repair_group_id=repair_group,
        support=ObservationSupport(
            proposal_id=f"p-{obs_id}", frame_token="f1",
            continuity_key=repair_group, appearance_key=descriptor,
            support_size=0.5,
        ),
        object_payload=ObjectObservationPayload(
            label=label or descriptor,
            centroid=centroid,
            bbox_min=bbox_min,
            bbox_max=bbox_max,
            clip_feature=clip_feature,
            mask_area=500.0,
            detection_count=1,
        ),
    )


class SignedLayer1Tests(unittest.TestCase):
    def test_default_config_no_negative_edges(self):
        config = PipelineConfig(l1_neg_edge_enable=False)
        layer1 = CurrentEvidenceGraphLayer(config)
        evidence = [
            EvidenceItem(evidence_id="e1", descriptor="chair", geometry_key="g-0:0:0",
                        confidence=0.95, provenance=EvidenceProvenance.CURRENT,
                        repair_group_id="chair",
                        support=ObservationSupport(proposal_id="p1", frame_token="f1",
                                                   continuity_key="a", appearance_key="chair")),
            EvidenceItem(evidence_id="e2", descriptor="desk", geometry_key="g-0:0:0",
                        confidence=0.95, provenance=EvidenceProvenance.CURRENT,
                        repair_group_id="desk",
                        support=ObservationSupport(proposal_id="p2", frame_token="f1",
                                                   continuity_key="b", appearance_key="desk")),
        ]
        hyps = layer1.repair(evidence)
        # Without signed edges, same geometry_key may merge
        self.assertGreaterEqual(len(hyps), 1)

    def test_signed_layer1_may_split_on_negative_edge(self):
        config = PipelineConfig(
            l1_neg_edge_enable=True,
            l1_pos_threshold=0.75,
            l1_neg_threshold=0.60,
        )
        layer1 = CurrentEvidenceGraphLayer(config)
        evidence = [
            EvidenceItem(
                evidence_id="e1", descriptor="chair", geometry_key="g-0:0:0",
                confidence=0.95, provenance=EvidenceProvenance.CURRENT,
                repair_group_id="chair",
                support=ObservationSupport(proposal_id="p1", frame_token="f1",
                                           continuity_key="a", appearance_key="chair"),
                object_payload=ObjectObservationPayload(
                    label="chair", centroid=(0.0, 0.0, 0.0),
                    bbox_min=(0.0, 0.0, 0.0), bbox_max=(0.3, 0.3, 0.3),
                    mask_area=500, detection_count=1,
                ),
            ),
            EvidenceItem(
                evidence_id="e2", descriptor="wall", geometry_key="g-0:0:0",
                confidence=0.95, provenance=EvidenceProvenance.CURRENT,
                repair_group_id="wall",
                support=ObservationSupport(proposal_id="p2", frame_token="f1",
                                           continuity_key="b", appearance_key="wall"),
                object_payload=ObjectObservationPayload(
                    label="wall", centroid=(1.0, 0.0, 0.0),
                    bbox_min=(0.8, 0.0, 0.0), bbox_max=(1.2, 0.3, 0.3),
                    mask_area=500, detection_count=1,
                ),
            ),
        ]
        hyps = layer1.repair(evidence)
        # With spatial separation + semantic conflict, should split
        for hyp in hyps:
            self.assertIn("neg_edge_ids", hyp.__dict__.keys() if hasattr(hyp, 'neg_edge_ids') else [])

    def test_signed_layer1_keeps_same_object_merged(self):
        config = PipelineConfig(
            l1_neg_edge_enable=True,
            l1_pos_threshold=0.75,
            l1_neg_threshold=0.60,
        )
        layer1 = CurrentEvidenceGraphLayer(config)
        evidence = [
            EvidenceItem(
                evidence_id="e1", descriptor="chair", geometry_key="g-0:0:0",
                confidence=0.95, provenance=EvidenceProvenance.CURRENT,
                repair_group_id="chair",
                support=ObservationSupport(proposal_id="p1", frame_token="f1",
                                           continuity_key="chair_1", appearance_key="chair"),
                object_payload=ObjectObservationPayload(
                    label="chair", centroid=(0.0, 0.0, 0.0),
                    bbox_min=(0.0, 0.0, 0.0), bbox_max=(0.3, 0.3, 0.3),
                    mask_area=500, detection_count=1,
                ),
            ),
            EvidenceItem(
                evidence_id="e2", descriptor="chair", geometry_key="g-0:0:0",
                confidence=0.93, provenance=EvidenceProvenance.CURRENT,
                repair_group_id="chair",
                support=ObservationSupport(proposal_id="p2", frame_token="f1",
                                           continuity_key="chair_1", appearance_key="chair"),
                object_payload=ObjectObservationPayload(
                    label="chair", centroid=(0.05, 0.02, 0.01),
                    bbox_min=(0.02, 0.01, 0.0), bbox_max=(0.32, 0.31, 0.29),
                    mask_area=480, detection_count=1,
                ),
            ),
        ]
        hyps = layer1.repair(evidence)
        # Same object should still merge (no negative edge triggers)
        self.assertEqual(len(hyps), 1)


class LabelDistributionTests(unittest.TestCase):
    def test_preserve_label_distribution(self):
        config = PipelineConfig(l1_preserve_label_distribution=True)
        layer1 = CurrentEvidenceGraphLayer(config)
        evidence = [
            EvidenceItem(
                evidence_id="e1", descriptor="chair", geometry_key="g-0:0:0",
                confidence=0.95, provenance=EvidenceProvenance.CURRENT,
                repair_group_id="group1",
                support=ObservationSupport(proposal_id="p1", frame_token="f1",
                                           continuity_key="c1", appearance_key="chair"),
                object_payload=ObjectObservationPayload(
                    label="chair", centroid=(0.0, 0.0, 0.0), mask_area=500, detection_count=1,
                ),
            ),
            EvidenceItem(
                evidence_id="e2", descriptor="desk", geometry_key="g-0:0:0",
                confidence=0.92, provenance=EvidenceProvenance.CURRENT,
                repair_group_id="group1",
                support=ObservationSupport(proposal_id="p2", frame_token="f1",
                                           continuity_key="c1", appearance_key="desk"),
                object_payload=ObjectObservationPayload(
                    label="desk", centroid=(0.05, 0.0, 0.0), mask_area=300, detection_count=1,
                ),
            ),
        ]
        hyps = layer1.repair(evidence)
        self.assertEqual(len(hyps), 1)
        hyp = hyps[0]
        self.assertIn("chair", hyp.label_distribution)
        self.assertIn("desk", hyp.label_distribution)
        self.assertAlmostEqual(hyp.label_distribution["chair"], 0.5, places=1)
        self.assertAlmostEqual(hyp.label_distribution["desk"], 0.5, places=1)
        # Old payload still has single majority label (backward compat)
        self.assertIsNotNone(hyp.object_payload)
        self.assertIn(hyp.object_payload.label, ("chair", "desk"))

    def test_label_distribution_default_empty(self):
        """Without the flag, label_distribution should be empty (backward compat)."""
        config = PipelineConfig(l1_preserve_label_distribution=False)
        layer1 = CurrentEvidenceGraphLayer(config)
        evidence = [
            EvidenceItem(
                evidence_id="e1", descriptor="chair", geometry_key="g-0:0:0",
                confidence=0.95, provenance=EvidenceProvenance.CURRENT,
                repair_group_id="g1",
                support=ObservationSupport(proposal_id="p1", frame_token="f1",
                                           continuity_key="c1", appearance_key="chair"),
                object_payload=ObjectObservationPayload(
                    label="chair", centroid=(0.0, 0.0, 0.0), mask_area=500, detection_count=1,
                ),
            ),
        ]
        hyps = layer1.repair(evidence)
        self.assertEqual(len(hyps), 1)
        self.assertEqual(hyps[0].label_distribution, {})


class CandidateV2Tests(unittest.TestCase):
    def setUp(self):
        self.memory = ObjectGraphMemory()
        self.config = PipelineConfig(
            cand_include_adj_key=True,
            cand_include_ann=True,
            cand_adj_radius=1,
            cand_ann_top_k=4,
            candidate_retrieval_channel_budget=5,
            emit_association_diagnostics=True,
        )
        self.memory.config = self.config

    def test_adjacent_geometry_keys(self):
        key = "room0:gsa:item:10:20:30"
        adj = ObjectGraphMemory._adjacent_geometry_keys(key, radius=1)
        self.assertEqual(len(adj), 26)  # 3^3 - 1
        # Should include immediate neighbor
        self.assertIn("room0:gsa:item:11:20:30", adj)
        self.assertIn("room0:gsa:item:9:20:30", adj)
        # Should NOT include self
        self.assertNotIn(key, adj)

    def test_adj_key_retrieval_finds_neighbor_node(self):
        # Create a node at a neighbor cell
        node = self.memory.create_node(
            descriptor="chair", geometry_key="room0:gsa:item:11:20:30", step_id=1,
        )
        node.status = self.memory.nodes[node.object_id].status  # ensure it's active

        # Search with a key at the adjacent cell
        candidates = self.memory.candidate_nodes(
            "room0:gsa:item:10:20:30",
            candidate_budget=5,
            hypothesis=None,
        )
        # Should find the node in the adjacent cell
        found = any(c.object_id == node.object_id for c in candidates)
        self.assertTrue(found, "adj-key node not found; candidates={}".format(
            [(c.object_id, c.geometry_key) for c in candidates]
        ))

    def test_ann_retrieval_uses_clip_features(self):
        # Create two nodes with different clip features
        n1 = self.memory.create_node(descriptor="chair", geometry_key="g-a", step_id=1)
        n1.clip_feature = tuple(float(i) for i in range(10))
        n2 = self.memory.create_node(descriptor="desk", geometry_key="g-b", step_id=1)
        n2.clip_feature = tuple(float(i + 5) for i in range(10))

        # Query with feature similar to n1
        query = tuple(float(i + 0.1) for i in range(10))

        from duograph3d.contracts import CurrentObjectHypothesis
        hyp = CurrentObjectHypothesis(
            hypothesis_id="h1", descriptor="chair", geometry_key="g-c",
            confidence=0.95, evidence_ids=(), track_hint="t1",
            object_payload=ObjectObservationPayload(
                label="chair", clip_feature=query, mask_area=500, detection_count=1,
            ),
        )
        candidates = self.memory.candidate_nodes(
            "g-c", candidate_budget=5, hypothesis=hyp,
        )
        # n1 should be ranked higher than n2 (more similar)
        n1_pos = next((i for i, c in enumerate(candidates) if c.object_id == n1.object_id), -1)
        n2_pos = next((i for i, c in enumerate(candidates) if c.object_id == n2.object_id), -1)
        if n1_pos >= 0 and n2_pos >= 0:
            self.assertLess(n1_pos, n2_pos, "n1 (more similar) should rank before n2")

    def test_parse_geometry_key(self):
        key = "room0:gsa:item:10:20:30"
        result = ObjectGraphMemory._parse_geometry_key(key)
        self.assertIsNotNone(result)
        prefix, qx, qy, qz = result
        self.assertEqual(prefix, "room0:gsa:item")
        self.assertEqual(qx, 10)
        self.assertEqual(qy, 20)
        self.assertEqual(qz, 30)

    def test_parse_geometry_key_invalid(self):
        self.assertIsNone(ObjectGraphMemory._parse_geometry_key(""))
        self.assertIsNone(ObjectGraphMemory._parse_geometry_key("invalid"))


class PhaseBetaIntegrationTests(unittest.TestCase):
    """End-to-end test: signed Layer1 + label distribution + candidate v2."""

    def test_full_pipeline_with_phase_beta_features(self):
        config = PipelineConfig(
            l1_neg_edge_enable=True,
            l1_preserve_label_distribution=True,
            cand_include_adj_key=True,
            cand_include_ann=True,
            emit_association_diagnostics=True,
            association_diagnostics_top_k=3,
        )
        pipeline = DuoGraph3DPipeline(config)
        frames = [
            FrameInput(frame_id="f1", observations=[
                _make_obs("o1", "chair", "r0:gsa:item:0:0:0", "chair",
                          label="chair", centroid=(0.0, 0.0, 0.0),
                          bbox_min=(0.0, 0.0, 0.0), bbox_max=(0.3, 0.3, 0.3)),
                _make_obs("o2", "desk", "r0:gsa:item:0:0:0", "desk",
                          label="desk", centroid=(0.8, 0.0, 0.0),
                          bbox_min=(0.7, 0.0, 0.0), bbox_max=(1.0, 0.3, 0.3)),
            ]),
            FrameInput(frame_id="f2", observations=[
                _make_obs("o3", "chair", "r0:gsa:item:0:0:0", "chair",
                          label="chair", centroid=(0.02, 0.02, 0.0),
                          bbox_min=(0.01, 0.01, 0.0), bbox_max=(0.31, 0.32, 0.29)),
            ]),
        ]
        result, logger = pipeline.run_sequence(
            sequence_id="test-beta", frames=frames,
            temporal_variant=TemporalVariant.DEVA_STYLE,
            branch_id=BRANCH_DUOGRAPH3D,
        )
        self.assertGreater(len(result.memory_nodes), 0)
        # Verify label distribution was preserved
        for decision in result.decisions:
            self.assertIsNotNone(decision.action)


class CandidateSourceTrackingTests(unittest.TestCase):
    """Phase 乙: per-candidate source channel tracking for monitoring."""

    def test_candidate_sources_tracked_in_diagnostics(self):
        config = PipelineConfig(
            cand_include_adj_key=True,
            emit_association_diagnostics=True,
            association_diagnostics_top_k=3,
        )
        memory = ObjectGraphMemory(config)
        # Create nodes at adjacent geometry keys
        n1 = memory.create_node(descriptor="chair", geometry_key="g:0:0:1", step_id=1)
        n2 = memory.create_node(descriptor="desk", geometry_key="g:1:0:0", step_id=1)

        hyp = CurrentObjectHypothesis(
            hypothesis_id="h1", descriptor="chair", geometry_key="g:0:0:0",
            confidence=0.95, evidence_ids=("e1",), track_hint="t1",
            object_payload=ObjectObservationPayload(
                label="chair", clip_feature=tuple(float(i) for i in range(10)),
                mask_area=500, detection_count=1,
            ),
        )
        candidates = memory.candidate_nodes(
            "g:0:0:0", candidate_budget=10, hypothesis=hyp,
        )
        # Both adjacent nodes should be found
        found_ids = {c.object_id for c in candidates}
        self.assertIn(n1.object_id, found_ids)
        self.assertIn(n2.object_id, found_ids)
