# Phase 1 Real Observation Cases

日期：2026-04-23

## Purpose
Document the first real-observation qualitative evidence used to validate Phase 1.

## Case A — Replica / office0 / DEVA output observations

- Observation source: `real_deva_output_json`
- Remote report path: `/home/nebula/xxy/duograph3d_phase1_validation/replica/bounded_slice_replica_office0.json`
- Frames with observations: `6/6`
- Memory nodes after DuoGraph3D full run: `1`
- Event count: `24`

### Representative event trace
- `current_hypothesis_emit` step=1 track=`office0:deva-track:14802278`
- `birth_commit` step=1 object=`obj-1`
- `association_commit` step=2 object=`obj-1` score=`2.5008`
- `association_commit` step=3 object=`obj-1` score=`2.5954`
- `association_commit` step=4 object=`obj-1` score=`2.5196`

### Interpretation
This is the first verified non-synthetic Replica path in the current DuoGraph3D execution lane. The observation stream is derived from executed DEVA JSON outputs rather than the prior template generator.

## Case B — ScanNet / scene0568_00 / online monitor observations

- Observation source: `real_scannet_online_monitor_json`
- Remote report path: `/home/nebula/xxy/duograph3d_phase1_validation/scannet/bounded_slice_scannet_scene0568_00.json`
- Frames with observations: `5/6`
- Memory nodes after DuoGraph3D full run: `119`
- Event count: `408`
- Known issue: missing label mesh artifact `scene0568_00_vh_clean_2.labels.ply`

### Representative event trace
- `current_hypothesis_emit` step=2 track=`scene0568_00:track:21`
- `current_hypothesis_emit` step=2 track=`scene0568_00:track:23`
- `current_hypothesis_emit` step=2 track=`scene0568_00:track:31`
- `current_hypothesis_emit` step=2 track=`scene0568_00:track:33`
- `current_hypothesis_emit` step=2 track=`scene0568_00:track:34`
- `current_hypothesis_emit` step=2 track=`scene0568_00:track:35`

### Interpretation
This is the first verified non-synthetic ScanNet path in the current execution lane. The observation stream is built from a real online monitor JSON rather than the template-based pose heuristic path.

## Phase 1 nonempty real-scene summary

The following scenes produced nonempty real-observation runs during Phase 1 validation:

- Replica: `office0`, `office2`, `office3`
- ScanNet: `scene0568_00`, `scene0568_01`, `scene0568_02`

Total: **6 scenes with nonempty real-observation evidence**
