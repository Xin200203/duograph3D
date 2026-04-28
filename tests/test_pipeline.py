import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from duograph3d.contracts import (
    CurrentObjectHypothesis,
    EvidenceProvenance,
    EvidenceItem,
    FrameInput,
    HistoryCandidate,
    Observation,
    ObjectObservationPayload,
    ObjectStatus,
    ObservationSupport,
    PipelineConfig,
    TemporalVariant,
)
from duograph3d.evidence import EvidenceBuilder
from duograph3d.layer1 import CurrentEvidenceGraphLayer
from duograph3d.layer2 import CurrentToMemoryAssociationLayer
from duograph3d.memory import ObjectGraphMemory
from duograph3d.metrics import summarize_run
from duograph3d.pipeline import DuoGraph3DPipeline
from duograph3d.events import EventLogger


class PipelineTests(unittest.TestCase):
    def test_layer1_does_not_mutate_memory(self) -> None:
        memory = ObjectGraphMemory()
        frame = FrameInput(
            frame_id="f1",
            observations=[Observation(observation_id="o1", descriptor="chair", geometry_key="g-chair", repair_group_id="chair")],
        )
        evidence = EvidenceBuilder().build(frame, memory=memory, temporal_variant=TemporalVariant.NAIVE_FRAMEWISE)
        hypotheses = CurrentEvidenceGraphLayer().repair(evidence)
        self.assertEqual(memory.nodes, {})
        self.assertEqual(len(hypotheses), 1)
        self.assertFalse(any("obj-" in evidence_id for evidence_id in hypotheses[0].evidence_ids))

    def test_pipeline_births_memory_node_via_layer2(self) -> None:
        pipeline = DuoGraph3DPipeline()
        frame = FrameInput(
            frame_id="f1",
            observations=[Observation(observation_id="o1", descriptor="chair", geometry_key="g-chair", repair_group_id="chair")],
        )
        result, logger = pipeline.run_sequence(sequence_id="seq", frames=[frame], temporal_variant=TemporalVariant.NAIVE_FRAMEWISE)
        self.assertEqual(len(result.memory_nodes), 1)
        self.assertEqual(logger.count("birth_commit"), 1)

    def test_ambiguous_birth_logs_memory_authority(self) -> None:
        pipeline = DuoGraph3DPipeline()
        frame = FrameInput(
            frame_id="f1",
            observations=[
                Observation(observation_id="o1", descriptor="chair", geometry_key="g-chair", repair_group_id="chair"),
                Observation(observation_id="o2", descriptor="desk", geometry_key="g-chair-alt", repair_group_id="chair", confidence=0.5),
            ],
        )
        _result, logger = pipeline.run_sequence(sequence_id="seq-amb", frames=[frame], temporal_variant=TemporalVariant.NAIVE_FRAMEWISE)
        self.assertEqual(logger.count("memory_authority_used"), 1)

    def test_layer2_can_associate_from_observation_support(self) -> None:
        memory = ObjectGraphMemory()
        node = memory.create_node(descriptor="chair", geometry_key="g-old", step_id=1)
        node.continuity_key_recent = "scene:objectA"
        node.appearance_key_recent = "chair"
        node.avg_support_size = 0.5
        node.avg_depth_scale = 1.1
        node.avg_geometry_support = 0.6
        item = EvidenceItem(
            evidence_id="e1",
            descriptor="chair",
            geometry_key="g-new",
            confidence=0.9,
            provenance=EvidenceProvenance.CURRENT,
            repair_group_id="scene:objectA",
            support=ObservationSupport(
                proposal_id="p1",
                frame_token="f1",
                pose_token="pose:1",
                source_kind="replica_frame",
                support_size=0.5,
                depth_scale=1.1,
                appearance_key="chair",
                continuity_key="scene:objectA",
                geometry_support=0.6,
            ),
        )
        hypothesis = CurrentEvidenceGraphLayer().repair([item])[0]
        decisions = CurrentToMemoryAssociationLayer().update(
            sequence_id="seq-support",
            step_id=2,
            branch_id="duograph3d_full",
            hypotheses=[hypothesis],
            memory=memory,
            logger=EventLogger(),
        )
        self.assertEqual(decisions[0].action, "associate")
        self.assertEqual(decisions[0].object_id, node.object_id)

    def test_propagation_keepalive_misses_uses_config(self) -> None:
        memory = ObjectGraphMemory()
        node = memory.create_node(descriptor="chair", geometry_key="g-chair", step_id=1)
        node.miss_count = 1
        frame = FrameInput(frame_id="f2", observations=[])
        evidence = EvidenceBuilder(PipelineConfig(propagation_keepalive_misses=0)).build(
            frame,
            memory=memory,
            temporal_variant=TemporalVariant.DEVA_STYLE,
        )
        self.assertEqual(evidence, [])

    def test_layer2_does_not_associate_without_strong_identity(self) -> None:
        memory = ObjectGraphMemory()
        node = memory.create_node(descriptor="chair", geometry_key="g-old", step_id=1)
        node.appearance_key_recent = "chair"
        node.avg_support_size = 0.5
        node.avg_depth_scale = 1.1
        node.avg_geometry_support = 0.6
        item = EvidenceItem(
            evidence_id="e-weak",
            descriptor="chair",
            geometry_key="g-new",
            confidence=0.9,
            provenance=EvidenceProvenance.CURRENT,
            repair_group_id="scene:objectB",
            support=ObservationSupport(
                proposal_id="p-weak",
                frame_token="f2",
                pose_token="pose:2",
                source_kind="replica_frame",
                support_size=0.5,
                depth_scale=1.1,
                appearance_key="table",
                continuity_key="scene:objectB",
                geometry_support=0.6,
            ),
        )
        hypothesis = CurrentEvidenceGraphLayer().repair([item])[0]
        decisions = CurrentToMemoryAssociationLayer().update(
            sequence_id="seq-weak",
            step_id=2,
            branch_id="duograph3d_full",
            hypotheses=[hypothesis],
            memory=memory,
            logger=EventLogger(),
        )
        self.assertEqual(decisions[0].action, "birth")
        self.assertNotEqual(decisions[0].object_id, node.object_id)

    def test_same_class_appearance_without_continuity_births_new_node(self) -> None:
        memory = ObjectGraphMemory()
        node = memory.create_node(descriptor="chair", geometry_key="g-chair-a", step_id=1)
        node.appearance_key_recent = "chair"
        node.avg_support_size = 0.45
        node.avg_depth_scale = 1.05
        node.avg_geometry_support = 0.55
        item = EvidenceItem(
            evidence_id="e-same-class",
            descriptor="chair",
            geometry_key="g-chair-b",
            confidence=0.92,
            provenance=EvidenceProvenance.CURRENT,
            repair_group_id="scene:objectB",
            support=ObservationSupport(
                proposal_id="p-same-class",
                frame_token="f3",
                pose_token="pose:3",
                source_kind="replica_frame",
                support_size=0.45,
                depth_scale=1.05,
                appearance_key="chair",
                continuity_key="scene:objectB",
                geometry_support=0.55,
            ),
        )
        hypothesis = CurrentEvidenceGraphLayer().repair([item])[0]
        decisions = CurrentToMemoryAssociationLayer().update(
            sequence_id="seq-same-class",
            step_id=2,
            branch_id="duograph3d_full",
            hypotheses=[hypothesis],
            memory=memory,
            logger=EventLogger(),
        )
        self.assertEqual(decisions[0].action, "birth")
        self.assertNotEqual(decisions[0].object_id, node.object_id)

    def test_continuity_without_geometry_profile_births_new_node(self) -> None:
        memory = ObjectGraphMemory()
        node = memory.create_node(descriptor="chair", geometry_key="g-chair-a", step_id=1)
        node.continuity_key_recent = "scene:objectA"
        node.appearance_key_recent = "chair"
        node.avg_support_size = 0.2
        node.avg_depth_scale = 1.0
        node.avg_geometry_support = 0.25
        item = EvidenceItem(
            evidence_id="e-cont-no-geom",
            descriptor="chair",
            geometry_key="g-chair-b",
            confidence=0.95,
            provenance=EvidenceProvenance.CURRENT,
            repair_group_id="scene:objectA",
            support=ObservationSupport(
                proposal_id="p-cont-no-geom",
                frame_token="f4",
                pose_token="pose:4",
                source_kind="replica_frame",
                support_size=0.9,
                depth_scale=1.8,
                appearance_key="chair",
                continuity_key="scene:objectA",
                geometry_support=1.4,
            ),
        )
        hypothesis = CurrentEvidenceGraphLayer().repair([item])[0]
        decisions = CurrentToMemoryAssociationLayer().update(
            sequence_id="seq-cont-no-geom",
            step_id=2,
            branch_id="duograph3d_full",
            hypotheses=[hypothesis],
            memory=memory,
            logger=EventLogger(),
        )
        self.assertEqual(decisions[0].action, "birth")
        self.assertNotEqual(decisions[0].object_id, node.object_id)

    def test_deva_hypotheses_do_not_double_associate_same_node(self) -> None:
        memory = ObjectGraphMemory()
        node = memory.create_node(descriptor="chair", geometry_key="g-old", step_id=1)
        node.continuity_key_recent = "scene:objectA"
        node.appearance_key_recent = "chair"
        node.avg_support_size = 0.5
        node.avg_depth_scale = 1.0
        node.avg_geometry_support = 0.6
        frame = FrameInput(
            frame_id="f2",
            observations=[
                Observation(
                    observation_id="o1",
                    descriptor="chair",
                    geometry_key="g-new",
                    repair_group_id="scene:objectA",
                    support=ObservationSupport(
                        proposal_id="p1",
                        frame_token="f2",
                        pose_token="pose:2",
                        source_kind="replica_frame",
                        support_size=0.5,
                        depth_scale=1.0,
                        appearance_key="chair",
                        continuity_key="scene:objectA",
                        geometry_support=0.6,
                    ),
                )
            ],
        )
        evidence = EvidenceBuilder(PipelineConfig()).build(
            frame,
            memory=memory,
            temporal_variant=TemporalVariant.DEVA_STYLE,
        )
        hypotheses = CurrentEvidenceGraphLayer().repair(evidence)
        decisions = CurrentToMemoryAssociationLayer().update(
            sequence_id="seq-deva",
            step_id=2,
            branch_id="duograph3d_full",
            hypotheses=hypotheses,
            memory=memory,
            logger=EventLogger(),
        )
        associated = [decision for decision in decisions if decision.object_id == node.object_id and decision.action in {"associate", "reentry"}]
        self.assertEqual(len(associated), 1)

    def test_layer1_graph_records_edge_reasons(self) -> None:
        items = [
            EvidenceItem(
                evidence_id="e-1",
                descriptor="chair",
                geometry_key="g-chair-a",
                confidence=0.9,
                provenance=EvidenceProvenance.CURRENT,
                support=ObservationSupport(
                    proposal_id="p-1",
                    frame_token="f1",
                    source_kind="replica_frame",
                    support_size=0.42,
                    depth_scale=1.05,
                    appearance_key="chair",
                    continuity_key="scene:chair-1",
                    geometry_support=0.62,
                ),
            ),
            EvidenceItem(
                evidence_id="e-2",
                descriptor="chair",
                geometry_key="g-chair-b",
                confidence=0.88,
                provenance=EvidenceProvenance.CURRENT,
                support=ObservationSupport(
                    proposal_id="p-2",
                    frame_token="f1",
                    source_kind="replica_frame",
                    support_size=0.45,
                    depth_scale=1.08,
                    appearance_key="chair",
                    continuity_key="scene:chair-1",
                    geometry_support=0.6,
                ),
            ),
        ]
        hypotheses = CurrentEvidenceGraphLayer().repair(items)
        self.assertEqual(len(hypotheses), 1)
        self.assertEqual(hypotheses[0].support_signals["repair_edge_count"], 1)
        self.assertIn("continuity_match", hypotheses[0].support_signals["repair_reasons"])

    def test_relation_bonus_prefers_historically_covisible_candidate(self) -> None:
        memory = ObjectGraphMemory()
        anchor = memory.create_node(descriptor="chair", geometry_key="g-anchor", step_id=1)
        anchor.continuity_key_recent = "scene:anchor"
        anchor.appearance_key_recent = "chair"
        anchor.avg_support_size = 0.4
        anchor.avg_depth_scale = 1.0
        anchor.avg_geometry_support = 0.5

        distractor = memory.create_node(descriptor="lamp", geometry_key="g-lamp-distractor", step_id=1)
        distractor.continuity_key_recent = "scene:lamp"
        distractor.appearance_key_recent = "lamp"
        distractor.avg_support_size = 0.3
        distractor.avg_depth_scale = 1.0
        distractor.avg_geometry_support = 0.5

        preferred = memory.create_node(descriptor="lamp", geometry_key="g-lamp-preferred", step_id=1)
        preferred.continuity_key_recent = "scene:lamp"
        preferred.appearance_key_recent = "lamp"
        preferred.avg_support_size = 0.3
        preferred.avg_depth_scale = 1.0
        preferred.avg_geometry_support = 0.5

        memory.register_co_visibility([anchor.object_id, preferred.object_id], step_id=1)

        hypotheses = CurrentEvidenceGraphLayer().repair(
            [
                EvidenceItem(
                    evidence_id="e-anchor",
                    descriptor="chair",
                    geometry_key="g-anchor-new",
                    confidence=0.9,
                    provenance=EvidenceProvenance.CURRENT,
                    repair_group_id="scene:anchor",
                    support=ObservationSupport(
                        proposal_id="p-anchor",
                        frame_token="f2",
                        source_kind="replica_frame",
                        support_size=0.4,
                        depth_scale=1.0,
                        appearance_key="chair",
                        continuity_key="scene:anchor",
                        geometry_support=0.5,
                    ),
                ),
                EvidenceItem(
                    evidence_id="e-lamp",
                    descriptor="lamp",
                    geometry_key="g-lamp-new",
                    confidence=0.9,
                    provenance=EvidenceProvenance.CURRENT,
                    repair_group_id="scene:lamp",
                    support=ObservationSupport(
                        proposal_id="p-lamp",
                        frame_token="f2",
                        source_kind="replica_frame",
                        support_size=0.3,
                        depth_scale=1.0,
                        appearance_key="lamp",
                        continuity_key="scene:lamp",
                        geometry_support=0.5,
                    ),
                ),
            ]
        )
        logger = EventLogger()
        decisions = CurrentToMemoryAssociationLayer().update(
            sequence_id="seq-rel",
            step_id=2,
            branch_id="duograph3d_full",
            hypotheses=hypotheses,
            memory=memory,
            logger=logger,
        )
        self.assertEqual(decisions[0].object_id, anchor.object_id)
        self.assertEqual(decisions[1].object_id, preferred.object_id)
        self.assertEqual(len(memory.relation_edges), 1)

    def test_pipeline_reports_relation_edges_in_summary(self) -> None:
        pipeline = DuoGraph3DPipeline()
        frame = FrameInput(
            frame_id="f1",
            observations=[
                Observation(observation_id="o1", descriptor="chair", geometry_key="g-chair", repair_group_id="chair"),
                Observation(observation_id="o2", descriptor="lamp", geometry_key="g-lamp", repair_group_id="lamp"),
            ],
        )
        result, logger = pipeline.run_sequence(sequence_id="seq-rel-summary", frames=[frame], temporal_variant=TemporalVariant.NAIVE_FRAMEWISE)
        summary = summarize_run(result, logger)
        self.assertEqual(summary["memory_relation_edge_count"], 1)

    def test_association_diagnostics_log_candidates_and_birth_reasons(self) -> None:
        pipeline = DuoGraph3DPipeline(
            PipelineConfig(
                emit_association_diagnostics=True,
                association_diagnostics_top_k=2,
            )
        )
        frames = [
            FrameInput(
                frame_id="f1",
                observations=[
                    Observation(
                        observation_id="o1",
                        descriptor="chair",
                        geometry_key="g-chair",
                        confidence=0.9,
                        repair_group_id="chair",
                        support=ObservationSupport(
                            proposal_id="p1",
                            frame_token="f1",
                            source_kind="unit",
                            support_size=0.4,
                            depth_scale=1.0,
                            appearance_key="chair",
                            continuity_key="chair",
                            geometry_support=0.5,
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
                        geometry_key="g-chair",
                        confidence=0.95,
                        repair_group_id="chair",
                        support=ObservationSupport(
                            proposal_id="p2",
                            frame_token="f2",
                            source_kind="unit",
                            support_size=0.42,
                            depth_scale=1.02,
                            appearance_key="chair",
                            continuity_key="chair",
                            geometry_support=0.52,
                        ),
                    )
                ],
            ),
        ]

        _result, logger = pipeline.run_sequence(
            sequence_id="seq-diag",
            frames=frames,
            temporal_variant=TemporalVariant.NAIVE_FRAMEWISE,
        )

        self.assertEqual(logger.count("association_candidate_diagnostic"), 2)
        self.assertEqual(logger.count("association_birth_diagnostic"), 1)
        first_birth = logger.filter(event_type="association_birth_diagnostic")[0]
        self.assertEqual(first_birth.payload["reason"], "no_candidate")
        candidate_records = [
            record
            for record in logger.filter(event_type="association_candidate_diagnostic")
            if record.payload["candidate_count"] > 0
        ]
        self.assertEqual(len(candidate_records), 1)
        top_candidate = candidate_records[0].payload["top_candidates"][0]
        self.assertIn("components", top_candidate)
        self.assertGreater(top_candidate["components"]["geometry_key"], 0.0)
        self.assertGreater(top_candidate["components"]["geometry_profile"], 0.0)
        self.assertIn("best_has_strong_identity", candidate_records[0].payload)

    def test_layer1_shared_history_object_boost_merges_fragments(self) -> None:
        shared_history = HistoryCandidate(
            object_id="obj-history",
            affinity=0.9,
            spatial_score=0.7,
            semantic_score=1.0,
            recency_score=1.0,
            size_score=0.5,
            margin=0.3,
            strong=True,
        )
        items = [
            EvidenceItem(
                evidence_id="e-history-a",
                descriptor="chair",
                geometry_key="g-a",
                confidence=0.9,
                provenance=EvidenceProvenance.CURRENT,
                repair_group_id="fragment-a",
                history_candidates=(shared_history,),
                support=ObservationSupport(
                    proposal_id="p-a",
                    frame_token="f-history",
                    support_size=0.1,
                    depth_scale=0.6,
                    appearance_key="chair",
                    continuity_key="current-fragment-a",
                    geometry_support=0.2,
                ),
            ),
            EvidenceItem(
                evidence_id="e-history-b",
                descriptor="chair",
                geometry_key="g-b",
                confidence=0.88,
                provenance=EvidenceProvenance.CURRENT,
                repair_group_id="fragment-b",
                history_candidates=(shared_history,),
                support=ObservationSupport(
                    proposal_id="p-b",
                    frame_token="f-history",
                    support_size=0.9,
                    depth_scale=1.4,
                    appearance_key="chair",
                    continuity_key="current-fragment-b",
                    geometry_support=1.2,
                ),
            ),
        ]

        hypotheses = CurrentEvidenceGraphLayer().repair(items)

        self.assertEqual(len(hypotheses), 1)
        self.assertIn("shared_history_object", hypotheses[0].support_signals["repair_reasons"])
        self.assertEqual(hypotheses[0].support_signals["history_object_id"], "obj-history")

    def test_layer2_greedy_many_to_one_history_association(self) -> None:
        memory = ObjectGraphMemory()
        node = memory.create_node(descriptor="chair", geometry_key="g-old", step_id=1)
        node.appearance_key_recent = "chair"
        node.avg_support_size = 0.4
        node.avg_depth_scale = 1.0
        node.avg_geometry_support = 0.5
        history = HistoryCandidate(
            object_id=node.object_id,
            affinity=0.92,
            spatial_score=0.72,
            semantic_score=1.0,
            margin=0.4,
            strong=True,
        )
        hypotheses = [
            CurrentObjectHypothesis(
                hypothesis_id="hyp-a",
                descriptor="chair",
                geometry_key="g-new-a",
                confidence=0.9,
                evidence_ids=("e-a",),
                track_hint="fragment-a",
                history_candidates=(history,),
                support_signals={"appearance_key": "chair", "support_size": 0.4, "depth_scale": 1.0, "geometry_support": 0.5},
            ),
            CurrentObjectHypothesis(
                hypothesis_id="hyp-b",
                descriptor="chair",
                geometry_key="g-new-b",
                confidence=0.91,
                evidence_ids=("e-b",),
                track_hint="fragment-b",
                history_candidates=(history,),
                support_signals={"appearance_key": "chair", "support_size": 0.4, "depth_scale": 1.0, "geometry_support": 0.5},
            ),
        ]

        decisions = CurrentToMemoryAssociationLayer().update(
            sequence_id="seq-many-to-one",
            step_id=2,
            branch_id="duograph3d_full",
            hypotheses=hypotheses,
            memory=memory,
            logger=EventLogger(),
        )

        self.assertEqual([decision.action for decision in decisions], ["associate", "associate"])
        self.assertEqual([decision.object_id for decision in decisions], [node.object_id, node.object_id])

    def test_layer2_history_identity_requires_context_gate(self) -> None:
        config = PipelineConfig(emit_association_diagnostics=True)
        memory = ObjectGraphMemory(config)
        node = memory.create_node(descriptor="chair", geometry_key="g-old", step_id=1)
        node.appearance_key_recent = "chair"
        node.avg_support_size = 0.4
        node.avg_depth_scale = 1.0
        node.avg_geometry_support = 0.5
        weak_history = HistoryCandidate(
            object_id=node.object_id,
            affinity=0.95,
            spatial_score=0.9,
            semantic_score=0.0,
            point_overlap_score=0.0,
            margin=0.4,
            strong=True,
        )
        hypothesis = CurrentObjectHypothesis(
            hypothesis_id="hyp-low-semantic-history",
            descriptor="chair",
            geometry_key="g-new",
            confidence=0.9,
            evidence_ids=("e-low-semantic-history",),
            track_hint="fragment-low-semantic-history",
            history_candidates=(weak_history,),
            support_signals={"appearance_key": "chair", "support_size": 0.4, "depth_scale": 1.0, "geometry_support": 0.5},
        )
        logger = EventLogger()

        decisions = CurrentToMemoryAssociationLayer(config).update(
            sequence_id="seq-history-gate",
            step_id=2,
            branch_id="duograph3d_full",
            hypotheses=[hypothesis],
            memory=memory,
            logger=logger,
        )

        self.assertEqual(decisions[0].action, "birth")
        diagnostic = logger.filter(event_type="association_candidate_diagnostic")[0]
        top_candidate = diagnostic.payload["top_candidates"][0]
        self.assertFalse(top_candidate["components"]["history_identity_gate_passed"])
        self.assertEqual(top_candidate["components"]["history_candidate"], 0.0)

    def test_layer2_relation_bonus_is_capped_and_diagnostic(self) -> None:
        config = PipelineConfig(emit_association_diagnostics=True, association_diagnostics_top_k=5, layer2_relation_bonus_cap=0.3)
        memory = ObjectGraphMemory(config)
        anchor_a = memory.create_node(descriptor="anchor", geometry_key="g-anchor-a", step_id=1)
        anchor_b = memory.create_node(descriptor="anchor", geometry_key="g-anchor-b", step_id=1)
        related = memory.create_node(descriptor="lamp", geometry_key="g-related-old", step_id=1)
        related.class_counts["table"] = 1
        for _ in range(5):
            memory.register_co_visibility([anchor_a.object_id, related.object_id], step_id=1)
            memory.register_co_visibility([anchor_b.object_id, related.object_id], step_id=1)
        hypotheses = [
            CurrentObjectHypothesis(
                hypothesis_id="hyp-anchor-a",
                descriptor="anchor",
                geometry_key="g-anchor-a",
                confidence=0.9,
                evidence_ids=("e-anchor-a",),
                track_hint="anchor-a",
            ),
            CurrentObjectHypothesis(
                hypothesis_id="hyp-anchor-b",
                descriptor="anchor",
                geometry_key="g-anchor-b",
                confidence=0.9,
                evidence_ids=("e-anchor-b",),
                track_hint="anchor-b",
            ),
            CurrentObjectHypothesis(
                hypothesis_id="hyp-related",
                descriptor="unmatched",
                geometry_key="g-new-related",
                confidence=0.9,
                evidence_ids=("e-related",),
                track_hint="related",
                object_payload=ObjectObservationPayload(label="table", detection_count=1),
            ),
        ]
        logger = EventLogger()

        CurrentToMemoryAssociationLayer(config).update(
            sequence_id="seq-relation-cap",
            step_id=2,
            branch_id="duograph3d_full",
            hypotheses=hypotheses,
            memory=memory,
            logger=logger,
        )

        related_diag = [
            record
            for record in logger.filter(event_type="association_candidate_diagnostic")
            if record.payload["hypothesis_id"] == "hyp-related"
        ][0]
        related_candidate = next(
            item for item in related_diag.payload["top_candidates"] if item["object_id"] == related.object_id
        )
        self.assertEqual(related_candidate["relation_bonus_raw"], 0.5)
        self.assertEqual(related_candidate["relation_bonus"], 0.3)
        self.assertTrue(related_candidate["relation_bonus_allowed"])

    def test_history_candidate_uses_object_point_overlap(self) -> None:
        memory = ObjectGraphMemory(PipelineConfig(history_point_overlap_affinity_weight=0.2))
        node = memory.create_node(descriptor="chair", geometry_key="g-old", step_id=1)
        memory.fuse_hypothesis(
            node,
            CurrentObjectHypothesis(
                hypothesis_id="hyp-history",
                descriptor="chair",
                geometry_key="g-old",
                confidence=0.9,
                evidence_ids=("e-history",),
                track_hint="history",
                object_payload=ObjectObservationPayload(
                    label="chair",
                    points_sample=((0.0, 0.0, 0.0), (0.05, 0.0, 0.0), (0.0, 0.05, 0.0)),
                    bbox_min=(0.0, 0.0, 0.0),
                    bbox_max=(0.05, 0.05, 0.0),
                    centroid=(0.02, 0.02, 0.0),
                    detection_count=1,
                ),
            ),
            step_id=1,
        )
        item = EvidenceItem(
            evidence_id="e-overlap",
            descriptor="chair",
            geometry_key="g-fragment",
            confidence=0.9,
            provenance=EvidenceProvenance.CURRENT,
            object_payload=ObjectObservationPayload(
                label="chair",
                points_sample=((0.01, 0.0, 0.0), (0.04, 0.0, 0.0), (0.0, 0.04, 0.0)),
                centroid=(0.02, 0.01, 0.0),
                detection_count=1,
            ),
        )

        candidates = memory.history_candidates_for(item)

        self.assertEqual(len(candidates), 1)
        self.assertEqual(candidates[0].object_id, node.object_id)
        self.assertGreaterEqual(candidates[0].point_overlap_score, 0.99)
        self.assertGreaterEqual(candidates[0].affinity, 0.7)

    def test_layer2_residual_absorbs_same_frame_point_fragment(self) -> None:
        config = PipelineConfig(emit_association_diagnostics=True, layer2_enable_residual_absorption=True)
        memory = ObjectGraphMemory(config)
        node = memory.create_node(descriptor="chair", geometry_key="g-anchor", step_id=1)
        node.appearance_key_recent = "chair"
        hypotheses = [
            CurrentObjectHypothesis(
                hypothesis_id="hyp-anchor",
                descriptor="chair",
                geometry_key="g-anchor",
                confidence=0.9,
                evidence_ids=("e-anchor",),
                track_hint="anchor",
                support_signals={"appearance_key": "chair", "support_size": 0.4, "depth_scale": 1.0, "geometry_support": 0.5},
                object_payload=ObjectObservationPayload(
                    label="chair",
                    points_sample=((0.0, 0.0, 0.0), (0.05, 0.0, 0.0), (0.0, 0.05, 0.0)),
                    centroid=(0.02, 0.02, 0.0),
                    detection_count=1,
                ),
            ),
            CurrentObjectHypothesis(
                hypothesis_id="hyp-fragment",
                descriptor="chair",
                geometry_key="g-fragment",
                confidence=0.9,
                evidence_ids=("e-fragment",),
                track_hint="fragment",
                support_signals={"appearance_key": "chair", "support_size": 0.48, "depth_scale": 1.0, "geometry_support": 0.7},
                object_payload=ObjectObservationPayload(
                    label="chair",
                    points_sample=((0.01, 0.0, 0.0), (0.04, 0.0, 0.0), (0.0, 0.04, 0.0)),
                    centroid=(0.02, 0.01, 0.0),
                    detection_count=1,
                ),
            ),
        ]
        logger = EventLogger()

        decisions = CurrentToMemoryAssociationLayer(config).update(
            sequence_id="seq-residual",
            step_id=2,
            branch_id="duograph3d_full",
            hypotheses=hypotheses,
            memory=memory,
            logger=logger,
        )

        self.assertEqual([decision.action for decision in decisions], ["associate", "absorb"])
        self.assertEqual(decisions[1].object_id, node.object_id)
        self.assertEqual(decisions[1].reason, "residual_absorption_above_threshold")
        self.assertEqual(logger.count("residual_absorption_commit"), 1)

    def test_birth_diagnostic_decomposes_failure_family(self) -> None:
        config = PipelineConfig(emit_association_diagnostics=True)
        memory = ObjectGraphMemory(config)
        node = memory.create_node(descriptor="chair", geometry_key="g-old", step_id=1)
        node.appearance_key_recent = "chair"
        hypothesis = CurrentObjectHypothesis(
            hypothesis_id="hyp-low-semantic",
            descriptor="chair",
            geometry_key="g-new",
            confidence=0.9,
            evidence_ids=("e-low-semantic",),
            track_hint="fragment-low-semantic",
            support_signals={"appearance_key": "table"},
        )
        logger = EventLogger()

        decisions = CurrentToMemoryAssociationLayer(config).update(
            sequence_id="seq-birth-family",
            step_id=2,
            branch_id="duograph3d_full",
            hypotheses=[hypothesis],
            memory=memory,
            logger=logger,
        )

        self.assertEqual(decisions[0].action, "birth")
        diagnostic = logger.filter(event_type="association_birth_diagnostic")[0]
        self.assertEqual(diagnostic.payload["failure_family"], "semantic_gate_low")
        self.assertTrue(diagnostic.payload["top_candidates"])
        self.assertIn("point_overlap_score", diagnostic.payload["top_candidates"][0])

    def test_memory_fuses_payload_and_merges_duplicate_objects(self) -> None:
        memory = ObjectGraphMemory(PipelineConfig(object_merge_threshold=0.8))
        left = memory.create_node(descriptor="chair", geometry_key="g-left", step_id=1)
        right = memory.create_node(descriptor="chair", geometry_key="g-right", step_id=2)
        payload_left = ObjectObservationPayload(
            label="chair",
            points_sample=((0.0, 0.0, 0.0), (1.0, 1.0, 1.0)),
            bbox_min=(0.0, 0.0, 0.0),
            bbox_max=(1.0, 1.0, 1.0),
            centroid=(0.5, 0.5, 0.5),
            clip_feature=(1.0, 0.0),
            detection_count=1,
        )
        payload_right = ObjectObservationPayload(
            label="chair",
            points_sample=((0.2, 0.2, 0.2), (0.8, 0.8, 0.8)),
            bbox_min=(0.2, 0.2, 0.2),
            bbox_max=(0.8, 0.8, 0.8),
            centroid=(0.5, 0.5, 0.5),
            clip_feature=(1.0, 0.0),
            detection_count=1,
        )
        memory.fuse_hypothesis(
            left,
            CurrentObjectHypothesis(
                hypothesis_id="hyp-left",
                descriptor="chair",
                geometry_key="g-left",
                confidence=0.9,
                evidence_ids=("e-left",),
                track_hint="left",
                object_payload=payload_left,
                support_signals={"appearance_key": "chair"},
            ),
            step_id=1,
        )
        memory.fuse_hypothesis(
            right,
            CurrentObjectHypothesis(
                hypothesis_id="hyp-right",
                descriptor="chair",
                geometry_key="g-right",
                confidence=0.9,
                evidence_ids=("e-right",),
                track_hint="right",
                object_payload=payload_right,
                support_signals={"appearance_key": "chair"},
            ),
            step_id=2,
        )

        merges = memory.merge_duplicate_objects()

        self.assertEqual(len(merges), 1)
        self.assertEqual(right.status.value, "retired")
        self.assertEqual(right.merge_target_id, left.object_id)
        self.assertEqual(left.detection_count, 2)
        self.assertEqual(left.class_counts["chair"], 2)
        self.assertEqual(left.bbox_min, (0.0, 0.0, 0.0))
        self.assertEqual(left.bbox_max, (1.0, 1.0, 1.0))

    def test_memory_uses_conceptgraphs_style_feature_semantic_fusion(self) -> None:
        memory = ObjectGraphMemory()
        node = memory.create_node(descriptor="scene:chair", geometry_key="g-object", step_id=1)
        memory.fuse_hypothesis(
            node,
            CurrentObjectHypothesis(
                hypothesis_id="hyp-chair",
                descriptor="scene:chair",
                geometry_key="g-object",
                confidence=0.9,
                evidence_ids=("e-chair",),
                track_hint="chair-fragment",
                object_payload=ObjectObservationPayload(
                    label="chair",
                    clip_feature=(1.0, 0.0),
                    text_feature=(1.0, 0.0),
                    detection_count=1,
                ),
            ),
            step_id=1,
        )
        memory.fuse_hypothesis(
            node,
            CurrentObjectHypothesis(
                hypothesis_id="hyp-table-noisy",
                descriptor="scene:table",
                geometry_key="g-object",
                confidence=0.8,
                evidence_ids=("e-table",),
                track_hint="same-object-noisy-label",
                object_payload=ObjectObservationPayload(
                    label="table",
                    clip_feature=(0.0, 1.0),
                    text_feature=(0.0, 1.0),
                    detection_count=1,
                ),
            ),
            step_id=2,
        )

        self.assertEqual(node.descriptor_recent, "scene:table")
        self.assertEqual(node.descriptor_fused, "scene:chair")
        self.assertEqual(node.class_counts, {"chair": 1, "table": 1})
        self.assertAlmostEqual(node.clip_feature[0], 0.707107, places=5)
        self.assertAlmostEqual(node.clip_feature[1], 0.707107, places=5)
        self.assertAlmostEqual(node.text_feature[0], 0.707107, places=5)
        self.assertAlmostEqual(node.text_feature[1], 0.707107, places=5)

    def test_class_agnostic_identity_descriptor_survives_semantic_fusion(self) -> None:
        memory = ObjectGraphMemory()
        node = memory.create_node(descriptor="room0:item", geometry_key="g-object", step_id=1)

        memory.fuse_hypothesis(
            node,
            CurrentObjectHypothesis(
                hypothesis_id="hyp-chair-fragment",
                descriptor="room0:item",
                geometry_key="g-object",
                confidence=0.9,
                evidence_ids=("e-chair",),
                track_hint="chair-fragment",
                object_payload=ObjectObservationPayload(
                    label="chair",
                    clip_feature=(1.0, 0.0),
                    text_feature=(1.0, 0.0),
                    detection_count=1,
                ),
            ),
            step_id=1,
        )

        self.assertEqual(node.descriptor_fused, "room0:item")
        self.assertEqual(node.descriptor_recent, "room0:item")
        self.assertEqual(node.class_counts, {"chair": 1})
        self.assertEqual(ObjectGraphMemory.dominant_semantic_label(node), "chair")

    def test_semantic_score_prefers_object_text_feature_over_noisy_top1_label(self) -> None:
        memory = ObjectGraphMemory()
        node = memory.create_node(descriptor="scene:chair", geometry_key="g-object", step_id=1)
        node.class_counts["chair"] = 3
        node.text_feature = (1.0, 0.0)
        hypothesis = CurrentObjectHypothesis(
            hypothesis_id="hyp-noisy-label",
            descriptor="scene:table",
            geometry_key="g-object",
            confidence=0.9,
            evidence_ids=("e-noisy-label",),
            track_hint="same-object",
            object_payload=ObjectObservationPayload(
                label="table",
                text_feature=(1.0, 0.0),
                detection_count=1,
            ),
        )

        self.assertEqual(memory.hypothesis_semantic_score(hypothesis, node), 1.0)

    def test_layer2_can_use_visual_feature_when_descriptor_and_appearance_are_unreliable(self) -> None:
        config = PipelineConfig(
            emit_association_diagnostics=True,
            layer2_descriptor_match_weight=0.0,
            layer2_appearance_match_weight=0.0,
            layer2_visual_similarity_weight=0.35,
        )
        memory = ObjectGraphMemory(config)
        node = memory.create_node(descriptor="scene:chair", geometry_key="g-object", step_id=1)
        node.clip_feature = (1.0, 0.0)
        node.avg_support_size = 0.5
        node.avg_depth_scale = 1.0
        node.avg_geometry_support = 0.6
        hypothesis = CurrentObjectHypothesis(
            hypothesis_id="hyp-visual",
            descriptor="scene:table",
            geometry_key="g-object",
            confidence=0.9,
            evidence_ids=("e-visual",),
            track_hint="visually-same-object",
            support_signals={
                "appearance_key": "table",
                "support_size": 0.5,
                "depth_scale": 1.0,
                "geometry_support": 0.6,
            },
            object_payload=ObjectObservationPayload(
                label="table",
                clip_feature=(1.0, 0.0),
                detection_count=1,
            ),
        )
        logger = EventLogger()

        decisions = CurrentToMemoryAssociationLayer(config).update(
            sequence_id="seq-visual",
            step_id=2,
            branch_id="duograph3d_full",
            hypotheses=[hypothesis],
            memory=memory,
            logger=logger,
        )

        self.assertEqual(decisions[0].action, "associate")
        top_candidate = logger.filter(event_type="association_candidate_diagnostic")[0].payload["top_candidates"][0]
        self.assertEqual(top_candidate["components"]["descriptor"], 0.0)
        self.assertEqual(top_candidate["components"]["appearance"], 0.0)
        self.assertGreater(top_candidate["components"]["visual"], 0.0)

    def test_export_gate_filters_short_lived_retired_fragments(self) -> None:
        memory = ObjectGraphMemory()
        stable = memory.create_node(descriptor="room0:item", geometry_key="stable", step_id=1)
        stable.status = ObjectStatus.RETIRED
        stable.detection_count = 3
        stable.point_count = 6
        stable.sampled_points = tuple((float(i), 0.0, 0.0) for i in range(6))

        fragment = memory.create_node(descriptor="room0:item", geometry_key="fragment", step_id=2)
        fragment.status = ObjectStatus.RETIRED
        fragment.detection_count = 1
        fragment.point_count = 6
        fragment.sampled_points = tuple((float(i), 1.0, 0.0) for i in range(6))

        self.assertEqual(
            ObjectGraphMemory.export_skip_reason(stable, min_points=4, min_detections=3),
            "",
        )
        self.assertEqual(
            ObjectGraphMemory.export_skip_reason(fragment, min_points=4, min_detections=3),
            "too_few_detections",
        )


if __name__ == "__main__":
    unittest.main()
