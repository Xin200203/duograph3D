import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from duograph3d.contracts import (
    EvidenceProvenance,
    EvidenceItem,
    FrameInput,
    Observation,
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


if __name__ == "__main__":
    unittest.main()
