import json
import sys
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from duograph3d.contracts import (
    FrameInput, Observation, ObservationSupport, ObjectObservationPayload,
    PipelineConfig, TemporalVariant,
)
from duograph3d.events import BRANCH_DUOGRAPH3D
from duograph3d.pipeline import DuoGraph3DPipeline
from duograph3d.experiment_logger import (
    ExperimentRunMetadata,
    config_to_snapshot,
    export_event_stream_jsonl,
    load_event_stream,
    count_event_types,
    filter_records,
)
from duograph3d.candidate_metrics import (
    build_candidate_recall_table,
    candidate_recall_summary_to_dict,
)
from duograph3d.memory_purity import (
    build_memory_purity_table,
    memory_purity_summary_to_dict,
)
from duograph3d.carrier_metrics import (
    build_carrier_table,
    carrier_summary_to_dict,
)
from duograph3d.shadow_metrics import generate_shadow_report, compare_shadow_reports


class ExperimentLoggerTests(unittest.TestCase):
    def setUp(self):
        self.config = PipelineConfig(
            emit_association_diagnostics=True,
            association_diagnostics_top_k=3,
        )
        self.pipeline = DuoGraph3DPipeline(self.config)
        self.frames = [
            FrameInput(frame_id="f1", observations=[
                Observation(observation_id="o1", descriptor="chair", geometry_key="g-chair",
                           repair_group_id="chair", confidence=0.95,
                           support=ObservationSupport(proposal_id="p1", frame_token="f1", continuity_key="objA",
                                                      appearance_key="chair", support_size=0.5)),
                Observation(observation_id="o2", descriptor="desk", geometry_key="g-desk",
                           repair_group_id="desk", confidence=0.92,
                           support=ObservationSupport(proposal_id="p2", frame_token="f1", continuity_key="objB",
                                                      appearance_key="desk", support_size=0.6)),
            ]),
        ]

    def test_config_to_snapshot_is_json_serializable(self):
        snapshot = config_to_snapshot(self.config)
        json.dumps(snapshot)  # should not raise
        self.assertIsInstance(snapshot, dict)
        self.assertIn("association_threshold", snapshot)

    def test_export_event_stream_jsonl_roundtrip(self):
        result, logger = self.pipeline.run_sequence(
            sequence_id="test-seq", frames=self.frames,
            temporal_variant=TemporalVariant.NAIVE_FRAMEWISE,
            branch_id=BRANCH_DUOGRAPH3D,
        )
        with TemporaryDirectory() as tmp:
            path = Path(tmp) / "events.jsonl"
            metadata = ExperimentRunMetadata(
                run_id="test-run", branch_id=BRANCH_DUOGRAPH3D,
                scene_id="test-scene", temporal_variant="naive_framewise",
                config_snapshot=config_to_snapshot(self.config), seed=0,
            )
            exported = export_event_stream_jsonl(logger, path, metadata=metadata)
            self.assertTrue(exported.exists())
            self.assertGreater(exported.stat().st_size, 0)

            loaded = load_event_stream(exported)
            self.assertGreater(len(loaded), 0)
            for record in loaded:
                self.assertIn("event_type", record)
                self.assertIn("schema_version", record)

    def test_count_event_types(self):
        result, logger = self.pipeline.run_sequence(
            sequence_id="test-seq", frames=self.frames,
            temporal_variant=TemporalVariant.NAIVE_FRAMEWISE,
            branch_id=BRANCH_DUOGRAPH3D,
        )
        with TemporaryDirectory() as tmp:
            path = Path(tmp) / "events.jsonl"
            export_event_stream_jsonl(logger, path)
            loaded = load_event_stream(path)
            counts = count_event_types(loaded)
            self.assertIn("birth_commit", counts)
            self.assertIn("comparison_slice_start", counts)

    def test_filter_records(self):
        result, logger = self.pipeline.run_sequence(
            sequence_id="test-seq", frames=self.frames,
            temporal_variant=TemporalVariant.NAIVE_FRAMEWISE,
            branch_id=BRANCH_DUOGRAPH3D,
        )
        with TemporaryDirectory() as tmp:
            path = Path(tmp) / "events.jsonl"
            export_event_stream_jsonl(logger, path)
            loaded = load_event_stream(path)
            births = filter_records(loaded, event_type="birth_commit")
            self.assertGreater(len(births), 0)
            for birth in births:
                self.assertEqual(birth["event_type"], "birth_commit")


class CandidateMetricsTests(unittest.TestCase):
    def setUp(self):
        self.config = PipelineConfig(
            emit_association_diagnostics=True,
            association_diagnostics_top_k=3,
        )
        self.pipeline = DuoGraph3DPipeline(self.config)
        self.frames = [
            FrameInput(frame_id="f1", observations=[
                Observation(observation_id="o1", descriptor="chair", geometry_key="g-c",
                           repair_group_id="chair", confidence=0.95,
                           support=ObservationSupport(proposal_id="p1", frame_token="f1", continuity_key="a",
                                                      appearance_key="chair")),
            ]),
            FrameInput(frame_id="f2", observations=[
                Observation(observation_id="o2", descriptor="chair", geometry_key="g-c",
                           repair_group_id="chair", confidence=0.93,
                           support=ObservationSupport(proposal_id="p2", frame_token="f1", continuity_key="a",
                                                      appearance_key="chair")),
            ]),
        ]

    def test_build_candidate_recall_table(self):
        result, logger = self.pipeline.run_sequence(
            sequence_id="test", frames=self.frames,
            temporal_variant=TemporalVariant.NAIVE_FRAMEWISE,
            branch_id=BRANCH_DUOGRAPH3D,
        )
        with TemporaryDirectory() as tmp:
            path = Path(tmp) / "events.jsonl"
            export_event_stream_jsonl(logger, path)
            loaded = load_event_stream(path)
            summary = build_candidate_recall_table(loaded, run_id="r1", scene_id="test")
            self.assertGreaterEqual(summary.total_hypotheses, 1)
            self.assertGreaterEqual(summary.association_count + summary.birth_count, 1)
            d = candidate_recall_summary_to_dict(summary)
            self.assertIn("birth_rate", d)


class MemoryPurityTests(unittest.TestCase):
    def setUp(self):
        self.config = PipelineConfig(emit_association_diagnostics=True)
        self.pipeline = DuoGraph3DPipeline(self.config)
        self.frames = [
            FrameInput(frame_id="f1", observations=[
                Observation(observation_id="o1", descriptor="chair", geometry_key="g-c",
                           repair_group_id="c", confidence=0.95,
                           support=ObservationSupport(proposal_id="p1", frame_token="f1", continuity_key="a",
                                                      appearance_key="chair")),
            ]),
        ]

    def test_build_memory_purity_table(self):
        result, logger = self.pipeline.run_sequence(
            sequence_id="test", frames=self.frames,
            temporal_variant=TemporalVariant.NAIVE_FRAMEWISE,
            branch_id=BRANCH_DUOGRAPH3D,
        )
        with TemporaryDirectory() as tmp:
            path = Path(tmp) / "events.jsonl"
            export_event_stream_jsonl(logger, path)
            loaded = load_event_stream(path)
            summary = build_memory_purity_table(loaded, run_id="r1", scene_id="test")
            self.assertGreaterEqual(summary.total_nodes_created, 1)
            d = memory_purity_summary_to_dict(summary)
            self.assertIn("total_nodes_created", d)


class CarrierMetricsTests(unittest.TestCase):
    def setUp(self):
        self.config = PipelineConfig(emit_association_diagnostics=True)
        self.pipeline = DuoGraph3DPipeline(self.config)
        self.frames = [
            FrameInput(frame_id="f1", observations=[
                Observation(observation_id="o1", descriptor="chair", geometry_key="g-c",
                           repair_group_id="c", confidence=0.95),
            ]),
        ]

    def test_build_carrier_table_empty(self):
        result, logger = self.pipeline.run_sequence(
            sequence_id="test", frames=self.frames,
            temporal_variant=TemporalVariant.NAIVE_FRAMEWISE,
            branch_id=BRANCH_DUOGRAPH3D,
        )
        with TemporaryDirectory() as tmp:
            path = Path(tmp) / "events.jsonl"
            export_event_stream_jsonl(logger, path)
            loaded = load_event_stream(path)
            summary = build_carrier_table(loaded, run_id="r1", scene_id="test")
            d = carrier_summary_to_dict(summary)
            self.assertIn("coverage_verdict", d)


class ShadowMetricsTests(unittest.TestCase):
    def setUp(self):
        self.config = PipelineConfig(
            emit_association_diagnostics=True,
            association_diagnostics_top_k=3,
        )
        self.pipeline = DuoGraph3DPipeline(self.config)
        self.frames = [
            FrameInput(frame_id="f1", observations=[
                Observation(observation_id="o1", descriptor="chair", geometry_key="g-c",
                           repair_group_id="c", confidence=0.95,
                           support=ObservationSupport(proposal_id="p1", frame_token="f1", continuity_key="a",
                                                      appearance_key="chair", support_size=0.5)),
            ]),
        ]

    def test_generate_shadow_report(self):
        result, logger = self.pipeline.run_sequence(
            sequence_id="test", frames=self.frames,
            temporal_variant=TemporalVariant.NAIVE_FRAMEWISE,
            branch_id=BRANCH_DUOGRAPH3D,
        )
        with TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            event_path = tmp / "events.jsonl"
            export_event_stream_jsonl(logger, event_path)
            report = generate_shadow_report(
                event_path, run_id="r1", scene_id="test", output_dir=tmp / "metrics",
            )
            self.assertIn("candidate_recall", report)
            self.assertIn("memory_purity", report)
            self.assertIn("carrier", report)
            self.assertTrue((tmp / "metrics" / "test_candidate_recall.json").exists())
            self.assertTrue((tmp / "metrics" / "test_memory_purity.json").exists())

    def test_compare_shadow_reports_identical(self):
        result, logger = self.pipeline.run_sequence(
            sequence_id="test", frames=self.frames,
            temporal_variant=TemporalVariant.NAIVE_FRAMEWISE,
            branch_id=BRANCH_DUOGRAPH3D,
        )
        with TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            event_path = tmp / "events.jsonl"
            export_event_stream_jsonl(logger, event_path)
            r1 = generate_shadow_report(event_path, run_id="r1", scene_id="test")
            r2 = generate_shadow_report(event_path, run_id="r1", scene_id="test")
            comp = compare_shadow_reports(r1, r2)
            self.assertIn("deltas", comp)
            # Identical inputs -> all deltas should be zero
            for key, delta in comp["deltas"].items():
                for sub_key, val in delta.items():
                    self.assertEqual(val, 0.0, f"{key}.{sub_key} delta should be 0, got {val}")


class DeterministicReplayTests(unittest.TestCase):
    """Verify that the pipeline produces identical output on repeated runs."""

    def setUp(self):
        self.config = PipelineConfig(emit_association_diagnostics=True)
        self.pipeline = DuoGraph3DPipeline(self.config)
        self.frames = [
            FrameInput(frame_id="f1", observations=[
                Observation(observation_id=f"o{i}", descriptor="chair" if i % 2 == 0 else "desk",
                           geometry_key=f"g-{i//2}", repair_group_id=f"g{i//2}", confidence=0.95,
                           support=ObservationSupport(proposal_id=f"p{i}", frame_token="f1", continuity_key=f"c{i//3}",
                                                      appearance_key="chair" if i % 2 == 0 else "desk",
                                                      support_size=0.5 + i * 0.01),
                           object_payload=ObjectObservationPayload(
                               label="chair" if i % 2 == 0 else "desk",
                               centroid=(float(i), 0.5, 0.5), mask_area=500.0, detection_count=1))
                for i in range(8)
            ]),
            FrameInput(frame_id="f2", observations=[
                Observation(observation_id=f"o{i}", descriptor="chair" if i % 2 == 0 else "desk",
                           geometry_key=f"g-{i//2}", repair_group_id=f"g{i//2}", confidence=0.93,
                           support=ObservationSupport(proposal_id=f"p2-{i}", frame_token="f2", continuity_key=f"c{i//3}",
                                                      appearance_key="chair" if i % 2 == 0 else "desk",
                                                      support_size=0.5 + i * 0.01),
                           object_payload=ObjectObservationPayload(
                               label="chair" if i % 2 == 0 else "desk",
                               centroid=(float(i), 0.5, 0.5), mask_area=500.0, detection_count=1))
                for i in range(8)
            ]),
        ]

    def test_two_runs_produce_identical_results(self):
        from dataclasses import replace
        frozen_frames1 = [replace(f, observations=list(f.observations)) for f in self.frames]
        frozen_frames2 = [replace(f, observations=list(f.observations)) for f in self.frames]

        r1 = self.pipeline.run_sequence(
            sequence_id="test", frames=frozen_frames1,
            temporal_variant=TemporalVariant.NAIVE_FRAMEWISE,
            branch_id=BRANCH_DUOGRAPH3D,
        )
        r2 = self.pipeline.run_sequence(
            sequence_id="test", frames=frozen_frames2,
            temporal_variant=TemporalVariant.NAIVE_FRAMEWISE,
            branch_id=BRANCH_DUOGRAPH3D,
        )

        res1, log1 = r1
        res2, log2 = r2

        # Memory node count
        self.assertEqual(len(res1.memory_nodes), len(res2.memory_nodes),
                        "Memory node count differs between runs")
        # Decision sequence
        self.assertEqual(len(res1.decisions), len(res2.decisions),
                        "Decision count differs between runs")
        for i, (d1, d2) in enumerate(zip(res1.decisions, res2.decisions)):
            self.assertEqual(d1.action, d2.action, f"Decision {i} action differs")
            self.assertEqual(d1.object_id, d2.object_id, f"Decision {i} object_id differs")
            self.assertEqual(d1.hypothesis_id, d2.hypothesis_id, f"Decision {i} hypothesis_id differs")

        # Event log ordering
        log1_types = [r.event_type for r in log1.records]
        log2_types = [r.event_type for r in log2.records]
        self.assertEqual(log1_types, log2_types, "Event type sequence differs between runs")

        # Node details
        for key in sorted(res1.memory_nodes):
            n1 = res1.memory_nodes[key]
            n2 = res2.memory_nodes[key]
            self.assertEqual(n1.status, n2.status, f"Node {key} status differs")
            self.assertEqual(n1.birth_step, n2.birth_step, f"Node {key} birth_step differs")
            self.assertEqual(n1.detection_count, n2.detection_count, f"Node {key} detection_count differs")
