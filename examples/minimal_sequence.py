from duograph3d import DuoGraph3DPipeline, FrameInput, Observation, TemporalVariant

frames = [
    FrameInput(frame_id="f1", observations=[Observation(observation_id="o1", descriptor="chair", geometry_key="g-chair", repair_group_id="chair")]),
    FrameInput(frame_id="f2", observations=[]),
    FrameInput(frame_id="f3", observations=[Observation(observation_id="o2", descriptor="chair", geometry_key="g-chair", repair_group_id="chair")]),
]

pipeline = DuoGraph3DPipeline()
result, logger = pipeline.run_sequence(sequence_id="demo-seq", frames=frames, temporal_variant=TemporalVariant.DEVA_STYLE)
print("memory nodes:", sorted(result.memory_nodes))
print("events:", len(logger.records))
print("reentries:", logger.count("reentry_commit"))
